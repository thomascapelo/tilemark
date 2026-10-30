import random

from PIL import Image, ImageChops

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
