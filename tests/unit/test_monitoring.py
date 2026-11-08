import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from src.application.services.monitoring import MonitoringService
from src.domain.entities.service import CheckResult, Service, ServiceStatus, StatusLevel
from src.domain.interfaces.service_repository import ServiceRepository
from src.infrastructure.adapters.memory_repository import InMemoryServiceRepository
from tests.fixtures.checkers import StaticTlsChecker


class IntermittentChecker:
    async def check(self, service: Service) -> CheckResult:
        if service.id == 1:
            raise ValueError("invalid target")
        return CheckResult(
            service.id,
            datetime.now(UTC),
            success=True,
            status_code=200,
        )


def test_one_checker_exception_does_not_interrupt_other_services() -> None:
    services = [Service(1, "bad", "bad-url"), Service(2, "ok", "https://tpu.ru")]
    repository = InMemoryServiceRepository(services)
    monitoring = MonitoringService(
        repository, IntermittentChecker(), StaticTlsChecker()
    )

    statuses = asyncio.run(monitoring.check_all())

    assert [status.level for status in statuses] == [
        StatusLevel.YELLOW,
        StatusLevel.GREEN,
    ]
    assert all(status.last_checked_at is not None for status in statuses)


def test_list_statuses_uses_one_repository_call() -> None:
    service = Service(1, "demo", "https://example.org")
    expected = [(service, ServiceStatus(service.id), None)]
    repository = AsyncMock(spec=ServiceRepository)
    repository.list_statuses.return_value = expected
    monitoring = MonitoringService(
        repository, IntermittentChecker(), StaticTlsChecker()
    )

    assert asyncio.run(monitoring.list_statuses()) == expected
    repository.list_statuses.assert_awaited_once_with()
    repository.list_services.assert_not_awaited()
    repository.get_status.assert_not_awaited()
    repository.get_last_result.assert_not_awaited()
