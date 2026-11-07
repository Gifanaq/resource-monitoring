from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from src.application.services.monitoring import MonitoringService
from src.domain.entities.tls import TlsResult
from src.presentation.api.schemas.service import ServiceStatusOut

router = APIRouter(tags=["services"])


def get_monitoring(request: Request) -> MonitoringService:
    return cast("MonitoringService", request.app.state.monitoring)


@router.get("/services")
async def list_services(
    monitoring: Annotated[MonitoringService, Depends(get_monitoring)],
) -> list[ServiceStatusOut]:
    return [
        ServiceStatusOut(
            id=service.id,
            name=service.name,
            url=service.url,
            status=status.level,
            changed_at=status.changed_at,
            last_checked_at=status.last_checked_at,
            status_code=result.status_code if result else None,
            response_time_ms=result.response_time_ms if result else None,
            error=result.error if result else None,
            tls=result.tls if result else TlsResult(),
        )
        for service, status, result in await monitoring.list_statuses()
    ]
