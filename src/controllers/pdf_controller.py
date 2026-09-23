from pathlib import Path

import questionary
from pypdf import PdfReader

from src.config import get_output_directory
from src.logger import logger
from src.models.dtos import RotateRequest, SplitRequest
from src.services.pdf_service import find_pdfs, get_pdf_info, rotate_pdf, split_pdf
from src.utils import ensure_pdf_extension, sanitize_filename


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def handle_pdf_tools_ui(current_directory: Path) -> None:
    """Run PDF-only utility operations."""
    output_dir = get_output_directory(current_directory)

    while True:
        choice = questionary.select(
            "PDF Tools",
            choices=["PDF Information", "Split PDF", "Rotate PDF", "Back"],
        ).ask()

        if choice == "PDF Information":
            _show_pdf_info(current_directory)
        elif choice == "Split PDF":
            _split_pdf(current_directory, output_dir)
        elif choice == "Rotate PDF":
            _rotate_pdf(current_directory, output_dir)
        else:
            return


def _select_single_pdf(current_directory: Path, prompt: str):
    pdfs = find_pdfs(current_directory)
    if not pdfs:
        logger.warning("No PDF files found directly in the current directory.")
        return None
    return questionary.select(
        prompt,
        choices=[questionary.Choice(path.name, value=path) for path in pdfs],
    ).ask()


def _show_pdf_info(current_directory: Path) -> None:
    pdf_path = _select_single_pdf(current_directory, "Select a PDF:")
    if pdf_path is None:
        return

    try:
        info = get_pdf_info(pdf_path)
        print("\n" + "-" * 45)
        print(f"File:      {pdf_path.name}")
        print(f"Size:      {_format_size(int(info['size_bytes']))}")
        print(f"Pages:     {info['pages']}")
        print(f"Encrypted: {'Yes' if info['encrypted'] else 'No'}")
        print("Metadata:")
        metadata = info["metadata"]
        if metadata:
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        else:
            print("  None")
        print("-" * 45)
    except Exception as exc:
        logger.error(f"Could not read '{pdf_path.name}': {exc}")


def _split_pdf(current_directory: Path, output_dir: Path) -> None:
    pdf_path = _select_single_pdf(current_directory, "Select a PDF to split:")
    if pdf_path is None:
        return

    default_prefix = sanitize_filename(pdf_path.stem, default="document")
    prefix = questionary.text("Output file prefix:", default=default_prefix).ask()
    if prefix is None:
        return
    prefix = sanitize_filename(prefix, default=default_prefix)

    target_dir_name = questionary.text(
        "Output folder name:",
        default=f"{pdf_path.stem}_pages",
        validate=lambda value: bool(value.strip()),
    ).ask()
    if target_dir_name is None:
        return
    target_dir = output_dir / sanitize_filename(target_dir_name, default="pages")

    try:
        split_pdf(SplitRequest(pdf_path, target_dir, prefix))
    except Exception as exc:
        logger.error(f"Could not split '{pdf_path.name}': {exc}")


def _rotate_pdf(current_directory: Path, output_dir: Path) -> None:
    pdf_path = _select_single_pdf(current_directory, "Select a PDF to rotate:")
    if pdf_path is None:
        return

    angle_label = questionary.select(
        "Clockwise rotation:",
        choices=["90°", "180°", "270°"],
    ).ask()
    if angle_label is None:
        return
    angle = int(angle_label.rstrip("°"))

    default_name = ensure_pdf_extension(f"{pdf_path.stem}_rotated_{angle}")
    output_name = questionary.text("Output PDF name:", default=default_name).ask()
    if output_name is None:
        return
    output_name = ensure_pdf_extension(sanitize_filename(output_name, default=default_name))

    try:
        rotate_pdf(
            RotateRequest(
                input_path=pdf_path,
                output_path=output_dir / output_name,
                angle=angle,
            )
        )
    except Exception as exc:
        logger.error(f"Could not rotate '{pdf_path.name}': {exc}")
