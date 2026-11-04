import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


async def run_periodically(
    job: Callable[[], Awaitable[object]], interval_sec: float
) -> None:
    while True:
        try:
            await job()
        except Exception:
            logger.exception("Periodic job failed")
        await asyncio.sleep(interval_sec)
