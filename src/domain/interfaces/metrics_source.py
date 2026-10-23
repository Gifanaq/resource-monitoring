from typing import Protocol

from src.domain.entities.host import Host, MetricSample


class MetricsSource(Protocol):
    async def collect(self, host: Host) -> list[MetricSample]: ...
