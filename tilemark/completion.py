"""Tab completion of folder paths at the interactive prompts, via readline."""

import os
import unicodedata
from pathlib import Path

_readline = None
_matches: list[str] = []


def _fold(name: str) -> str:
    # macOS stores names decomposed (NFD) while keyboards type composed (NFC).
    return unicodedata.normalize("NFC", name).casefold()


def complete_path(text: str) -> list[str]:
    """Folders matching what was typed so far, keeping the user's spelling of the prefix."""
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
    matches = [
        f"{prefix}{entry.name}/"
        for entry in entries
        if _fold(entry.name).startswith(wanted)
        and (partial.startswith(".") or not entry.name.startswith("."))
        and entry.is_dir()
    ]
    return sorted(matches, key=_fold)


def _complete(text: str, state: int) -> str | None:
    """readline callback: called with state 0, 1, 2… until it returns None."""
    global _matches
    if state == 0:
        _matches = complete_path(text)
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


def complete_paths(enabled: bool) -> None:
    """Turn folder completion on for the next prompt, or off (e.g. for free text)."""
    if _readline is not None:
        _readline.set_completer(_complete if enabled else _no_completion)
