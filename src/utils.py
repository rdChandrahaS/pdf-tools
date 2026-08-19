import re
from pathlib import Path

from src.logger import logger


def natural_sort_key(filename: str):
    """
    Sort filenames primarily by the first number appearing
    in the filename.
    """

    stem = Path(filename).stem

    numbers = re.findall(r"\d+", stem)

    if numbers:
        return (
            0,
            tuple(int(number) for number in numbers),
            stem.lower(),
        )

    return (
        1,
        (),
        stem.lower(),
    )


def get_longest_common_prefix(names: list[str]) -> str:
    """Return a useful common prefix for a collection of filenames."""
    if not names:
        return "output"

    stems = [Path(name).stem for name in names]
    prefix = stems[0]
    for stem in stems[1:]:
        length = 0
        for a, b in zip(prefix, stem):
            if a.lower() != b.lower():
                break
            length += 1
        prefix = prefix[:length]
        if not prefix:
            break

    prefix = prefix.rstrip(" _-.()")
    return prefix or "output"


def sanitize_filename(name: str, default: str = "output") -> str:
    """Return a safe single filename without directory traversal."""
    cleaned = Path(name.strip()).name
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", cleaned).strip(" .")
    return cleaned or default


def ensure_pdf_extension(name: str) -> str:
    """Ensure a filename has a .pdf suffix."""
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"


def unique_output_path(path: Path) -> Path:
    """Avoid overwriting an existing output file by adding a numeric suffix."""
    if not path.exists():
        return path

    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def clean_directory(directory: Path) -> None:
    """Remove files generated in a temporary directory."""
    if not directory.exists():
        return

    for path in directory.iterdir():
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
        except OSError as exc:
            logger.warning(f"Could not remove {path}: {exc}")
