-- Consultas para revisar el resultado de cada corrida.
-- Se ejecutan con:
--   docker compose exec -T datapath-db psql -U dp_user_pg -d datapath_pg < sql/verificacion.sql

-- 1. Ventas válidas por fecha
SELECT fecha, COUNT(*) AS ventas, COUNT(DISTINCT id_venta) AS ids_distintos, SUM(total) AS monto
FROM ventas_limpias
GROUP BY fecha
ORDER BY fecha;

-- 2. Rechazos por fecha y motivo
SELECT fecha_archivo, motivo, COUNT(*) AS filas
FROM ventas_rechazadas
GROUP BY fecha_archivo, motivo
ORDER BY fecha_archivo, motivo;

-- 3. Resumen por región
SELECT *
FROM resumen_ventas_diario
ORDER BY fecha, region;
