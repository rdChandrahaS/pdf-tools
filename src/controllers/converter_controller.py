from pathlib import Path

from src.config import get_output_directory
from src.logger import logger
from src.models.dtos import ImagePdfRequest, SeparateImagePdfRequest
from src.services.convert_service import (
    convert_images_separately,
    convert_images_to_pdf,
    find_images,
    find_unsupported_files,
)
from src.utils import ensure_pdf_extension, sanitize_filename


def _log_ignored_files(directory: Path) -> None:
    for file_path in find_unsupported_files(directory):
        logger.warning(f"Ignoring unsupported file: {file_path.name}")


def _ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(f"{prompt} [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter y or n.")


def _ask_output_name(default_name: str) -> str:
    name = input(f"Output PDF name (Enter = '{default_name}'): ").strip()
    name = sanitize_filename(name or default_name, default=default_name)
    return ensure_pdf_extension(name)


def handle_image_to_pdf_ui(current_directory: Path) -> None:
    """Run the Image -> PDF workflow against the current working directory."""
    output_dir = get_output_directory()

    print("\n" + "-" * 45)
    print("Image -> PDF")
    print("  [1] Convert every image separately")
    print("  [2] Convert images into one PDF")
    print("-" * 45)

    choice = input("Choose an option: ").strip()

    if choice == "1":
        image_files = find_images(current_directory)
        _log_ignored_files(current_directory)

        if not image_files:
            logger.warning("No supported images found in the current directory.")
            return

        logger.info(f"Found {len(image_files)} image(s) in the current directory.")
        request = SeparateImagePdfRequest(
            image_files=image_files,
            output_dir=output_dir,
        )
        convert_images_separately(request)
        return

    if choice != "2":
        logger.warning("Invalid Image -> PDF option.")
        return

    print("\nConvert images into one PDF")
    current_images = find_images(current_directory)
    _log_ignored_files(current_directory)

    process_current_images = _ask_yes_no("Read all image files directly in the current directory?")
    if process_current_images:
        if not current_images:
            logger.warning("No supported images found directly in the current directory.")
        else:
            default_name = "images.pdf"
            output_name = _ask_output_name(default_name)
            output_path = output_dir / output_name
            request = ImagePdfRequest(
                image_files=current_images,
                output_path=output_path,
                chunk_size=100,
            )
            convert_images_to_pdf(request)

    process_folders = _ask_yes_no("Read all image-containing folders directly inside the current directory?")
    if not process_folders:
        return

    folders = sorted(
        [path for path in current_directory.iterdir() if path.is_dir() and path.name != "output"],
        key=lambda p: p.name.lower(),
    )

    if not folders:
        logger.warning("No folders found in the current directory.")
        return

    for folder in folders:
        folder_images = find_images(folder)
        if not folder_images:
            continue

        for file_path in find_unsupported_files(folder):
            logger.warning(f"Ignoring unsupported file in '{folder.name}': {file_path.name}")

        output_name = ensure_pdf_extension(sanitize_filename(folder.name, default="folder"))
        output_path = output_dir / output_name
        logger.info(f"Processing folder '{folder.name}' ({len(folder_images)} image(s)).")

        request = ImagePdfRequest(
            image_files=folder_images,
            output_path=output_path,
            chunk_size=100,
        )
        convert_images_to_pdf(request)
