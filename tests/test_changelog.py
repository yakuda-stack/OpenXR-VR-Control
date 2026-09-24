#!/usr/bin/env python3
"""tests/test_changelog.py — Changelog im Info-Fenster."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT))

import version  # noqa: E402


def test_changelog_file_has_current_version():
    from ui.changelog_dialog import read_changelog
    text = read_changelog()
    assert f"v{version.VERSION}" in text


def test_changelog_dialog_shows_text(qapp):
    from ui.changelog_dialog import ChangelogDialog
    dlg = ChangelogDialog(None, text="### v9.9.9\n- test")
    assert "v9.9.9" in dlg.view.toPlainText()
    dlg2 = ChangelogDialog(None, text="")
    assert "github.com" in dlg2.view.toPlainText()
