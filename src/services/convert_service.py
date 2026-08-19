from pathlib import Path
import zlib

from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import (
    DictionaryObject,
    NameObject,
    NumberObject,
    StreamObject,
)

from src.config import SUPPORTED_IMAGE_EXTENSIONS
from src.logger import logger
from src.models.dtos import ImagePdfRequest, SeparateImagePdfRequest
from src.utils import clean_directory, natural_sort_key, unique_output_path


def _get_page_size(image: Image.Image) -> tuple[float, float]:
    """Keep all source pixels while using embedded DPI for physical page size when available."""
    width, height = image.size
    dpi = image.info.get("dpi")

    if isinstance(dpi, tuple) and len(dpi) >= 2 and dpi[0] > 0 and dpi[1] > 0:
        return width * 72.0 / dpi[0], height * 72.0 / dpi[1]

    return float(width), float(height)


def _add_image_page(writer: PdfWriter, image_path: Path) -> None:
    """Add the source image to a PDF page without resizing or lossy recompression."""
    with Image.open(image_path) as image:
        width, height = image.size
        page_width, page_height = _get_page_size(image)
        original_format = (image.format or "").upper()
        mode = image.mode

        # JPEG is kept as its original compressed bitstream.
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
            image_stream.update({
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Image"),
                NameObject("/Width"): NumberObject(width),
                NameObject("/Height"): NumberObject(height),
                NameObject("/ColorSpace"): color_space,
                NameObject("/BitsPerComponent"): NumberObject(8),
                NameObject("/Filter"): NameObject("/DCTDecode"),
            })
        else:
            # Other formats are decoded to RGB and stored with lossless Flate compression.
            # No resizing or lossy JPEG/WebP encoding is performed.
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
            image_stream.update({
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Image"),
                NameObject("/Width"): NumberObject(width),
                NameObject("/Height"): NumberObject(height),
                NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                NameObject("/BitsPerComponent"): NumberObject(8),
                NameObject("/Filter"): NameObject("/FlateDecode"),
            })

        image_ref = writer._add_object(image_stream)

        resources = DictionaryObject()
        x_objects = DictionaryObject()
        x_objects[NameObject("/Im0")] = image_ref
        resources[NameObject("/XObject")] = x_objects

        content = StreamObject()
        content._data = (
            f"q\n{page_width} 0 0 {page_height} 0 0 cm\n/Im0 Do\nQ\n".encode("ascii")
        )
        content_ref = writer._add_object(content)

        page = writer.add_blank_page(width=page_width, height=page_height)
        page[NameObject("/Resources")] = resources
        page[NameObject("/Contents")] = content_ref


def _write_images_to_pdf(image_files: list[Path], output_path: Path) -> None:
    """Write a list of images directly into one PDF."""
    writer = PdfWriter()
    try:
        for image_path in image_files:
            _add_image_page(writer, image_path)
        with output_path.open("wb") as output_file:
            writer.write(output_file)
    finally:
        writer.close()


def convert_images_separately(request: SeparateImagePdfRequest) -> list[Path]:
    """Convert every image into an individual PDF."""
    request.output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    for image_path in request.image_files:
        output_path = unique_output_path(request.output_dir / f"{image_path.stem}.pdf")
        try:
            _write_images_to_pdf([image_path], output_path)
            created.append(output_path)
            logger.info(f"Created: {output_path.name}")
        except Exception as exc:
            logger.error(f"Failed to convert '{image_path.name}': {exc}")

    return created


def convert_images_to_pdf(request: ImagePdfRequest) -> None:
    """Convert many images into one PDF using chunk PDFs for large batches."""
    if not request.image_files:
        logger.warning("No images were provided.")
        return
    if request.chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = request.output_path.parent / ".pdf-tools-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    clean_directory(cache_dir)

    chunk_paths: list[Path] = []
    image_files = sorted(request.image_files, key=lambda p: natural_sort_key(p.name))

    try:
        for start in range(0, len(image_files), request.chunk_size):
            chunk = image_files[start:start + request.chunk_size]
            chunk_path = cache_dir / f"chunk_{start + 1}-{start + len(chunk)}.pdf"
            logger.info(
                f"Converting images {start + 1}-{start + len(chunk)} "
                f"of {len(image_files)}..."
            )
            try:
                _write_images_to_pdf(chunk, chunk_path)
                chunk_paths.append(chunk_path)
            except Exception as exc:
                logger.error(f"Failed converting chunk {start + 1}-{start + len(chunk)}: {exc}")
                raise

        final_path = unique_output_path(request.output_path)
        final_writer = PdfWriter()
        try:
            for chunk_path in chunk_paths:
                final_writer.append(chunk_path)
            with final_path.open("wb") as output_file:
                final_writer.write(output_file)
        finally:
            final_writer.close()

        logger.info(f"Created: {final_path}")
    finally:
        clean_directory(cache_dir)
        try:
            cache_dir.rmdir()
        except OSError:
            pass


def find_images(directory: Path) -> list[Path]:
    """Return supported image files directly inside one directory, never recursively."""
    if not directory.exists():
        return []
    return sorted(
        [
            path for path in directory.iterdir()
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
            path for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS
        ],
        key=lambda p: natural_sort_key(p.name),
    )
