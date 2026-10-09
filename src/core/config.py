from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="TPUMON_", extra="ignore"
    )

    app_name: str = "tpumon"
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://tpumon:tpumon@localhost:5432/tpumon"


settings = Settings()
