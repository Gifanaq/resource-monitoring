import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from psycopg import sql
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import insert, inspect, make_url, select
from sqlalchemy.exc import IntegrityError

from src.core.config import DatabaseSettings
from src.infrastructure.db.models import (
    Base,
    CategoryModel,
    CheckModel,
    CheckResultModel,
    CheckTypeModel,
    HttpCheckSettingsModel,
    ServiceModel,
    ServiceStatusModel,
    StatusLevelModel,
    TlsCheckSettingsModel,
)
from src.infrastructure.db.session import create_engine, create_session_factory


@pytest.fixture
def database():
    address = os.environ.get("TPUMON_TEST_DATABASE_URL")
    if not address:
        pytest.skip("TPUMON_TEST_DATABASE_URL is required for PostgreSQL tests")
    admin_url = make_url(address)
    name = "tpumon_test_" + uuid4().hex
    dsn = admin_url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = admin_url.set(database=name, drivername="postgresql+psycopg")
    engine = create_sync_engine(url)
    try:
        yield url, engine
    finally:
        engine.dispose()
        with psycopg.connect(dsn, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


def migrate(engine, target):
    config = Config("alembic.ini")
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        if target == "base":
            command.downgrade(config, target)
        else:
            command.upgrade(config, target)


@pytest.fixture
def migrated_database(database):
    url, engine = database
    migrate(engine, "head")
    return url, engine


def test_upgrade_matches_metadata_and_downgrade_is_reversible(migrated_database):
    _, engine = migrated_database
    expected = set(Base.metadata.tables)
    assert len(expected) == 9
    assert set(inspect(engine).get_table_names()) == expected | {"alembic_version"}
    with engine.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )
        assert set(connection.scalars(select(CheckTypeModel.code))) == {
            "http",
            "tls",
            "tcp",
        }
        assert set(connection.scalars(select(StatusLevelModel.code))) == {
            "UNKNOWN",
            "GREEN",
            "YELLOW",
            "RED",
        }
    indexes = inspect(engine).get_indexes("check_results")
    index = next(
        item
        for item in indexes
        if item["name"] == "ix_check_results_check_id_checked_at"
    )
    assert index["column_names"] == ["check_id", "checked_at"]
    assert index["column_sorting"]["checked_at"] == ("desc",)
    migrate(engine, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    migrate(engine, "head")
    with engine.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )


def test_async_orm_stores_http_tls_and_status(migrated_database):
    url, _ = migrated_database

    async def run():
        settings = DatabaseSettings(
            _env_file=None,
            postgres_user=url.username,
            postgres_password=url.password or "",
            postgres_db=url.database,
            postgres_host=url.host,
            postgres_port=url.port,
        )
        engine = create_engine(settings)
        factory = create_session_factory(engine)
        now = datetime.now(UTC)
        try:
            async with factory.begin() as session:
                category = CategoryModel(name="TPU")
                session.add(category)
                await session.flush()
                service = ServiceModel(category_id=category.id, name="demo")
                session.add(service)
                await session.flush()
                http = CheckModel(
                    service_id=service.id,
                    check_type_id=1,
                    target="https://example.org",
                    timeout_sec=0.5,
                )
                tls = CheckModel(
                    service_id=service.id, check_type_id=2, target="https://example.org"
                )
                session.add_all([http, tls])
                await session.flush()
                session.add_all(
                    [
                        HttpCheckSettingsModel(
                            check_id=http.id, follow_redirects=False
                        ),
                        TlsCheckSettingsModel(check_id=tls.id),
                        CheckResultModel(
                            check_id=http.id,
                            checked_at=now,
                            success=True,
                            status_code=200,
                            response_time_ms=42,
                        ),
                        CheckResultModel(
                            check_id=tls.id,
                            checked_at=now,
                            success=True,
                            tls_expires_at=now + timedelta(days=30),
                        ),
                        ServiceStatusModel(
                            service_id=service.id,
                            status_level_id=2,
                            last_checked_at=now,
                        ),
                    ]
                )
            async with factory() as session:
                check = await session.get(CheckModel, http.id)
                assert check.timeout_sec == 0.5
                http_settings = await session.get(HttpCheckSettingsModel, http.id)
                assert not http_settings.follow_redirects
                tls_settings = await session.get(TlsCheckSettingsModel, tls.id)
                assert tls_settings.warn_before_days == 14
                result = await session.scalar(
                    select(CheckResultModel).where(CheckResultModel.check_id == tls.id)
                )
                assert result.tls_expires_at == now + timedelta(days=30)
                status = await session.get(ServiceStatusModel, service.id)
                assert status.last_checked_at == now
                assert status.changed_at is None
                assert status.consecutive_failures == 0
        finally:
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "invalid",
    [
        "threshold",
        "timeout",
        "infinite_timeout",
        "foreign_key",
        "unique",
        "http_status",
        "tls_threshold",
        "counter",
    ],
)
def test_database_rejects_invalid_monitoring_data(migrated_database, invalid):
    _, engine = migrated_database
    with engine.begin() as connection:
        category_id = connection.scalar(
            insert(CategoryModel).values(name="TPU").returning(CategoryModel.id)
        )
        service_id = connection.scalar(
            insert(ServiceModel)
            .values(category_id=category_id, name="demo")
            .returning(ServiceModel.id)
        )
        check_id = connection.scalar(
            insert(CheckModel)
            .values(
                service_id=service_id, check_type_id=1, target="https://example.org"
            )
            .returning(CheckModel.id)
        )
    statements = {
        "threshold": insert(ServiceModel).values(
            category_id=category_id, name="bad", failure_threshold=0
        ),
        "timeout": insert(CheckModel).values(
            service_id=service_id, check_type_id=1, target="x", timeout_sec=0
        ),
        "infinite_timeout": insert(CheckModel).values(
            service_id=service_id, check_type_id=1, target="x", timeout_sec=float("inf")
        ),
        "foreign_key": insert(CheckModel).values(
            service_id=service_id, check_type_id=999, target="x"
        ),
        "unique": insert(CategoryModel).values(name="TPU"),
        "http_status": insert(HttpCheckSettingsModel).values(
            check_id=check_id, expected_status=600
        ),
        "tls_threshold": insert(TlsCheckSettingsModel).values(
            check_id=check_id, warn_before_days=0
        ),
        "counter": insert(ServiceStatusModel).values(
            service_id=service_id, status_level_id=1, consecutive_successes=-1
        ),
    }
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(statements[invalid])
