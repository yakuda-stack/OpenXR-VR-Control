#!/usr/bin/env python3
"""
ui/changelog_dialog.py — CHANGELOG.md in der App anzeigen (Info → Changelog)
===========================================================================
Liest die mitgelieferte CHANGELOG.md (liegt in AppImage, AUR-Paket und
Quellcode neben starter.py). Fehlt sie, gibt es nur den GitHub-Link.
"""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout

import links
from translations import tr

CHANGELOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "CHANGELOG.md")


def read_changelog(path=CHANGELOG_PATH):
    """Inhalt der CHANGELOG.md oder '' (fehlt / nicht lesbar)."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


class ChangelogDialog(QDialog):
    def __init__(self, parent=None, text=None):
        super().__init__(parent)
        self.setWindowTitle(tr("changelog_title"))
        self.resize(760, 620)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)

        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        self.view.setStyleSheet("QTextBrowser { background:#1c1f26; color:#d8dee9; "
                                "border:1px solid #2e3440; border-radius:6px; padding:10px; }")
        self.view.document().setDefaultStyleSheet("a { color:#88c0d0; }")
        text = read_changelog() if text is None else text
        if text:
            self.view.setMarkdown(text)
        else:
            self.view.setMarkdown(tr("changelog_missing").format(url=links.CHANGELOG))
        root.addWidget(self.view, 1)

        row = QHBoxLayout()
        web = QPushButton(tr("changelog_online"))
        web.setCursor(Qt.PointingHandCursor)
        web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(links.CHANGELOG)))
        row.addWidget(web)
        row.addStretch()
        close = QPushButton(tr("about_close"))
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        row.addWidget(close)
        root.addLayout(row)
