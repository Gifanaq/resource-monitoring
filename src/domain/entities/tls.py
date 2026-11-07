from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TlsState(StrEnum):
    NOT_CHECKED = "NOT_CHECKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    VALID = "VALID"
    EXPIRING = "EXPIRING"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class TlsResult:
    state: TlsState = TlsState.NOT_CHECKED
    checked_at: datetime | None = None
    expires_at: datetime | None = None
    error: str | None = None
