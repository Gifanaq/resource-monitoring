from fastapi import FastAPI

from tpumon.api.v1.routers import health
from tpumon.core.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name)
    app.include_router(health.router)
    return app


app = create_app()
