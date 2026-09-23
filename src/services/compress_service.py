from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import fitz

from src.logger import logger
from src.models.dtos import CompressionPreview, CompressRequest
from src.utils import unique_output_path


def _count_unique_images(document: fitz.Document) -> int:
    """Count distinct image XObjects referenced by pages."""
    xrefs: set[int] = set()
    for page in document:
        for image in page.get_images(full=True):
            if image and image[0] > 0:
                xrefs.add(int(image[0]))
    return len(xrefs)


def _validate_request(request: CompressRequest) -> None:
    if request.mode not in {"lossless", "lossy"}:
        raise ValueError("Compression mode must be 'lossless' or 'lossy'.")
    if request.mode == "lossy":
        if request.dpi < 36 or request.dpi > 1200:
            raise ValueError("Lossy DPI must be between 36 and 1200.")
        if request.quality < 1 or request.quality > 100:
            raise ValueError("JPEG quality must be between 1 and 100.")


def _save_compressed(document: fitz.Document, temporary_path: Path, request: CompressRequest) -> None:
    if request.mode == "lossless":
        # No image recompression. This only removes unused objects and compresses
        # uncompressed streams / object containers while preserving page content.
        document.save(
            str(temporary_path),
            garbage=4,
            clean=1,
            deflate=1,
            deflate_images=0,
            deflate_fonts=1,
            use_objstms=1,
            preserve_metadata=1,
        )
        return

    document.rewrite_images(
        # PyMuPDF requires dpi_threshold to be strictly greater than dpi_target.
        dpi_threshold=request.dpi + 1,
        dpi_target=request.dpi,
        quality=request.quality,
        lossy=True,
        lossless=True,
        bitonal=True,
        color=True,
        gray=True,
        set_to_gray=request.grayscale,
    )
    document.save(
        str(temporary_path),
        garbage=4,
        clean=1,
        deflate=1,
        deflate_images=0,
        deflate_fonts=1,
        use_objstms=1,
        preserve_metadata=1,
    )


def prepare_compression_preview(request: CompressRequest) -> CompressionPreview:
    """Create a temporary compressed PDF and return its measured size."""
    _validate_request(request)
    if not request.input_path.exists():
        raise FileNotFoundError(f"PDF not found: {request.input_path}")

    cache_dir = request.output_path.parent / ".pdf-tools-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale previews so canceled operations do not accumulate junk.
    for path in cache_dir.glob("compression-preview-*.pdf"):
        try:
            path.unlink()
        except OSError:
            pass

    temporary_path: Path | None = None
    document: fitz.Document | None = None
    try:
        document = fitz.open(str(request.input_path))
        if document.needs_pass:
            raise ValueError("Password-protected PDFs are not supported by compression.")
        if document.page_count == 0:
            raise ValueError("The PDF contains no pages.")

        page_count = document.page_count
        image_count = _count_unique_images(document)
        with NamedTemporaryFile(
            mode="wb",
            suffix=".pdf",
            prefix="compression-preview-",
            dir=cache_dir,
            delete=False,
        ) as temp_file:
            temporary_path = Path(temp_file.name)

        # fitz.save() writes the completed PDF to the path itself.
        temporary_path.unlink()
        _save_compressed(document, temporary_path, request)
    except Exception:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass
        raise
    finally:
        if document is not None:
            document.close()

    original_size = request.input_path.stat().st_size
    compressed_size = temporary_path.stat().st_size if temporary_path else 0
    logger.info(
        f"Compression preview: {original_size:,} -> {compressed_size:,} bytes "
        f"({((original_size - compressed_size) / original_size * 100.0) if original_size else 0.0:.1f}% change)."
    )

    return CompressionPreview(
        temporary_path=temporary_path,
        original_size=original_size,
        compressed_size=compressed_size,
        pages=page_count,
        image_count=image_count,
        mode=request.mode,
    )


def finalize_compression(preview: CompressionPreview, output_path: Path) -> Path:
    """Move a preview result to a collision-safe final output path."""
    if not preview.temporary_path.exists():
        raise FileNotFoundError("Compression preview no longer exists. Please preview again.")

    final_path = unique_output_path(output_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    preview.temporary_path.replace(final_path)
    logger.info(f"Created compressed PDF: {final_path.name}")
    return final_path


def discard_compression_preview(preview: CompressionPreview) -> None:
    """Delete a temporary compression preview."""
    try:
        if preview.temporary_path.exists():
            preview.temporary_path.unlink()
    except OSError as exc:
        logger.warning(f"Could not remove compression preview: {exc}")

    cache_dir = preview.temporary_path.parent
    try:
        cache_dir.rmdir()
    except OSError:
        pass
