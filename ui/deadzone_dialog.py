#!/usr/bin/env python3
"""
ui/deadzone_dialog.py — Knopf „◎ Deadzone“ neben den Action-Set-Tabs
====================================================================
Schneller Weg zur Deadzone beider Sticks, ohne erst einen Stick anzuklicken.

  * OpenVR-Spiel (obah): DeadzoneChooser (Haken deadzone_pct / xrBinder)
  * OpenXR-Spiel (xrBinder): nur DeadzonePanel

Gearbeitet wird auf Kopien; „Übernehmen“ gibt sie an den Controls-Tab zurueck.
"""
import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from translations import tr
from ui.binding_dialog import DIALOG_CSS


class DeadzoneDialog(QDialog):
    def __init__(self, parent, *, title, manifest=None, sides=None, xr=None,
                 controller_type=None, show_choice=True, xr_state=None, xr_mappings=None):
        """OpenVR: sides = [(key, label, drafts, modes), ...] (+ xr, show_choice).
        OpenXR: xr_state + xr_mappings."""
        super().__init__(parent)
        self.setObjectName("bindingDialog")
        self.setStyleSheet(DIALOG_CSS)
        self.setModal(True)
        self.resize(640, 460)
        self.setWindowTitle(tr("dz_dialog_title").format(set=title))

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        head = QLabel("◎  " + tr("dz_dialog_title").format(set=title))
        head.setObjectName("bdtitle")
        root.addWidget(head)

        self.chooser = None
        self.xr_mappings = None
        self.sides = None
        if xr_mappings is not None:
            from ui.xr_deadzone_panel import DeadzonePanel
            self.xr_mappings = copy.deepcopy(xr_mappings)
            self.panel = DeadzonePanel(xr_state, self.xr_mappings,
                                       controller_type=controller_type)
            root.addWidget(self.panel, 1)
        else:
            from ui.deadzone_chooser import DeadzoneChooser
            self.sides = [(k, label, [copy.deepcopy(x) for x in drafts], modes)
                          for k, label, drafts, modes in sides]
            self.chooser = DeadzoneChooser(manifest, self.sides, xr=xr,
                                           controller_type=controller_type,
                                           show_choice=show_choice)
            self.panel = self.chooser
            root.addWidget(self.chooser, 1)

        foot = QHBoxLayout()
        foot.addStretch()
        cancel = QPushButton(tr("bd_cancel"))
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        foot.addWidget(cancel)
        self.btn_apply = QPushButton("✓  " + tr("bd_apply"))
        self.btn_apply.setObjectName("bdprimary")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self.accept)
        foot.addWidget(self.btn_apply)
        root.addLayout(foot)

    @property
    def use_pct(self):
        return self.chooser is not None and self.chooser.use_pct

    @property
    def dz_mappings(self):
        return self.chooser.dz_mappings if self.chooser else None

    def drafts_of(self, key):
        return next(d for k, _l, d, _m in self.sides if k == key)
