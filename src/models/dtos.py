from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImagePdfRequest:
    """Request for converting images into one or more PDFs."""
    image_files: list[Path]
    output_path: Path
    chunk_size: int = 100


@dataclass
class SeparateImagePdfRequest:
    """Request for converting each image into its own PDF."""
    image_files: list[Path]
    output_dir: Path


@dataclass
class MergeRequest:
    """Request for merging PDF files."""
    input_files: list[Path]
    output_path: Path
    chunk_size: int = 10
