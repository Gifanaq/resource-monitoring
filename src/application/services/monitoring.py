import asyncio
from dataclasses import replace
from datetime import UTC, datetime

from src.application.services.status_calculator import next_status
from src.core.logging import logger
from src.domain.entities.service import CheckResult, Service, ServiceStatus
from src.domain.entities.tls import TlsResult, TlsState
from src.domain.interfaces.checker import Checker
from src.domain.interfaces.service_repository import ServiceRepository
from src.domain.interfaces.tls_checker import TlsChecker


class MonitoringService:
    def __init__(
        self, repository: ServiceRepository, checker: Checker, tls_checker: TlsChecker
    ) -> None:
        self._repository = repository
        self._checker = checker
        self._tls_checker = tls_checker

    async def _check_http(self, service: Service) -> CheckResult:
        try:
            return await self._checker.check(service)
        except Exception as exc:
            logger.exception("Check failed for service %s", service.id)
            return CheckResult(
                service.id,
                datetime.now(UTC),
                success=False,
                error=type(exc).__name__,
            )

    async def _check_tls(self, service: Service) -> TlsResult:
        try:
            return await self._tls_checker.check(service)
        except Exception as exc:
            logger.exception("TLS check failed for service %s", service.id)
            return TlsResult(
                TlsState.ERROR, datetime.now(UTC), error=type(exc).__name__
            )

    async def check_service(self, service: Service) -> ServiceStatus:
        async with asyncio.TaskGroup() as group:
            http_task = group.create_task(self._check_http(service))
            tls_task = group.create_task(self._check_tls(service))
        result = replace(http_task.result(), tls=tls_task.result())
        await self._repository.add_result(result)
        current = await self._repository.get_status(service.id)
        status = next_status(service, current, result)
        await self._repository.save_status(status)
        logger.info(
            "Checked service %s: success=%s status=%s error=%s tls=%s tls_error=%s",
            service.id,
            result.success,
            status.level,
            result.error,
            result.tls.state,
            result.tls.error,
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

    async def list_statuses(
        self,
    ) -> list[tuple[Service, ServiceStatus, CheckResult | None]]:
        services = await self._repository.list_services()
        return [
            (
                service,
                await self._repository.get_status(service.id),
                await self._repository.get_last_result(service.id),
            )
            for service in services
        ]
