from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from src.application.services.monitoring import MonitoringService
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
        )
        for service, status in await monitoring.list_statuses()
    ]
