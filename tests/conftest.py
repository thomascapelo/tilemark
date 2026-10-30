from pathlib import Path

import pikepdf
from PIL import Image

SECRET_TEXT = "Jane Doe 123456789"


def make_pdf(path: Path, pages: int = 2, rotate: int = 0, password: str | None = None) -> Path:
    pdf = pikepdf.new()
    font = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.Helvetica,
        )
    )
    for number in range(pages):
        text = f"BT /F1 14 Tf 72 770 Td ({SECRET_TEXT} page {number + 1}) Tj ET"
        page = pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 595, 842],  # A4 in points
            Contents=pdf.make_stream(text.encode()),
            Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
        )
        if rotate:
            page.Rotate = rotate
        pdf.pages.append(pikepdf.Page(page))
    pdf.docinfo["/Title"] = "ID card"
    pdf.docinfo["/Author"] = "Jane Doe"
    options = {}
    if password:
        options["encryption"] = pikepdf.Encryption(user=password, owner="owner", R=6)
    pdf.save(path, **options)
    return path


def make_encrypted_pdf(path: Path) -> Path:
    return make_pdf(path, pages=1, password="secret")


def make_truncated_pdf(path: Path) -> Path:
    """PDF cut short, like an interrupted download, but still openable."""
    data = make_pdf(path).read_bytes()
    path.write_bytes(data[: data.rindex(b"%%EOF")])
    return path


EXIF_MAKE = 0x010F
EXIF_MODEL = 0x0110
EXIF_ORIENTATION = 0x0112


def make_jpeg_with_exif(path: Path, orientation: int = 1) -> Path:
    image = Image.new("RGB", (400, 300), "white")
    exif = Image.Exif()
    exif[EXIF_MAKE] = "Apple"
    exif[EXIF_MODEL] = "iPhone"
    exif[EXIF_ORIENTATION] = orientation
    image.save(path, format="JPEG", exif=exif)
    return path


def make_transparent_png(path: Path) -> Path:
    Image.new("RGBA", (400, 300), (0, 0, 0, 0)).save(path, format="PNG")
    return path


def make_16bit_gray_png(path: Path) -> Path:
    """Dark-gray 16-bit grayscale PNG, as some scanner software saves them."""
    Image.new("I;16", (400, 300), 10000).save(path, format="PNG")
    return path
