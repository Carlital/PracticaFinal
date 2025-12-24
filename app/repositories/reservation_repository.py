from datetime import datetime
from typing import List, Optional
from app.core.config import Settings
from app.core.db import get_connection
from app.models.reservation import Reservation

class ReservationRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create(self, reservation: Reservation) -> Reservation:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reservas (user_id, cancha_id, fecha_inicio, fecha_fin, estado, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (reservation.user_id, reservation.cancha_id, reservation.fecha_inicio, 
                 reservation.fecha_fin, reservation.estado, reservation.created_at)
            )
            new_id = cur.fetchone()['id']
            reservation.id = new_id
        conn.close()
        return reservation

    def find_by_id(self, reservation_id: int) -> Optional[Reservation]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM reservas WHERE id = %s", (reservation_id,))
            row = cur.fetchone()
        conn.close()
        if row:
            return Reservation(**row)
        return None

    def find_detailed_by_id(self, reservation_id: int) -> Optional[dict]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            query = """
                SELECT r.id, u.nombre as usuario, c.nombre as cancha, r.fecha_inicio, r.fecha_fin, r.estado, r.user_id, c.precio_hora
                FROM reservas r
                JOIN users u ON r.user_id = u.id
                JOIN canchas c ON r.cancha_id = c.id
                WHERE r.id = %s
            """
            cur.execute(query, (reservation_id,))
            row = cur.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def update_status(self, reservation_id: int, new_status: str):
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("UPDATE reservas SET estado = %s WHERE id = %s", (new_status, reservation_id))
        conn.close()

    def find_overlapping(self, cancha_id: int, start: datetime, end: datetime) -> List[Reservation]:
        """Busca reservas activas que se solapen con el horario dado."""
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            # Lógica de solapamiento: (StartA < EndB) and (EndA > StartB)
            query = """
                SELECT * FROM reservas 
                WHERE cancha_id = %s 
                AND estado != 'cancelada'
                AND fecha_inicio < %s 
                AND fecha_fin > %s
            """
            cur.execute(query, (cancha_id, end, start))
            rows = cur.fetchall()
        conn.close()
        # Mapeo manual simple ya que el constructor espera argumentos posicionales o kwargs
        return [Reservation(
            id=r['id'], user_id=r['user_id'], cancha_id=r['cancha_id'],
            fecha_inicio=r['fecha_inicio'], fecha_fin=r['fecha_fin'],
            estado=r['estado'], created_at=r['created_at']
        ) for r in rows]

    def find_by_user(self, user_id: int) -> List[dict]:
        """Devuelve reservas con detalles de la cancha para el usuario."""
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            query = """
                SELECT r.id, c.nombre as cancha, r.fecha_inicio, r.fecha_fin, r.estado
                FROM reservas r
                JOIN canchas c ON r.cancha_id = c.id
                WHERE r.user_id = %s
                ORDER BY r.fecha_inicio DESC
            """
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def find_all_detailed(self) -> List[dict]:
        """Devuelve todas las reservas con nombres de usuario y cancha para el admin."""
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            query = """
                SELECT r.id, u.nombre as usuario, c.nombre as cancha, r.fecha_inicio, r.fecha_fin, r.estado
                FROM reservas r
                JOIN users u ON r.user_id = u.id
                JOIN canchas c ON r.cancha_id = c.id
                ORDER BY r.fecha_inicio DESC
            """
            cur.execute(query)
            rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]