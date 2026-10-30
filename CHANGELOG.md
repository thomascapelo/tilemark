# Changelog

## 0.1.0 — 2026-10-30

First release.

- Watermark every PDF, JPG and PNG directly inside a folder; results go to
  `<folder>/watermarked/`, originals are never modified.
- Watermark burned into the pixels: PDF pages are rasterized at 150 DPI and
  rebuilt as an image-only PDF.
- Randomized angle, tiling offset and per-copy opacity, so the overlay cannot
  be rebuilt and subtracted.
- Metadata stripped (PDF info, EXIF including GPS, ICC, PNG text chunks).
- Today's date appended to the text (`--no-date` to disable), adjustable
  `--opacity`.
- Handles Finder drag and drop, phone photo orientation, transparent and
  16-bit PNGs, password-protected, corrupted and truncated PDFs.
