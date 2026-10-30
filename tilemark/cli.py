"""Command-line interface: watermark every PDF and image of a folder."""

import argparse
import shlex
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .processors import process_image, process_pdf

OUTPUT_DIR = "watermarked"
OUTPUT_SUFFIX = "_watermarked"
PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def build_text(raw: str, with_date: bool = True, today: date | None = None) -> str:
    text = raw.strip()
    if with_date:
        text = f"{text} - {(today or date.today()).isoformat()}"
    return text


def clean_path(raw: str) -> Path:
    """Accept a path pasted between quotes or dragged and dropped into the Terminal."""
    value = raw.strip()
    direct = Path(value).expanduser()
    if direct.is_dir():
        return direct
    # Undo shell quoting and escapes (\ , \', \(, \&…) added by the Terminal.
    try:
        parts = shlex.split(value)
    except ValueError:
        return direct
    return Path(parts[0]).expanduser() if len(parts) == 1 else direct


def _opacity(value: str) -> float:
    try:
        opacity = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number, e.g. 0.3") from None
    if not 0.05 <= opacity <= 1.0:
        raise argparse.ArgumentTypeError("must be between 0.05 and 1.0")
    return opacity


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tilemark",
        description="Burn a tiled watermark into every PDF and image of a folder.",
    )
    parser.add_argument("folder", nargs="?", help="folder to process (asked if omitted)")
    parser.add_argument(
        "--opacity",
        type=_opacity,
        default=0.30,
        help="watermark opacity, from 0.05 to 1.0 (default: 0.30)",
    )
    parser.add_argument("--no-date", action="store_true", help="do not append today's date")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _ask(prompt: str) -> str:
    while True:
        answer = input(prompt).strip()
        if answer:
            return answer
        print("  A value is required.")


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count > 1 else ''}"


def _visible_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith("."))


def _error(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return 1


def _run(args: argparse.Namespace) -> int:
    folder = clean_path(args.folder or _ask("Folder to watermark: "))
    if not folder.is_dir():
        return _error(f"“{folder}” is not a folder.")
    if folder.name == OUTPUT_DIR:
        return _error(f"“{folder}” is a tilemark output folder; pick the original folder.")

    output_dir = folder / OUTPUT_DIR
    try:
        files = _visible_files(folder)
        earlier = _visible_files(output_dir) if output_dir.is_dir() else []
    except OSError as exc:
        return _error(f"cannot read “{folder}”: {exc.strerror}.")

    text = build_text(_ask("Watermark text: "), with_date=not args.no_date)
    print(f"→ Watermark: “{text}”")
    if earlier:
        print(
            f"  Note: {OUTPUT_DIR}/ already contains {_plural(len(earlier), 'file')} "
            "from an earlier run; they are kept."
        )

    done = failed = 0
    for path in files:
        suffix = path.suffix.lower()
        if suffix not in PDF_SUFFIXES | IMAGE_SUFFIXES:
            print(f"  ⚠ {path.name}   skipped (unsupported format)")
            continue

        try:
            output_dir.mkdir(exist_ok=True)
        except OSError as exc:
            return _error(f"cannot create “{output_dir}”: {exc.strerror}.")
        dst = output_dir / f"{path.stem}{OUTPUT_SUFFIX}{path.suffix}"
        try:
            if suffix in PDF_SUFFIXES:
                pages, incomplete = process_pdf(path, dst, text, args.opacity)
                warning = ", possibly incomplete: check it" if incomplete else ""
                detail = f"({_plural(pages, 'page')}{warning})"
            else:
                process_image(path, dst, text, args.opacity)
                detail = ""
        except KeyboardInterrupt:
            dst.unlink(missing_ok=True)
            raise
        except Exception as exc:
            # One failing file must never stop the others.
            dst.unlink(missing_ok=True)
            print(f"  ✗ {path.name}   error: {exc or type(exc).__name__}")
            failed += 1
            continue
        print(f"  ✓ {path.name}   {detail}".rstrip())
        done += 1

    if done:
        print(f"{_plural(done, 'file')} watermarked → {output_dir}")
    elif not failed:
        print("No PDF or image to watermark.")
    elif output_dir.is_dir() and not any(output_dir.iterdir()):
        output_dir.rmdir()
    if failed:
        print(f"{_plural(failed, 'file')} failed.")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return _run(args)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return 1
