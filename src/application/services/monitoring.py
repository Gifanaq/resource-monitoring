import asyncio
import logging
from datetime import UTC, datetime

from src.application.services.status_calculator import next_status
from src.domain.entities.service import CheckResult, Service, ServiceStatus
from src.domain.interfaces.checker import Checker
from src.domain.interfaces.service_repository import ServiceRepository

logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, repository: ServiceRepository, checker: Checker) -> None:
        self._repository = repository
        self._checker = checker

    async def check_service(self, service: Service) -> ServiceStatus:
        try:
            result = await self._checker.check(service)
        except Exception as exc:
            logger.exception("Check failed for service %s", service.id)
            result = CheckResult(
                service.id,
                datetime.now(UTC),
                success=False,
                error=type(exc).__name__,
            )
        await self._repository.add_result(result)
        current = await self._repository.get_status(service.id)
        status = next_status(service, current, result)
        await self._repository.save_status(status)
        logger.info(
            "Checked service %s: success=%s status=%s error=%s",
            service.id,
            result.success,
            status.level,
            result.error,
        )
        return status

    async def check_all(self) -> list[ServiceStatus]:
        services = await self._repository.list_services()
        results = await asyncio.gather(
            *(self.check_service(service) for service in services),
            return_exceptions=True,
        )
        statuses = []
        for service, result in zip(services, results, strict=True):
            if isinstance(result, BaseException):
                logger.error(
                    "Failed to save check for service %s",
                    service.id,
                    exc_info=(type(result), result, result.__traceback__),
                )
            else:
                statuses.append(result)
        return statuses

    async def list_statuses(self) -> list[tuple[Service, ServiceStatus]]:
        services = await self._repository.list_services()
        return [(s, await self._repository.get_status(s.id)) for s in services]
