import secrets

from pydantic import SecretStr
from sqlalchemy import URL

from src.core.config import DatabaseSettings
from src.infrastructure.db.session import create_engine


def test_database_credentials_are_optional_for_demo_and_safely_encoded():
    token = secrets.token_urlsafe(12) + "@:/%"
    settings = DatabaseSettings(
        _env_file=None,
        postgres_user="test@user",
        postgres_password=SecretStr(token),
        postgres_db="demo",
        postgres_host="localhost",
    )
    engine = create_engine(settings)
    assert isinstance(engine.url, URL)
    assert engine.url.username == "test@user"
    assert engine.url.password == token
    assert engine.url.drivername == "postgresql+psycopg"
    assert token not in repr(settings)
    assert token not in str(engine.url)
