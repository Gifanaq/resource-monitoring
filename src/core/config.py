from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class MonitoredService(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl
    expected_status: int = Field(default=200, ge=100, le=599)
    follow_redirects: bool = True
    timeout_sec: float = Field(default=10.0, gt=0, allow_inf_nan=False)
    slow_response_ms: int = Field(default=2000, gt=0)
    tls_warn_before_days: int = Field(default=14, gt=0, strict=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "tpumon"
    app_env: str = "dev"
    check_interval_sec: Annotated[int, Field(ge=60)] = 60
    services: list[MonitoredService] = []


settings = Settings()
