from datetime import datetime

from pydantic import BaseModel

from src.domain.entities.service import StatusLevel
from src.domain.entities.tls import TlsResult


class ServiceStatusOut(BaseModel):
    id: int
    name: str
    url: str
    status: StatusLevel
    changed_at: datetime | None
    last_checked_at: datetime | None
    status_code: int | None
    response_time_ms: int | None
    tls: TlsResult
    error: str | None
