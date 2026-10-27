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
    raise NotImplementedError("Completa validar_fila")


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
    raise NotImplementedError("Completa separar_ventas")


def revisar_calidad(total_leidas, total_rechazadas, umbral=UMBRAL_RECHAZO):
    """Devuelve la tasa de rechazo (rechazadas / leídas).

    Lanza ValueError si el archivo no trae filas o si la tasa supera el umbral.
    """
    raise NotImplementedError("Completa revisar_calidad")
