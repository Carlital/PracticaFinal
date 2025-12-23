import os
import psycopg2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(BASE_DIR, "scripts", "schema.sql")
ENV_PATH = os.path.join(BASE_DIR, ".env")


def load_env(path=ENV_PATH):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def run_migration():
    load_env()
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5434"),
        dbname=os.environ.get("DB_NAME", "centro_deportivo"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "12345"),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
            sql = schema_file.read()
            cur.execute(sql)
    conn.close()
    print("Migración inicial ejecutada correctamente.")


if __name__ == "__main__":
    run_migration()
