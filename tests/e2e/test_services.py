import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.application.services.monitoring import MonitoringService
from src.domain.entities.service import CheckResult, Service
from src.domain.entities.tls import TlsResult, TlsState
from src.infrastructure.adapters.memory_repository import InMemoryServiceRepository
from src.main import create_app
from tests.fixtures.checkers import StaticTlsChecker

CHECKED_AT = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
SERVICE = Service(1, "demo", "https://example.org")


class StaticChecker:
    async def check(self, service: Service) -> CheckResult:
        return CheckResult(
            service.id,
            CHECKED_AT,
            success=False,
            status_code=503,
            response_time_ms=120,
        )


def test_services_returns_status_and_last_http_result() -> None:
    repository = InMemoryServiceRepository([SERVICE])
    monitoring = MonitoringService(repository, StaticChecker(), StaticTlsChecker())
    asyncio.run(monitoring.check_service(SERVICE))
    app = create_app()
    app.state.monitoring = monitoring

    response = TestClient(app).get("/services")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "demo"
    assert body[0]["status"] == "YELLOW"
    assert datetime.fromisoformat(body[0]["last_checked_at"]) == CHECKED_AT
    assert body[0]["status_code"] == 503
    assert body[0]["response_time_ms"] == 120
    assert body[0]["error"] is None
    assert body[0]["tls"]["state"] == "VALID"
    assert body[0]["tls"]["checked_at"] is not None


def test_services_reports_unknown_before_first_check() -> None:
    repository = InMemoryServiceRepository([SERVICE])
    app = create_app()
    app.state.monitoring = MonitoringService(
        repository, StaticChecker(), StaticTlsChecker()
    )

    response = TestClient(app).get("/services")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "UNKNOWN"
    assert response.json()[0]["last_checked_at"] is None
    assert response.json()[0]["status_code"] is None
    assert response.json()[0]["response_time_ms"] is None
    assert response.json()[0]["error"] is None
    assert response.json()[0]["tls"] == {
        "state": "NOT_CHECKED",
        "checked_at": None,
        "expires_at": None,
        "error": None,
    }


def test_services_exposes_tls_error_without_replacing_http_fields() -> None:
    class FailedTlsChecker:
        async def check(self, _service: Service) -> TlsResult:
            return TlsResult(TlsState.ERROR, CHECKED_AT, error="TimeoutError")

    repository = InMemoryServiceRepository([SERVICE])
    monitoring = MonitoringService(repository, StaticChecker(), FailedTlsChecker())
    asyncio.run(monitoring.check_service(SERVICE))
    app = create_app()
    app.state.monitoring = monitoring
    body = TestClient(app).get("/services").json()[0]
    assert body["status"] == "YELLOW"
    assert body["status_code"] == 503
    assert body["response_time_ms"] == 120
    assert body["error"] is None
    assert body["tls"]["state"] == "ERROR"
    assert body["tls"]["expires_at"] is None
    assert body["tls"]["error"] == "TimeoutError"
