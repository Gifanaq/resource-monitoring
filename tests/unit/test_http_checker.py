import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from src.application.services.monitoring import MonitoringService
from src.domain.entities.service import Service, StatusLevel
from src.infrastructure.adapters import http_checker
from src.infrastructure.adapters.memory_repository import InMemoryServiceRepository
from tests.fixtures.checkers import StaticTlsChecker

SERVICE = Service(1, "demo", "https://example.org")


def test_transport_errors_retry_after_increasing_delays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 4:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, request=request)

    monkeypatch.setattr(http_checker.asyncio, "sleep", record_sleep)

    async def run() -> http_checker.CheckResult:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await http_checker.HttpChecker(client).check(SERVICE)

    result = asyncio.run(run())

    assert attempts == 4
    assert delays == [5, 10, 15]
    assert result.success
    assert result.status_code == 200
    assert result.response_time_ms is not None


def test_exhausted_retries_count_as_one_failed_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    def fail(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("unreachable", request=request)

    monkeypatch.setattr(http_checker.asyncio, "sleep", record_sleep)
    repository = InMemoryServiceRepository([SERVICE])

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
            monitoring = MonitoringService(
                repository,
                http_checker.HttpChecker(client),
                StaticTlsChecker(),
            )
            status = await monitoring.check_service(SERVICE)
            assert status.level is StatusLevel.YELLOW
            assert status.consecutive_failures == 1

    asyncio.run(run())

    assert attempts == 4
    assert delays == [5, 10, 15]
    result = asyncio.run(repository.get_last_result(SERVICE.id))
    assert result is not None
    assert not result.success
    assert result.error == "ConnectError"


def test_http_error_response_is_recorded_without_retry() -> None:
    attempts = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, request=request)

    async def run() -> http_checker.CheckResult:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await http_checker.HttpChecker(client).check(SERVICE)

    result = asyncio.run(run())

    assert attempts == 1
    assert not result.success
    assert result.status_code == 503
    assert result.error is None
    assert result.checked_at <= datetime.now(UTC)


def test_redirect_status_can_be_checked_without_following_it() -> None:
    paths: list[str] = []
    service = Service(
        2,
        "redirect",
        "https://example.org/start",
        expected_status=302,
        follow_redirects=False,
    )

    def respond(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(
            302,
            headers={"location": "/login"},
            request=request,
        )

    async def run() -> http_checker.CheckResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(respond),
            follow_redirects=True,
        ) as client:
            return await http_checker.HttpChecker(client).check(service)

    result = asyncio.run(run())

    assert result.success
    assert result.status_code == 302
    assert paths == ["/start"]


def test_redirect_is_followed_by_default() -> None:
    paths: list[str] = []
    service = Service(2, "redirect", "https://example.org/start")

    def respond(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/start":
            return httpx.Response(
                302,
                headers={"location": "/login"},
                request=request,
            )
        return httpx.Response(200, request=request)

    async def run() -> http_checker.CheckResult:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await http_checker.HttpChecker(client).check(service)

    result = asyncio.run(run())

    assert result.success
    assert result.status_code == 200
    assert paths == ["/start", "/login"]
