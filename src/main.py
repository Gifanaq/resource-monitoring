import asyncio
import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from functools import partial

import httpx
from fastapi import FastAPI

from src.application.services.monitoring import MonitoringService
from src.application.services.scheduler import run_periodically
from src.core.config import settings
from src.core.logging import setup_logging
from src.domain.entities.service import Service
from src.infrastructure.adapters.http_checker import HttpChecker
from src.infrastructure.adapters.memory_repository import InMemoryServiceRepository
from src.infrastructure.adapters.tls_checker import TlsCertificateChecker
from src.presentation.api.routes import health, services


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        monitored_services = [
            Service(
                id=index,
                name=item.name,
                url=str(item.url),
                expected_status=item.expected_status,
                follow_redirects=item.follow_redirects,
                timeout_sec=item.timeout_sec,
                slow_response_ms=item.slow_response_ms,
                tls_warn_before_days=item.tls_warn_before_days,
            )
            for index, item in enumerate(settings.services, start=1)
        ]
        repository = InMemoryServiceRepository(monitored_services)
        monitoring = MonitoringService(
            repository,
            HttpChecker(client),
            TlsCertificateChecker(ssl.create_default_context()),
        )
        app.state.monitoring = monitoring
        tasks = [
            asyncio.create_task(
                run_periodically(
                    partial(monitoring.check_service, service),
                    settings.check_interval_sec,
                )
            )
            for service in monitored_services
        ]
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with suppress(asyncio.CancelledError):
                    await task


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(services.router)
    return app


app = create_app()
