from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class StatusLevel(StrEnum):
    UNKNOWN = "UNKNOWN"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass(frozen=True, slots=True)
class Service:
    id: int
    name: str
    url: str
    expected_status: int = 200
    timeout_sec: float = 10.0
    slow_response_ms: int = 2000
    failure_threshold: int = 3
    recovery_threshold: int = 2


@dataclass(frozen=True, slots=True)
class CheckResult:
    service_id: int
    checked_at: datetime
    success: bool
    status_code: int | None = None
    response_time_ms: int | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    service_id: int
    level: StatusLevel = StatusLevel.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    changed_at: datetime | None = None
