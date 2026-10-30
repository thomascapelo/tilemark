<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/logo-dark.svg">
    <img src="docs/brand/logo.svg" alt="tilemark" height="64">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/thomascapelo/tilemark/actions/workflows/ci.yml"><img src="https://github.com/thomascapelo/tilemark/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+">
</p>

<p align="center">
  Burn a tiled, hard-to-remove watermark into every PDF and image of a folder,<br>
  before sending your ID card, payslips or tax notices to a landlord, an agency or a bank.
</p>

![A fictitious payslip before and after tilemark](docs/images/before-after.png)

## Why

Rental and loan applications routinely ask for copies of identity documents.
Once sent, those copies can be reused for identity fraud. Writing the recipient
and the purpose across every page ("Rental application only - Dupont Agency -
2026-10-30") makes a leaked copy useless for anything else.

## Private by design

- **Runs entirely on your computer.** No upload, no network access, no telemetry.
- **The watermark is part of the pixels.** PDF pages are rasterized and rebuilt
  as images: there is no layer to delete in a PDF editor and no selectable text
  left underneath.
- **No predictable pattern.** Angle, tiling offset and per-copy opacity are
  randomized for every file, so the overlay cannot simply be rebuilt and
  subtracted.
- **Metadata is stripped**: PDF author and title, EXIF data including GPS
  location, ICC profiles, PNG text chunks.
- **Originals are never modified.** Results go to a `watermarked/` subfolder.

No watermark is impossible to remove, but a dense, explicit one makes misuse
slow, visible and not worth the effort.

## Install

Requires Python 3.10+ and [pipx](https://pipx.pypa.io/).

```bash
pipx install git+https://github.com/thomascapelo/tilemark
```

If `tilemark` is then "command not found", run `pipx ensurepath` once and open
a new terminal.

## Usage

```bash
tilemark ~/Documents/rental_application
```

Or run `tilemark` alone and type the folder path (Tab completes folder names)
or drag the folder into the terminal when prompted.
You are then asked for the watermark text; today's date is appended.

```
 tilemark   v0.1.0 · local only, nothing leaves this machine

◇  Watermark text
│  Rental application only - Dupont Agency - 2026-10-30
│
◇  Processing 3 files
│  ✓ id_card.pdf    2 pages
│  ✓ payslip.jpg
│  ▲ notes.txt      skipped · unsupported format
│
└  2 files watermarked in 0.8s
   ~/Documents/rental_application/watermarked
```

| Option | Effect |
|---|---|
| `--opacity 0.4` | Watermark strength, from 0.05 to 1.0 (default 0.30) |
| `--no-date` | Do not append today's date |
| `--version` | Show the version |

Supported formats: PDF, JPG/JPEG, PNG. Only files directly inside the folder
are processed, not subfolders. Hidden files are ignored. Unsupported,
corrupted or password-protected files are reported and the rest are still
processed. A PDF that looks truncated is processed but flagged
"possibly incomplete: check it".

**Tip:** name both the recipient and the purpose in the text. "CONFIDENTIAL"
protects much less than "Rental application only - Dupont Agency".

## How it works

1. Each PDF page is rendered at 150 DPI with [PDFium](https://pdfium.googlesource.com/pdfium/)
   (via `pypdfium2`), including annotations and filled-in form fields.
2. The text is drawn on a transparent layer, repeated in staggered rows, rotated
   by 30° ± 5°, and blended into the page.
3. A new PDF is assembled from the JPEG page images, with the original page
   sizes. Images are saved in their original format without metadata.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest          # tests
.venv/bin/ruff check .    # lint
.venv/bin/ruff format .   # format
```

- `tilemark/watermark.py` draws the randomized, tiled text on a Pillow image
- `tilemark/processors.py` handles PDF rasterization and image cleanup
- `tilemark/cli.py` handles prompts, the folder scan and the summary

## License

[MIT](LICENSE). Dependencies: [pypdfium2](https://github.com/pypdfium2-team/pypdfium2)
(Apache-2.0 / BSD-3-Clause) and [Pillow](https://python-pillow.org/) (MIT-CMU).
