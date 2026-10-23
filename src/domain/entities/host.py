from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Host:
    id: int
    name: str
    exporter_url: str


@dataclass(frozen=True, slots=True)
class MetricSample:
    host_id: int
    name: str
    value: float
    collected_at: datetime
