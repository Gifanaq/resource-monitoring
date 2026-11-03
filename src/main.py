import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI

from src.application.services.monitoring import MonitoringService
from src.application.services.scheduler import run_periodically
from src.core.config import settings
from src.domain.entities.service import Service
from src.infrastructure.adapters.http_checker import HttpChecker
from src.infrastructure.adapters.memory_repository import InMemoryServiceRepository
from src.presentation.api.routes import health, services


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        repository = InMemoryServiceRepository(
            Service(id=index, name=item.name, url=item.url)
            for index, item in enumerate(settings.services, start=1)
        )
        app.state.monitoring = MonitoringService(repository, HttpChecker(client))
        task = asyncio.create_task(
            run_periodically(
                app.state.monitoring.check_all, settings.check_interval_sec
            )
        )
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(services.router)
    return app


app = create_app()
