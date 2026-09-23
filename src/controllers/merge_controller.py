from pathlib import Path

import questionary

from src.config import DEFAULT_PDF_CHUNK_SIZE, get_output_directory
from src.logger import logger
from src.models.dtos import MergeRequest
from src.services.merge_service import execute_merge
from src.services.pdf_service import find_pdfs
from src.utils import ensure_pdf_extension, get_longest_common_prefix, natural_sort_key, sanitize_filename


def _ask_output_name(default_name: str) -> str | None:
    answer = questionary.text("Output PDF name:", default=default_name).ask()
    if answer is None:
        return None
    return ensure_pdf_extension(sanitize_filename(answer, default=default_name))


def handle_merge_ui(current_directory: Path) -> None:
    """Merge selected PDF files found directly in the current working directory."""
    output_dir = get_output_directory(current_directory)
    pdf_files = find_pdfs(current_directory)

    if not pdf_files:
        logger.warning("No PDF files found directly in the current directory.")
        return

    selected = questionary.checkbox(
        "Select PDFs to merge (they will follow the displayed natural order):",
        choices=[questionary.Choice(path.name, value=path) for path in pdf_files],
        validate=lambda choices: len(choices) >= 2,
    ).ask()
    if selected is None:
        return

    selected.sort(key=lambda p: natural_sort_key(p.name))

    default_name = f"{get_longest_common_prefix([p.name for p in selected])}.pdf"
    output_name = _ask_output_name(default_name)
    if output_name is None:
        return

    chunk_answer = questionary.text(
        "PDFs per internal batch:",
        default=str(DEFAULT_PDF_CHUNK_SIZE),
        validate=lambda value: value.isdigit() and int(value) > 0,
    ).ask()
    chunk_size = int(chunk_answer) if chunk_answer else DEFAULT_PDF_CHUNK_SIZE

    execute_merge(
        MergeRequest(
            input_files=selected,
            output_path=output_dir / output_name,
            chunk_size=chunk_size,
        )
    )
