import asyncio
import socket
import ssl
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.entities.service import Service
from src.domain.entities.tls import TlsState
from src.infrastructure.adapters import tls_checker

NOW = datetime(2026, 11, 8, tzinfo=UTC)
SERVICE = Service(1, "demo", "https://example.org/path", timeout_sec=0.05)


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None) -> datetime:
        return NOW.astimezone(tz)


@pytest.fixture
def connection(monkeypatch):
    monkeypatch.setattr(tls_checker, "datetime", FrozenDatetime)
    certificate = Mock(spec=ssl.SSLObject)
    writer = Mock(spec=asyncio.StreamWriter)
    writer.get_extra_info.return_value = certificate
    writer.wait_closed = AsyncMock()
    writer.transport = Mock()
    connect = AsyncMock(return_value=(Mock(), writer))
    monkeypatch.setattr(tls_checker.asyncio, "open_connection", connect)
    return certificate, writer, connect


@pytest.mark.parametrize(
    ("seconds", "threshold", "expected"),
    [
        (30 * 86400, 14, TlsState.VALID),
        (14 * 86400, 14, TlsState.EXPIRING),
        (14 * 86400 - 1, 14, TlsState.EXPIRING),
        (14 * 86400 + 1, 14, TlsState.VALID),
        (20 * 86400, 21, TlsState.EXPIRING),
    ],
)
def test_expiry_boundary_and_threshold(connection, seconds, threshold, expected):
    certificate, writer, connect = connection
    expires_at = NOW + timedelta(seconds=seconds)
    certificate.getpeercert.return_value = {
        "notAfter": expires_at.strftime("%b %d %H:%M:%S %Y GMT")
    }
    context = ssl.create_default_context()
    result = asyncio.run(
        tls_checker.TlsCertificateChecker(context).check(
            replace(SERVICE, tls_warn_before_days=threshold)
        )
    )
    assert result.state is expected
    assert result.checked_at == NOW
    assert result.expires_at == expires_at
    assert result.error is None
    connect.assert_awaited_once_with(
        "example.org",
        443,
        ssl=context,
        server_hostname="example.org",
        ssl_handshake_timeout=0.05,
        ssl_shutdown_timeout=0.05,
    )
    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()
    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED


def test_http_skips_tls_even_when_redirects_enabled(connection):
    _, _, connect = connection
    result = asyncio.run(
        tls_checker.TlsCertificateChecker(ssl.create_default_context()).check(
            replace(SERVICE, url="http://example.org")
        )
    )
    assert result.state is TlsState.NOT_APPLICABLE
    assert result.checked_at == NOW
    assert result.expires_at is None
    connect.assert_not_called()


def test_explicit_https_port(connection):
    certificate, _, connect = connection
    certificate.getpeercert.return_value = {"notAfter": "Dec 30 00:00:00 2026 GMT"}
    asyncio.run(
        tls_checker.TlsCertificateChecker(ssl.create_default_context()).check(
            replace(SERVICE, url="https://example.org:8443/path")
        )
    )
    assert connect.call_args.args == ("example.org", 8443)
    assert connect.call_args.kwargs["server_hostname"] == "example.org"


@pytest.mark.parametrize(
    "error",
    [
        ssl.SSLCertVerificationError(),
        socket.gaierror(),
        ConnectionRefusedError(),
        TimeoutError(),
    ],
)
def test_connection_errors_are_separate_results(connection, error):
    _, _, connect = connection
    connect.side_effect = error
    result = asyncio.run(
        tls_checker.TlsCertificateChecker(ssl.create_default_context()).check(SERVICE)
    )
    assert result.state is TlsState.ERROR
    assert result.error == type(error).__name__
    assert result.expires_at is None
    connect.assert_awaited_once()


def test_missing_expiry_closes_connection(connection):
    certificate, writer, _ = connection
    certificate.getpeercert.return_value = {}
    result = asyncio.run(
        tls_checker.TlsCertificateChecker(ssl.create_default_context()).check(SERVICE)
    )
    assert result.state is TlsState.ERROR
    assert result.expires_at is None
    writer.wait_closed.assert_awaited_once()


def test_connect_timeout_is_bounded(connection):
    _, _, connect = connection

    async def blocked(*_args: object, **_kwargs: object):
        await asyncio.Event().wait()

    connect.side_effect = blocked
    result = asyncio.run(
        tls_checker.TlsCertificateChecker(ssl.create_default_context()).check(SERVICE)
    )
    assert result.state is TlsState.ERROR
    assert result.error == "TimeoutError"


def test_close_timeout_aborts_transport_without_losing_certificate(connection):
    certificate, writer, _ = connection
    certificate.getpeercert.return_value = {"notAfter": "Dec 30 00:00:00 2026 GMT"}

    async def blocked():
        await asyncio.Event().wait()

    writer.wait_closed.side_effect = blocked
    result = asyncio.run(
        tls_checker.TlsCertificateChecker(ssl.create_default_context()).check(SERVICE)
    )
    assert result.state is TlsState.VALID
    writer.transport.abort.assert_called_once()


def test_cancellation_during_close_aborts_transport(connection):
    certificate, writer, _ = connection
    certificate.getpeercert.return_value = {"notAfter": "Dec 30 00:00:00 2026 GMT"}

    async def run():
        started = asyncio.Event()

        async def blocked():
            started.set()
            await asyncio.Event().wait()

        writer.wait_closed.side_effect = blocked
        task = asyncio.create_task(
            tls_checker.TlsCertificateChecker(ssl.create_default_context()).check(
                SERVICE
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    writer.close.assert_called_once()
    writer.transport.abort.assert_called_once()


def test_cancellation_during_handshake_propagates(connection):
    _, _, connect = connection

    async def run():
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def blocked(*_args: object, **_kwargs: object):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        connect.side_effect = blocked
        task = asyncio.create_task(
            tls_checker.TlsCertificateChecker(ssl.create_default_context()).check(
                SERVICE
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancelled.is_set()

    asyncio.run(run())
