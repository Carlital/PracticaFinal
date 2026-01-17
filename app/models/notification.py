from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Notification:
    """Modelo de dominio para notificaciones por email"""
    user_id: int
    tipo: str  # 'welcome', 'reservation_confirmation', 'payment_confirmation', 'cancellation'
    asunto: str
    contenido: str
    estado: str = "pendiente"  # 'pendiente', 'enviado', 'fallido'
    id: Optional[int] = None
    sent_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
