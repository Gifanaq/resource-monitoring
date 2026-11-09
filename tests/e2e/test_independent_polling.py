import asyncio
from datetime import UTC, datetime
from threading import Event

import pytest
from fastapi.testclient import TestClient

from src.core.config import MonitoredService, settings
from src.domain.entities.service import CheckResult, Service, ServiceStatus
from src.infrastructure.adapters.http_checker import HttpChecker
from src.infrastructure.adapters.memory_repository import InMemoryServiceRepository
from src.infrastructure.adapters.tls_checker import TlsCertificateChecker
from src.main import create_app
from tests.fixtures.checkers import StaticTlsChecker


def test_slow_service_does_not_block_other_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_saved = Event()
    original_save_status = InMemoryServiceRepository.save_status

    async def save_status(
        repository: InMemoryServiceRepository,
        status: ServiceStatus,
    ) -> None:
        await original_save_status(repository, status)
        if status.service_id == 2:
            second_saved.set()

    async def check(_checker: HttpChecker, service: Service) -> CheckResult:
        if service.id == 1:
            await asyncio.Event().wait()
        return CheckResult(
            service.id,
            datetime.now(UTC),
            success=True,
            status_code=200,
        )

    monkeypatch.setattr(
        settings,
        "services",
        [
            MonitoredService(name="slow", url="https://slow.example.org"),
            MonitoredService(name="fast", url="https://fast.example.org"),
        ],
    )
    monkeypatch.setattr(settings, "check_interval_sec", 3600)
    monkeypatch.setattr(HttpChecker, "check", check)
    monkeypatch.setattr(TlsCertificateChecker, "check", StaticTlsChecker.check)
    monkeypatch.setattr(InMemoryServiceRepository, "save_status", save_status)

    with TestClient(create_app()) as client:
        assert second_saved.wait(timeout=5)
        response = client.get("/services")

    assert response.status_code == 200
    assert [item["status"] for item in response.json()] == ["UNKNOWN", "GREEN"]
