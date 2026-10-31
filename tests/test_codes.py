import pypdfium2 as pdfium
import zxingcpp
from PIL import Image

from tilemark.codes import find_codes
from tilemark.processors import process_image, process_pdf

from conftest import make_page_with_code

QR = zxingcpp.BarcodeFormat.QRCode
DATA_MATRIX = zxingcpp.BarcodeFormat.DataMatrix
CONTENT = "DC04FR0000011E6A1E6A0101FR"  # 2D-Doc style payload


def _contains(outer, inner):
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def _read(image):
    return [code.text for code in zxingcpp.read_barcodes(image, formats=(QR, DATA_MATRIX))]


def test_finds_qr_code_with_margin():
    page, box = make_page_with_code(CONTENT, QR)
    (found,) = find_codes(page)
    assert _contains(found, box)


def test_finds_data_matrix():
    page, box = make_page_with_code(CONTENT, DATA_MATRIX)
    (found,) = find_codes(page)
    assert _contains(found, box)


def test_no_code_on_blank_page():
    assert find_codes(Image.new("RGB", (800, 600), "white")) == []


def test_image_code_left_untouched_and_readable(tmp_path):
    page, box = make_page_with_code(CONTENT, DATA_MATRIX)
    src = tmp_path / "notice.png"
    page.save(src)
    dst = tmp_path / "out.png"
    process_image(src, dst, "Test", 0.3)
    with Image.open(dst) as out:
        assert out.crop(box).tobytes() == page.crop(box).tobytes()
        assert _read(out) == [CONTENT]


def test_pdf_code_still_readable(tmp_path):
    page, _ = make_page_with_code(CONTENT, QR)
    src = tmp_path / "notice.pdf"
    page.save(src, resolution=150)
    dst = tmp_path / "out.pdf"
    process_pdf(src, dst, "Test", 0.3)
    rendered = pdfium.PdfDocument(dst)[0].render(scale=150 / 72).to_pil()
    assert _read(rendered) == [CONTENT]
