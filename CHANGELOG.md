# Changelog

## 0.2.1 — 2026-10-31

- The watermark outline now passes behind printed text instead of cutting
  through it: small text crossed by the watermark stays readable. It still
  resists brightness and levels removal, and still covers photos, hair
  included.

## 0.2.0 — 2026-10-31

- Redesigned terminal output.
- Files can be given instead of a folder (`tilemark id_card.pdf payslip.jpg`),
  or dragged into the terminal at the prompt.
- Tab completion of folders and supported files at the path prompt, with line
  editing and history.
- Watermark hardened against brightness, levels and color-channel removal: a
  thin outline as dark as the document's text, inverting the text it crosses,
  plus a random wave distortion. A regression test runs the attack.
- QR codes and 2D-Doc (Data Matrix) codes are left untouched so they stay
  scannable. New dependency: zxing-cpp (Apache-2.0).
- Each run adds a short reference (`Ref 7KQ2`) to the text and logs it in
  `~/.tilemark/history.csv`; `--no-ref` disables both.
- About 3× faster watermarking per page.

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
