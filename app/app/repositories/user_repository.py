from typing import Optional

from app.core.db import get_connection
from app.core.config import Settings
from app.models.user import User


class UserRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create(self, user: User) -> User:
        query = """
        INSERT INTO users (nombre, email, password_hash, rol_id, estado)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, created_at;
        """
        with get_connection(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (user.nombre, user.email, user.password_hash, user.rol_id, user.estado),
                )
                row = cur.fetchone()
                user.id = row["id"]
                user.created_at = row["created_at"]
        return user

    def find_by_email(self, email: str) -> Optional[User]:
        query = """
        SELECT id, nombre, email, password_hash, rol_id, estado, created_at
        FROM users WHERE email = %s;
        """
        with get_connection(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (email,))
                row = cur.fetchone()
                if not row:
                    return None
                return User(
                    id=row["id"],
                    nombre=row["nombre"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    rol_id=row["rol_id"],
                    estado=row["estado"],
                    created_at=row["created_at"],
                )

    def find_by_id(self, user_id: int) -> Optional[User]:
        query = """
        SELECT id, nombre, email, password_hash, rol_id, estado, created_at
        FROM users WHERE id = %s;
        """
        with get_connection(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return User(
                    id=row["id"],
                    nombre=row["nombre"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    rol_id=row["rol_id"],
                    estado=row["estado"],
                    created_at=row["created_at"],
                )

    def update(self, user: User) -> None:
        query = """
        UPDATE users SET nombre=%s, email=%s, password_hash=%s, rol_id=%s, estado=%s
        WHERE id=%s;
        """
        with get_connection(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        user.nombre,
                        user.email,
                        user.password_hash,
                        user.rol_id,
                        user.estado,
                        user.id,
                    ),
                )
