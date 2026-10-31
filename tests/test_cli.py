import csv
import os
import re
from datetime import date
from pathlib import Path

import pytest

from tilemark import __version__, cli
from tilemark.cli import build_text, clean_paths, main

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
def test_clean_paths(raw, expected):
    assert clean_paths(raw) == [Path(expected)]


def test_clean_paths_expands_home():
    assert clean_paths("~/folder") == [Path.home() / "folder"]


def test_clean_paths_existing_folder_with_apostrophe(tmp_path):
    folder = tmp_path / "Pièces d'identité"
    folder.mkdir()
    assert clean_paths(str(folder)) == [folder]


def test_clean_paths_existing_file_with_spaces(tmp_path):
    file = tmp_path / "ID card.pdf"
    file.write_bytes(b"x")
    assert clean_paths(str(file)) == [file]


def test_clean_paths_several_dropped_files():
    # Finder drops several files as one line of escaped paths.
    assert clean_paths("/x/ID\\ card.pdf /x/payslip.pdf ") == [
        Path("/x/ID card.pdf"),
        Path("/x/payslip.pdf"),
    ]


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
    assert "✓ id_card.pdf    2 pages" in output
    assert "✓ photo.JPG" in output
    assert "▲ notes.txt" in output and "skipped · unsupported format" in output
    assert ".DS_Store" not in output
    assert "other.pdf" not in output
    assert "2 files watermarked" in output
    assert "\x1b" not in output  # not a TTY: no colors
    assert output.startswith("tilemark v")


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
    assert "▲ protected.pdf" in output and "skipped · password" in output
    assert "▲ broken.pdf" in output
    assert "2 failed" in output


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


def test_missing_path(tmp_path, capsys):
    assert main([str(tmp_path / "missing")]) == 1
    assert "not found" in capsys.readouterr().err


def test_processes_single_file(tmp_path, answers, capsys):
    make_pdf(tmp_path / "id_card.pdf")
    make_jpeg_with_exif(tmp_path / "photo.jpg")
    answers("Agency X")

    assert main([str(tmp_path / "id_card.pdf")]) == 0

    out_dir = tmp_path / "watermarked"
    assert [p.name for p in out_dir.iterdir()] == ["id_card_watermarked.pdf"]
    output = capsys.readouterr().out
    assert "Processing 1 file" in output
    assert "1 file watermarked" in output


def test_processes_several_files(tmp_path, answers, capsys, isolated_home):
    make_pdf(tmp_path / "id_card.pdf")
    make_jpeg_with_exif(tmp_path / "photo.jpg")
    make_pdf(tmp_path / "not_this_one.pdf")
    answers("Agency X")

    paths = [str(tmp_path / "photo.jpg"), str(tmp_path / "id_card.pdf")]
    assert main([*paths, paths[0]]) == 0  # duplicates are processed once

    out_dir = tmp_path / "watermarked"
    assert sorted(p.name for p in out_dir.iterdir()) == [
        "id_card_watermarked.pdf",
        "photo_watermarked.jpg",
    ]
    assert "Processing 2 files" in capsys.readouterr().out
    with (isolated_home / ".tilemark" / "history.csv").open(encoding="utf-8") as file:
        (row,) = csv.DictReader(file)
    assert row["folder"] == str(tmp_path)
    assert row["files"] == "id_card.pdf; photo.jpg"


def test_unsupported_file_given_is_skipped(tmp_path, answers, capsys):
    (tmp_path / "notes.txt").write_text("hello")
    answers("Agency X")
    assert main([str(tmp_path / "notes.txt")]) == 0
    assert "skipped · unsupported format" in capsys.readouterr().out
    assert not (tmp_path / "watermarked").exists()


def test_refuses_files_from_different_folders(tmp_path, capsys):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    make_pdf(tmp_path / "a" / "one.pdf")
    make_pdf(tmp_path / "b" / "two.pdf")
    assert main([str(tmp_path / "a" / "one.pdf"), str(tmp_path / "b" / "two.pdf")]) == 1
    assert "same folder" in capsys.readouterr().err


def test_refuses_folder_and_files_together(tmp_path, capsys):
    (tmp_path / "sub").mkdir()
    make_pdf(tmp_path / "one.pdf")
    assert main([str(tmp_path / "sub"), str(tmp_path / "one.pdf")]) == 1
    assert "not both" in capsys.readouterr().err


def test_refuses_file_from_output_folder(tmp_path, capsys):
    out_dir = tmp_path / "watermarked"
    out_dir.mkdir()
    make_pdf(out_dir / "id_card_watermarked.pdf")
    assert main([str(out_dir / "id_card_watermarked.pdf")]) == 1
    assert "tilemark output" in capsys.readouterr().err


def test_asks_for_files_when_missing(tmp_path, answers, capsys):
    (tmp_path / "My docs").mkdir()
    folder = tmp_path / "My docs"
    make_pdf(folder / "id card.pdf")
    make_jpeg_with_exif(folder / "photo.jpg")
    escaped = str(folder).replace(" ", "\\ ")
    answers(f"{escaped}/id\\ card.pdf {escaped}/photo.jpg ", "Agency X")

    assert main([]) == 0

    assert sorted(p.name for p in (folder / "watermarked").iterdir()) == [
        "id card_watermarked.pdf",
        "photo_watermarked.jpg",
    ]
    assert "· 2 files" in capsys.readouterr().out


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
    assert "No files watermarked" in capsys.readouterr().out
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


def test_unexpected_error_marked_as_error(tmp_path, answers, monkeypatch, capsys):
    make_pdf(tmp_path / "id_card.pdf")

    def crash(src, dst, text, opacity):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "process_pdf", crash)
    answers("Agency X")
    assert main([str(tmp_path)]) == 1
    assert "✗ id_card.pdf" in capsys.readouterr().out


def test_no_dangling_prompt_when_input_is_piped(tmp_path, monkeypatch):
    prompts = []

    def fake_input(prompt=""):
        prompts.append(prompt)
        return "Agency X"

    monkeypatch.setattr("builtins.input", fake_input)
    main([str(tmp_path)])
    assert prompts == [""]  # pytest's stdin is not a TTY


class FakeKeyboard:
    def isatty(self):
        return True


def test_interactive_prompts_show_hints(tmp_path, monkeypatch, capsys):
    make_pdf(tmp_path / "id_card.pdf")
    answers = [str(tmp_path), "Agency X"]
    prompts = []

    def fake_input(prompt=""):
        prompts.append(prompt)
        return answers.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr("sys.stdin", FakeKeyboard())
    assert main(["--no-date", "--no-ref"]) == 0

    output = capsys.readouterr().out
    assert prompts == ["│  › ", "│  › "]
    assert "│  Drag a folder or files here, or type a path (Tab completes)" in output
    assert "│  Say who it is for and why" in output
    # Without color the answer cannot be rewritten in place, and printing it
    # again would only repeat what was typed.
    assert output.count("Agency X") == 0


def test_interactive_text_with_date_is_shown(tmp_path, monkeypatch, capsys):
    answers = ["Agency X"]
    monkeypatch.setattr("builtins.input", lambda prompt="": answers.pop(0))
    monkeypatch.setattr("sys.stdin", FakeKeyboard())
    main([str(tmp_path)])
    assert "│  Agency X - " in capsys.readouterr().out


def test_build_text_with_reference():
    assert (
        build_text("Agency X", today=date(2026, 10, 27), ref="7KQ2")
        == "Agency X - 2026-10-27 - Ref 7KQ2"
    )
    assert build_text("Agency X", with_date=False, ref="7KQ2") == "Agency X - Ref 7KQ2"


def test_reference_added_and_logged(tmp_path, answers, capsys, isolated_home):
    make_pdf(tmp_path / "id_card.pdf")
    make_jpeg_with_exif(tmp_path / "photo.jpg")
    answers("Agency X")
    assert main([str(tmp_path)]) == 0

    output = capsys.readouterr().out
    ref = re.search(r"Ref ([0-9A-Z]{4})", output).group(1)
    assert f"Ref {ref} · logged in ~/.tilemark/history.csv" in output
    with (isolated_home / ".tilemark" / "history.csv").open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]["ref"] == ref
    assert rows[0]["text"].startswith("Agency X - ") and rows[0]["text"].endswith(f"Ref {ref}")
    assert rows[0]["folder"] == str(tmp_path)
    assert rows[0]["files"] == "id_card.pdf; photo.jpg"


def test_no_ref_option(tmp_path, answers, capsys, isolated_home):
    make_pdf(tmp_path / "id_card.pdf")
    answers("Agency X")
    assert main([str(tmp_path), "--no-ref"]) == 0
    assert "Ref " not in capsys.readouterr().out
    assert not (isolated_home / ".tilemark").exists()


def test_nothing_logged_when_nothing_watermarked(tmp_path, answers, isolated_home):
    (tmp_path / "notes.txt").write_text("x")
    answers("Agency X")
    main([str(tmp_path)])
    assert not (isolated_home / ".tilemark").exists()


def test_history_failure_does_not_fail_the_run(tmp_path, answers, monkeypatch, capsys):
    make_pdf(tmp_path / "id_card.pdf")

    def broken(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(cli.history, "record", broken)
    answers("Agency X")
    assert main([str(tmp_path)]) == 0
    assert "could not log Ref" in capsys.readouterr().out
