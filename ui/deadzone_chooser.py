#!/usr/bin/env python3
"""
ui/deadzone_chooser.py — Deadzone fuer OpenVR-Spiele (obah)
===========================================================
Zwei Wege, zwischen denen der Haken „Ich nutze nicht xrizer (z. B. SteamVR)
– deadzone_pct verwenden“ umschaltet (Standard: AN, siehe deadzone_pref):

  * AN:  PctDeadzonePanel — ein Regler 0–100 % je Stick. Schreibt
         'deadzone_pct' in alle Bindings dieses Sticks im Modus joystick.
         Gespeichert mit „Übernehmen“ und danach „Speichern“.
  * AUS: DeadzonePanel (xrBinder) inklusive Vorlage-Knopf — oder ein
         Hinweis, wenn xrBinder aus ist bzw. das Spiel noch unbekannt.

Genutzt vom Deadzone-Tab im Binding-Dialog und vom Knopf „◎ Deadzone“
neben den Action-Set-Tabs.
"""
import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel, QSlider, QToolButton,
                               QVBoxLayout, QWidget)

import deadzone_pref
import obah_editor as oe
from translations import get_language, tr

MODE_BOX_CSS = """
    QFrame#dzModeBox { background:#3a3527; border:1px solid #ebcb8b; border-radius:6px; }
    QFrame#dzModeBox QCheckBox { color:#eceff4; font-size:12px; font-weight:bold; }
    QFrame#dzModeBox QCheckBox::indicator { width:16px; height:16px; }
    QFrame#dzModeBox QLabel { color:#d8c79a; font-size:11px; background:transparent; border:none; }
"""


class PctDeadzonePanel(QFrame):
    """Regler fuer 'deadzone_pct'. sides: [(key, label, drafts, modes), ...].
    Die Listen werden direkt veraendert. Bei mehr als einer Seite gibt es
    zusaetzlich die Zeile „Beide“."""

    changed = Signal()

    def __init__(self, manifest, sides, parent=None):
        super().__init__(parent)
        self.manifest = manifest
        self.sides = {key: (drafts, modes) for key, _label, drafts, modes in sides}
        self.setObjectName("bdpanel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        intro = QLabel(tr("xrd_deadzone_tip"))
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#a6b2c0; font-size:11px;")
        lay.addWidget(intro)
        labels = [(key, label) for key, label, _d, _m in sides]
        if len(labels) > 1:
            labels.append(("both", tr("xrd_deadzone_both")))
        self.rows = {}
        for key, label in labels:
            row = QHBoxLayout()
            row.setSpacing(10)
            name = QLabel(label.upper())
            name.setObjectName("bdsection")
            name.setMinimumWidth(80)
            row.addWidget(name)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(0, oe.DEADZONE_MAX_PCT)
            sl.setPageStep(5)
            sl.setToolTip(tr("xrd_deadzone_value_tip"))
            sl.valueChanged.connect(lambda v, k=key: self._changed(k, v))
            row.addWidget(sl, 1)
            val = QLabel()
            val.setMinimumWidth(44)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(val)
            rst = QToolButton()
            rst.setObjectName("bdx")
            rst.setText("↺")
            rst.setToolTip(tr("xrd_deadzone_reset_tip"))
            rst.setCursor(Qt.PointingHandCursor)
            rst.clicked.connect(lambda _=False, k=key: self._changed(k, 0))
            row.addWidget(rst)
            lay.addLayout(row)
            info = QLabel()
            info.setWordWrap(True)
            info.setStyleSheet("color:#4c566a; font-size:11px; margin-left:90px;")
            lay.addWidget(info)
            self.rows[key] = {"slider": sl, "value": val, "reset": rst, "info": info}
        note = QLabel(tr("dz_pct_note"))
        note.setWordWrap(True)
        note.setStyleSheet("color:#7b88a1; font-size:11px;")
        lay.addWidget(note)
        lay.addStretch()
        self.sync()

    def _keys(self, key):
        return list(self.sides) if key == "both" else [key]

    def _targets(self, key):
        return [x for k in self._keys(key)
                for x in oe.deadzone_drafts(self.sides[k][0], self.sides[k][1])]

    def _changed(self, key, value):
        if getattr(self, "_syncing", False):
            return
        for k in self._keys(key):
            drafts, modes = self.sides[k]
            oe.set_drafts_deadzone(drafts, value, modes)
        self.sync()
        self.changed.emit()

    def sync(self):
        self._syncing = True
        try:
            for key, row in self.rows.items():
                targets = self._targets(key)
                vals = [oe.draft_deadzone(x) for x in targets]
                same = len(set(vals)) <= 1
                v = vals[0] if vals and same else 0
                row["slider"].setEnabled(bool(targets))
                row["slider"].setValue(min(v, oe.DEADZONE_MAX_PCT))
                if not vals:
                    txt = "—"
                elif not same:
                    txt = "≠"
                else:
                    txt = f"{v} %" if v else tr("xrd_deadzone_off")
                row["value"].setText(txt)
                row["reset"].setEnabled(any(vals))
                if key == "both":
                    row["info"].setText(tr("xrd_deadzone_differs") if vals and not same else "")
                    row["info"].setVisible(bool(vals) and not same)
                elif targets:
                    names = ", ".join(filter(None, (
                        oe.draft_summary(self.manifest, x, get_language()) for x in targets)))
                    row["info"].setText(tr("xrd_deadzone_affects").format(
                        actions=names or tr("bd_no_actions")))
                else:
                    row["info"].setText(tr("dz_pct_none"))
        finally:
            self._syncing = False


class DeadzoneChooser(QWidget):
    """Haken + passendes Panel. xr: Daten wie von xr_openvr_deadzone()
    ({"state", "mappings", "game"} oder {"note"}) oder None.
    show_choice=False: nur deadzone_pct (z. B. Trackpad)."""

    changed = Signal()

    def __init__(self, manifest, sides, xr=None, controller_type=None,
                 show_choice=True, parent=None):
        super().__init__(parent)
        self.xr = xr
        self.dz_mappings = (copy.deepcopy(xr["mappings"])
                            if xr and "mappings" in xr else None)
        self.xr_rows = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.check = None
        if show_choice:
            self.check = QCheckBox("⚠  " + tr("dz_use_pct"))
            self.check.setToolTip(tr("dz_use_pct_tip"))
            self.check.setCursor(Qt.PointingHandCursor)
            self.check.setChecked(deadzone_pref.use_pct())
            self.check.toggled.connect(self._toggled)
            box = QFrame()
            box.setObjectName("dzModeBox")
            box.setStyleSheet(MODE_BOX_CSS)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(12, 8, 12, 8)
            bl.setSpacing(2)
            bl.addWidget(self.check)
            hint = QLabel(tr("dz_use_pct_hint"))
            hint.setWordWrap(True)
            bl.addWidget(hint)
            lay.addWidget(box)

        self.pct_panel = PctDeadzonePanel(manifest, sides)
        self.pct_panel.changed.connect(self.changed)
        lay.addWidget(self.pct_panel, 1)

        self.xr_box = None
        if show_choice:
            self.xr_box = self._build_xr_box(controller_type)
            lay.addWidget(self.xr_box, 1)
        self._update()

    def _build_xr_box(self, controller_type):
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        if self.dz_mappings is not None:
            import xr_bindings as xrb
            from ui.xr_deadzone_panel import DeadzonePanel
            info = QLabel(tr("bd_deadzone_xr_info").format(game=self.xr.get("game", "")))
            info.setWordWrap(True)
            info.setStyleSheet("color:#7b88a1; font-size:11px;")
            lay.addWidget(info)
            panel = DeadzonePanel(self.xr["state"], self.dz_mappings,
                                  controller_type=controller_type or xrb.DEFAULT_CT)
            self.xr_rows = panel.rows
            self.xr_panel = panel
            lay.addWidget(panel, 1)
        else:
            note = QLabel((self.xr or {}).get("note") or tr("bd_deadzone_xr_off"))
            note.setWordWrap(True)
            note.setObjectName("bdpanel")
            note.setStyleSheet("color:#ebcb8b; font-size:12px; padding:14px;")
            note.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            lay.addWidget(note, 1)
        return box

    @property
    def use_pct(self):
        return self.check is None or self.check.isChecked()

    def _toggled(self, on):
        deadzone_pref.set_use_pct(on)
        self._update()

    def _update(self):
        self.pct_panel.setVisible(self.use_pct)
        if self.xr_box is not None:
            self.xr_box.setVisible(not self.use_pct)

    def sync(self):
        self.pct_panel.sync()
