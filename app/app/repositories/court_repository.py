from typing import List, Optional
from app.core.config import Settings
from app.core.db import get_connection
from app.models.court import Court

class CourtRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def find_all(self) -> List[Court]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, deporte, precio_hora FROM canchas ORDER BY id")
            rows = cur.fetchall()
        conn.close()
        return [Court(**row) for row in rows]

    def find_by_id(self, court_id: int) -> Optional[Court]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, deporte, precio_hora FROM canchas WHERE id = %s", (court_id,))
            row = cur.fetchone()
        conn.close()
        if row:
            return Court(**row)
        return None

    def create(self, court: Court) -> Court:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO canchas (nombre, deporte, precio_hora) VALUES (%s, %s, %s) RETURNING id",
                (court.nombre, court.deporte, court.precio_hora)
            )
            court.id = cur.fetchone()['id']
        conn.close()
        return court

    def update(self, court: Court):
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE canchas SET nombre = %s, deporte = %s, precio_hora = %s WHERE id = %s",
                (court.nombre, court.deporte, court.precio_hora, court.id)
            )
        conn.close()

    def delete(self, court_id: int):
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM canchas WHERE id = %s", (court_id,))
        conn.close()