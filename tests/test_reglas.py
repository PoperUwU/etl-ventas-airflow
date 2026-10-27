import pytest

from ventas.reglas import revisar_calidad, separar_ventas, validar_fila

FECHA = "2026-10-05"


def fila(**cambios):
    """Fila válida de ejemplo; pásale solo lo que quieras cambiar."""
    base = {
        "id_venta": "70001",
        "fecha": FECHA,
        "region": "norte",
        "producto": "Mouse",
        "cantidad": "3",
        "precio_unitario": "45.50",
    }
    base.update(cambios)
    return base


# Estas cuatro pruebas son de ejemplo. Van a fallar hasta que completes reglas.py.

def test_fila_valida_calcula_el_total():
    registro, motivo = validar_fila(fila(), FECHA)
    assert motivo is None
    assert registro["total"] == 136.5


def test_region_desconocida_se_rechaza():
    registro, motivo = validar_fila(fila(region="Lima"), FECHA)
    assert registro is None
    assert motivo == "region_invalida"


def test_duplicado_conserva_la_primera_aparicion():
    limpias, rechazadas = separar_ventas([fila(), fila(cantidad="9")], FECHA)
    assert len(limpias) == 1
    assert limpias[0]["cantidad"] == 3
    assert rechazadas[0]["motivo"] == "id_duplicado"


def test_calidad_rechaza_sobre_el_umbral():
    with pytest.raises(ValueError):
        revisar_calidad(10, 3)


# TODO: agrega tus pruebas. Como mínimo deben cubrir:
#   - región y producto normalizados ("  SUR " -> "Sur", " AURICULARES" -> "Auriculares")
#   - cada motivo de rechazo: id_invalido, fecha_distinta, producto_vacio,
#     cantidad_invalida (vacía, 0, negativa, "dos", "1.5") y precio_invalido
#     (vacío, "0.00", "0.004", con coma decimal "45,50", "1e3")
#   - una línea con columnas de más: 45,50 SIN comillas en el CSV
#     (escribe un archivo con tmp_path y léelo con leer_csv)
#   - un duplicado cuya primera aparición fue rechazada por otro motivo
#   - que se reporte solo el primer problema cuando una fila tiene varios
#   - que separar_ventas no pierda filas: limpias + rechazadas == leídas
#   - que revisar_calidad acepte una tasa exactamente igual al umbral
#   - que revisar_calidad falle con un archivo vacío
# Tip: @pytest.mark.parametrize te ahorra repetir la misma prueba muchas veces.
