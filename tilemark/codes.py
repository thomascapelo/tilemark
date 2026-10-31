"""Find QR codes and Data Matrix codes (the French 2D-Doc) so the watermark spares them.

Landlords and agencies scan 2D-Doc codes to check that a tax notice or a
payslip is genuine; a watermark drawn over them could make them unreadable.
"""

import zxingcpp
from PIL import Image

from .watermark import Box

FORMATS = (zxingcpp.BarcodeFormat.QRCode, zxingcpp.BarcodeFormat.DataMatrix)
# Quiet zone kept around each code, relative to its size.
MARGIN = 0.15
MIN_MARGIN = 8


def find_codes(image: Image.Image) -> list[Box]:
    """Boxes (left, top, right, bottom) around every readable code, with a margin."""
    boxes = []
    for code in zxingcpp.read_barcodes(image, formats=FORMATS):
        corners = code.position
        points = (corners.top_left, corners.top_right, corners.bottom_right, corners.bottom_left)
        xs, ys = [p.x for p in points], [p.y for p in points]
        margin = max(MIN_MARGIN, round(MARGIN * max(max(xs) - min(xs), max(ys) - min(ys))))
        boxes.append(
            (
                max(0, min(xs) - margin),
                max(0, min(ys) - margin),
                min(image.width, max(xs) + margin + 1),
                min(image.height, max(ys) + margin + 1),
            )
        )
    return boxes
