from typing import List, Optional
from app.core.config import Settings
from app.core.db import get_connection


class PaymentMethodRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def find_all(self) -> List[dict]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, tipo FROM payment_methods ORDER BY id")
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def find_by_name(self, name: str) -> Optional[dict]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, tipo FROM payment_methods WHERE tipo = %s LIMIT 1", (name,))
            row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
