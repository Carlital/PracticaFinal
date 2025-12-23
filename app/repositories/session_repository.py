from datetime import datetime, timezone
from typing import Optional

from app.core.db import get_connection
from app.core.config import Settings
from app.models.session import Session


class SessionRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create(self, session: Session) -> Session:
        query = """
        INSERT INTO sessions (user_id, token, expires_at)
        VALUES (%s, %s, %s)
        RETURNING id, created_at;
        """
        with get_connection(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (session.user_id, session.token, session.expires_at))
                row = cur.fetchone()
                session.id = row["id"]
                session.created_at = row["created_at"]
        return session

    def find_by_token(self, token: str) -> Optional[Session]:
        query = """
        SELECT id, user_id, token, expires_at, created_at
        FROM sessions WHERE token = %s;
        """
        with get_connection(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (token,))
                row = cur.fetchone()
                if not row:
                    return None
                return Session(
                    id=row["id"],
                    user_id=row["user_id"],
                    token=row["token"],
                    expires_at=row["expires_at"],
                    created_at=row["created_at"],
                )

    def delete(self, token: str) -> None:
        with get_connection(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE token = %s;", (token,))

    def delete_expired(self) -> None:
        with get_connection(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM sessions WHERE expires_at <= %s;",
                    (datetime.now(timezone.utc),),
                )
