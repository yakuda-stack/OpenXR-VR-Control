#!/usr/bin/env python3
"""
ui/add_game_dialog.py — „Steam-Spiel hinzufügen“ / „Lokales Spiel hinzufügen“
============================================================================
Zwei kleine Dialoge fuer Spiele, die nicht automatisch als VR-Spiel in der
Liste stehen. Gespeichert wird in core/game_library.py.

  * SteamGameDialog : Auswahl aus allen installierten Steam-Spielen und
                      Nicht-Steam-Spielen in Steam (mit Suchfeld)
  * LocalGameDialog : Name + Programmdatei eines Spiels ohne Steam
"""
import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
                               QVBoxLayout)

import game_library as lib
from logging_setup import get_logger
from translations import tr

log = get_logger("add_game_dialog")

_HINT_CSS = "color:#7b88a1; font-size:11px; font-style:italic;"


class _CandidateWorker(QThread):
    """Steam-Bibliothek im Hintergrund lesen (der erste Durchlauf prueft
    Spielordner und kann ein paar Sekunden dauern)."""
    result = Signal(list)

    def __init__(self, exclude=()):
        super().__init__()
        self.exclude = set(exclude)

    def run(self):
        try:
            items = lib.steam_candidates(self.exclude)
        except Exception as exc:  # noqa: BLE001 — leere Liste statt Absturz
            log.warning("Steam-Spiele nicht lesbar: %s", exc)
            items = []
        self.result.emit(items)


class SteamGameDialog(QDialog):
    """Rueckgabe ueber .selected(): {"id", "name", "kind"} oder None."""

    def __init__(self, parent=None, candidates=None, exclude=()):
        super().__init__(parent)
        self.setWindowTitle(tr("lib_steam_title"))
        self.resize(520, 560)
        self._worker = None

        v = QVBoxLayout(self)
        info = QLabel(tr("lib_steam_text"))
        info.setWordWrap(True)
        v.addWidget(info)

        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("lib_search"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        v.addWidget(self.search)

        self.list = QListWidget()
        self.list.setStyleSheet("QListWidget::item { padding: 5px 4px; }")
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        self.list.currentItemChanged.connect(lambda *_a: self._update_ok())
        v.addWidget(self.list, 1)

        self.lbl_state = QLabel("")
        self.lbl_state.setStyleSheet(_HINT_CSS)
        v.addWidget(self.lbl_state)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(tr("lib_add_btn"))
        self.buttons.button(QDialogButtonBox.Cancel).setText(tr("controls_cancel"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        v.addWidget(self.buttons)
        self._update_ok()

        if candidates is not None:            # Tests
            self._fill(candidates)
        else:
            self.lbl_state.setText(tr("lib_loading"))
            self._worker = _CandidateWorker(exclude)
            self._worker.result.connect(self._fill)
            self._worker.start()

    def _fill(self, items):
        self.list.clear()
        for g in items:
            label = g["name"]
            if g["kind"] == lib.KIND_SHORTCUT:
                label += "   · " + tr("obah_game_shortcut")
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, g)
            it.setToolTip(f"AppID {g['id']}")
            self.list.addItem(it)
        self.lbl_state.setText(tr("lib_steam_count").format(n=len(items)) if items
                               else tr("lib_steam_empty"))
        self._filter(self.search.text())

    def _filter(self, text):
        text = (text or "").strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(bool(text) and text not in it.text().lower())
        self._update_ok()

    def _update_ok(self):
        it = self.list.currentItem()
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(it) and not it.isHidden())

    def selected(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def done(self, result):
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(10000)
        super().done(result)


class LocalGameDialog(QDialog):
    """Name + Programmdatei. Rueckgabe ueber .values(): (name, exe)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("lib_local_title"))
        self.resize(560, 220)

        v = QVBoxLayout(self)
        info = QLabel(tr("lib_local_text"))
        info.setWordWrap(True)
        v.addWidget(info)

        form = QFormLayout()
        self.edit_name = QLineEdit()
        form.addRow(tr("lib_local_name"), self.edit_name)
        exe_row = QHBoxLayout()
        self.edit_exe = QLineEdit()
        self.edit_exe.setPlaceholderText("~/Games/…/Game.exe")
        exe_row.addWidget(self.edit_exe, 1)
        btn = QPushButton(tr("lib_browse"))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._browse)
        exe_row.addWidget(btn)
        form.addRow(tr("lib_local_exe"), exe_row)
        v.addLayout(form)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color:#bf616a; font-size:12px;")
        self.lbl_error.setWordWrap(True)
        v.addWidget(self.lbl_error)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("lib_add_btn"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("controls_cancel"))
        buttons.accepted.connect(self._check)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def _browse(self):
        start = os.path.dirname(os.path.expanduser(self.edit_exe.text().strip())) \
            or os.path.expanduser("~")
        path, _flt = QFileDialog.getOpenFileName(self, tr("lib_local_exe"), start)
        if path:
            self.edit_exe.setText(path)
            if not self.edit_name.text().strip():
                self.edit_name.setText(os.path.splitext(os.path.basename(path))[0])

    def _check(self):
        name, exe = self.values()
        if not name:
            self.lbl_error.setText(tr("lib_err_no_name"))
        elif not exe:
            self.lbl_error.setText(tr("lib_err_no_exe"))
        elif not os.path.exists(os.path.expanduser(exe)):
            self.lbl_error.setText(tr("lib_err_not_found"))
        else:
            self.accept()

    def values(self):
        return self.edit_name.text().strip(), self.edit_exe.text().strip()
