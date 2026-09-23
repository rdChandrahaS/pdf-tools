import re
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.logger import logger


def natural_sort_key(filename: str) -> tuple[tuple[int, object], ...]:
    """Sort filenames naturally without mixing incomparable Python types."""
    stem = Path(filename).stem.lower()
    parts = re.split(r"(\d+)", stem)
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part)
        for part in parts
        if part
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
    """Return a safe filename without directory traversal or platform-reserved characters."""
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


def atomic_write_pdf(writer, output_path: Path) -> Path:
    """Write a PDF to a temporary file and atomically replace the final path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None

    try:
        with NamedTemporaryFile(
            mode="wb",
            suffix=".pdf.tmp",
            prefix=f".{output_path.stem}-",
            dir=output_path.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            writer.write(temp_file)

        temp_path.replace(output_path)
        return output_path
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError as exc:
                logger.warning(f"Could not remove temporary file {temp_path.name}: {exc}")


def clean_directory(directory: Path) -> None:
    """Remove files generated in a temporary directory."""
    if not directory.exists():
        return

    for path in directory.iterdir():
        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        except OSError as exc:
            logger.warning(f"Could not remove {path}: {exc}")
