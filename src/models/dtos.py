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


@dataclass(frozen=True)
class CompressRequest:
    """Request for previewing/finalizing PDF compression."""
    input_path: Path
    output_path: Path
    mode: str = "lossless"
    dpi: int = 150
    quality: int = 80
    grayscale: bool = False


@dataclass(frozen=True)
class CompressionPreview:
    """Result of a compression dry-run saved to a temporary PDF."""
    temporary_path: Path
    original_size: int
    compressed_size: int
    pages: int
    image_count: int
    mode: str

    @property
    def bytes_saved(self) -> int:
        return self.original_size - self.compressed_size

    @property
    def reduction_percent(self) -> float:
        if self.original_size <= 0:
            return 0.0
        return (self.bytes_saved / self.original_size) * 100.0
