from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import DatabaseSettings


def create_engine(database: DatabaseSettings) -> AsyncEngine:
    url = URL.create(
        "postgresql+psycopg",
        username=database.postgres_user,
        password=database.postgres_password.get_secret_value(),
        host=database.postgres_host,
        port=database.postgres_port,
        database=database.postgres_db,
    )
    return create_async_engine(url, pool_pre_ping=True, hide_parameters=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
