import io
import sys
from pathlib import Path

from tilemark import ui


class FakeTerminal(io.StringIO):
    encoding = "utf-8"

    def isatty(self):
        return True


# pytest re-installs its own sys.stdout capture between fixture setup and the
# test call, so these helpers are called from inside each test.
def use_terminal(monkeypatch):
    """Make sys.stdout look like an interactive UTF-8 terminal."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setattr(sys, "stdout", FakeTerminal())


def use_cp1252(monkeypatch):
    """Make sys.stdout a non-interactive Windows cp1252 stream."""
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))


def _all_rendered():
    return [
        ui.badge("0.1.0"),
        ui.step("Watermark text"),
        ui.thread("hello"),
        ui.prompt(),
        ui.warning("note"),
        ui.file_line("ok", "a.pdf", 9, "2 pages"),
        ui.file_line("warn", "b.txt", 9, "skipped · unsupported format"),
        ui.file_line("error", "c.png", 9, "error · boom"),
        ui.footer(2, 1, 0.83, Path("/tmp/x/watermarked")),
        ui.footer(0, 0, 0.1, Path("/tmp/x/watermarked")),
        ui.clear_previous_line(),
    ]


def test_color_enabled_on_a_terminal(monkeypatch):
    use_terminal(monkeypatch)
    assert ui.color_enabled()
    assert "\x1b[" in ui.badge("0.1.0")


def test_color_disabled_when_not_a_tty():
    # Under pytest's capture, stdout is not a TTY.
    assert not ui.color_enabled()


def test_color_disabled_by_no_color(monkeypatch):
    use_terminal(monkeypatch)
    monkeypatch.setenv("NO_COLOR", "1")
    assert not ui.color_enabled()


def test_color_disabled_on_dumb_terminal(monkeypatch):
    use_terminal(monkeypatch)
    monkeypatch.setenv("TERM", "dumb")
    assert not ui.color_enabled()


def test_no_escape_codes_without_color(monkeypatch):
    use_terminal(monkeypatch)
    monkeypatch.setenv("NO_COLOR", "1")
    for rendered in _all_rendered():
        assert "\x1b" not in rendered


def test_badge_without_color():
    assert ui.badge("0.1.0") == "tilemark v0.1.0 · local only, nothing leaves this machine"


def test_unicode_symbols_kept_without_color():
    assert ui.step("Processing 3 files") == "◇  Processing 3 files"
    assert ui.thread("text") == "│  text"
    assert ui.thread() == "│"
    assert ui.file_line("ok", "a.pdf", 9) == "│  ✓ a.pdf"


def test_columns_line_up():
    names = ["id_card.pdf", "payslip.jpg", "a.png"]
    width = max(len(name) for name in names) + 4
    lines = [
        ui.file_line("ok", "id_card.pdf", width, "2 pages"),
        ui.file_line("warn", "payslip.jpg", width, "skipped · unsupported format"),
        ui.file_line("error", "a.png", width, "error · boom"),
    ]
    details = ["2 pages", "skipped", "error"]
    starts = {line.index(detail) for line, detail in zip(lines, details, strict=True)}
    assert len(starts) == 1
    assert lines[0] == "│  ✓ id_card.pdf    2 pages"


def test_ascii_fallback(monkeypatch):
    use_cp1252(monkeypatch)
    assert not ui.unicode_enabled()
    assert ui.step("Processing") == "*  Processing"
    assert ui.thread("text") == "|  text"
    assert ui.prompt() == "|  > "
    assert ui.footer(0, 0, 0.1, Path("/tmp/watermarked")) == "`  No files watermarked"
    lines = [
        ui.file_line("ok", "a.pdf", 9, "2 pages"),
        ui.file_line("warn", "b.txt", 9, "skipped"),
        ui.file_line("error", "c.png", 9, "error"),
    ]
    assert lines[0] == "|  ok a.pdf    2 pages"
    assert lines[1] == "|  !  b.txt    skipped"
    assert lines[2] == "|  x  c.png    error"
    for line in lines:
        line.encode("cp1252")


def test_shorten_home():
    assert ui.shorten_home(Path.home() / "Documents" / "x") == "~/Documents/x"
    assert ui.shorten_home(Path.home()) == "~"
    assert ui.shorten_home(Path("/tmp/elsewhere")) == "/tmp/elsewhere"


def test_footer_success():
    folder = Path.home() / "Documents" / "rental" / "watermarked"
    assert ui.footer(2, 0, 0.83, folder) == (
        "└  2 files watermarked in 0.8s\n   ~/Documents/rental/watermarked"
    )


def test_footer_singular_and_failures():
    assert ui.footer(1, 2, 1.0, Path("/tmp/watermarked")).splitlines()[0] == (
        "└  1 file watermarked · 2 failed in 1.0s"
    )
    assert ui.footer(0, 1, 0.2, Path("/tmp/watermarked")) == "└  No files watermarked · 1 failed"


def test_prompt_has_no_escape_codes_even_with_color(monkeypatch):
    # readline counts escape codes as visible characters and misplaces the cursor.
    use_terminal(monkeypatch)
    assert ui.color_enabled()
    assert "\x1b" not in ui.prompt()
    assert ui.prompt() == "│  › "


def test_hint_is_dim_thread_text(monkeypatch):
    assert ui.hint("Drag a folder here") == "│  Drag a folder here"
    use_terminal(monkeypatch)
    assert "\x1b[2m" in ui.hint("Drag a folder here")


def test_clear_several_lines(monkeypatch):
    assert ui.clear_previous_line(3) == ""  # no color: cannot rewrite
    use_terminal(monkeypatch)
    assert ui.clear_previous_line(3) == "\x1b[1A\x1b[2K" * 3
