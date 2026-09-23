from pathlib import Path

import questionary

from src.config import DEFAULT_IMAGE_CHUNK_SIZE, get_output_directory
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


def _ask_output_name(default_name: str) -> str | None:
    answer = questionary.text(
        "Output PDF name:",
        default=default_name,
        validate=lambda value: bool(value.strip()),
    ).ask()
    if answer is None:
        return None
    name = sanitize_filename(answer, default=default_name)
    return ensure_pdf_extension(name)


def _ask_chunk_size(default: int = DEFAULT_IMAGE_CHUNK_SIZE) -> int:
    answer = questionary.text(
        "Images per internal batch:",
        default=str(default),
        validate=lambda value: value.isdigit() and int(value) > 0,
    ).ask()
    return int(answer) if answer else default


def _convert_one_pdf(
    image_files: list[Path],
    output_dir: Path,
    default_name: str = "images.pdf",
) -> None:
    if not image_files:
        logger.warning("No images selected.")
        return

    logger.info(f"Selected {len(image_files)} image(s).")
    output_name = _ask_output_name(default_name)
    if output_name is None:
        return

    request = ImagePdfRequest(
        image_files=image_files,
        output_path=output_dir / output_name,
        chunk_size=_ask_chunk_size(),
    )
    convert_images_to_pdf(request)


def _convert_current_images(current_directory: Path, output_dir: Path) -> None:
    images = find_images(current_directory)
    _log_ignored_files(current_directory)
    if not images:
        logger.warning("No supported images found in the current directory.")
        return
    _convert_one_pdf(images, output_dir)


def _convert_selected_images(current_directory: Path, output_dir: Path) -> None:
    images = find_images(current_directory)
    if not images:
        logger.warning("No supported images found in the current directory.")
        return

    selected = questionary.checkbox(
        "Select images to include:",
        choices=[questionary.Choice(path.name, value=path) for path in images],
        validate=lambda choices: bool(choices),
    ).ask()
    if selected is None:
        return
    _convert_one_pdf(selected, output_dir, default_name="selected-images.pdf")


def _convert_folders(current_directory: Path, output_dir: Path) -> None:
    folders = sorted(
        [
            path
            for path in current_directory.iterdir()
            if path.is_dir() and path.name not in {"output", ".git", ".pdf-tools-cache"}
        ],
        key=lambda p: p.name.lower(),
    )

    jobs: list[tuple[Path, list[Path]]] = []
    for folder in folders:
        folder_images = find_images(folder)
        if folder_images:
            jobs.append((folder, folder_images))

    if not jobs:
        logger.warning("No image-containing folders were found.")
        return

    selected_folders = questionary.checkbox(
        "Select folders to convert (one PDF per folder):",
        choices=[
            questionary.Choice(f"{folder.name} ({len(images)} image(s))", value=folder)
            for folder, images in jobs
        ],
        validate=lambda choices: bool(choices),
    ).ask()
    if selected_folders is None:
        return

    for folder in selected_folders:
        folder_images = find_images(folder)
        if not folder_images:
            continue
        _log_ignored_files(folder)
        output_name = ensure_pdf_extension(
            sanitize_filename(folder.name, default="folder")
        )
        convert_images_to_pdf(
            ImagePdfRequest(
                image_files=folder_images,
                output_path=output_dir / output_name,
                chunk_size=DEFAULT_IMAGE_CHUNK_SIZE,
            )
        )


def handle_image_to_pdf_ui(current_directory: Path) -> None:
    """Run the interactive Image -> PDF workflow."""
    output_dir = get_output_directory(current_directory)

    while True:
        choice = questionary.select(
            "Image -> PDF",
            choices=[
                "Convert every image separately",
                "Images in current directory -> one PDF",
                "Select images -> one PDF",
                "Immediate folders -> one PDF per folder",
                "Back",
            ],
        ).ask()

        if choice == "Convert every image separately":
            image_files = find_images(current_directory)
            _log_ignored_files(current_directory)
            if not image_files:
                logger.warning("No supported images found in the current directory.")
                continue
            convert_images_separately(
                SeparateImagePdfRequest(image_files=image_files, output_dir=output_dir)
            )
        elif choice == "Images in current directory -> one PDF":
            _convert_current_images(current_directory, output_dir)
        elif choice == "Select images -> one PDF":
            _convert_selected_images(current_directory, output_dir)
        elif choice == "Immediate folders -> one PDF per folder":
            _convert_folders(current_directory, output_dir)
        else:
            return
