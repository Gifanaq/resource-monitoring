import pytest
from pydantic import ValidationError

from src.core.config import MonitoredService, Settings


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", "ftp://example.org"),
        ("expected_status", 99),
        ("expected_status", 600),
        ("timeout_sec", 0),
        ("timeout_sec", float("inf")),
        ("tls_warn_before_days", 0),
        ("tls_warn_before_days", 1.5),
        ("tls_warn_before_days", True),
        ("slow_response_ms", 0),
    ],
)
def test_invalid_http_service_settings_are_rejected(
    field: str,
    value: str | int,
) -> None:
    data: dict[str, str | int] = {
        "name": "demo",
        "url": "https://example.org",
    }
    data[field] = value

    with pytest.raises(ValidationError):
        MonitoredService.model_validate(data)


def test_expected_http_status_can_be_configured() -> None:
    service = MonitoredService(
        name="demo",
        url="https://example.org",
        expected_status=302,
        follow_redirects=False,
    )

    assert service.expected_status == 302
    assert not service.follow_redirects
    assert service.timeout_sec == 10


def test_services_can_be_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SERVICES",
        '[{"name":"demo","url":"https://example.org","expected_status":302}]',
    )

    settings = Settings(_env_file=None)

    assert len(settings.services) == 1
    assert settings.services[0].name == "demo"
    assert settings.services[0].expected_status == 302
