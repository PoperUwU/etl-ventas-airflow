"""ETL diario de ventas: CSV de las tiendas -> validación -> PostgreSQL.

Se dispara a mano con el parámetro `fecha` (AAAA-MM-DD). Cada corrida debe
reemplazar solo los datos de esa fecha, así que repetirla no puede duplicar filas.

El DAG ya importa sin errores, pero cada tarea levanta NotImplementedError
hasta que la completes. El encadenamiento del final ya está armado.
"""

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import Param, dag, get_current_context, task

from ventas.reglas import leer_csv, revisar_calidad, separar_ventas

CARPETA_ENTRADA = Path(os.environ.get("VENTAS_CARPETA_ENTRADA", "/opt/airflow/data/entrada"))
CONEXION = "postgres_datapath"

CREAR_TABLAS = """
CREATE TABLE IF NOT EXISTS ventas_limpias (
    id_venta        INTEGER PRIMARY KEY,
    fecha           DATE NOT NULL,
    region          TEXT NOT NULL,
    producto        TEXT NOT NULL,
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(10, 2) NOT NULL CHECK (precio_unitario > 0),
    total           NUMERIC(12, 2) NOT NULL,
    cargado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ventas_rechazadas (
    fecha_archivo DATE NOT NULL,
    linea         INTEGER NOT NULL,
    id_venta      TEXT,
    motivo        TEXT NOT NULL,
    fila_original TEXT NOT NULL,
    PRIMARY KEY (fecha_archivo, linea)
);
CREATE TABLE IF NOT EXISTS resumen_ventas_diario (
    fecha       DATE NOT NULL,
    region      TEXT NOT NULL,
    num_ventas  INTEGER NOT NULL,
    unidades    INTEGER NOT NULL,
    monto_total NUMERIC(14, 2) NOT NULL,
    PRIMARY KEY (fecha, region)
);
"""


@dag(
    dag_id="etl_ventas_diarias",
    description="Carga diaria de ventas desde CSV a PostgreSQL",
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    params={
        "fecha": Param("2026-10-05", type="string", format="date",
                       description="Fecha del archivo a procesar (AAAA-MM-DD)"),
    },
    default_args={"owner": "equipo-datos", "retries": 1, "retry_delay": timedelta(seconds=15)},
    tags=["laboratorio", "ventas", "etl"],
)
def etl_ventas_diarias():

    @task
    def extraer():
        # 1. Toma la fecha de get_current_context()["params"]["fecha"]
        # 2. Arma la ruta CARPETA_ENTRADA / f"ventas_{fecha}.csv" y falla con un
        #    mensaje claro si el archivo no existe
        # 3. Lee las filas con leer_csv y devuelve {"fecha": ..., "filas": [...]}
        raise NotImplementedError("Completa extraer")

    @task
    def transformar(datos):
        # Usa separar_ventas y devuelve un dict con:
        # fecha, leidas (cuántas filas trajo el archivo), limpias y rechazadas
        raise NotImplementedError("Completa transformar")

    @task
    def validar_calidad(resultado):
        # Llama a revisar_calidad. Si pasa, devuelve el mismo `resultado` para
        # que siga a la carga. ¿Tiene sentido que esta tarea reintente?
        raise NotImplementedError("Completa validar_calidad")

    @task
    def cargar(resultado):
        # Todo en UNA transacción con PostgresHook(postgres_conn_id=CONEXION):
        #   - CREAR_TABLAS
        #   - borrar lo que ya exista de esa fecha en ventas_limpias y ventas_rechazadas
        #   - insertar con parámetros (%s), nunca armando el SQL con f-strings
        #   - comprobar que en la tabla quedó la misma cantidad que transformaste
        # Devuelve {"fecha": ..., "cargadas": n, "rechazadas": m}
        raise NotImplementedError("Completa cargar")

    @task
    def actualizar_resumen(carga):
        # Recalcula resumen_ventas_diario SOLO para la fecha cargada, agrupando
        # ventas_limpias por región: número de ventas, unidades y monto total
        raise NotImplementedError("Completa actualizar_resumen")

    actualizar_resumen(cargar(validar_calidad(transformar(extraer()))))


etl_ventas_diarias()
