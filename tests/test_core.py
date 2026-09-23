import tempfile
import unittest
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from src.models.dtos import (
    ImagePdfRequest,
    MergeRequest,
    RotateRequest,
    SeparateImagePdfRequest,
    SplitRequest,
)
from src.services.convert_service import convert_images_separately, convert_images_to_pdf
from src.services.merge_service import execute_merge
from src.services.pdf_service import get_pdf_info, rotate_pdf, split_pdf
from src.utils import natural_sort_key, sanitize_filename, unique_output_path


class CoreWorkflowTests(unittest.TestCase):
    def test_utilities(self) -> None:
        names = ["page10.png", "2cover.png", "page2.png", "appendix.png", "page1.png"]
        assert sorted(names, key=natural_sort_key) == [
            "appendix.png",
            "page1.png",
            "page2.png",
            "page10.png",
            "2cover.png",
        ]
        assert sanitize_filename("../bad:name?.pdf") == "bad_name_.pdf"

    def test_image_pdf_merge_split_rotate_info(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_dir = root / "images"
            output_dir = root / "output"
            image_dir.mkdir()
            output_dir.mkdir()

            for name, size in [("page10.png", (200, 100)), ("page2.png", (100, 200)), ("page1.png", (80, 80))]:
                Image.new("RGB", size, "white").save(image_dir / name)

            images = list(image_dir.glob("*.png"))
            combined = convert_images_to_pdf(
                ImagePdfRequest(images, output_dir / "combined.pdf", chunk_size=2)
            )
            assert combined is not None
            assert len(PdfReader(combined).pages) == 3

            separate = convert_images_separately(
                SeparateImagePdfRequest(images, output_dir)
            )
            assert len(separate) == 3

            merged = execute_merge(
                MergeRequest([combined, separate[0]], output_dir / "merged.pdf", chunk_size=1)
            )
            assert merged is not None
            assert len(PdfReader(merged).pages) == 4

            info = get_pdf_info(merged)
            assert info["pages"] == 4
            assert info["encrypted"] is False
            assert int(info["size_bytes"]) > 0

            split_files = split_pdf(SplitRequest(combined, output_dir / "split"))
            assert len(split_files) == 3
            assert all(len(PdfReader(path).pages) == 1 for path in split_files)

            rotated = rotate_pdf(RotateRequest(combined, output_dir / "rotated.pdf", 90))
            assert rotated is not None
            assert PdfReader(rotated).pages[0].get("/Rotate") == 90

            collision = output_dir / "collision.pdf"
            collision.write_bytes(b"existing")
            assert unique_output_path(collision).name == "collision (1).pdf"


if __name__ == "__main__":
    unittest.main()
