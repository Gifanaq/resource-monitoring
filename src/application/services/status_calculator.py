from src.domain.entities.service import (
    CheckResult,
    Service,
    ServiceStatus,
    StatusLevel,
)


def next_status(
    service: Service, current: ServiceStatus, result: CheckResult
) -> ServiceStatus:
    if result.success:
        failures, successes = 0, current.consecutive_successes + 1
    else:
        failures, successes = current.consecutive_failures + 1, 0
    level = _level(service, current.level, result, failures, successes)
    changed_at = result.checked_at if level != current.level else current.changed_at
    return ServiceStatus(
        service.id, level, failures, successes, changed_at, result.checked_at
    )


def _level(
    service: Service,
    previous: StatusLevel,
    result: CheckResult,
    failures: int,
    successes: int,
) -> StatusLevel:
    if failures >= service.failure_threshold:
        return StatusLevel.RED
    if not result.success:
        return StatusLevel.RED if previous is StatusLevel.RED else StatusLevel.YELLOW
    degraded = previous in (StatusLevel.RED, StatusLevel.YELLOW)
    if degraded and successes < service.recovery_threshold:
        return previous
    slow = (
        result.response_time_ms is not None
        and result.response_time_ms > service.slow_response_ms
    )
    return StatusLevel.YELLOW if slow else StatusLevel.GREEN
