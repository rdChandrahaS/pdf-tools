from pathlib import Path

from pypdf import PdfReader, PdfWriter
from tqdm import tqdm

from src.logger import logger
from src.models.dtos import RotateRequest, SplitRequest
from src.utils import atomic_write_pdf, natural_sort_key, unique_output_path


def find_pdfs(directory: Path) -> list[Path]:
    """Return PDF files directly inside a directory in natural order."""
    if not directory.exists():
        return []
    return sorted(
        [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"],
        key=lambda p: natural_sort_key(p.name),
    )


def get_pdf_info(pdf_path: Path) -> dict[str, object]:
    """Return basic information about a PDF."""
    reader = PdfReader(pdf_path, strict=False)
    metadata = reader.metadata or {}
    return {
        "pages": len(reader.pages),
        "encrypted": bool(reader.is_encrypted),
        "metadata": {
            key.lstrip("/"): str(value)
            for key, value in metadata.items()
            if value is not None
        },
        "size_bytes": pdf_path.stat().st_size,
    }


def split_pdf(request: SplitRequest) -> list[Path]:
    """Split a PDF into one PDF per page."""
    request.output_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(request.input_path, strict=False)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported by the split operation.")

    page_count = len(reader.pages)
    if page_count == 0:
        logger.warning("The PDF contains no pages.")
        return []

    prefix = request.output_prefix or request.input_path.stem
    digits = max(3, len(str(page_count)))
    created: list[Path] = []

    logger.info(f"Splitting {request.input_path.name} ({page_count} pages)...")
    with tqdm(total=page_count, desc="Splitting PDF", unit="page", dynamic_ncols=True) as pbar:
        for page_number, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            try:
                writer.add_page(page)
                output_path = unique_output_path(
                    request.output_dir / f"{prefix}_page_{page_number:0{digits}d}.pdf"
                )
                atomic_write_pdf(writer, output_path)
                created.append(output_path)
            finally:
                writer.close()
            pbar.update(1)

    logger.info(f"Created {len(created)} page PDF(s).")
    return created


def rotate_pdf(request: RotateRequest) -> Path | None:
    """Rotate every page in a PDF clockwise by 90, 180, or 270 degrees."""
    if request.angle not in {90, 180, 270}:
        raise ValueError("Rotation angle must be 90, 180, or 270 degrees.")

    reader = PdfReader(request.input_path, strict=False)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported by the rotate operation.")

    writer = PdfWriter()
    try:
        for page in reader.pages:
            page.rotate(request.angle)
            writer.add_page(page)
        final_path = unique_output_path(request.output_path)
        atomic_write_pdf(writer, final_path)
        logger.info(f"Created: {final_path.name}")
        return final_path
    finally:
        writer.close()
