import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import Settings


def get_connection(settings: Settings):
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        cursor_factory=RealDictCursor,
        options='-c timezone=utc'
    )
    conn.autocommit = True  # evitar rollbacks implícitos al cerrar
    return conn
