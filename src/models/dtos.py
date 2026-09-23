from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImagePdfRequest:
    """Request for converting multiple images into one PDF."""
    image_files: list[Path]
    output_path: Path
    chunk_size: int = 100


@dataclass(frozen=True)
class SeparateImagePdfRequest:
    """Request for converting each image into an individual PDF."""
    image_files: list[Path]
    output_dir: Path


@dataclass(frozen=True)
class MergeRequest:
    """Request for merging PDF files."""
    input_files: list[Path]
    output_path: Path
    chunk_size: int = 10


@dataclass(frozen=True)
class SplitRequest:
    """Request for splitting one PDF into one PDF per page."""
    input_path: Path
    output_dir: Path
    output_prefix: str | None = None


@dataclass(frozen=True)
class RotateRequest:
    """Request for rotating every page in a PDF by a clockwise angle."""
    input_path: Path
    output_path: Path
    angle: int
