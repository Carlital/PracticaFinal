import os
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(os.path.dirname(BASE_DIR), ".env")


def load_env(path: str = ENV_PATH) -> None:
    """Load key=value pairs from a .env file into os.environ if not already set."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    secret_key: str
    server_port: int

    @classmethod
    def from_env(cls) -> "Settings":
        load_env()
        return cls(
            db_host=os.environ.get("DB_HOST", "localhost"),
            db_port=int(os.environ.get("DB_PORT", "5434")),
            db_name=os.environ.get("DB_NAME", "centro_deportivo"),
            db_user=os.environ.get("DB_USER", "postgres"),
            db_password=os.environ.get("DB_PASSWORD", "12345"),
            secret_key=os.environ.get("SECRET_KEY", "changeme"),
            server_port=int(os.environ.get("SERVER_PORT", "8000")),
        )
