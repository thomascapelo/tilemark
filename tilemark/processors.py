"""Turn a PDF or image file into its watermarked version."""

import io
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageOps

from .codes import find_codes
from .watermark import apply_watermark

DPI = 150
JPEG_QUALITY = 85


class ProcessingError(Exception):
    """Expected per-file failure; the message is shown to the user as is."""


def _mark(image: Image.Image, text: str, opacity: float) -> Image.Image:
    """Watermark one page or picture, sparing its QR and 2D-Doc codes."""
    return apply_watermark(image, text, opacity, keep_clear=find_codes(image))


def _open_pdf(src: Path) -> pdfium.PdfDocument:
    try:
        return pdfium.PdfDocument(src)
    except pdfium.PdfiumError as exc:
        if exc.err_code == pdfium.raw.FPDF_ERR_PASSWORD:
            raise ProcessingError("password-protected PDF") from exc
        raise ProcessingError("unreadable or corrupted PDF") from exc


def process_pdf(src: Path, dst: Path, text: str, opacity: float) -> tuple[int, bool]:
    """Rasterize each page, burn the watermark in and write an image-only PDF.

    Return the page count and whether the file looks truncated (no end-of-file
    marker), in which case pages may be blank or incomplete and the user
    should check them.
    """
    incomplete = b"%%EOF" not in src.read_bytes()[-1024:]
    source = _open_pdf(src)
    output = pdfium.PdfDocument.new()
    try:
        if len(source) == 0:
            raise ProcessingError("PDF has no pages")
        source.init_forms()  # so filled-in form fields are rendered too

        for page in source:
            # Size and rendering both account for the page's own rotation.
            width, height = page.get_size()
            image = page.render(scale=DPI / 72).to_pil()
            marked = _mark(image, text, opacity)

            buffer = io.BytesIO()
            marked.save(buffer, format="JPEG", quality=JPEG_QUALITY)
            buffer.seek(0)
            new_page = output.new_page(width, height)
            picture = pdfium.PdfImage.new(output)
            picture.load_jpeg(buffer, inline=False)
            picture.set_matrix(pdfium.PdfMatrix().scale(width, height))
            new_page.insert_obj(picture)
            new_page.gen_content()

        output.save(dst)
        return len(source), incomplete
    finally:
        output.close()
        source.close()


def _flatten(image: Image.Image) -> Image.Image:
    """Convert to RGB, laying any transparency over a white background."""
    if image.mode in ("I", "I;16", "I;16B", "I;16L", "I;16N"):
        # 16-bit grayscale: scale down to 8 bits, a plain convert would clip to white.
        image = image.convert("I").point(lambda value: value * (1 / 256)).convert("L")
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def process_image(src: Path, dst: Path, text: str, opacity: float) -> None:
    """Burn the watermark into an image and save it without metadata."""
    try:
        with Image.open(src) as image:
            upright = ImageOps.exif_transpose(image)
            marked = _mark(_flatten(upright), text, opacity)
    except (OSError, Image.DecompressionBombError) as exc:
        raise ProcessingError("unreadable or corrupted image") from exc

    # Drop EXIF (including GPS), ICC profile and anything else inherited from the original.
    marked.info.clear()
    if dst.suffix.lower() == ".png":
        marked.save(dst, format="PNG")
    else:
        marked.save(dst, format="JPEG", quality=JPEG_QUALITY)
