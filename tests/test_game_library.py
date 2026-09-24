#!/usr/bin/env python3
"""
tests/test_game_library.py — Spieleliste + „Spiel hinzufügen“
============================================================
Baut eine kleine Steam-Bibliothek im Wegwerf-HOME:
  100  Beat Game   (Action-Datei im Spielordner -> steht automatisch da)
  200  Flat Game   (weder VR noch Action-Datei  -> nur ueber Hand-Eintrag)
"""
import json
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT))

import game_library as lib  # noqa: E402

MANIFEST = {"actions": [{"name": "/actions/main/in/jump", "type": "boolean"}],
            "action_sets": [{"name": "/actions/main", "usage": "leftright"}],
            "default_bindings": []}


@pytest.fixture
def steam(tmp_path, monkeypatch):
    sa = tmp_path / "steamapps"
    (sa / "common").mkdir(parents=True)

    def add(appid, name, folder, manifest):
        (sa / f"appmanifest_{appid}.acf").write_text(
            f'"AppState"\n{{\n "appid" "{appid}"\n "name" "{name}"\n "installdir" "{folder}"\n}}\n')
        g = sa / "common" / folder
        g.mkdir()
        if manifest:
            (g / "actions.json").write_text(json.dumps(MANIFEST))
    add(100, "Beat Game", "BeatGame", True)
    add(200, "Flat Game", "FlatGame", False)
    monkeypatch.setattr(lib, "_steamapps_dirs", lambda: [str(sa)])
    monkeypatch.setattr(lib, "APP_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setattr(lib.steam_appinfo, "commons", lambda ids: ({}, False))
    monkeypatch.setattr(lib.steam_shortcuts, "list_shortcuts", lambda *a, **k: [])
    return tmp_path


def test_nothing_is_vr_by_default(steam):
    assert lib.games_tab_entries() == []
    ids = [c["id"] for c in lib.steam_candidates()]
    assert ids == ["100", "200"]


def test_steam_flag_marks_vr(steam, monkeypatch):
    monkeypatch.setattr(lib.steam_appinfo, "commons",
                        lambda ids: ({"200": {"openxrsupport": "1"}}, True))
    monkeypatch.setattr(lib.steam_appinfo, "is_playable_type", lambda c: True)
    monkeypatch.setattr(lib.steam_appinfo, "common_says_vr", lambda c: True)
    assert [e["id"] for e in lib.games_tab_entries()] == ["200"]


def test_manual_steam_game_and_remove(steam):
    assert lib.add_manual_steam_appid("200")
    assert not lib.add_manual_steam_appid("200")            # schon drin
    entries = lib.games_tab_entries()
    assert [(e["id"], e["kind"]) for e in entries] == [("200", "steam")]
    assert lib.is_manual("200", "steam")
    assert "200" not in [c["id"] for c in lib.steam_candidates()]
    lib.remove_game("200", "steam")
    assert lib.games_tab_entries() == []
    # wieder eintragen holt es aus der Ausblendliste zurueck
    lib.add_manual_steam_appid("200")
    assert [e["id"] for e in lib.games_tab_entries()] == ["200"]


def test_candidates_exclude(steam):
    ids = [c["id"] for c in lib.steam_candidates(exclude={"steam:100"})]
    assert ids == ["200"]


def test_local_game_validation_and_ids(steam):
    exe = steam / "Game.x86_64"
    exe.write_text("x")
    assert lib.add_local_game("", str(exe)) == (False, "no_name")
    assert lib.add_local_game("A", "") == (False, "no_exe")
    assert lib.add_local_game("A", str(steam / "missing")) == (False, "not_found")
    assert lib.add_local_game("A", str(exe)) == (True, "local:1")
    assert lib.add_local_game("B", str(exe)) == (True, "local:2")
    lib.remove_game("local:1", "local")
    assert lib.add_local_game("C", str(exe)) == (True, "local:1")   # Nummer frei
    names = [e["name"] for e in lib.games_tab_entries()]
    assert names == ["B", "C"]


def test_manual_shortcut(steam, monkeypatch):
    sc_id = str(0x80000000 + 5)
    monkeypatch.setattr(lib.steam_shortcuts, "list_shortcuts",
                        lambda *a, **k: [{"appid": sc_id, "name": "Heroic Game"}])
    assert [c["kind"] for c in lib.steam_candidates()] == ["steam", "steam", "shortcut"]
    lib.add_manual_steam_appid(sc_id)
    assert [(e["name"], e["kind"]) for e in lib.games_tab_entries()] == [("Heroic Game", "shortcut")]


# --------------------------------------------------------------------------- #
#  Knoepfe im Fenster
# --------------------------------------------------------------------------- #
def _pump(qapp, win):
    import time
    for _ in range(200):
        qapp.processEvents()
        w = win._obah_scan_worker
        if w is None or not w.isRunning():
            qapp.processEvents()
            return
        time.sleep(0.02)


def _items(win):
    c = win.ui.combo_obah_game
    return [c.itemText(i) for i in range(c.count())]


def test_buttons_add_select_and_remove(qapp, steam, monkeypatch):
    import obah_bindings as ob
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(ob, "prefix_dirs", lambda appid: [])
    monkeypatch.setattr(ob, "load_manual_manifests", lambda: {})
    from main import ControlsWindow
    win = ControlsWindow()
    try:
        win.ui.btn_obah_expand.setChecked(True)
        _pump(qapp, win)
        assert [t.split("   ")[0] for t in _items(win)] == ["Beat Game"]
        assert not win.ui.btn_remove_game.isVisibleTo(win)

        assert win.add_steam_game({"id": "200", "name": "Flat Game", "kind": "steam"})
        _pump(qapp, win)
        assert win.ui.combo_obah_game.currentText().startswith("Flat Game")
        assert win.ui.btn_remove_game.isVisibleTo(win)

        exe = steam / "MyGame" / "run.sh"
        exe.parent.mkdir()
        exe.write_text("x")
        (exe.parent / "actions.json").write_text(json.dumps(MANIFEST))
        assert win.add_local_game(("My Game", str(exe)))
        _pump(qapp, win)
        game = win._current_obah_game()
        assert game.name == "My Game" and game.kind == "local" and game.has_manifest

        assert not win.add_local_game(("", str(exe)))            # Fehler -> Meldung

        assert win.remove_current_game(confirm=False)
        _pump(qapp, win)
        assert "My Game" not in " ".join(_items(win))
    finally:
        win._obah_dirty = False
        win.close()
