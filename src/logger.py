import logging
import sys

from tqdm import tqdm

from src.config import get_current_directory


logger = logging.getLogger("pdf-tools")


class TqdmLoggingHandler(logging.Handler):
    """Send log messages above/below tqdm progress bars without corrupting them."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            tqdm.write(message, file=sys.stderr)
        except Exception:
            self.handleError(record)


def setup_logging() -> None:
    """Configure CLI logging while keeping tqdm progress bars clean."""
    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    console_handler = TqdmLoggingHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("INFO: %(message)s"))

    log_file_path = get_current_directory() / "pdf-tools.log"
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
