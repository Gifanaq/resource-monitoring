from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TPUMON_")

    app_name: str = "tpumon"
    app_env: str = "dev"


settings = Settings()
