import pytest
from pydantic import ValidationError

from src.core.config import Settings


@pytest.mark.parametrize("interval", [-1, 0, 1, 59])
def test_interval_below_minimum_is_rejected(monkeypatch, interval):
    monkeypatch.setenv("CHECK_INTERVAL_SEC", str(interval))
    monkeypatch.setenv("SERVICES", "[]")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize("interval", [60, 300])
def test_valid_interval_is_loaded_from_environment(monkeypatch, interval):
    monkeypatch.setenv("CHECK_INTERVAL_SEC", str(interval))
    monkeypatch.setenv("SERVICES", "[]")
    assert Settings(_env_file=None).check_interval_sec == interval
