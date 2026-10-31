"""Local log of every run, to trace a leaked copy back to the recipient it was sent to."""

import csv
import secrets
from datetime import datetime
from pathlib import Path

# Crockford base32: no I, L, O or U, so a reference is easy to read back.
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
COLUMNS = ["date", "ref", "text", "folder", "files"]


def new_reference(length: int = 4) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def history_file() -> Path:
    return Path.home() / ".tilemark" / "history.csv"


def record(
    ref: str, text: str, folder: Path, files: list[str], when: datetime | None = None
) -> Path:
    """Append one run to the history file, creating it with a header if needed."""
    path = history_file()
    path.parent.mkdir(exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if is_new:
            writer.writerow(COLUMNS)
        moment = (when or datetime.now()).isoformat(timespec="seconds")
        writer.writerow([moment, ref, text, str(folder), "; ".join(files)])
    return path
