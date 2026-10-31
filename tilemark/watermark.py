"""Watermark drawing: slanted, wavy text tiled across the whole image.

The text is drawn twice from one layout: a light gray fill that keeps it
legible, and a thin outline that inverts the page beneath it. On blank paper
the outline is as dark as the document's own text, and where it crosses that
text it turns it light, so no brightness, contrast or color-channel adjustment
can separate the watermark from the document. Angle, tiling offset, wave and
per-copy strength are random on every call, so the overlay cannot be rebuilt
and subtracted either.
"""

import math
import random
import secrets
from collections.abc import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps

FILL_COLOR = (80, 80, 80)
ANGLE = 30
ANGLE_JITTER = 5
STRENGTH_JITTER = 0.2
MIN_FONT_SIZE = 12
# At the default opacity (0.30) the fill stays light and the outline near-black.
FILL_GAIN = 0.75
OUTLINE_GAIN = 3.4
WAVE_STRIP = 8

# Fonts tried in order; Pillow's built-in font is the last resort.
FONT_CANDIDATES = (
    "DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
)

Box = tuple[int, int, int, int]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _steps(text: str, font: ImageFont.FreeTypeFont, font_size: int) -> tuple[int, int]:
    left, top, right, bottom = font.getbbox(text)
    return (right - left) + font_size * 2, (bottom - top) + font_size * 4


def _tile(side: int, text: str, font_size: int, rng: random.Random) -> tuple[Image.Image, ...]:
    """Fill and outline masks of the text, tiled in staggered rows from a random offset."""
    font = _load_font(font_size)
    step_x, step_y = _steps(text, font, font_size)
    # At least 2 px, so anti-aliasing cannot leave the outline lighter than text.
    stroke = max(2, font_size // 20)

    fill = Image.new("L", (side, side), 0)
    outline = Image.new("L", (side, side), 0)
    fill_draw, outline_draw = ImageDraw.Draw(fill), ImageDraw.Draw(outline)
    shift_x, shift_y = rng.randrange(step_x), rng.randrange(step_y)
    for row, y in enumerate(range(-shift_y, side, step_y)):
        offset = step_x // 2 if row % 2 else 0
        for x in range(offset - step_x - shift_x, side, step_x):
            alpha = round(255 * rng.uniform(1 - STRENGTH_JITTER, 1))
            fill_draw.text((x, y), text, font=font, fill=alpha)
            # The outline stays at full strength: it is what thresholds cannot remove.
            outline_draw.text((x, y), text, font=font, fill=0, stroke_width=stroke, stroke_fill=255)
    return fill, outline


def _wave_mesh(side: int, amplitude: float, rng: random.Random) -> list:
    """Vertical sine displacement, as a mesh of thin strips for Image.transform."""
    period = rng.uniform(0.35, 0.6) * side
    phase = rng.uniform(0, 2 * math.pi)

    def shift(x: int) -> float:
        return amplitude * math.sin(2 * math.pi * x / period + phase)

    mesh = []
    for x0 in range(0, side, WAVE_STRIP):
        x1 = min(side, x0 + WAVE_STRIP)
        d0, d1 = shift(x0), shift(x1)
        mesh.append(((x0, 0, x1, side), (x0, d0, x0, side + d0, x1, side + d1, x1, d1)))
    return mesh


def _rotation(side: int, size: tuple[int, int], angle: float) -> tuple[float, ...]:
    """Affine data rotating a square layer of `side` pixels by `angle` degrees about its center,
    as Image.rotate does, into an output of `size` centered on the same point."""
    radians = -math.radians(angle)
    a, b = math.cos(radians), math.sin(radians)
    d, e = -b, a
    out_x, out_y = size[0] / 2, size[1] / 2
    center = side / 2
    return (a, b, center - a * out_x - b * out_y, d, e, center - d * out_x - e * out_y)


def _scaled(mask: Image.Image, factor: float) -> Image.Image:
    factor = min(1.0, factor)
    return mask.point(lambda value: round(value * factor))


def apply_watermark(
    image: Image.Image,
    text: str,
    opacity: float = 0.30,
    rng: random.Random | None = None,
    keep_clear: Iterable[Box] = (),
) -> Image.Image:
    """Return an RGB copy of `image` with `text` burned in diagonally everywhere.

    `keep_clear` lists boxes (left, top, right, bottom) left untouched, such as
    QR codes that must stay scannable. Pass a seeded `rng` for reproducible output.
    """
    rng = rng or secrets.SystemRandom()
    base = image.convert("RGB")
    width, height = base.size
    font_size = max(MIN_FONT_SIZE, width // 28)

    # Square layer just large enough to cover the whole image once rotated and waved.
    amplitude = rng.uniform(0.25, 0.4) * font_size
    side = math.ceil(math.hypot(width, height) + 2 * amplitude) + 2
    fill, outline = _tile(side, text, font_size, rng)
    mesh = _wave_mesh(side, amplitude, rng)
    rotation = _rotation(side, (width, height), ANGLE + rng.uniform(-ANGLE_JITTER, ANGLE_JITTER))

    masks = []
    for mask in (fill, outline):
        mask = mask.transform(mask.size, Image.Transform.MESH, mesh, Image.Resampling.BILINEAR)
        # Rotate straight into the image's size: only the pixels kept are computed.
        mask = mask.transform(
            (width, height), Image.Transform.AFFINE, rotation, Image.Resampling.BICUBIC
        )
        for box in keep_clear:
            mask.paste(0, box)
        masks.append(mask)
    fill, outline = masks

    filled = Image.composite(
        Image.new("RGB", base.size, FILL_COLOR), base, _scaled(fill, opacity * FILL_GAIN)
    )
    return Image.composite(
        ImageOps.invert(filled), filled, _scaled(outline, opacity * OUTLINE_GAIN)
    )
