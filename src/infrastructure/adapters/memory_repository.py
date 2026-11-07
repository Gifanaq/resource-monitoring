from collections import deque
from collections.abc import Iterable

from src.domain.entities.service import CheckResult, Service, ServiceStatus


class InMemoryServiceRepository:
    def __init__(self, services: Iterable[Service]) -> None:
        self._services = {s.id: s for s in services}
        self._statuses: dict[int, ServiceStatus] = {}
        self._results: deque[CheckResult] = deque(maxlen=10_000)
        self._last_results: dict[int, CheckResult] = {}

    async def list_services(self) -> list[Service]:
        return list(self._services.values())

    async def get_status(self, service_id: int) -> ServiceStatus:
        return self._statuses.get(service_id, ServiceStatus(service_id))

    async def save_status(self, status: ServiceStatus) -> None:
        self._statuses[status.service_id] = status

    async def add_result(self, result: CheckResult) -> None:
        self._results.append(result)
        self._last_results[result.service_id] = result

    async def get_last_result(self, service_id: int) -> CheckResult | None:
        return self._last_results.get(service_id)
