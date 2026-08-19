import logging
import sys

logger = logging.getLogger("pdf-tools")


def setup_logging() -> None:
    """Configure simple CLI logging for the current process."""
    if logger.handlers:
        return

    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
