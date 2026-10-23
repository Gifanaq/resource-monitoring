from datetime import UTC, datetime

import httpx

from src.domain.entities.host import Host, MetricSample

METRICS = frozenset(
    {
        "node_boot_time_seconds",
        "node_time_seconds",
        "node_vmstat_oom_kill",
        "node_memory_MemAvailable_bytes",
        "node_memory_MemTotal_bytes",
        "node_load1",
    }
)


class NodeExporterSource:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def collect(self, host: Host) -> list[MetricSample]:
        response = await self._client.get(host.exporter_url)
        response.raise_for_status()
        collected_at = datetime.now(UTC)
        samples = []
        for line in response.text.splitlines():
            name, _, value = line.partition(" ")
            if name in METRICS:
                samples.append(MetricSample(host.id, name, float(value), collected_at))
        return samples
