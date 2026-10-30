import os
from datetime import date
from pathlib import Path

import pytest

from tilemark import __version__, cli
from tilemark.cli import build_text, clean_path, main

from conftest import make_encrypted_pdf, make_jpeg_with_exif, make_pdf, make_truncated_pdf


@pytest.fixture
def answers(monkeypatch):
    """Simulate keyboard answers, in order."""

    def set_answers(*values):
        queue = list(values)
        monkeypatch.setattr("builtins.input", lambda prompt="": queue.pop(0))

    return set_answers


def test_build_text_adds_date():
    assert build_text("  Agency X  ", today=date(2026, 10, 27)) == "Agency X - 2026-10-27"


def test_build_text_without_date():
    assert build_text("Agency X", with_date=False) == "Agency X"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("/Users/x/My\\ Documents ", "/Users/x/My Documents"),  # Terminal drag and drop
        ("'/Users/x/My Documents'", "/Users/x/My Documents"),
        ('"/Users/x/My Documents"', "/Users/x/My Documents"),
        ("/Users/x/folder", "/Users/x/folder"),
        # Terminal.app also escapes apostrophes, brackets and ampersands.
        ("/Users/x/Pièces\\ d\\'identité ", "/Users/x/Pièces d'identité"),
        ("/Users/x/Rental\\ \\(2026\\)", "/Users/x/Rental (2026)"),
        ("/Users/x/Lease\\ \\&\\ guarantor", "/Users/x/Lease & guarantor"),
    ],
)
def test_clean_path(raw, expected):
    assert clean_path(raw) == Path(expected)


def test_clean_path_expands_home():
    assert clean_path("~/folder") == Path.home() / "folder"


def test_clean_path_existing_folder_with_apostrophe(tmp_path):
    folder = tmp_path / "Pièces d'identité"
    folder.mkdir()
    assert clean_path(str(folder)) == folder


def test_processes_folder(tmp_path, answers, capsys):
    make_pdf(tmp_path / "id_card.pdf")
    make_jpeg_with_exif(tmp_path / "photo.JPG")
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / ".DS_Store").write_bytes(b"\x00")
    (tmp_path / "subfolder").mkdir()
    make_pdf(tmp_path / "subfolder" / "other.pdf")
    answers("Agency X")

    assert main([str(tmp_path)]) == 0

    out_dir = tmp_path / "watermarked"
    assert sorted(p.name for p in out_dir.iterdir()) == [
        "id_card_watermarked.pdf",
        "photo_watermarked.JPG",
    ]
    output = capsys.readouterr().out
    assert "Agency X - " in output
    assert "✓ id_card.pdf" in output and "(2 pages)" in output
    assert "✓ photo.JPG" in output
    assert "⚠ notes.txt" in output and "skipped" in output
    assert ".DS_Store" not in output
    assert "other.pdf" not in output
    assert "2 files watermarked" in output


def test_asks_for_folder_when_missing(tmp_path, answers):
    make_pdf(tmp_path / "id_card.pdf")
    answers(f"'{tmp_path}'", "Agency X")
    assert main([]) == 0
    assert (tmp_path / "watermarked" / "id_card_watermarked.pdf").exists()


def test_empty_text_is_asked_again(tmp_path, answers):
    make_pdf(tmp_path / "id_card.pdf")
    answers("   ", "", "Agency X")
    assert main([str(tmp_path), "--no-date"]) == 0


def test_bad_files_reported_others_processed(tmp_path, answers, capsys):
    make_pdf(tmp_path / "good.pdf")
    make_encrypted_pdf(tmp_path / "protected.pdf")
    (tmp_path / "broken.pdf").write_bytes(b"not a pdf")
    answers("Agency X")

    assert main([str(tmp_path)]) == 1

    out_dir = tmp_path / "watermarked"
    assert sorted(p.name for p in out_dir.iterdir()) == ["good_watermarked.pdf"]
    output = capsys.readouterr().out
    assert "✗ protected.pdf" in output and "password" in output
    assert "✗ broken.pdf" in output
    assert "2 files failed" in output


def test_all_files_failing_leaves_no_output_folder(tmp_path, answers, capsys):
    (tmp_path / "broken.pdf").write_bytes(b"not a pdf")
    answers("Agency X")
    assert main([str(tmp_path)]) == 1
    assert not (tmp_path / "watermarked").exists()
    assert "0 file" not in capsys.readouterr().out


def test_truncated_pdf_flagged_in_output(tmp_path, answers, capsys):
    make_truncated_pdf(tmp_path / "truncated.pdf")
    answers("Agency X")
    assert main([str(tmp_path)]) == 0
    assert "possibly incomplete" in capsys.readouterr().out


def test_invalid_folder(tmp_path, capsys):
    assert main([str(tmp_path / "missing")]) == 1
    assert "is not a folder" in capsys.readouterr().err


def test_refuses_output_folder(tmp_path, capsys):
    out_dir = tmp_path / "watermarked"
    out_dir.mkdir()
    assert main([str(out_dir)]) == 1
    assert "output folder" in capsys.readouterr().err


def test_warns_about_earlier_outputs(tmp_path, answers, capsys):
    make_pdf(tmp_path / "id_card.pdf")
    out_dir = tmp_path / "watermarked"
    out_dir.mkdir()
    (out_dir / "old_watermarked.pdf").write_bytes(b"old")
    answers("Agency X")
    assert main([str(tmp_path)]) == 0
    assert "already contains 1 file" in capsys.readouterr().out


def test_output_path_taken_by_a_file(tmp_path, answers, capsys):
    make_pdf(tmp_path / "id_card.pdf")
    (tmp_path / "watermarked").write_text("not a folder")
    answers("Agency X")
    assert main([str(tmp_path)]) == 1
    assert "Error:" in capsys.readouterr().err


@pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="needs POSIX permissions enforced (not root, not Windows)",
)
def test_read_only_folder(tmp_path, answers, capsys):
    make_pdf(tmp_path / "id_card.pdf")
    tmp_path.chmod(0o555)
    answers("Agency X")
    try:
        assert main([str(tmp_path)]) == 1
    finally:
        tmp_path.chmod(0o755)
    assert "Error:" in capsys.readouterr().err


def test_empty_folder(tmp_path, answers, capsys):
    answers("Agency X")
    assert main([str(tmp_path)]) == 0
    assert "No PDF or image" in capsys.readouterr().out
    assert not (tmp_path / "watermarked").exists()


def test_originals_untouched(tmp_path, answers):
    src = make_pdf(tmp_path / "id_card.pdf")
    before = src.read_bytes()
    answers("Agency X")
    main([str(tmp_path)])
    assert src.read_bytes() == before


def test_invalid_opacity_rejected(tmp_path):
    with pytest.raises(SystemExit):
        main([str(tmp_path), "--opacity", "2"])


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert f"tilemark {__version__}" in capsys.readouterr().out


def test_ctrl_c_exits_cleanly(tmp_path, monkeypatch, capsys):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrupt)
    assert main([str(tmp_path)]) == 1
    assert "Cancelled" in capsys.readouterr().out


def test_ctrl_c_while_writing_leaves_no_partial_file(tmp_path, answers, monkeypatch):
    make_pdf(tmp_path / "id_card.pdf")

    def write_then_interrupt(src, dst, text, opacity):
        dst.write_bytes(b"half a pdf")
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "process_pdf", write_then_interrupt)
    answers("Agency X")
    assert main([str(tmp_path)]) == 1
    assert not (tmp_path / "watermarked" / "id_card_watermarked.pdf").exists()
