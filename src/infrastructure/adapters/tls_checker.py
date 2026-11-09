import asyncio
import ssl
from datetime import UTC, datetime
from urllib.parse import urlsplit

from src.core.logging import logger
from src.domain.entities.service import Service
from src.domain.entities.tls import TlsResult, TlsState


class TlsCertificateChecker:
    def __init__(self, context: ssl.SSLContext) -> None:
        self._context = context

    async def check(self, service: Service) -> TlsResult:
        checked_at = datetime.now(UTC)
        writer: asyncio.StreamWriter | None = None
        try:
            target = urlsplit(service.url)
            if target.scheme == "http":
                return TlsResult(TlsState.NOT_APPLICABLE, checked_at)
            if target.scheme != "https" or not target.hostname:
                return TlsResult(TlsState.ERROR, checked_at, error="ValueError")
            async with asyncio.timeout(service.timeout_sec):
                _, writer = await asyncio.open_connection(
                    target.hostname,
                    target.port if target.port is not None else 443,
                    ssl=self._context,
                    server_hostname=target.hostname,
                    ssl_handshake_timeout=service.timeout_sec,
                    ssl_shutdown_timeout=service.timeout_sec,
                )
                expires_at = self._expires_at(writer)
            remaining_sec = (expires_at - checked_at).total_seconds()
            state = (
                TlsState.EXPIRING
                if remaining_sec <= service.tls_warn_before_days * 86400
                else TlsState.VALID
            )
            return TlsResult(state, checked_at, expires_at)
        except (OSError, TimeoutError, ValueError, TypeError) as exc:
            return TlsResult(TlsState.ERROR, checked_at, error=type(exc).__name__)
        finally:
            if writer is not None:
                await self._close(writer, service.timeout_sec)

    @staticmethod
    def _expires_at(writer: asyncio.StreamWriter) -> datetime:
        connection = writer.get_extra_info("ssl_object")
        if not isinstance(connection, ssl.SSLObject):
            raise TypeError("TLS connection is unavailable")
        certificate = connection.getpeercert()
        not_after = certificate.get("notAfter") if certificate else None
        if not isinstance(not_after, str):
            raise TypeError("certificate expiry is unavailable")
        return datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), UTC)

    @staticmethod
    async def _close(writer: asyncio.StreamWriter, timeout_sec: float) -> None:
        writer.close()
        try:
            async with asyncio.timeout(timeout_sec):
                await writer.wait_closed()
        except asyncio.CancelledError:
            writer.transport.abort()
            raise
        except (OSError, TimeoutError):
            writer.transport.abort()
            logger.debug("TLS connection close failed", exc_info=True)
