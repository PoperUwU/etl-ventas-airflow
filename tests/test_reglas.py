import pytest

from ventas.reglas import leer_csv, revisar_calidad, separar_ventas, validar_fila

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


# --- Pruebas de ejemplo de la plantilla -------------------------------------

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


# --- Normalización de la fila válida ----------------------------------------

def test_region_y_producto_se_normalizan():
    registro, motivo = validar_fila(fila(region="  SUR ", producto=" AURICULARES"), FECHA)
    assert motivo is None
    assert registro["region"] == "Sur"
    assert registro["producto"] == "Auriculares"


def test_registro_valido_trae_los_tipos_correctos():
    registro, _ = validar_fila(fila(id_venta="070001", precio_unitario="699"), FECHA)
    assert registro["id_venta"] == 70001
    assert registro["cantidad"] == 3
    assert registro["precio_unitario"] == 699.0
    assert registro["total"] == 2097.0


# --- Un caso por cada motivo de rechazo -------------------------------------

@pytest.mark.parametrize("id_venta", ["", "abc", "0", "-5", "+7", "12.5", "1e3"])
def test_id_invalido(id_venta):
    assert validar_fila(fila(id_venta=id_venta), FECHA) == (None, "id_invalido")


def test_fecha_distinta():
    assert validar_fila(fila(fecha="2026-10-04"), FECHA) == (None, "fecha_distinta")


@pytest.mark.parametrize("producto", ["", "   "])
def test_producto_vacio(producto):
    assert validar_fila(fila(producto=producto), FECHA) == (None, "producto_vacio")


@pytest.mark.parametrize("cantidad", ["", "0", "-2", "dos", "1.5", "+3"])
def test_cantidad_invalida(cantidad):
    assert validar_fila(fila(cantidad=cantidad), FECHA) == (None, "cantidad_invalida")


@pytest.mark.parametrize("precio", ["", "0.00", "0.004", "45,50", "1e3", "5.", "-3", "abc"])
def test_precio_invalido(precio):
    assert validar_fila(fila(precio_unitario=precio), FECHA) == (None, "precio_invalido")


@pytest.mark.parametrize("precio", ["699", "45.50", "0.01", "0.005"])
def test_precio_valido(precio):
    registro, motivo = validar_fila(fila(precio_unitario=precio), FECHA)
    assert motivo is None


# --- Columnas de más: 45,50 SIN comillas ------------------------------------

def test_linea_con_columnas_de_mas(tmp_path):
    ruta = tmp_path / "ventas.csv"
    ruta.write_text(
        "id_venta,fecha,region,producto,cantidad,precio_unitario\n"
        "70001,2026-10-05,norte,Mouse,3,45,50\n",
        encoding="utf-8",
    )
    filas = leer_csv(ruta)
    assert validar_fila(filas[0], FECHA) == (None, "columnas_incorrectas")


def test_linea_con_columnas_de_menos(tmp_path):
    ruta = tmp_path / "ventas.csv"
    ruta.write_text(
        "id_venta,fecha,region,producto,cantidad,precio_unitario\n"
        "70001,2026-10-05,norte,Mouse\n",
        encoding="utf-8",
    )
    filas = leer_csv(ruta)
    assert validar_fila(filas[0], FECHA) == (None, "columnas_incorrectas")


# --- Orden de las reglas ----------------------------------------------------

def test_solo_se_reporta_el_primer_problema():
    # región inválida, cantidad inválida y precio inválido a la vez
    malo = fila(region="Lima", cantidad="0", precio_unitario="0.00")
    assert validar_fila(malo, FECHA) == (None, "region_invalida")


def test_id_invalido_gana_a_los_demas_problemas():
    malo = fila(id_venta="abc", region="Lima")
    assert validar_fila(malo, FECHA) == (None, "id_invalido")


# --- separar_ventas ---------------------------------------------------------

def test_duplicado_cuya_primera_aparicion_fue_rechazada():
    filas = [fila(region="Lima"), fila()]
    limpias, rechazadas = separar_ventas(filas, FECHA)
    assert limpias == []
    assert [r["motivo"] for r in rechazadas] == ["region_invalida", "id_duplicado"]


def test_ids_se_comparan_como_numero():
    limpias, rechazadas = separar_ventas([fila(id_venta="70001"), fila(id_venta="070001")], FECHA)
    assert len(limpias) == 1
    assert rechazadas[0]["motivo"] == "id_duplicado"


def test_id_invalido_no_se_convierte_en_duplicado():
    filas = [fila(id_venta="abc"), fila(id_venta="abc")]
    limpias, rechazadas = separar_ventas(filas, FECHA)
    assert [r["motivo"] for r in rechazadas] == ["id_invalido", "id_invalido"]


def test_separar_ventas_no_pierde_filas():
    filas = [fila(id_venta="1"), fila(id_venta="2", region="Lima"), fila(id_venta="1"), fila(id_venta="x")]
    limpias, rechazadas = separar_ventas(filas, FECHA)
    assert len(limpias) + len(rechazadas) == len(filas)


def test_rechazada_trae_linea_id_motivo_y_fila_original():
    limpias, rechazadas = separar_ventas([fila(), fila(id_venta="2", region="Lima")], FECHA)
    rechazada = rechazadas[0]
    assert rechazada["linea"] == 3  # la línea 1 es el encabezado
    assert rechazada["id_venta"] == "2"
    assert rechazada["motivo"] == "region_invalida"
    assert '"region": "Lima"' in rechazada["fila_original"]


# --- revisar_calidad --------------------------------------------------------

def test_calidad_acepta_la_tasa_exactamente_igual_al_umbral():
    assert revisar_calidad(10, 2) == pytest.approx(0.2)


def test_calidad_sin_rechazos():
    assert revisar_calidad(10, 0) == 0


def test_calidad_falla_con_archivo_vacio():
    with pytest.raises(ValueError):
        revisar_calidad(0, 0)