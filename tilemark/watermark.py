"""Watermark drawing: slanted text repeated across the whole image."""

import random
import secrets

from PIL import Image, ImageDraw, ImageFont

COLOR = (80, 80, 80)
ANGLE = 30
# Random spread, so the exact mask cannot be rebuilt and subtracted.
ANGLE_JITTER = 5
OPACITY_JITTER = 0.2
MIN_FONT_SIZE = 12

# Fonts tried in order; Pillow's built-in font is the last resort.
FONT_CANDIDATES = (
    "DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def apply_watermark(
    image: Image.Image,
    text: str,
    opacity: float = 0.30,
    rng: random.Random | None = None,
) -> Image.Image:
    """Return an RGB copy of `image` with `text` burned in diagonally everywhere.

    Angle, tiling offset and per-copy opacity vary randomly on each call;
    pass a seeded `rng` for reproducible output.
    """
    rng = rng or secrets.SystemRandom()
    base = image.convert("RGB")
    width, height = base.size
    font_size = max(MIN_FONT_SIZE, width // 28)
    font = _load_font(font_size)

    left, top, right, bottom = font.getbbox(text)
    step_x = (right - left) + font_size * 2
    step_y = (bottom - top) + font_size * 3

    # Square layer large enough to cover the whole image once rotated.
    side = int((width**2 + height**2) ** 0.5) + step_x
    mask = Image.new("L", (side, side), 0)
    draw = ImageDraw.Draw(mask)
    shift_x = rng.randrange(step_x)
    shift_y = rng.randrange(step_y)
    for row, y in enumerate(range(-shift_y, side, step_y)):
        offset = step_x // 2 if row % 2 else 0
        for x in range(offset - step_x - shift_x, side, step_x):
            jitter = rng.uniform(1 - OPACITY_JITTER, 1 + OPACITY_JITTER)
            alpha = min(255, round(255 * opacity * jitter))
            draw.text((x, y), text, font=font, fill=alpha)

    angle = ANGLE + rng.uniform(-ANGLE_JITTER, ANGLE_JITTER)
    mask = mask.rotate(angle, resample=Image.Resampling.BICUBIC)
    crop_left = (side - width) // 2
    crop_top = (side - height) // 2
    mask = mask.crop((crop_left, crop_top, crop_left + width, crop_top + height))

    color = Image.new("RGB", base.size, COLOR)
    return Image.composite(color, base, mask)
