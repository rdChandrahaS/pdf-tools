from pathlib import Path

from src.config import get_output_directory
from src.logger import logger
from src.models.dtos import MergeRequest
from src.services.merge_service import execute_merge
from src.utils import ensure_pdf_extension, get_longest_common_prefix, natural_sort_key, sanitize_filename


def handle_merge_ui(current_directory: Path) -> None:
    """Merge PDF files found directly in the current working directory."""
    output_dir = get_output_directory()
    pdf_files = [
        path for path in current_directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    ]
    pdf_files.sort(key=lambda p: natural_sort_key(p.name))

    if not pdf_files:
        logger.warning("No PDF files found directly in the current directory.")
        return

    print("\n" + "-" * 45)
    print(f"Found {len(pdf_files)} PDF file(s):")
    for index, pdf_file in enumerate(pdf_files, 1):
        print(f"  [{index}] {pdf_file.name}")
    print("-" * 45)

    default_name = f"{get_longest_common_prefix([p.name for p in pdf_files])}.pdf"
    user_name = input(f"Output PDF name (Enter = '{default_name}'): ").strip()
    output_name = ensure_pdf_extension(
        sanitize_filename(user_name or default_name, default=default_name)
    )

    batch_input = input("PDFs per internal batch (Enter = 10): ").strip()
    chunk_size = int(batch_input) if batch_input.isdigit() and int(batch_input) > 0 else 10

    request = MergeRequest(
        input_files=pdf_files,
        output_path=output_dir / output_name,
        chunk_size=chunk_size,
    )
    execute_merge(request)
