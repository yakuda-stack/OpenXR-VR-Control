#!/usr/bin/env python3
"""
tests/test_controls_tab.py — Schalter obah
=====================================================
Weg eines Schalters in OpenXR-VR-Control (ohne Tools-Tab):
  an + installiert        -> bleibt an, wird gemerkt
  an + nicht installiert  -> Rueckfrage -> Worker startet direkt
  Abbruch / Fehler        -> Schalter geht wieder aus
"""
import json
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def app(qapp):
    from PySide6.QtWidgets import QMessageBox
    for m in ("warning", "information", "critical"):
        setattr(QMessageBox, m, staticmethod(lambda *a, **k: QMessageBox.Ok))
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    from main import ControlsWindow
    window = ControlsWindow()
    yield window
    window.close()


class FakeWorker:
    """Steht fuer CargoInstallWorker/InstallWorker — startet nichts."""
    created = []

    def __init__(self, *args, **kwargs):
        from PySide6.QtCore import QObject
        self.args = args
        self._running = False
        self._callbacks = []
        FakeWorker.created.append(self)

        class _Sig:
            def __init__(sig):
                sig.slots = []

            def connect(sig, fn):
                sig.slots.append(fn)
        self.finished_signal = _Sig()
        self.status_signal = _Sig()
        QObject  # noqa: B018

    def start(self):
        self._running = True

    def isRunning(self):
        return self._running

    def finish(self, ok):
        self._running = False
        for fn in self.finished_signal.slots:
            fn(ok)


@pytest.fixture
def env(app, monkeypatch):
    import appimage_installer as appimg
    import cargo_installer
    import install_worker
    from PySide6.QtWidgets import QMessageBox
    state = {"installed": set(), "answer": "Cargo", "asked": []}
    FakeWorker.created.clear()
    monkeypatch.setattr(appimg, "installed_locally",
                        lambda tool: tool.get("key") in state["installed"])
    monkeypatch.setattr(appimg, "detect_install_methods",
                        lambda tool: ["yay", "cargo"] if tool.get("pkg") else ["cargo"])
    monkeypatch.setattr(cargo_installer, "CargoInstallWorker", FakeWorker)
    monkeypatch.setattr(install_worker, "InstallWorker", FakeWorker)

    def fake_exec(box, *a, **k):
        state["asked"].append(box.windowTitle())
        for btn in box.buttons():
            if state["answer"] and btn.text() == state["answer"]:
                btn.click()
                return 0
        for btn in box.buttons():
            if box.buttonRole(btn) == QMessageBox.RejectRole:
                btn.click()
        return 0
    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    app.tool_worker = None
    for key in app.ui.controls_rows:
        app._set_control_toggle(key, False)
        app._controls_pending.discard(key)
    yield state
    app.tool_worker = None


def _saved(key):
    import paths
    with open(paths.config_file("config.json"), encoding="utf-8") as fh:
        return json.load(fh).get("controls_" + key.replace("-", "_"))


def test_both_toggles_exist(app):
    assert set(app.ui.controls_rows) == {"obah"}


def test_toggle_on_when_installed(app, env):
    env["installed"].add("obah")
    app.ui.controls_rows["obah"]["toggle"].setChecked(True)
    assert not env["asked"]
    assert app.ui.controls_rows["obah"]["toggle"].isChecked()
    assert _saved("obah") is True


def test_not_installed_asks_and_starts_cargo(app, env):
    app.ui.controls_rows["obah"]["toggle"].setChecked(True)
    assert env["asked"]
    assert len(FakeWorker.created) == 1
    worker = FakeWorker.created[0]
    assert worker.isRunning() and app.tool_worker is worker
    assert "obah" in app._controls_pending
    env["installed"].add("obah")
    worker.finish(True)
    assert "obah" not in app._controls_pending
    assert app.ui.controls_rows["obah"]["toggle"].isChecked()
    assert _saved("obah") is True


def test_yay_uses_package_name(app, env):
    env["answer"] = "yay (AUR)"
    app.ui.controls_rows["obah"]["toggle"].setChecked(True)
    assert FakeWorker.created[0].args[0] == ["obah-git"]


def test_cancel_turns_toggle_off(app, env):
    env["answer"] = None
    app.ui.controls_rows["obah"]["toggle"].setChecked(True)
    assert not app.ui.controls_rows["obah"]["toggle"].isChecked()
    assert not FakeWorker.created


def test_failed_install_turns_toggle_off(app, env):
    app.ui.controls_rows["obah"]["toggle"].setChecked(True)
    FakeWorker.created[0].finish(False)
    assert not app.ui.controls_rows["obah"]["toggle"].isChecked()
    assert _saved("obah") is False


def test_busy_worker_blocks_second_install(app, env):
    app.tool_worker = FakeWorker()
    app.tool_worker.start()
    app.ui.controls_rows["obah"]["toggle"].setChecked(True)
    assert len(FakeWorker.created) == 1                 # nur der vorhandene
    assert not app.ui.controls_rows["obah"]["toggle"].isChecked()
