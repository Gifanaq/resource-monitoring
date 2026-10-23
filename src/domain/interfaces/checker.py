from typing import Protocol

from src.domain.entities.service import CheckResult, Service


class Checker(Protocol):
    async def check(self, service: Service) -> CheckResult: ...
