"""Reglas de limpieza y validación de los archivos diarios de ventas.

Este módulo no importa nada de Airflow a propósito: así las reglas se pueden
probar con pytest en segundos, sin levantar Docker ni una base de datos.

Las reglas completas (y su orden) están en el enunciado, sección "Reglas de
validación". leer_csv ya viene resuelta; completa las otras tres funciones.
"""

import csv
import json
import re

COLUMNAS = ["id_venta", "fecha", "region", "producto", "cantidad", "precio_unitario"]
REGIONES = {"norte", "sur", "centro"}

# Si se rechaza más del 20 % de un archivo no se carga nada de ese día
UMBRAL_RECHAZO = 0.20


def leer_csv(ruta):
    """Lee el archivo y devuelve una lista de diccionarios con los valores en texto.

    Si una línea trae columnas de más, lo que sobra queda en la clave "_sobrantes".
    Si trae de menos, las columnas que faltan quedan en None.
    """
    # utf-8-sig tolera el BOM que agrega Excel al guardar como "CSV UTF-8".
    # strict=True hace fallar el archivo si una comilla queda sin cerrar; sin eso,
    # el lector se come en silencio las líneas que siguen.
    with open(ruta, newline="", encoding="utf-8-sig") as archivo:
        lector = csv.DictReader(archivo, restkey="_sobrantes", strict=True)
        encabezado = lector.fieldnames or []
        faltantes = [col for col in COLUMNAS if col not in encabezado]
        if faltantes:
            raise ValueError(f"Al archivo le faltan columnas: {', '.join(faltantes)}")
        sobrantes = [col for col in encabezado if col not in COLUMNAS]
        if sobrantes:
            raise ValueError(f"Columnas que no se esperan: {', '.join(sobrantes)}")
        return [dict(fila) for fila in lector]


def _texto(fila, columna):
    return (fila.get(columna) or "").strip()


def validar_fila(fila, fecha):
    """Aplica las reglas a una fila del CSV.

    Devuelve (registro, None) si la fila es válida o (None, motivo) si no lo es.
    Revisa en este orden y reporta solo el primer problema:
    columnas_incorrectas, id_invalido, fecha_distinta, region_invalida,
    producto_vacio, cantidad_invalida, precio_invalido.
    (id_duplicado no se revisa aquí sino en separar_ventas.)

    El registro válido tiene las claves: id_venta (int), fecha (str),
    region ("Norte"), producto ("Mouse"), cantidad (int),
    precio_unitario (float redondeado a 2 decimales) y total
    (cantidad * precio_unitario, redondeado a 2 decimales).

    Pista: int() y float() aceptan cosas como "+3", "1_000", "1e3" o "nan".
    Con re.fullmatch puedes exigir que el texto tenga solo dígitos.
    """
    # Regla 1: la línea debe traer exactamente las seis columnas
    if "_sobrantes" in fila or any(fila.get(col) is None for col in COLUMNAS):
        return None, "columnas_incorrectas"

    # Regla 2: id_venta solo con dígitos y mayor que 0
    id_texto = _texto(fila, "id_venta")
    if not re.fullmatch(r"[0-9]+", id_texto) or int(id_texto) <= 0:
        return None, "id_invalido"

    # (La regla 3, id_duplicado, se revisa en separar_ventas)

    # Regla 4: la fecha debe ser la que se está procesando
    if _texto(fila, "fecha") != fecha:
        return None, "fecha_distinta"

    # Regla 5: la región, en minúsculas, debe ser norte, sur o centro
    region = _texto(fila, "region").lower()
    if region not in REGIONES:
        return None, "region_invalida"

    # Regla 6: el producto no puede estar vacío
    producto = _texto(fila, "producto")
    if producto == "":
        return None, "producto_vacio"

    # Regla 7: cantidad solo con dígitos y mayor que 0
    cantidad_texto = _texto(fila, "cantidad")
    if not re.fullmatch(r"[0-9]+", cantidad_texto) or int(cantidad_texto) <= 0:
        return None, "cantidad_invalida"
    cantidad = int(cantidad_texto)

    # Regla 8: precio con dígitos y punto decimal opcional; mayor que 0 al redondear
    precio_texto = _texto(fila, "precio_unitario")
    if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", precio_texto):
        return None, "precio_invalido"
    precio = round(float(precio_texto), 2)
    if precio < 0:
        return None, "precio_invalido"

    registro = {
        "id_venta": int(id_texto),
        "fecha": fecha,
        "region": region.capitalize(),
        "producto": producto.capitalize(),
        "cantidad": cantidad,
        "precio_unitario": precio,
        "total": round(cantidad * precio, 2),
    }
    return registro, None


def separar_ventas(filas, fecha):
    """Separa las filas en (limpias, rechazadas).

    - Usa validar_fila para cada fila.
    - Si un id_venta ya apareció antes en el archivo, la fila se rechaza como
      id_duplicado, aunque la primera aparición haya sido rechazada por otro
      motivo. Los ids se comparan como número: "070001" y "70001" son el mismo.
      Es la regla 3: si la fila ya falló por columnas_incorrectas o id_invalido,
      se queda con ese motivo; si falló por cualquier otra regla, gana id_duplicado.
    - Cada rechazada es un dict con: linea (la primera fila de datos es la
      línea 2 porque la 1 es el encabezado), id_venta (texto o None), motivo y
      fila_original (la fila como JSON, usa json.dumps(fila, ensure_ascii=False)).
    """
    limpias = []
    rechazadas = []
    ids_vistos = set()

    for linea, fila in enumerate(filas, start=2):
        registro, motivo = validar_fila(fila, fecha)

        # Las reglas 1 y 2 van antes que la 3: si fallaron, se conserva ese motivo
        # y el id de esa fila no cuenta como "ya visto".
        if motivo not in ("columnas_incorrectas", "id_invalido"):
            id_numero = int(_texto(fila, "id_venta"))
            if id_numero in ids_vistos:
                registro, motivo = None, "id_duplicado"
            else:
                ids_vistos.add(id_numero)

        if motivo is None:
            limpias.append(registro)
        else:
            id_original = fila.get("id_venta")
            rechazadas.append({
                "linea": linea,
                "id_venta": id_original.strip() if id_original is not None else None,
                "motivo": motivo,
                "fila_original": json.dumps(fila, ensure_ascii=False),
            })

    return limpias, rechazadas


def revisar_calidad(total_leidas, total_rechazadas, umbral=UMBRAL_RECHAZO):
    """Devuelve la tasa de rechazo (rechazadas / leídas).

    Lanza ValueError si el archivo no trae filas o si la tasa supera el umbral.
    """
    if total_leidas == 0:
        raise ValueError("El archivo no trae filas")
    tasa = total_rechazadas / total_leidas
    if tasa > umbral:
        raise ValueError(f"Se rechazó el {tasa:.1%} de las filas, más del límite permitido")
    return tasa