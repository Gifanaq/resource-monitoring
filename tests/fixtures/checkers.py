from datetime import UTC, datetime

from src.domain.entities.service import Service
from src.domain.entities.tls import TlsResult, TlsState


class StaticTlsChecker:
    async def check(self, _service: Service) -> TlsResult:
        return TlsResult(TlsState.VALID, datetime.now(UTC))
