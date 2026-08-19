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


def get_current_directory() -> Path:
    """Return the directory from which pdf-tools was launched."""
    return Path.cwd()


def get_output_directory() -> Path:
    """Return and create the output directory in the current working directory."""
    output_dir = get_current_directory() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
