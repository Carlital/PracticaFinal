import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.core import security

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


@dataclass
class User:
    nombre: str
    email: str
    password_hash: str
    rol_id: int
    estado: str = "activo"
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str) -> None:
        self.password_hash = security.generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return security.verify_password(password, self.password_hash)

    def validar_datos(self) -> None:
        if not self.nombre or not self.email:
            raise ValueError("Nombre y email son obligatorios.")
        if not self.email_valida(self.email):
            raise ValueError("Email no tiene un formato válido.")
        if not self.password_hash:
            raise ValueError("La contraseña es obligatoria.")

    @staticmethod
    def email_valida(email: str) -> bool:
        return bool(EMAIL_REGEX.match(email))

    @staticmethod
    def password_valida(password: str) -> bool:
        return bool(PASSWORD_REGEX.match(password))
