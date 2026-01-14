"""Script rápido para comprobar la conexión a la BD usando los mismos Settings de la app.
Ejecutar con el mismo intérprete que usarás para la app:
python test_db.py
"""
import sys
from app.core.config import Settings
import psycopg2

s = Settings.from_env()
print(f"Probando conexión a {s.db_host}:{s.db_port} base {s.db_name} como {s.db_user}")
try:
    conn = psycopg2.connect(host=s.db_host, port=s.db_port, dbname=s.db_name, user=s.db_user, password=s.db_password)
    conn.close()
    print("Conexión exitosa ✅")
    sys.exit(0)
except Exception as e:
    print("Fallo de conexión:\n", e)
    sys.exit(1)
