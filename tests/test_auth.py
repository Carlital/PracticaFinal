import unittest
from datetime import datetime, timedelta, timezone

from app.core import security
from app.models.session import Session
from app.models.user import User
from app.services.auth_service import AuthService

class FakeUserRepo:
    def __init__(self):
        self.users = {}
        self.counter = 1

    def create(self, user: User) -> User:
        user.id = self.counter
        self.counter += 1
        self.users[user.email] = user
        return user

    def find_by_email(self, email: str):
        return self.users.get(email)

    def find_by_id(self, user_id: int):
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None

    def update(self, user: User):
        self.users[user.email] = user


class FakeSessionRepo:
    def __init__(self):
        self.sessions = {}

    def create(self, session: Session):
        session.id = len(self.sessions) + 1
        self.sessions[session.token] = session
        return session

    def find_by_token(self, token: str):
        return self.sessions.get(token)

    def delete(self, token: str):
        self.sessions.pop(token, None)

    def delete_expired(self):
        now = datetime.now(timezone.utc)
        for token, session in list(self.sessions.items()):
            if session.expires_at <= now:
                self.sessions.pop(token)


class AuthServiceTest(unittest.TestCase):
    def setUp(self):
        self.user_repo = FakeUserRepo()
        self.session_repo = FakeSessionRepo()
        self.service = AuthService(self.user_repo, self.session_repo)

    def test_registro_correcto(self):
        user = self.service.registrar_usuario("Ana", "ana@example.com", "Password1", 2)
        self.assertIsNotNone(user.id)
        self.assertTrue(self.user_repo.find_by_email("ana@example.com").check_password("Password1"))

    def test_registro_email_repetido(self):
        self.service.registrar_usuario("Ana", "ana@example.com", "Password1", 2)
        with self.assertRaises(ValueError):
            self.service.registrar_usuario("Ana2", "ana@example.com", "Password1", 2)

    def test_login_correcto(self):
        self.service.registrar_usuario("Ana", "ana@example.com", "Password1", 2)
        user, session = self.service.autenticar("ana@example.com", "Password1")
        self.assertEqual(user.email, "ana@example.com")
        self.assertIn(session.token, self.session_repo.sessions)

    def test_login_incorrecto(self):
        self.service.registrar_usuario("Ana", "ana@example.com", "Password1", 2)
        with self.assertRaises(ValueError):
            self.service.autenticar("ana@example.com", "WrongPass1")

    def test_validacion_email(self):
        self.assertFalse(User.email_valida("mal_correo"))
        self.assertTrue(User.email_valida("bien@example.com"))

    def test_validacion_password(self):
        self.assertFalse(User.password_valida("short"))
        self.assertFalse(User.password_valida("nonumbersssss"))
        self.assertTrue(User.password_valida("Password1"))


if __name__ == "__main__":
    unittest.main()
