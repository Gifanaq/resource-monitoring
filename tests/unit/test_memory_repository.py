import asyncio
from datetime import UTC, datetime

from src.domain.entities.service import CheckResult, Service, ServiceStatus, StatusLevel
from src.domain.entities.tls import TlsResult, TlsState
from src.infrastructure.adapters.memory_repository import InMemoryServiceRepository


def test_list_statuses_is_empty_without_services() -> None:
    assert asyncio.run(InMemoryServiceRepository([]).list_statuses()) == []


def test_list_statuses_preserves_order_defaults_and_latest_results() -> None:
    services = [
        Service(2, "checked", "https://example.org"),
        Service(1, "new", "http://example.org"),
    ]
    repository = InMemoryServiceRepository(services)
    checked_at = datetime(2026, 11, 9, tzinfo=UTC)
    status = ServiceStatus(2, StatusLevel.YELLOW, last_checked_at=checked_at)
    first = CheckResult(2, checked_at, success=True, status_code=200)
    latest = CheckResult(
        2,
        checked_at,
        success=False,
        status_code=503,
        response_time_ms=42,
        tls=TlsResult(TlsState.ERROR, checked_at, error="TimeoutError"),
    )

    async def run():
        await repository.add_result(first)
        await repository.add_result(latest)
        await repository.save_status(status)
        return await repository.list_statuses()

    assert asyncio.run(run()) == [
        (services[0], status, latest),
        (services[1], ServiceStatus(1), None),
    ]
