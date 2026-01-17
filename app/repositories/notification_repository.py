"""Repository for managing notifications in the database"""
import psycopg2
from typing import Optional, List
from datetime import datetime
from app.core.config import Settings
from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _get_connection(self):
        """Create a new database connection"""
        return psycopg2.connect(
            host=self.settings.db_host,
            port=self.settings.db_port,
            dbname=self.settings.db_name,
            user=self.settings.db_user,
            password=self.settings.db_password,
        )

    def create(self, notification: Notification) -> Notification:
        """Create a new notification record"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notifications (user_id, tipo, asunto, contenido, estado, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, sent_at
                    """,
                    (
                        notification.user_id,
                        notification.tipo,
                        notification.asunto,
                        notification.contenido,
                        notification.estado,
                        notification.created_at,
                    ),
                )
                notification_id, sent_at = cur.fetchone()
                notification.id = notification_id
                notification.sent_at = sent_at
                conn.commit()
                return notification
        finally:
            conn.close()

    def update_status(
        self,
        notification_id: int,
        estado: str,
        sent_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update notification status after sending attempt"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notifications
                    SET estado = %s, sent_at = %s, error_message = %s
                    WHERE id = %s
                    """,
                    (estado, sent_at, error_message, notification_id),
                )
                conn.commit()
        finally:
            conn.close()

    def get_by_user(self, user_id: int) -> List[Notification]:
        """Get all notifications for a specific user"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, tipo, asunto, contenido, estado, sent_at, error_message, created_at
                    FROM notifications
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
                return [
                    Notification(
                        id=row[0],
                        user_id=row[1],
                        tipo=row[2],
                        asunto=row[3],
                        contenido=row[4],
                        estado=row[5],
                        sent_at=row[6],
                        error_message=row[7],
                        created_at=row[8],
                    )
                    for row in rows
                ]
        finally:
            conn.close()

    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        """Get a specific notification by ID"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, tipo, asunto, contenido, estado, sent_at, error_message, created_at
                    FROM notifications
                    WHERE id = %s
                    """,
                    (notification_id,),
                )
                row = cur.fetchone()
                if row:
                    return Notification(
                        id=row[0],
                        user_id=row[1],
                        tipo=row[2],
                        asunto=row[3],
                        contenido=row[4],
                        estado=row[5],
                        sent_at=row[6],
                        error_message=row[7],
                        created_at=row[8],
                    )
                return None
        finally:
            conn.close()
