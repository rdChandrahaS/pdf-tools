from pathlib import Path

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
}


DEFAULT_IMAGE_CHUNK_SIZE = 100
DEFAULT_PDF_CHUNK_SIZE = 10
OUTPUT_DIRECTORY_NAME = "output"
CACHE_DIRECTORY_NAME = ".pdf-tools-cache"


def get_current_directory() -> Path:
    """Return the directory from which pdf-tools was launched."""
    return Path.cwd()


def get_output_directory(current_directory: Path | None = None) -> Path:
    """Return and create the output directory in the working directory."""
    base_directory = current_directory or get_current_directory()
    output_dir = base_directory / OUTPUT_DIRECTORY_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
