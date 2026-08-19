from pathlib import Path
from tqdm import tqdm
from pypdf import PdfWriter

from src.logger import logger
from src.models.dtos import MergeRequest
from src.utils import clean_directory, unique_output_path


def execute_merge(request: MergeRequest) -> None:
    """Merge PDFs using chunk files so large merges remain manageable."""
    if not request.input_files:
        logger.warning("No PDF files were provided.")
        return
    if request.chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = request.output_path.parent / ".pdf-tools-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    clean_directory(cache_dir)

    chunked_pdf_paths: list[Path] = []
    pdf_files = request.input_files

    try:
        logger.info(f"Merging {len(pdf_files)} PDFs...")

        with tqdm(total=len(pdf_files), desc="Merging PDFs", unit="file", dynamic_ncols=True) as pbar:
            for start in range(0, len(pdf_files), request.chunk_size):
                chunk = pdf_files[start:start + request.chunk_size]
                chunk_path = cache_dir / f"merge_{start + 1}-{start + len(chunk)}.pdf"

                writer = PdfWriter()
                try:
                    for pdf_path in chunk:
                        logger.debug(f"  Adding: {pdf_path.name}")
                        writer.append(pdf_path)
                        pbar.update(1)
                    with chunk_path.open("wb") as output_file:
                        writer.write(output_file)
                    chunked_pdf_paths.append(chunk_path)
                finally:
                    writer.close()

        
        logger.info("Compiling final document...")
        final_path = unique_output_path(request.output_path)
        final_writer = PdfWriter()
        try:
            for chunk_path in chunked_pdf_paths:
                final_writer.append(chunk_path)
            with final_path.open("wb") as output_file:
                final_writer.write(output_file)
        finally:
            final_writer.close()

        logger.info(f"Successfully Created: {final_path.name}")

    except Exception as exc:
        logger.error(f"Merge failed: {exc}")
    finally:
        clean_directory(cache_dir)
        try:
            cache_dir.rmdir()
        except OSError:
            pass
