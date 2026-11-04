from datetime import datetime

from pydantic import BaseModel

from src.domain.entities.service import StatusLevel


class ServiceStatusOut(BaseModel):
    id: int
    name: str
    url: str
    status: StatusLevel
    changed_at: datetime | None
    last_checked_at: datetime | None
