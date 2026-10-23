import time
from datetime import UTC, datetime

import httpx

from src.domain.entities.service import CheckResult, Service


class HttpChecker:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def check(self, service: Service) -> CheckResult:
        checked_at = datetime.now(UTC)
        started = time.perf_counter()
        try:
            response = await self._client.get(service.url, timeout=service.timeout_sec)
        except httpx.HTTPError as exc:
            return CheckResult(service.id, checked_at, False, error=type(exc).__name__)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return CheckResult(
            service.id,
            checked_at,
            response.status_code == service.expected_status,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
        )
