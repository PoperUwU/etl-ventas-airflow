# ETL de ventas diarias con Airflow

Laboratorio de los módulos 6 y 7: archivos CSV de ventas -> validación -> PostgreSQL, orquestado con Airflow 3.3.2 y con pruebas automáticas en GitHub Actions.

El DAG `etl_ventas_diarias` tiene cinco tareas encadenadas: `extraer` -> `transformar` -> `validar_calidad` -> `cargar` -> `actualizar_resumen`. Se dispara a mano y recibe el parámetro `fecha` (por ejemplo `2026-10-05`), que decide qué archivo `data/entrada/ventas_<fecha>.csv` se procesa.

## Cómo levantarlo

Requisitos: Git, Python 3 y Docker Desktop abierto (con el motor en marcha).

```
git clone https://github.com/PoperUwU/etl-ventas-airflow.git
cd etl-ventas-airflow
python preparar_entorno.py
docker compose build airflow-init
docker compose up airflow-init
docker compose up -d --wait
```

1. `preparar_entorno.py` crea el archivo `.env` con las claves (no se sube a Git).
2. Se construye solo `airflow-init` porque los cuatro servicios de Airflow comparten la misma imagen; si se construyen en paralelo con `docker compose build`, Docker puede fallar con `image ... already exists`.
3. Airflow queda en http://localhost:8080 (usuario `airflow`, contraseña `airflow`).
4. Para correr una fecha: activar el DAG, pulsar **Trigger** y escribir la fecha en el campo `fecha`.

Para revisar la base después de una corrida (en cmd de Windows):

```
docker compose exec -T datapath-db psql -U dp_user_pg -d datapath_pg < sql/verificacion.sql
```

Para detener todo conservando los datos: `docker compose down`. Con `docker compose down -v` también se borran las bases.

## Cómo correr las pruebas

Dentro del contenedor, con el entorno ya levantado:

```
docker compose exec airflow-scheduler pytest
```

Son 51 pruebas (46 de las reglas de validación y 5 de integridad del DAG). También corren solas en GitHub Actions en cada push a `main` y en cada pull request hacia `main` (ver `.github/workflows/ci.yml`).

## Respuestas

1. **¿Por qué falló la corrida del 7 de octubre? ¿Qué habría quedado en la base si no existiera `validar_calidad`?**
   El archivo original trae los precios de las tiendas Centro y Sur con coma decimal (`"45,50"`), y las reglas solo aceptan punto, así que esas 22 filas se rechazaron como `precio_invalido`. Sumadas a una cantidad escrita como `dos` y a la región `Oeste`, se rechazaron 24 de 41 filas (58,5 %), muy por encima del 20 % permitido, y `validar_calidad` detuvo la corrida antes de `cargar`. Sin esa tarea, `cargar` habría guardado las 17 ventas válidas, que son todas de Norte, y el resumen del 7 de octubre habría mostrado solo esa región: la base habría quedado con un día incompleto que parece normal y nadie notaría hasta que los totales no cuadren.

2. **¿Qué hace que repetir una fecha no duplique ventas? ¿Qué pasaría si `cargar` solo hiciera `INSERT`?**
   `cargar` hace, dentro de una sola transacción, un `DELETE` de todo lo de esa fecha y luego los `INSERT`; así, repetir la fecha reemplaza lo que había en vez de sumarlo, y si algo falla a la mitad se deshace todo y la fecha queda como estaba. `actualizar_resumen` también borra y recalcula solo esa fecha. Con solo `INSERT`, la segunda corrida del mismo día chocaría con la clave primaria de `id_venta` y fallaría, y sin esa clave las ventas quedarían duplicadas y los totales inflados; además no se podría corregir un día ya cargado.

3. **¿Por qué las pruebas del CI pueden correr sin PostgreSQL ni el scheduler? Nombra una cosa que esas pruebas no comprueban.**
   Porque las reglas viven en `reglas.py`, que no importa Airflow ni toca la base: son funciones que reciben filas de texto y devuelven resultados, así que se prueban con Python y pytest. Las pruebas de integridad solo cargan el archivo del DAG y revisan su estructura (tareas, orden, reintentos) sin ejecutarlo. Lo que no comprueban es la carga real en PostgreSQL: por ejemplo, que `cargar` sea de verdad atómica e idempotente, o que las restricciones de las tablas (claves primarias, `CHECK`) funcionen como se espera.

4. **¿Por qué tiene sentido que `validar_calidad` no reintente y que `extraer` sí?**
   Si el archivo viene mal, volver a leerlo da exactamente el mismo resultado: el error no es pasajero, así que reintentar solo retrasa el aviso y hace perder tiempo; lo que hace falta es que una persona corrija el archivo y vuelva a disparar la fecha. En cambio, `extraer` puede fallar por algo momentáneo (el archivo todavía se está copiando, el disco ocupado), y un segundo intento pasados unos segundos puede resolverlo sin que nadie intervenga.

## Pull request

Pull request de la parte 5: https://github.com/PoperUwU/etl-ventas-airflow/pull/1

La rama `feature/precio-cero` cambió la validación del precio de `> 0` a `>= 0`. El CI quedó en rojo porque fallaron `test_precio_invalido[0.00]` y `test_precio_invalido[0.004]`; después se revirtió el cambio en la misma rama, el CI pasó a verde y se hizo el merge.

## Evidencias

En la carpeta `evidencias/`:

- `corridas.png`: lista de corridas del DAG (cinco corridas de la parte 4, una de ellas fallida a propósito).
- `verificacion.txt`: salida de `sql/verificacion.sql` (126 ventas, 9 filas en el resumen).
- `actions.png`: pestaña Actions con ejecuciones en rojo y en verde.