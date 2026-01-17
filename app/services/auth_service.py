from datetime import datetime, timezone
from typing import Optional, Tuple

from app.core import security
from app.models.session import Session
from app.models.user import User
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService


class AuthService:
    def __init__(self, user_repo: UserRepository, session_repo: SessionRepository, notification_service: Optional[NotificationService] = None):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.notification_service = notification_service

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
        created_user = self.user_repo.create(user)
        
        # Send welcome email notification
        if self.notification_service:
            try:
                self.notification_service.send_welcome_email(created_user)
            except Exception as e:
                print(f"[WARNING] Error sending welcome email: {e}")
                # Don't fail registration if email fails
        
        return created_user

    def autenticar(self, email: str, password: str) -> Tuple[User, Session]:
        user = self.user_repo.find_by_email(email)
        if not user or not user.check_password(password):
            raise ValueError("Credenciales inválidas.")
        if user.estado != "activo":
            raise ValueError("Usuario inactivo.")
        self.session_repo.delete_expired()
        token = security.generate_token()
        expires_at = security.token_expiration(60)
        print(f"[DEBUG] autenticar: Creando sesión con expires_at: {expires_at}")
        session = Session(user_id=user.id, token=token, expires_at=expires_at)
        session = self.session_repo.create(session)
        print(f"[DEBUG] autenticar: Sesión creada - expires_at después de guardar: {session.expires_at}")
        return user, session

    def cerrar_sesion(self, token: str) -> None:
        if token:
            self.session_repo.delete(token)

    def obtener_usuario_actual(self, token: str) -> Optional[User]:
        if not token:
            print("[DEBUG] obtener_usuario_actual: No token provided")
            return None
        print(f"[DEBUG] obtener_usuario_actual: Buscando sesión para token: {token}")
        session = self.session_repo.find_by_token(token)
        if not session:
            print("[DEBUG] obtener_usuario_actual: No se encontró sesión para este token")
            return None
        print(f"[DEBUG] obtener_usuario_actual: Sesión encontrada - user_id: {session.user_id}, expires_at: {session.expires_at}")
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        print(f"[DEBUG] obtener_usuario_actual: Comparando expires_at ({expires_at}) con now ({now})")
        if expires_at <= now:
            print("[DEBUG] obtener_usuario_actual: Sesión expirada")
            return None
        user = self.user_repo.find_by_id(session.user_id)
        print(f"[DEBUG] obtener_usuario_actual: Usuario encontrado: {user.email if user else 'None'}")
        return user
