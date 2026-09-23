from pathlib import Path
import zlib

from PIL import Image, UnidentifiedImageError
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject, StreamObject
from tqdm import tqdm

from src.config import CACHE_DIRECTORY_NAME, SUPPORTED_IMAGE_EXTENSIONS
from src.logger import logger
from src.models.dtos import ImagePdfRequest, SeparateImagePdfRequest
from src.utils import atomic_write_pdf, clean_directory, natural_sort_key, unique_output_path


def _get_page_size(image: Image.Image) -> tuple[float, float]:
    """Keep all source pixels while using embedded DPI for physical page size when available."""
    width, height = image.size
    dpi = image.info.get("dpi")

    if isinstance(dpi, tuple) and len(dpi) >= 2:
        try:
            x_dpi = float(dpi[0])
            y_dpi = float(dpi[1])
            if x_dpi > 0 and y_dpi > 0:
                return width * 72.0 / x_dpi, height * 72.0 / y_dpi
        except (TypeError, ValueError):
            pass

    return float(width), float(height)


def _add_image_page(writer: PdfWriter, image_path: Path) -> None:
    """Add an image as a PDF page without resizing or lossy recompression."""
    with Image.open(image_path) as image:
        width, height = image.size
        page_width, page_height = _get_page_size(image)
        original_format = (image.format or "").upper()
        mode = image.mode

        if original_format in {"JPEG", "JPG"}:
            jpeg_data = image_path.read_bytes()

            if mode == "L":
                color_space = NameObject("/DeviceGray")
            elif mode == "CMYK":
                color_space = NameObject("/DeviceCMYK")
            else:
                color_space = NameObject("/DeviceRGB")

            image_stream = StreamObject()
            image_stream.set_data(jpeg_data)
            image_stream.update(
                {
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(width),
                    NameObject("/Height"): NumberObject(height),
                    NameObject("/ColorSpace"): color_space,
                    NameObject("/BitsPerComponent"): NumberObject(8),
                    NameObject("/Filter"): NameObject("/DCTDecode"),
                }
            )
        else:
            if mode in {"RGBA", "LA"} or (mode == "P" and "transparency" in image.info):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                rgb = background
            else:
                rgb = image.convert("RGB")

            raw_pixels = rgb.tobytes()
            image_stream = StreamObject()
            image_stream.set_data(zlib.compress(raw_pixels, level=6))
            image_stream.update(
                {
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(width),
                    NameObject("/Height"): NumberObject(height),
                    NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                    NameObject("/BitsPerComponent"): NumberObject(8),
                    NameObject("/Filter"): NameObject("/FlateDecode"),
                }
            )

        image_ref = writer._add_object(image_stream)

        resources = DictionaryObject()
        x_objects = DictionaryObject()
        x_objects[NameObject("/Im0")] = image_ref
        resources[NameObject("/XObject")] = x_objects

        content = StreamObject()
        content.set_data(
            f"q\n{page_width} 0 0 {page_height} 0 0 cm\n/Im0 Do\nQ\n".encode("ascii")
        )
        content_ref = writer._add_object(content)

        page = writer.add_blank_page(width=page_width, height=page_height)
        page[NameObject("/Resources")] = resources
        page[NameObject("/Contents")] = content_ref


def _write_images_to_pdf(
    image_files: list[Path],
    output_path: Path,
    pbar: tqdm | None = None,
) -> None:
    """Write a list of images directly into one PDF."""
    writer = PdfWriter()
    try:
        for image_path in image_files:
            _add_image_page(writer, image_path)
            if pbar is not None:
                pbar.update(1)
        atomic_write_pdf(writer, output_path)
    finally:
        writer.close()


def _validate_images(image_files: list[Path]) -> list[Path]:
    """Remove unreadable images before starting a batch."""
    valid: list[Path] = []
    for image_path in image_files:
        try:
            with Image.open(image_path) as image:
                image.verify()
            valid.append(image_path)
        except (OSError, UnidentifiedImageError) as exc:
            logger.error(f"Skipping unreadable image '{image_path.name}': {exc}")
    return valid


def convert_images_separately(request: SeparateImagePdfRequest) -> list[Path]:
    """Convert every image into an individual PDF."""
    request.output_dir.mkdir(parents=True, exist_ok=True)
    valid_images = _validate_images(request.image_files)
    created: list[Path] = []

    if not valid_images:
        logger.warning("No readable images were found.")
        return created

    logger.info(f"Converting {len(valid_images)} images separately...")

    with tqdm(total=len(valid_images), desc="Converting images", unit="img", dynamic_ncols=True) as pbar:
        for image_path in valid_images:
            output_path = unique_output_path(request.output_dir / f"{image_path.stem}.pdf")
            try:
                _write_images_to_pdf([image_path], output_path)
                created.append(output_path)
                logger.info(f"Created: {output_path.name}")
            except Exception as exc:
                logger.error(f"Failed to convert '{image_path.name}': {exc}")
            finally:
                pbar.update(1)

    return created


def convert_images_to_pdf(request: ImagePdfRequest) -> Path | None:
    """Convert many images into one PDF using chunk PDFs for large batches."""
    if not request.image_files:
        logger.warning("No images were provided.")
        return None
    if request.chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    image_files = _validate_images(
        sorted(request.image_files, key=lambda p: natural_sort_key(p.name))
    )
    if not image_files:
        logger.warning("No readable images were found.")
        return None

    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = request.output_path.parent / CACHE_DIRECTORY_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    clean_directory(cache_dir)

    chunk_paths: list[Path] = []
    final_path = unique_output_path(request.output_path)

    try:
        logger.info(f"Converting {len(image_files)} images into {final_path.name}...")

        with tqdm(total=len(image_files), desc="Converting images", unit="img", dynamic_ncols=True) as pbar:
            for start in range(0, len(image_files), request.chunk_size):
                chunk = image_files[start : start + request.chunk_size]
                chunk_path = cache_dir / f"chunk_{start + 1}-{start + len(chunk)}.pdf"
                logger.info(
                    f"Converting images {start + 1}-{start + len(chunk)} of {len(image_files)}..."
                )
                _write_images_to_pdf(chunk, chunk_path, pbar)
                chunk_paths.append(chunk_path)

        logger.info("Compiling final document...")
        final_writer = PdfWriter()
        try:
            for chunk_path in chunk_paths:
                final_writer.append(chunk_path)
            atomic_write_pdf(final_writer, final_path)
        finally:
            final_writer.close()

        logger.info(f"Successfully created: {final_path.name}")
        return final_path
    except Exception as exc:
        logger.error(f"Image conversion failed: {exc}")
        return None
    finally:
        clean_directory(cache_dir)
        try:
            cache_dir.rmdir()
        except OSError:
            pass


def find_images(directory: Path) -> list[Path]:
    """Return supported image files directly inside one directory."""
    if not directory.exists():
        return []
    return sorted(
        [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        ],
        key=lambda p: natural_sort_key(p.name),
    )


def find_unsupported_files(directory: Path) -> list[Path]:
    """Return unsupported files directly inside one directory."""
    if not directory.exists():
        return []
    return sorted(
        [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS
        ],
        key=lambda p: natural_sort_key(p.name),
    )
