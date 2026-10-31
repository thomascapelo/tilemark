import csv
import re
from datetime import datetime
from pathlib import Path

from tilemark import history


def test_reference_is_short_and_unambiguous():
    refs = {history.new_reference() for _ in range(200)}
    assert len(refs) > 190  # random
    for ref in refs:
        assert re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{4}", ref)  # no I, L, O, U


def test_history_file_lives_in_home():
    assert history.history_file() == Path.home() / ".tilemark" / "history.csv"


def test_record_appends_rows_with_header():
    when = datetime(2026, 10, 30, 14, 5, 0)
    path = history.record(
        "7KQ2", "Agency X - 2026-10-30 - Ref 7KQ2", Path("/docs"), ["a.pdf"], when
    )
    history.record("9ZP4", "Bank Y - Ref 9ZP4", Path("/docs"), ["a.pdf", "b.jpg"], when)
    with path.open(encoding="utf-8") as file:
        rows = list(csv.reader(file))
    assert rows[0] == ["date", "ref", "text", "folder", "files"]
    assert rows[1] == [
        "2026-10-30T14:05:00",
        "7KQ2",
        "Agency X - 2026-10-30 - Ref 7KQ2",
        "/docs",
        "a.pdf",
    ]
    assert rows[2][1] == "9ZP4"
    assert rows[2][4] == "a.pdf; b.jpg"
