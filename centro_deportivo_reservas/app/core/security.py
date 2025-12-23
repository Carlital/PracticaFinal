import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

PASSWORD_ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 260_000
SALT_SIZE = 16


def _pbkdf2_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=32
    )


def generate_password_hash(password: str) -> str:
    salt = os.urandom(SALT_SIZE)
    hash_bytes = _pbkdf2_hash(password, salt)
    return f"{PASSWORD_ALGORITHM}${ITERATIONS}${salt.hex()}${hash_bytes.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_hex, hash_hex = stored_hash.split("$")
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        new_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected_hash)
        )
        return hmac.compare_digest(new_hash, expected_hash)
    except (ValueError, TypeError):
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def token_expiration(minutes: int = 60) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)
