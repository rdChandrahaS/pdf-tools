from pathlib import Path

import questionary

from src.config import get_output_directory
from src.logger import logger
from src.models.dtos import CompressRequest
from src.services.compress_service import (
    discard_compression_preview,
    finalize_compression,
    prepare_compression_preview,
)
from src.services.pdf_service import find_pdfs
from src.utils import ensure_pdf_extension, format_file_size, sanitize_filename


_DPI_PRESETS = ["300 DPI", "200 DPI", "150 DPI", "120 DPI", "96 DPI", "72 DPI", "Custom"]
_QUALITY_PRESETS = ["90 (High)", "80 (Good)", "70 (Balanced)", "60 (Small)", "50 (Smaller)", "Custom"]


def _select_pdf(current_directory: Path) -> Path | None:
    pdfs = find_pdfs(current_directory)
    if not pdfs:
        logger.warning("No PDF files found directly in the current directory.")
        return None
    return questionary.select(
        "Select a PDF:",
        choices=[questionary.Choice(path.name, value=path) for path in pdfs],
    ).ask()


def _ask_int(prompt: str, default: int, minimum: int, maximum: int) -> int | None:
    answer = questionary.text(
        prompt,
        default=str(default),
        validate=lambda value: value.isdigit() and minimum <= int(value) <= maximum,
    ).ask()
    return int(answer) if answer else None


def _choose_dpi() -> int | None:
    choice = questionary.select("Target image DPI:", choices=_DPI_PRESETS).ask()
    if choice is None:
        return None
    if choice == "Custom":
        return _ask_int("Target DPI (36-1200):", 150, 36, 1200)
    return int(choice.split()[0])


def _choose_quality() -> int | None:
    choice = questionary.select("JPEG quality:", choices=_QUALITY_PRESETS).ask()
    if choice is None:
        return None
    if choice == "Custom":
        return _ask_int("JPEG quality (1-100):", 80, 1, 100)
    return int(choice.split()[0])


def _show_preview(preview) -> None:
    print("\n" + "-" * 55)
    print("Compression preview")
    print("-" * 55)
    print(f"Original size:   {format_file_size(preview.original_size)}")
    print(f"Estimated size:  {format_file_size(preview.compressed_size)}")

    if preview.bytes_saved >= 0:
        print(f"Estimated save:  {format_file_size(preview.bytes_saved)} ({preview.reduction_percent:.1f}%)")
    else:
        print(f"Estimated change: +{format_file_size(-preview.bytes_saved)} ({abs(preview.reduction_percent):.1f}% larger)")

    print(f"Pages:           {preview.pages}")
    print(f"Images detected: {preview.image_count}")
    print(f"Mode:            {preview.mode.title()}")
    print("-" * 55)


def handle_compress_ui(current_directory: Path) -> None:
    """Run the interactive PDF compression workflow."""
    output_dir = get_output_directory(current_directory)

    while True:
        choice = questionary.select(
            "Compress PDF",
            choices=[
                "Lossless compression",
                "Lossy compression",
                "Back",
            ],
        ).ask()

        if choice == "Lossless compression":
            _compress_one(current_directory, output_dir, mode="lossless")
        elif choice == "Lossy compression":
            _compress_one(current_directory, output_dir, mode="lossy")
        else:
            return


def _compress_one(current_directory: Path, output_dir: Path, mode: str) -> None:
    input_path = _select_pdf(current_directory)
    if input_path is None:
        return

    dpi = 150
    quality = 80
    grayscale = False

    if mode == "lossy":
        dpi = _choose_dpi()
        if dpi is None:
            return
        quality = _choose_quality()
        if quality is None:
            return
        grayscale = bool(
            questionary.confirm(
                "Convert color/grayscale images to grayscale?",
                default=False,
            ).ask()
        )

    default_name = f"{input_path.stem}-compressed.pdf"
    answer = questionary.text(
        "Output PDF name:",
        default=default_name,
        validate=lambda value: bool(value.strip()),
    ).ask()
    if answer is None:
        return
    output_name = ensure_pdf_extension(sanitize_filename(answer, default=default_name))

    request = CompressRequest(
        input_path=input_path,
        output_path=output_dir / output_name,
        mode=mode,
        dpi=dpi,
        quality=quality,
        grayscale=grayscale,
    )

    preview = None
    try:
        logger.info(f"Preparing {mode} compression preview for {input_path.name}...")
        preview = prepare_compression_preview(request)
        _show_preview(preview)

        if preview.compressed_size >= preview.original_size:
            logger.warning("This compression setting is not expected to reduce the file size.")
            question = "Save anyway?"
        else:
            question = "Use this compression result?"

        proceed = questionary.confirm(question, default=preview.compressed_size < preview.original_size).ask()
        if not proceed:
            discard_compression_preview(preview)
            logger.info("Compression canceled; no output file was created.")
            return

        final_path = finalize_compression(preview, request.output_path)
        logger.info(
            f"Final size: {format_file_size(final_path.stat().st_size)} "
            f"(original: {format_file_size(preview.original_size)})."
        )
    except Exception as exc:
        if preview is not None:
            discard_compression_preview(preview)
        logger.error(f"Compression failed: {exc}")
