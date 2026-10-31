import random

from PIL import Image, ImageChops, ImageDraw

from tilemark.watermark import apply_watermark


def _quadrants(width, height):
    w, h = width // 2, height // 2
    return [(0, 0, w, h), (w, 0, width, h), (0, h, w, height), (w, h, width, height)]


def test_same_size_and_rgb():
    original = Image.new("RGB", (800, 600), "white")
    result = apply_watermark(original, "Test - 27/10/2026")
    assert result.size == original.size
    assert result.mode == "RGB"


def test_covers_every_quadrant():
    original = Image.new("RGB", (800, 600), "white")
    result = apply_watermark(original, "Test - 27/10/2026")
    diff = ImageChops.difference(original, result)
    for box in _quadrants(800, 600):
        assert diff.crop(box).getbbox() is not None, f"no watermark in quadrant {box}"


def test_does_not_modify_input():
    original = Image.new("RGB", (400, 300), "white")
    apply_watermark(original, "Test")
    assert original.getextrema() == ((255, 255), (255, 255), (255, 255))


def test_higher_opacity_is_darker():
    original = Image.new("RGB", (400, 300), "white")
    light = apply_watermark(original, "Test", opacity=0.1).convert("L")
    dark = apply_watermark(original, "Test", opacity=0.9).convert("L")
    assert dark.getextrema()[0] < light.getextrema()[0]


def test_tiny_image_and_long_text():
    original = Image.new("RGB", (40, 30), "white")
    long_text = "Uniquement pour location - Agence Dupont et Associés - 27/10/2026"
    result = apply_watermark(original, long_text)
    assert result.size == (40, 30)


def test_accepts_non_rgb_input():
    original = Image.new("L", (400, 300), 255)
    result = apply_watermark(original, "Test")
    assert result.mode == "RGB"


def test_layout_is_random_per_call():
    # A fixed layout lets anyone rebuild the mask and subtract it.
    original = Image.new("RGB", (400, 300), "white")
    first = apply_watermark(original, "Test")
    second = apply_watermark(original, "Test")
    assert ImageChops.difference(first, second).getbbox() is not None


def test_layout_reproducible_with_seeded_rng():
    original = Image.new("RGB", (400, 300), "white")
    first = apply_watermark(original, "Test", rng=random.Random(42))
    second = apply_watermark(original, "Test", rng=random.Random(42))
    assert ImageChops.difference(first, second).getbbox() is None


def _document():
    """Black text on white paper, like most supporting documents."""
    from tilemark.watermark import _load_font

    doc = Image.new("RGB", (1240, 900), "white")
    draw = ImageDraw.Draw(doc)
    font = _load_font(34)
    for line in range(14):
        draw.text(
            (80, 60 + line * 58),
            f"Jane Doe 0000-1234-{line:04d}  1,0{line:02d}.00",
            font=font,
            fill=25,
        )
    return doc


def _whiten_above(gray, threshold):
    return gray.point(lambda v: 255 if v >= threshold else v)


def _channel_max(image):
    red, green, blue = image.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def test_no_brightness_threshold_cleans_the_document():
    """The "levels" attack: whiten everything lighter than some gray.

    For every threshold, the attacker must either keep visible watermark
    traces or lose the document's own text.
    """
    doc = _document()
    marked = apply_watermark(doc, "Rental application only - Dupont Agency", rng=random.Random(5))
    clean = doc.convert("L")
    text_pixels = sum(1 for v in clean.get_flattened_data() if v < 90)
    for attacked_source in (marked.convert("L"), _channel_max(marked)):
        for threshold in range(30, 255, 5):
            attacked = _whiten_above(attacked_source, threshold)
            reference = _whiten_above(clean, threshold)
            differing = ImageChops.difference(attacked, reference).point(
                lambda v: 255 if v > 80 else 0
            )
            traces = differing.histogram()[255] / (doc.width * doc.height)
            text_kept = sum(1 for v in reference.get_flattened_data() if v < 90) / text_pixels
            cleaned = traces < 0.01 and text_kept > 0.9
            assert not cleaned, f"threshold {threshold} removes the watermark ({traces:.2%} left)"


def test_keep_clear_areas_are_untouched():
    original = Image.new("RGB", (800, 600), (200, 210, 220))
    box = (500, 350, 700, 550)
    result = apply_watermark(original, "Test", keep_clear=[box], rng=random.Random(1))
    assert result.crop(box).tobytes() == original.crop(box).tobytes()
    assert ImageChops.difference(original, result).getbbox() is not None
