"""Generate docs/images/before-after.png for the README from a fictitious document."""

import random
from pathlib import Path

from PIL import Image, ImageDraw

from tilemark.watermark import _load_font, apply_watermark

OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "images" / "before-after.png"
DOC_SIZE = (620, 820)
WATERMARK = "Rental application only - Dupont Agency - 2026-10-30"
INK = (30, 30, 30)
MUTED = (110, 110, 110)
RULE = (200, 200, 200)


def make_document() -> Image.Image:
    doc = Image.new("RGB", DOC_SIZE, "white")
    draw = ImageDraw.Draw(doc)
    title, label, value = _load_font(30), _load_font(17), _load_font(19)

    draw.text((40, 40), "PAYSLIP", font=title, fill=INK)
    draw.text((40, 82), "Example Corp · October 2026", font=label, fill=MUTED)
    draw.text((430, 48), "SPECIMEN", font=label, fill=(190, 40, 40))
    draw.line((40, 120, 580, 120), fill=RULE, width=2)

    fields = [
        ("Employee", "Jane Doe"),
        ("Employee ID", "0000-1234-5678"),
        ("Address", "1 Example Street, Springfield"),
        ("Social security no.", "1 23 45 67 890 123"),
        ("Position", "Product designer"),
    ]
    y = 145
    for name, content in fields:
        draw.text((40, y), name, font=label, fill=MUTED)
        draw.text((260, y), content, font=value, fill=INK)
        y += 42

    draw.line((40, y + 5, 580, y + 5), fill=RULE, width=2)
    y += 25
    for name, amount in [("Gross salary", "3,250.00"), ("Deductions", "-712.40")]:
        draw.text((40, y), name, font=value, fill=INK)
        draw.text((470, y), amount, font=value, fill=INK)
        y += 40
    draw.rectangle((40, y + 10, 580, y + 70), fill=(242, 242, 242))
    draw.text((60, y + 28), "Net pay", font=title, fill=INK)
    draw.text((430, y + 28), "2,537.60", font=title, fill=INK)

    for line in range(7):
        top = 640 + line * 22
        draw.line((40, top, 580 - (line % 3) * 90, top), fill=RULE, width=8)
    return doc


def main() -> None:
    before = make_document()
    after = apply_watermark(before, WATERMARK, rng=random.Random(7))

    margin, header = 40, 70
    width = DOC_SIZE[0] * 2 + margin * 3
    height = DOC_SIZE[1] + header + margin
    canvas = Image.new("RGB", (width, height), (236, 239, 243))
    draw = ImageDraw.Draw(canvas)
    font = _load_font(26)
    for index, (name, image) in enumerate([("Before", before), ("After", after)]):
        left = margin + index * (DOC_SIZE[0] + margin)
        draw.text((left, 22), name, font=font, fill=INK)
        canvas.paste(image, (left, header))
        draw.rectangle(
            (left - 1, header - 1, left + DOC_SIZE[0], header + DOC_SIZE[1]), outline=RULE
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT, optimize=True)
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
