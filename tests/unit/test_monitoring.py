import asyncio
from datetime import UTC, datetime

from src.application.services.monitoring import MonitoringService
from src.domain.entities.service import CheckResult, Service, StatusLevel
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
