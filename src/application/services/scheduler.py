import asyncio
from collections.abc import Awaitable, Callable

from src.core.logging import logger


async def run_periodically(
    job: Callable[[], Awaitable[object]], interval_sec: float
) -> None:
    while True:
        try:
            await job()
        except Exception:
            logger.exception("Periodic job failed")
        await asyncio.sleep(interval_sec)
