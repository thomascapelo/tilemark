"""Terminal rendering: colors, symbols and layout of tilemark's output.

Every helper returns a string; the CLI prints it. Colors and symbols are
decided at call time from sys.stdout, so redirected or non-UTF-8 output
degrades gracefully.
"""

import os
import sys
from pathlib import Path

ACCENT = "38;2;226;85;58"
ACCENT_BG = "48;2;226;85;58"
INK = "38;2;16;20;25"
SUCCESS = "38;2;79;178;122"
WARNING = "38;2;217;162;58"
THREAD = "38;2;58;63;70"
BOLD = "1"
DIM = "2"
UNDERLINE = "4"

UNICODE_SYMBOLS = {
    "step": "◇",
    "thread": "│",
    "end": "└",
    "input": "›",
    "ok": "✓",
    "warn": "▲",
    "error": "✗",
}
ASCII_SYMBOLS = {
    "step": "*",
    "thread": "|",
    "end": "`",
    "input": ">",
    "ok": "ok",
    "warn": "!",
    "error": "x",
}
STATUS_COLORS = {"ok": SUCCESS, "warn": WARNING, "error": ACCENT}

TAGLINE = "local only, nothing leaves this machine"


def color_enabled() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()


def unicode_enabled() -> bool:
    try:
        "".join(UNICODE_SYMBOLS.values()).encode(sys.stdout.encoding or "ascii")
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _symbol(name: str) -> str:
    return (UNICODE_SYMBOLS if unicode_enabled() else ASCII_SYMBOLS)[name]


def style(text: str, *codes: str) -> str:
    if not codes or not color_enabled():
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def shorten_home(path: Path) -> str:
    """Show paths under the home directory as ~/…"""
    try:
        relative = path.relative_to(Path.home())
    except ValueError:
        return str(path)
    return "~" if relative == Path() else f"~/{relative.as_posix()}"


def badge(version: str) -> str:
    details = f"v{version} · {TAGLINE}"
    if not color_enabled():
        return f"tilemark {details}"
    return f"{style(' tilemark ', BOLD, INK, ACCENT_BG)}  {style(details, DIM)}"


def step(title: str) -> str:
    return f"{style(_symbol('step'), SUCCESS)}  {title}"


def thread(text: str = "") -> str:
    line = style(_symbol("thread"), THREAD)
    return f"{line}  {text}" if text else line


def prompt() -> str:
    """Input prompt that keeps the cursor on the thread.

    Deliberately uncolored: readline counts escape codes as visible characters
    and would misplace the cursor. The line is restyled once answered.
    """
    return f"{_symbol('thread')}  {_symbol('input')} "


def clear_previous_line(count: int = 1) -> str:
    """Move up and erase `count` lines, so an answer can be rewritten in place."""
    return "\x1b[1A\x1b[2K" * count if color_enabled() else ""


def hint(text: str) -> str:
    """Dim help line under a question step."""
    return thread(style(text, DIM))


def warning(text: str) -> str:
    return thread(f"{style(_symbol('warn'), WARNING)} {style(text, DIM)}")


def file_line(status: str, name: str, width: int, detail: str = "") -> str:
    """One processed file: status symbol, name padded to `width`, dim detail."""
    symbol_width = max(len(_symbol(key)) for key in STATUS_COLORS)
    symbol = style(_symbol(status).ljust(symbol_width), STATUS_COLORS[status])
    if not detail:
        return thread(f"{symbol} {name}")
    return thread(f"{symbol} {name.ljust(width)}{style(detail, DIM)}")


def footer(done: int, failed: int, seconds: float, output_dir: Path) -> str:
    end = style(_symbol("end"), THREAD)
    failures = style(f" · {failed} failed", ACCENT) if failed else ""
    if not done:
        return f"{end}  {style('No files watermarked', BOLD)}{failures}"
    summary = style(f"{done} file{'s' if done != 1 else ''} watermarked", BOLD)
    timing = style(f" in {seconds:.1f}s", DIM)
    location = style(shorten_home(output_dir.parent) + "/", DIM)
    return f"{end}  {summary}{failures}{timing}\n   {location}{style(output_dir.name, UNDERLINE)}"
