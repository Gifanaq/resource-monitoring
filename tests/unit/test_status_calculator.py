from datetime import UTC, datetime, timedelta

import pytest

from src.application.services.status_calculator import next_status
from src.domain.entities.service import (
    CheckResult,
    Service,
    ServiceStatus,
    StatusLevel,
)

SERVICE = Service(id=1, name="tpu", url="https://tpu.ru")
START = datetime(2026, 10, 23, tzinfo=UTC)


def run(results: list[CheckResult]) -> ServiceStatus:
    status = ServiceStatus(SERVICE.id)
    for result in results:
        status = next_status(SERVICE, status, result)
    return status


def ok(step: int, response_time_ms: int = 100) -> CheckResult:
    return CheckResult(
        SERVICE.id,
        START + timedelta(minutes=step),
        success=True,
        status_code=200,
        response_time_ms=response_time_ms,
    )


def fail(step: int) -> CheckResult:
    return CheckResult(
        SERVICE.id,
        START + timedelta(minutes=step),
        success=False,
        error="ConnectError",
    )


def test_first_fast_success_is_green() -> None:
    status = run([ok(0)])
    assert status.level is StatusLevel.GREEN
    assert status.changed_at == START


def test_single_failure_is_yellow() -> None:
    assert run([ok(0), fail(1)]).level is StatusLevel.YELLOW


def test_consecutive_failures_reach_red() -> None:
    assert run([fail(0), fail(1), fail(2)]).level is StatusLevel.RED


def test_red_holds_until_recovery_threshold() -> None:
    failures = [fail(0), fail(1), fail(2)]
    assert run([*failures, ok(3)]).level is StatusLevel.RED
    assert run([*failures, ok(3), ok(4)]).level is StatusLevel.GREEN


def test_slow_success_is_yellow() -> None:
    assert run([ok(0, response_time_ms=5000)]).level is StatusLevel.YELLOW


def test_yellow_holds_until_recovery_threshold() -> None:
    assert run([ok(0), fail(1), ok(2)]).level is StatusLevel.YELLOW
    assert run([ok(0), fail(1), ok(2), ok(3)]).level is StatusLevel.GREEN


def test_red_holds_when_recovery_is_interrupted() -> None:
    status = run([fail(0), fail(1), fail(2), ok(3), fail(4)])
    assert status.level is StatusLevel.RED
    assert status.consecutive_successes == 0
    assert status.last_checked_at == START + timedelta(minutes=4)


def test_invalid_thresholds_are_rejected() -> None:
    for failures, recovery in ((0, 2), (3, 0)):
        with pytest.raises(ValueError, match="status thresholds must be positive"):
            Service(
                1,
                "tpu",
                "https://tpu.ru",
                failure_threshold=failures,
                recovery_threshold=recovery,
            )
