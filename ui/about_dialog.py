#!/usr/bin/env python3
"""
ui/about_dialog.py — Info-Dialog (Knopf „ⓘ Info“ oben rechts)
=============================================================
Version, Community-Links (Discord, Ko-fi, GitHub), verwendete Werkzeuge
und die anderen Programme von yakuda.
"""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout)

import links
import paths
from translations import tr
from version import APP_VERSION

_CSS = """
    QDialog { background:#1c1f26; }
    QLabel { background:transparent; }
    QFrame#aboutcard { background:#21252b; border:1px solid #2e3440; border-radius:8px; }
    QPushButton#link { background:#2e3440; color:#d8dee9; border:1px solid #3b4252;
                       border-radius:6px; padding:8px 14px; font-weight:bold; text-align:left; }
    QPushButton#link:hover { background:#3b4252; border-color:#5e81ac; color:#eceff4; }
    QPushButton#discord { background:#5865F2; color:white; border:none; border-radius:6px;
                          padding:8px 14px; font-weight:bold; }
    QPushButton#discord:hover { background:#6d78f5; }
    QPushButton#kofi { background:#FF5E5B; color:white; border:none; border-radius:6px;
                       padding:8px 14px; font-weight:bold; }
    QPushButton#kofi:hover { background:#ff7876; }
"""


def _open(url):
    QDesktopServices.openUrl(QUrl(url))


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("about_title"))
        self.setStyleSheet(_CSS)
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 16)
        root.setSpacing(14)

        # ---- Kopf: Icon, Name, Version
        head = QHBoxLayout()
        head.setSpacing(14)
        icon = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png")
        pm = QPixmap(icon_path)
        if not pm.isNull():
            icon.setPixmap(pm.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head.addWidget(icon, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel("OpenXR/VR-Controls")
        name.setStyleSheet("font-size:18px; font-weight:bold; color:#eceff4;")
        col.addWidget(name)
        ver = QLabel(f"{APP_VERSION}  ·  GPL-3.0  ·  by yakuda")
        ver.setStyleSheet("color:#7b88a1; font-size:12px;")
        col.addWidget(ver)
        desc = QLabel(tr("about_text"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#a6b2c0; font-size:12px; margin-top:4px;")
        col.addWidget(desc)
        head.addLayout(col, 1)
        root.addLayout(head)

        # ---- Community
        community = QHBoxLayout()
        community.setSpacing(8)
        for obj, text, url in (("discord", "💬  Discord", links.DISCORD),
                               ("kofi", "☕  Ko-fi", links.KOFI),
                               ("link", "  GitHub", links.REPO)):
            b = QPushButton(text)
            b.setObjectName(obj)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(url)
            b.clicked.connect(lambda _=False, u=url: _open(u))
            community.addWidget(b, 1)
        root.addLayout(community)

        # ---- Hilfe
        help_row = QHBoxLayout()
        help_row.setSpacing(8)
        for text, fn in ((tr("about_changelog"), self._show_changelog),
                         (tr("about_report_bug"), lambda: _open(links.ISSUES)),
                         (tr("about_open_log"),
                          lambda: _open(QUrl.fromLocalFile(paths.cache_root()).toString()))):
            b = QPushButton(text)
            b.setObjectName("link")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            help_row.addWidget(b, 1)
        root.addLayout(help_row)

        # ---- Mehr von yakuda
        root.addWidget(self._card(tr("about_more_apps"), [
            ("Yakuda Connect", tr("promo_yc"), links.YAKUDA_CONNECT),
            ("OSC-DreamChatbox", tr("promo_dcb"), links.DREAMCHATBOX),
        ]))

        # ---- Danke an
        root.addWidget(self._card(tr("about_credits"), [
            ("obah", "galister — OpenVR bindings", links.OBAH),
            ("xrBinder", "mittorn — OpenXR API layer", links.XRBINDER),
        ]))

        note = QLabel(tr("about_ai_note"))
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color:#4c566a; font-size:10px;")
        root.addWidget(note)

        close = QPushButton(tr("about_close"))
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        root.addLayout(row)

    def _show_changelog(self):
        from ui.changelog_dialog import ChangelogDialog
        ChangelogDialog(self).exec()

    def _card(self, title, entries):
        card = QFrame()
        card.setObjectName("aboutcard")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 10, 14, 12)
        v.setSpacing(6)
        head = QLabel(title.upper())
        head.setStyleSheet("color:#7b88a1; font-size:11px; font-weight:bold; letter-spacing:1px;")
        v.addWidget(head)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        for r, (name, text, url) in enumerate(entries):
            a = QLabel(f'<a href="{url}" style="color:#88c0d0; text-decoration:none;">'
                       f'<b>{name}</b></a>')
            a.setOpenExternalLinks(True)
            a.setCursor(Qt.PointingHandCursor)
            grid.addWidget(a, r, 0)
            t = QLabel(text)
            t.setWordWrap(True)
            t.setStyleSheet("color:#a6b2c0; font-size:12px;")
            grid.addWidget(t, r, 1)
        grid.setColumnStretch(1, 1)
        v.addLayout(grid)
        return card
