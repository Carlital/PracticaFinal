from datetime import datetime, timezone
from typing import Optional, Tuple

from app.core import security
from app.models.session import Session
from app.models.user import User
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository, session_repo: SessionRepository):
        self.user_repo = user_repo
        self.session_repo = session_repo

    def registrar_usuario(self, nombre: str, email: str, password: str, rol_id: int) -> User:
        if not nombre or not email or not password:
            raise ValueError("Todos los campos son obligatorios.")
        if not User.email_valida(email):
            raise ValueError("Email no es válido.")
        if not User.password_valida(password):
            raise ValueError("La contraseña debe tener mínimo 8 caracteres, una letra y un número.")
        existente = self.user_repo.find_by_email(email)
        if existente:
            raise ValueError("El email ya está registrado.")
        user = User(nombre=nombre, email=email, password_hash="", rol_id=rol_id)
        user.set_password(password)
        user.validar_datos()
        return self.user_repo.create(user)

    def autenticar(self, email: str, password: str) -> Tuple[User, Session]:
        user = self.user_repo.find_by_email(email)
        if not user or not user.check_password(password):
            raise ValueError("Credenciales inválidas.")
        if user.estado != "activo":
            raise ValueError("Usuario inactivo.")
        self.session_repo.delete_expired()
        token = security.generate_token()
        expires_at = security.token_expiration(60)
        session = Session(user_id=user.id, token=token, expires_at=expires_at)
        session = self.session_repo.create(session)
        return user, session

    def cerrar_sesion(self, token: str) -> None:
        if token:
            self.session_repo.delete(token)

    def obtener_usuario_actual(self, token: str) -> Optional[User]:
        if not token:
            return None
        session = self.session_repo.find_by_token(token)
        if not session or session.expires_at <= datetime.now(timezone.utc):
            return None
        return self.user_repo.find_by_id(session.user_id)
