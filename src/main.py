from fastapi import FastAPI

from src.core.config import settings
from src.presentation.api.routes import health


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health.router)
    return app


app = create_app()
