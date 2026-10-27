"""Pruebas de integridad del DAG, como en el lab de CI/CD del módulo 7.

Ojo: aquel lab usaba Airflow 2.9. En Airflow 3 DagBag vive en
airflow.dag_processing.dagbag, ya no acepta include_examples y los ciclos se
revisan con dag.check_cycle().
No necesitan PostgreSQL ni el scheduler: solo cargan los archivos de dags/.
"""

from pathlib import Path

import pytest
from airflow.dag_processing.dagbag import DagBag

CARPETA_DAGS = Path(__file__).resolve().parents[1] / "dags"
DAG_ID = "etl_ventas_diarias"


@pytest.fixture(scope="module")
def dagbag():
    return DagBag(dag_folder=str(CARPETA_DAGS))


def test_los_dags_cargan_sin_errores(dagbag):
    assert dagbag.import_errors == {}, dagbag.import_errors
    assert DAG_ID in dagbag.dags


def test_no_hay_ciclos(dagbag):
    for dag in dagbag.dags.values():
        dag.check_cycle()


def test_configuracion_del_dag(dagbag):
    dag = dagbag.dags[DAG_ID]
    assert dag.schedule is None
    assert dag.catchup is False
    assert dag.max_active_runs == 1
    assert "laboratorio" in dag.tags
    assert dag.default_args["retries"] >= 1
    assert "fecha" in dag.params


def test_orden_de_las_tareas(dagbag):
    dag = dagbag.dags[DAG_ID]
    orden = ["extraer", "transformar", "validar_calidad", "cargar", "actualizar_resumen"]
    assert sorted(dag.task_ids) == sorted(orden)
    for actual, siguiente in zip(orden, orden[1:]):
        assert dag.get_task(actual).downstream_task_ids == {siguiente}


def test_validar_calidad_no_reintenta(dagbag):
    # si el archivo viene mal, reintentar solo hace perder tiempo
    tarea = dagbag.dags[DAG_ID].get_task("validar_calidad")
    assert tarea.retries == 0
