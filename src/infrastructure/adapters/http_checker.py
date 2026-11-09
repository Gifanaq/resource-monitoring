import asyncio
import time
from datetime import UTC, datetime

import httpx

from src.domain.entities.service import CheckResult, Service

RETRY_DELAYS_SEC = (5, 10, 15)


class HttpChecker:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def check(self, service: Service) -> CheckResult:
        last_error: str | None = None
        checked_at = datetime.now(UTC)
        for attempt in range(len(RETRY_DELAYS_SEC) + 1):
            if attempt:
                await asyncio.sleep(RETRY_DELAYS_SEC[attempt - 1])
            checked_at = datetime.now(UTC)
            started = time.perf_counter()
            try:
                response = await self._client.get(
                    service.url,
                    timeout=service.timeout_sec,
                    follow_redirects=service.follow_redirects,
                )
            except httpx.RequestError as exc:
                last_error = type(exc).__name__
                continue
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            return CheckResult(
                service.id,
                checked_at,
                success=response.status_code == service.expected_status,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
            )
        return CheckResult(
            service.id,
            checked_at,
            success=False,
            error=last_error,
        )
