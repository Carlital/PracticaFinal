from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass
class Reservation:
    user_id: int
    cancha_id: int
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: str = "confirmada"
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Aquí podríamos agregar lógica de dominio extra si fuera necesario