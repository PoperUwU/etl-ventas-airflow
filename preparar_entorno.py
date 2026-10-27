"""Crea las carpetas que necesita Docker Compose y el archivo .env.

Se puede ejecutar varias veces: no pisa valores que ya existan en el .env.
Si copiaste .env.example como .env, completa las claves que quedaron vacías.
"""

import base64
import os
import secrets
from pathlib import Path

raiz = Path(__file__).resolve().parent
for nombre in ("logs", "config", "plugins"):
    (raiz / nombre).mkdir(exist_ok=True)

por_defecto = {
    "COMPOSE_PROJECT_NAME": "datapath-lab-ventas",
    "AIRFLOW_UID": str(os.getuid()) if hasattr(os, "getuid") else "50000",
    "AIRFLOW_PORT": "8080",
    "AIRFLOW_ADMIN_USER": "airflow",
    "AIRFLOW_ADMIN_PASSWORD": "airflow",
    "AIRFLOW_FERNET_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    "AIRFLOW_JWT_SECRET": secrets.token_urlsafe(48),
}

archivo_env = raiz / ".env"
lineas = archivo_env.read_text().splitlines() if archivo_env.exists() else []
presentes = set()
for i, linea in enumerate(lineas):
    if "=" not in linea or linea.lstrip().startswith("#"):
        continue
    clave, valor = (parte.strip() for parte in linea.split("=", 1))
    presentes.add(clave)
    if not valor and clave in por_defecto:
        lineas[i] = f"{clave}={por_defecto[clave]}"

lineas += [f"{clave}={valor}" for clave, valor in por_defecto.items() if clave not in presentes]
archivo_env.write_text("\n".join(lineas) + "\n")
archivo_env.chmod(0o600)

print("Listo. Las claves quedaron en .env (no se muestran aquí).")
