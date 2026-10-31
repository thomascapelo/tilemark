"""Command-line interface: watermark every PDF and image of a folder."""

import argparse
import os
import shlex
import sys
import time
from datetime import date
from pathlib import Path

from . import __version__, completion, history, ui
from .processors import ProcessingError, process_image, process_pdf

OUTPUT_DIR = "watermarked"
OUTPUT_SUFFIX = "_watermarked"
PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def build_text(
    raw: str, with_date: bool = True, today: date | None = None, ref: str | None = None
) -> str:
    text = raw.strip()
    if with_date:
        text = f"{text} - {(today or date.today()).isoformat()}"
    if ref:
        text = f"{text} - Ref {ref}"
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
    parser.add_argument(
        "--no-ref",
        action="store_true",
        help="do not add a reference to the text nor log the run in ~/.tilemark/history.csv",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


FOLDER_HINT = "Drag a folder here, or type its path (Tab completes)"
TEXT_HINT = 'Say who it is for and why, e.g. "Rental application only - Dupont Agency"'


def _ask(title: str, hint: str, *, paths: bool = False, display=str) -> str:
    """Ask on a `◇ title` step, then replace the hint and prompt with the answer.

    `display` turns the raw answer into what is shown once answered.
    """
    print(ui.step(title))
    # Piped answers are not echoed, so a hint and prompt would be left dangling.
    interactive = sys.stdin.isatty()
    lines = 0
    if interactive:
        print(ui.hint(hint))
        lines += 1
    completion.complete_paths(paths)
    while True:
        answer = input(ui.prompt() if interactive else "").strip()
        lines += 1
        if answer:
            break
        print(ui.clear_previous_line() + ui.warning("A value is required."))

    shown = display(answer)
    if interactive and ui.color_enabled():
        print(ui.clear_previous_line(lines) + ui.thread(ui.style(shown, ui.DIM)))
    elif not interactive or shown != answer:
        print(ui.thread(ui.style(shown, ui.DIM)))
    return answer


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count != 1 else ''}"


def _visible_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith("."))


def _error(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return 1


def _process(path: Path, dst: Path, text: str, opacity: float) -> tuple[str, str]:
    """Watermark one supported file; return its status and detail for display."""
    if path.suffix.lower() in PDF_SUFFIXES:
        pages, incomplete = process_pdf(path, dst, text, opacity)
        if incomplete:
            return "warn", "possibly incomplete: check it"
        return "ok", _plural(pages, "page")
    process_image(path, dst, text, opacity)
    return "ok", ""


def _run(args: argparse.Namespace) -> int:
    print(ui.badge(__version__))
    print()

    if args.folder:
        folder = clean_path(args.folder)
    else:
        folder = clean_path(
            _ask(
                "Folder to watermark",
                FOLDER_HINT,
                paths=True,
                display=lambda raw: ui.shorten_home(clean_path(raw)),
            )
        )
        print(ui.thread())
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

    with_date = not args.no_date
    ref = None if args.no_ref else history.new_reference()
    text = build_text(
        _ask("Watermark text", TEXT_HINT, display=lambda raw: build_text(raw, with_date, ref=ref)),
        with_date,
        ref=ref,
    )
    print(ui.thread())

    print(ui.step(f"Processing {_plural(len(files), 'file')}"))
    if earlier:
        print(
            ui.warning(
                f"{OUTPUT_DIR}/ already contains {_plural(len(earlier), 'file')} "
                "from an earlier run; they are kept"
            )
        )
    width = max((len(path.name) for path in files), default=0) + 4
    started = time.perf_counter()
    done = failed = 0
    watermarked = []
    for path in files:
        if path.suffix.lower() not in PDF_SUFFIXES | IMAGE_SUFFIXES:
            print(ui.file_line("warn", path.name, width, "skipped · unsupported format"))
            continue

        try:
            output_dir.mkdir(exist_ok=True)
        except OSError as exc:
            return _error(f"cannot create “{output_dir}”: {exc.strerror}.")
        dst = output_dir / f"{path.stem}{OUTPUT_SUFFIX}{path.suffix}"
        try:
            status, detail = _process(path, dst, text, args.opacity)
        except KeyboardInterrupt:
            dst.unlink(missing_ok=True)
            raise
        except ProcessingError as exc:
            dst.unlink(missing_ok=True)
            print(ui.file_line("warn", path.name, width, f"skipped · {exc}"))
            failed += 1
            continue
        except Exception as exc:
            # One failing file must never stop the others.
            dst.unlink(missing_ok=True)
            message = str(exc) or type(exc).__name__
            print(ui.file_line("error", path.name, width, f"error · {message}"))
            failed += 1
            continue
        print(ui.file_line(status, path.name, width, detail))
        watermarked.append(path.name)
        done += 1

    if not done and output_dir.is_dir() and not any(output_dir.iterdir()):
        output_dir.rmdir()
    print(ui.thread())
    print(ui.footer(done, failed, time.perf_counter() - started, output_dir))
    if ref and watermarked:
        _log(ref, text, folder, watermarked)
    return 1 if failed else 0


def _log(ref: str, text: str, folder: Path, files: list[str]) -> None:
    """Record the run so a leaked copy can be traced back; never fail the run over it."""
    try:
        path = history.record(ref, text, folder, files)
    except OSError as exc:
        print(ui.warning(f"could not log Ref {ref}: {exc.strerror or exc}"))
        return
    print(ui.note(f"Ref {ref} · logged in {ui.shorten_home(path)}"))


def main(argv: list[str] | None = None) -> int:
    if os.name == "nt":
        os.system("")  # enables ANSI escape processing in the Windows console
    args = _parse_args(argv)
    if sys.stdin.isatty():
        completion.install()
    try:
        return _run(args)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return 1
