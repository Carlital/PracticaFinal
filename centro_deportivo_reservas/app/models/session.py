from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Session:
    user_id: int
    token: str
    expires_at: datetime
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at
