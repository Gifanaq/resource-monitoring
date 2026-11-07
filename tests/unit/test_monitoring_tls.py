import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from src.application.services.monitoring import MonitoringService
from src.domain.entities.service import CheckResult, Service, StatusLevel
from src.domain.entities.tls import TlsResult, TlsState
from src.infrastructure.adapters.memory_repository import InMemoryServiceRepository
from tests.fixtures.checkers import StaticTlsChecker

SERVICE = Service(1, "demo", "https://example.org")


class GoodHttpChecker:
    async def check(self, service):
        return CheckResult(
            service.id,
            datetime.now(UTC),
            success=True,
            status_code=200,
            response_time_ms=42,
        )


def test_tls_failure_preserves_http_status_and_clears_old_expiry():
    class ChangingTlsChecker:
        calls = 0

        async def check(self, _service):
            self.calls += 1
            if self.calls == 1:
                return TlsResult(
                    TlsState.VALID,
                    datetime.now(UTC),
                    datetime.now(UTC) + timedelta(days=30),
                )
            raise OSError("unreachable")

    async def run():
        repository = InMemoryServiceRepository([SERVICE])
        tls = ChangingTlsChecker()
        monitoring = MonitoringService(repository, GoodHttpChecker(), tls)
        await monitoring.check_service(SERVICE)
        assert (await repository.get_last_result(1)).tls.expires_at is not None
        status = await monitoring.check_service(SERVICE)
        result = await repository.get_last_result(1)
        assert status.level is StatusLevel.GREEN
        assert result.success
        assert result.response_time_ms == 42
        assert result.error is None
        assert result.tls.state is TlsState.ERROR
        assert result.tls.expires_at is None
        assert tls.calls == 2

    asyncio.run(run())


def test_http_and_tls_are_parallel_and_cancelled_together():
    async def run():
        http_started, tls_started = asyncio.Event(), asyncio.Event()
        http_cancelled, tls_cancelled = asyncio.Event(), asyncio.Event()

        class Http:
            async def check(self, _service):
                http_started.set()
                try:
                    await tls_started.wait()
                    await asyncio.Event().wait()
                finally:
                    http_cancelled.set()

        class Tls:
            async def check(self, _service):
                tls_started.set()
                try:
                    await http_started.wait()
                    await asyncio.Event().wait()
                finally:
                    tls_cancelled.set()

        repository = InMemoryServiceRepository([SERVICE])
        task = asyncio.create_task(
            MonitoringService(repository, Http(), Tls()).check_service(SERVICE)
        )
        async with asyncio.timeout(1):
            await http_started.wait()
            await tls_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert http_cancelled.is_set()
        assert tls_cancelled.is_set()
        assert await repository.get_last_result(1) is None

    asyncio.run(run())


def test_slow_tls_does_not_block_other_service():
    async def run():
        class SlowTls(StaticTlsChecker):
            async def check(self, service):
                if service.id == 1:
                    await asyncio.Event().wait()
                return await super().check(service)

        other = Service(2, "fast", "https://fast.example.org")
        repository = InMemoryServiceRepository([SERVICE, other])
        monitoring = MonitoringService(repository, GoodHttpChecker(), SlowTls())
        slow = asyncio.create_task(monitoring.check_service(SERVICE))
        try:
            async with asyncio.timeout(1):
                status = await monitoring.check_service(other)
            assert status.level is StatusLevel.GREEN
            assert (await repository.get_status(1)).level is StatusLevel.UNKNOWN
        finally:
            slow.cancel()
            with pytest.raises(asyncio.CancelledError):
                await slow

    asyncio.run(run())
