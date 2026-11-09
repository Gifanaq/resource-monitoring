from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from src.domain.entities.tls import TlsResult


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
    follow_redirects: bool = True
    timeout_sec: float = 10.0
    slow_response_ms: int = 2000
    failure_threshold: int = 3
    recovery_threshold: int = 2
    tls_warn_before_days: int = 14

    def __post_init__(self) -> None:
        if self.failure_threshold < 1 or self.recovery_threshold < 1:
            raise ValueError("status thresholds must be positive")
        if self.tls_warn_before_days < 1:
            raise ValueError("TLS warning threshold must be positive")


@dataclass(frozen=True, slots=True)
class CheckResult:
    service_id: int
    checked_at: datetime
    success: bool
    status_code: int | None = None
    response_time_ms: int | None = None
    error: str | None = None
    tls: TlsResult = field(default_factory=TlsResult)


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    service_id: int
    level: StatusLevel = StatusLevel.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    changed_at: datetime | None = None
    last_checked_at: datetime | None = None
