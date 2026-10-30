import unicodedata

import pytest

from tilemark import completion
from tilemark.completion import complete_path


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Downloads").mkdir()
    (tmp_path / "Doc.txt").write_text("a file, not a folder")
    (tmp_path / ".hidden").mkdir()
    # macOS stores accented names decomposed (NFD).
    (tmp_path / unicodedata.normalize("NFD", "Téléchargements")).mkdir()
    return tmp_path


def test_completes_folders_only(home):
    assert complete_path(f"{home}/Doc") == [f"{home}/Documents/"]


def test_lists_all_matches(home):
    assert complete_path(f"{home}/Do") == [f"{home}/Documents/", f"{home}/Downloads/"]


def test_case_insensitive(home):
    assert complete_path(f"{home}/doc") == [f"{home}/Documents/"]


def test_accented_names_match_typed_text(home):
    (match,) = complete_path(f"{home}/tél")
    assert unicodedata.normalize("NFC", match) == f"{home}/Téléchargements/"


def test_keeps_tilde_prefix(home):
    assert complete_path("~/Docu") == ["~/Documents/"]
    assert complete_path("~") == ["~/"]


def test_relative_paths(home):
    assert complete_path("Dow") == ["Downloads/"]


def test_hidden_folders_only_when_asked(home):
    assert f"{home}/.hidden/" not in complete_path(f"{home}/")
    assert complete_path(f"{home}/.h") == [f"{home}/.hidden/"]


def test_missing_folder_gives_nothing(home):
    assert complete_path(f"{home}/nope/x") == []


def test_readline_callback_walks_matches(home):
    assert completion._complete(f"{home}/Do", 0) == f"{home}/Documents/"
    assert completion._complete(f"{home}/Do", 1) == f"{home}/Downloads/"
    assert completion._complete(f"{home}/Do", 2) is None


def test_no_completion_callback():
    assert completion._no_completion("anything", 0) is None
