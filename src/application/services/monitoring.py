import asyncio

from src.application.services.status_calculator import next_status
from src.domain.entities.service import Service, ServiceStatus
from src.domain.interfaces.checker import Checker
from src.domain.interfaces.service_repository import ServiceRepository


class MonitoringService:
    def __init__(self, repository: ServiceRepository, checker: Checker) -> None:
        self._repository = repository
        self._checker = checker

    async def check_service(self, service: Service) -> ServiceStatus:
        result = await self._checker.check(service)
        await self._repository.add_result(result)
        current = await self._repository.get_status(service.id)
        status = next_status(service, current, result)
        await self._repository.save_status(status)
        return status

    async def check_all(self) -> list[ServiceStatus]:
        services = await self._repository.list_services()
        return list(await asyncio.gather(*map(self.check_service, services)))

    async def list_statuses(self) -> list[tuple[Service, ServiceStatus]]:
        services = await self._repository.list_services()
        return [(s, await self._repository.get_status(s.id)) for s in services]
