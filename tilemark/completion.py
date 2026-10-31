"""Tab completion of folder and file paths at the interactive prompts, via readline."""

import os
import unicodedata
from collections.abc import Iterable
from pathlib import Path

_readline = None
_matches: list[str] = []
_suffixes: frozenset[str] = frozenset()


def _fold(name: str) -> str:
    # macOS stores names decomposed (NFD) while keyboards type composed (NFC).
    return unicodedata.normalize("NFC", name).casefold()


def complete_path(text: str, suffixes: Iterable[str] = ()) -> list[str]:
    """Folders, and files ending in one of `suffixes`, matching what was typed so far.

    The user's spelling of the prefix is kept; folders end with a slash.
    """
    if text == "~":
        return ["~/"]
    head, partial = os.path.split(text)
    directory = Path(os.path.expanduser(head or "."))
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []
    prefix = text[: len(text) - len(partial)]
    wanted = _fold(partial)
    suffixes = {suffix.lower() for suffix in suffixes}
    matches = []
    for entry in entries:
        if not _fold(entry.name).startswith(wanted):
            continue
        if entry.name.startswith(".") and not partial.startswith("."):
            continue
        if entry.is_dir():
            matches.append(f"{prefix}{entry.name}/")
        elif entry.suffix.lower() in suffixes:
            matches.append(f"{prefix}{entry.name}")
    return sorted(matches, key=_fold)


def _complete(text: str, state: int) -> str | None:
    """readline callback: called with state 0, 1, 2… until it returns None."""
    global _matches
    if state == 0:
        _matches = complete_path(text, _suffixes)
    return _matches[state] if state < len(_matches) else None


def _no_completion(text: str, state: int) -> None:
    return None


def install() -> None:
    """Load readline (line editing, history) and bind Tab to completion."""
    global _readline
    try:
        import readline
    except ImportError:  # Windows: plain input() without completion
        return
    # The whole line is one path, spaces included.
    readline.set_completer_delims("\t\n")
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    readline.set_completer(_no_completion)
    _readline = readline


def complete_paths(enabled: bool, suffixes: Iterable[str] = ()) -> None:
    """Turn path completion on for the next prompt, or off (e.g. for free text).

    Folders are always offered; files only when their extension is in `suffixes`.
    """
    global _suffixes
    _suffixes = frozenset(suffixes)
    if _readline is not None:
        _readline.set_completer(_complete if enabled else _no_completion)
