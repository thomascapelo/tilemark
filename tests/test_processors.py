import pypdfium2 as pdfium
import pytest
from PIL import Image

from tilemark.processors import ProcessingError, process_image, process_pdf

from conftest import (
    SECRET_TEXT,
    make_16bit_gray_png,
    make_encrypted_pdf,
    make_jpeg_with_exif,
    make_pdf,
    make_transparent_png,
    make_truncated_pdf,
)


def test_pdf_keeps_page_count_and_size(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf", pages=2)
    dst = tmp_path / "out.pdf"
    assert process_pdf(src, dst, "Test", 0.3) == (2, False)
    out = pdfium.PdfDocument(dst)
    assert len(out) == 2
    assert out[0].get_size() == (595, 842)


def test_pdf_rotated_page_comes_out_upright(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf", pages=1, rotate=90)
    dst = tmp_path / "out.pdf"
    process_pdf(src, dst, "Test", 0.3)
    page = pdfium.PdfDocument(dst)[0]
    assert page.get_size() == (842, 595)
    assert page.get_rotation() == 0


def test_pdf_has_no_extractable_text(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf")
    dst = tmp_path / "out.pdf"
    process_pdf(src, dst, "Test", 0.3)
    for page in pdfium.PdfDocument(dst):
        assert page.get_textpage().get_text_range().strip() == ""
    assert SECRET_TEXT.encode() not in dst.read_bytes()


def test_pdf_metadata_removed(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf")
    dst = tmp_path / "out.pdf"
    process_pdf(src, dst, "Test", 0.3)
    metadata = pdfium.PdfDocument(dst).get_metadata_dict()
    assert not metadata.get("Title")
    assert not metadata.get("Author")


def test_pdf_original_untouched(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf")
    before = src.read_bytes()
    process_pdf(src, tmp_path / "out.pdf", "Test", 0.3)
    assert src.read_bytes() == before


def test_encrypted_pdf_raises_and_writes_nothing(tmp_path):
    src = make_encrypted_pdf(tmp_path / "secret.pdf")
    dst = tmp_path / "out.pdf"
    with pytest.raises(ProcessingError, match="password"):
        process_pdf(src, dst, "Test", 0.3)
    assert not dst.exists()


def test_corrupted_pdf_raises_and_writes_nothing(tmp_path):
    src = tmp_path / "broken.pdf"
    src.write_bytes(b"this is not a pdf")
    dst = tmp_path / "out.pdf"
    with pytest.raises(ProcessingError, match="corrupted"):
        process_pdf(src, dst, "Test", 0.3)
    assert not dst.exists()


def test_jpeg_exif_removed_and_size_kept(tmp_path):
    src = make_jpeg_with_exif(tmp_path / "photo.jpg")
    dst = tmp_path / "out.jpg"
    process_image(src, dst, "Test", 0.3)
    with Image.open(dst) as out:
        assert out.format == "JPEG"
        assert out.size == (400, 300)
        assert len(out.getexif()) == 0
        assert "exif" not in out.info


def test_jpeg_orientation_applied(tmp_path):
    # Orientation 6 = camera was rotated 90°: the output must be portrait.
    src = make_jpeg_with_exif(tmp_path / "photo.jpg", orientation=6)
    dst = tmp_path / "out.jpg"
    process_image(src, dst, "Test", 0.3)
    with Image.open(dst) as out:
        assert out.size == (300, 400)


def test_png_stays_png_and_transparency_becomes_white(tmp_path):
    src = make_transparent_png(tmp_path / "scan.png")
    dst = tmp_path / "out.png"
    process_image(src, dst, "Test", 0.3)
    with Image.open(dst) as out:
        assert out.format == "PNG"
        assert out.mode == "RGB"
        # The lightest pixel must be white: the background did not turn black.
        assert out.convert("L").getextrema()[1] == 255


def test_image_watermark_visible(tmp_path):
    src = make_jpeg_with_exif(tmp_path / "photo.jpg")
    dst = tmp_path / "out.jpg"
    process_image(src, dst, "Test", 0.3)
    with Image.open(dst) as out:
        assert out.convert("L").getextrema()[0] < 230


def test_corrupted_image_raises_and_writes_nothing(tmp_path):
    src = tmp_path / "broken.jpg"
    src.write_bytes(b"not an image")
    dst = tmp_path / "out.jpg"
    with pytest.raises(ProcessingError):
        process_image(src, dst, "Test", 0.3)
    assert not dst.exists()


def test_truncated_pdf_flagged_as_incomplete(tmp_path):
    src = make_truncated_pdf(tmp_path / "truncated.pdf")
    dst = tmp_path / "out.pdf"
    pages, incomplete = process_pdf(src, dst, "Test", 0.3)
    assert incomplete is True
    assert pages >= 1


def test_16bit_gray_png_keeps_content(tmp_path):
    src = make_16bit_gray_png(tmp_path / "scan16.png")
    dst = tmp_path / "out.png"
    process_image(src, dst, "Test", 0.3)
    with Image.open(dst) as out:
        # 10000 / 65535 is dark gray (~39/255); clipping would turn it white.
        assert out.convert("L").getextrema()[0] < 60
