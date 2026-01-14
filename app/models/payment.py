from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Payment:
    user_id: int
    reservation_id: int
    amount: float
    currency: str = "USD"
    estado: str = "pendiente"
    payment_method_id: Optional[int] = None
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Transaction:
    payment_id: int
    gateway_ref: Optional[str]
    status: str
    details: dict = field(default_factory=dict)
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
