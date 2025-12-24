from typing import List, Dict, Any
from app.core.config import Settings
from app.core.db import get_connection

class AdminRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def get_all_users(self) -> List[Dict[str, Any]]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.nombre, u.email, r.nombre_rol as rol, u.estado 
                FROM users u
                JOIN roles r ON u.rol_id = r.id
                ORDER BY u.id
            """)
            rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]