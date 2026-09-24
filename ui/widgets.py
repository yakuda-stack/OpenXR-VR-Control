#!/usr/bin/env python3
"""ui/widgets.py — kleine gemeinsame Widgets (aus Yakuda Connect ui_main.py uebernommen)."""
from PySide6.QtCore import Property, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QCheckBox


class ToggleSwitch(QCheckBox):
    """Schiebeschalter (links = aus, rechts = an) im Stil eines iOS-Toggles.

    Verhält sich wie eine QCheckBox (isChecked/setChecked/toggled), zeichnet
    sich aber als animierter Schiebeschalter. sync_offset() setzt die
    Knopfposition ohne Animation passend zum aktuellen Zustand — praktisch,
    wenn der Zustand programmatisch gesetzt wird (z. B. beim Server-Check).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(52, 28)
        self._offset = 3.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(150)
        self.toggled.connect(self._on_toggled)

    def _knob_end(self):
        return self.width() - self.height() + 3

    def hitButton(self, pos):
        # Standardmäßig ist eine QCheckBox nur im kleinen Indikator-Bereich
        # klickbar. Wir machen die GESAMTE Fläche des Schalters klickbar.
        return self.rect().contains(pos)

    def _on_toggled(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(self._knob_end() if checked else 3.0)
        self._anim.start()

    def sync_offset(self):
        """Knopf ohne Animation an den aktuellen Zustand angleichen."""
        self._anim.stop()
        self._offset = self._knob_end() if self.isChecked() else 3.0
        self.update()

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        radius = self.height() / 2
        track = QColor("#81a1c1") if self.isChecked() else QColor("#4c566a")
        p.setBrush(track)
        p.drawRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        d = self.height() - 6
        p.setBrush(QColor("#eceff4"))
        p.drawEllipse(QRectF(self._offset, 3, d, d))
        p.end()
