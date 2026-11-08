import logging

logger = logging.getLogger("tpumon")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(module)s: %(message)s",
    )
