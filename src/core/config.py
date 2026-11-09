from typing import Annotated

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MonitoredService(BaseModel):
    name: str
    url: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "tpumon"
    app_env: str = "dev"
    check_interval_sec: Annotated[int, Field(ge=60)] = 60
    services: list[MonitoredService] = []


settings = Settings()
