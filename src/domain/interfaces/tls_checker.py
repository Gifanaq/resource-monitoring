from typing import Protocol

from src.domain.entities.service import Service
from src.domain.entities.tls import TlsResult


class TlsChecker(Protocol):
    async def check(self, service: Service) -> TlsResult: ...
