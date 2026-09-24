#!/usr/bin/env python3
"""
ui/ui_main.py — Aufbau des Hauptfensters (nur Widgets, keine Logik)
===================================================================
Der Controls-Aufbau (setup_controls_tab, _build_obah_panel) ist aus
Yakuda Connect uebernommen. Neu sind die Kopfzeile mit Sprachwahl und die
Knoepfe „Steam-Spiel hinzufuegen“ / „Lokales Spiel hinzufuegen“.
Die Logik haengt in core/main.py und den Mixins unter core/tabs/.
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

import links
from translations import available_languages, tr
from ui.widgets import ToggleSwitch

LANGUAGE_NAMES = {"de": "Deutsch", "en": "English"}


class Ui_MainWindow:
    def setupUi(self, main_window):
        main_window.setWindowTitle("OpenXR/VR-Controls")
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.svg")
        if os.path.exists(icon_path):
            main_window.setWindowIcon(QIcon(icon_path))
        main_window.resize(1100, 900)
        main_window.setMinimumSize(800, 600)

        # Dialoge, Menues, Tooltips und Listen-Popups AUSDRUECKLICH mit
        # Hintergrund UND Schriftfarbe belegt, statt sich auf das Systemtheme
        # zu verlassen. Am QApplication-Objekt greift das auch fuer Dialoge
        # ohne Eltern-Fenster.
        _stylesheet = """
            QMainWindow {
                background-color: #181a1f;
            }
            QWidget {
                color: #d8dee9;
                font-family: "Segoe UI", "Noto Sans", sans-serif;
            }

            /* Moderne Card-Optik für die GroupBoxen statt harter Rahmen */
            QGroupBox {
                background-color: #21252b;
                border: none;
                border-radius: 10px;
                margin-top: 35px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                top: 0px;
                color: #81a1c1;
                font-size: 14px;
                font-weight: bold;
                padding: 5px 10px;
                background-color: transparent;
            }

            /* Buttons modernisieren */
            QPushButton {
                background-color: #3b4252;
                border: 1px solid #434c5e;
                color: #eceff4;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4c566a;
                border: 1px solid #5e81ac;
            }
            QPushButton:pressed {
                background-color: #2e3440;
            }

            /* Eingabefelder und Dropdowns */
            QLineEdit, QComboBox, QSpinBox {
                background-color: #1e222a;
                border: 1px solid #3b4252;
                border-radius: 4px;
                padding: 6px;
                color: #eceff4;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #88c0d0;
            }

            /* Checkboxen */
            QCheckBox { spacing: 8px; font-size: 13px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #434c5e; background-color: #1e222a; }
            QCheckBox::indicator:checked { background-color: #5e81ac; border: 1px solid #81a1c1; }

            /* Scrollbars verstecken/minimalisieren */
            QScrollBar:vertical { width: 10px; background: transparent; }
            QScrollBar::handle:vertical { background: #434c5e; border-radius: 5px; }

            /* Flaechen, die bisher ihre Farbe vom System-Theme holten:
               Seitenstapel, Scrollbereiche und deren Inhalts-Widgets. Auf
               einem hellen Desktop-Theme leuchteten sie sonst weiss auf. */
            QStackedWidget { background-color: #181a1f; }
            QScrollArea { background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }

            /* ---------------------------------------------------------------
               Dialoge, Popups und Menues: eigener Hintergrund statt System-Theme.
               Ohne diesen Block steht helle Schrift auf hellem Grund, sobald
               der Desktop ein helles Theme benutzt.
               --------------------------------------------------------------- */
            QDialog, QMessageBox, QInputDialog, QFileDialog, QProgressDialog {
                background-color: #21252b;
            }
            QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel,
            QFileDialog QLabel, QProgressDialog QLabel {
                color: #eceff4;
                background: transparent;
            }
            QMessageBox QPushButton, QDialog QPushButton {
                min-width: 84px;
            }
            /* Detailansicht/Listen innerhalb von Dialogen */
            QDialog QTextEdit, QDialog QPlainTextEdit, QMessageBox QTextEdit,
            QDialog QListView, QDialog QTreeView, QDialog QTableView {
                background-color: #1e222a;
                color: #d8dee9;
                border: 1px solid #3b4252;
            }
            QHeaderView::section {
                background-color: #2e3440;
                color: #d8dee9;
                border: none;
                padding: 4px;
            }
            QDialog QToolButton, QFileDialog QToolButton {
                color: #d8dee9;
                background-color: #3b4252;
                border: 1px solid #434c5e;
                border-radius: 4px;
                padding: 4px;
            }
            QDialog QToolButton:hover, QFileDialog QToolButton:hover {
                background-color: #4c566a;
            }

            /* Aufklapplisten (QComboBox-Popup) und Kontextmenues */
            QComboBox QAbstractItemView {
                background-color: #2e3440;
                color: #d8dee9;
                selection-background-color: #5e81ac;
                selection-color: #eceff4;
                border: 1px solid #4c566a;
            }
            QMenu {
                background-color: #2e3440;
                color: #d8dee9;
                border: 1px solid #434c5e;
            }
            QMenu::item:selected { background-color: #5e81ac; color: #eceff4; }
            QMenu::separator { height: 1px; background: #434c5e; margin: 4px 8px; }

            /* Tooltips holten ihren Hintergrund ebenfalls vom System-Theme */
            QToolTip {
                background-color: #2e3440;
                color: #eceff4;
                border: 1px solid #4c566a;
                padding: 4px;
            }

            /* Fortschrittsbalken (z. B. APK-Installation) */
            QProgressBar {
                background-color: #1e222a;
                border: 1px solid #3b4252;
                border-radius: 4px;
                color: #eceff4;
                text-align: center;
            }
            QProgressBar::chunk { background-color: #5e81ac; border-radius: 3px; }
        """
        _app = QApplication.instance()
        if _app is not None:
            _app.setStyleSheet(_stylesheet)
        else:
            main_window.setStyleSheet(_stylesheet)

        self.central_widget = QWidget()
        main_window.setCentralWidget(self.central_widget)
        root = QVBoxLayout(self.central_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sprache oben rechts (die Controls-Seite bringt Titel + Untertitel mit)
        top = QHBoxLayout()
        top.setContentsMargins(20, 10, 20, 0)
        top.addStretch()
        self.lbl_language = QLabel(tr("app_language"))
        self.lbl_language.setStyleSheet("color:#7b88a1; font-size:12px;")
        top.addWidget(self.lbl_language)
        self.combo_language = QComboBox()
        for code in available_languages():
            self.combo_language.addItem(LANGUAGE_NAMES.get(code, code), code)
        top.addWidget(self.combo_language)
        self.btn_info = QPushButton(tr("info_btn"))
        self.btn_info.setCursor(Qt.PointingHandCursor)
        self.btn_info.setToolTip(tr("info_btn_tip"))
        self.btn_info.setStyleSheet("""
            QPushButton { background:#2e3440; color:#88c0d0; border:1px solid #3b4252;
                          border-radius:6px; padding:5px 12px; font-size:12px; font-weight:bold; }
            QPushButton:hover { background:#3b4252; border-color:#5e81ac; }
        """)
        top.addWidget(self.btn_info)
        root.addLayout(top)

        self.tab_controls = QWidget()
        root.addWidget(self.tab_controls, 1)
        self.setup_controls_tab()

        # ---- Fusszeile: dezent die anderen Programme von yakuda
        self.footer = QWidget()
        self.footer.setObjectName("footer")
        self.footer.setStyleSheet("""
            QWidget#footer { background:#15171c; border-top:1px solid #2e3440; }
            QLabel { color:#4c566a; font-size:11px; background:transparent; }
        """)
        foot = QHBoxLayout(self.footer)
        foot.setContentsMargins(20, 6, 20, 6)
        foot.setSpacing(18)
        self.lbl_footer_more = QLabel(tr("footer_more"))
        foot.addWidget(self.lbl_footer_more)
        self.footer_links = []
        for name, key, url in (("Yakuda Connect", "promo_yc", links.YAKUDA_CONNECT),
                               ("OSC-DreamChatbox", "promo_dcb", links.DREAMCHATBOX)):
            lbl = QLabel()
            lbl.setOpenExternalLinks(True)
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.setToolTip(url)
            foot.addWidget(lbl)
            self.footer_links.append((lbl, name, key, url))
        foot.addStretch()
        self.lbl_footer_support = QLabel()
        self.lbl_footer_support.setOpenExternalLinks(True)
        foot.addWidget(self.lbl_footer_support)
        root.addWidget(self.footer)
        self._retranslate_footer()

    def _retranslate_footer(self):
        self.lbl_footer_more.setText(tr("footer_more"))
        for lbl, name, key, url in self.footer_links:
            lbl.setText(f'<a href="{url}" style="color:#81a1c1; text-decoration:none;">{name}</a>'
                        f' <span style="color:#4c566a;">– {tr(key)}</span>')
        self.lbl_footer_support.setText(
            f'<a href="{links.DISCORD}" style="color:#7b88a1; text-decoration:none;">Discord</a>'
            f'  ·  <a href="{links.KOFI}" style="color:#7b88a1; text-decoration:none;">Ko-fi</a>')

    def retranslate_ui(self):
        self.lbl_language.setText(tr("app_language"))
        self.btn_info.setText(tr("info_btn"))
        self.btn_info.setToolTip(tr("info_btn_tip"))
        self._retranslate_footer()
        if hasattr(self, "lbl_controls_title"):
            self.lbl_controls_title.setText(tr("controls_title"))
            self.lbl_controls_subtitle.setText(tr("controls_subtitle"))
            for key, row in self.controls_rows.items():
                row["lbl_title"].setText(tr(row["title_key"]))
                row["lbl_desc"].setText(tr(row["desc_key"]))
                row["btn_start"].setText(tr("controls_start_btn"))
            self.btn_obah_expand.setText(tr("obah_panel_title").replace("&", "&&"))
            if hasattr(self, "xrbinder_card"):
                self.xrbinder_card.retranslate()
                self.btn_xr_reset_all.setText(tr("xrb_reset_all"))
                self.btn_xr_reset_all.setToolTip(tr("xrb_reset_all_tip"))
                self.btn_xr_template.setText(tr("xrb_template"))
                self.btn_xr_template.setToolTip(tr("xrb_template_tip"))
            self.btn_obah_refresh.setText(tr("obah_refresh_btn"))
            self.btn_obah_pick_manifest.setText(tr("obah_pick_manifest"))
            self.btn_obah_pick_manifest.setToolTip(tr("obah_pick_manifest_tip"))
            self.btn_obah_clear_manifest.setToolTip(tr("obah_clear_manifest_tip"))
            self.btn_obah_layout_reset.setText(tr("obah_layout_reset"))
            self.btn_obah_tidy.setText(tr("obah_tidy"))
            self.btn_obah_tidy.setToolTip(tr("obah_tidy_tip"))
            self.btn_obah_discard.setText(tr("obah_discard"))
            for lbl, key in self.obah_step_labels:
                lbl.setText(tr(key))
            self.btn_obah_aux_expand.setText(tr("obah_aux_section"))
            for entry in self.obah_aux_lists.values():
                entry["head"].setText(tr(entry["title_key"]))
            self.lbl_obah_profile.setText(tr("obah_profile_label"))
            self.btn_obah_profile_load.setText(tr("obah_profile_load"))
            self.btn_obah_profile_save.setText(tr("obah_profile_save"))
            self.btn_obah_profile_delete.setText(tr("obah_profile_delete"))
            self.btn_add_steam_game.setText(tr("lib_add_steam"))
            self.btn_add_steam_game.setToolTip(tr("lib_add_steam_tip"))
            self.btn_add_local_game.setText(tr("lib_add_local"))
            self.btn_add_local_game.setToolTip(tr("lib_add_local_tip"))
            self.btn_remove_game.setText(tr("lib_remove"))
            self.btn_remove_game.setToolTip(tr("lib_remove_tip"))

    CONTROLS_ENTRIES = [
        ("obah",     "controls_obah_title",    "controls_obah_desc"),
    ]

    def setup_controls_tab(self):
        """
        Controls-Tab: je Werkzeug ein Schalter. Die Logik (Installations-
        pruefung, Rueckfrage, Installation ueber den Tools-Tab) steckt in
        core/tabs/controls_mixin.py — hier nur der Aufbau.
        """
        from PySide6.QtWidgets import QFrame

        outer = QVBoxLayout(self.tab_controls)
        outer.setContentsMargins(20, 20, 20, 10)
        outer.setSpacing(10)

        self.lbl_controls_title = QLabel(tr("controls_title"))
        self.lbl_controls_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 2px;")
        outer.addWidget(self.lbl_controls_title)

        self.lbl_controls_subtitle = QLabel(tr("controls_subtitle"))
        self.lbl_controls_subtitle.setStyleSheet("color: #7b88a1; font-style: italic;")
        self.lbl_controls_subtitle.setWordWrap(True)
        outer.addWidget(self.lbl_controls_subtitle)

        # Alles darunter scrollt: die Bindings-Ansicht wird schnell hoeher
        # als das Fenster. Titel und Untertitel bleiben stehen.
        page_title_layout = outer
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        scroll.setViewportMargins(0, 4, 0, 0)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page = QWidget()
        scroll.setWidget(page)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 6, 6)
        outer.setSpacing(10)
        page_title_layout.addWidget(scroll, 1)
        self.controls_scroll = scroll

        self.controls_rows = {}
        for key, title_key, desc_key in self.CONTROLS_ENTRIES:
            card = QFrame()
            card.setObjectName("controlcard")
            card.setStyleSheet("""
                QFrame#controlcard {
                    background-color: #21252b;
                    border-radius: 6px;
                    border: 1px solid #2e3440;
                }
            """)
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 10, 12, 10)
            row.setSpacing(12)

            toggle = ToggleSwitch()
            row.addWidget(toggle, 0, Qt.AlignVCenter)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            lbl_title = QLabel(tr(title_key))
            lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #eceff4;")
            text_col.addWidget(lbl_title)
            lbl_desc = QLabel(tr(desc_key))
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("color: #a6b2c0; font-size: 12px;")
            text_col.addWidget(lbl_desc)
            row.addLayout(text_col, 1)

            lbl_status = QLabel("")
            lbl_status.setStyleSheet("color: #7b88a1; font-size: 12px; font-style: italic;")
            row.addWidget(lbl_status, 0, Qt.AlignVCenter)

            btn_start = QPushButton(tr("controls_start_btn"))
            btn_start.setCursor(Qt.PointingHandCursor)
            btn_start.setFixedHeight(28)
            btn_start.setStyleSheet("""
                QPushButton { background-color: #5e81ac; color: white; font-size: 11px;
                              font-weight: bold; padding: 0px 14px; border-radius: 4px; border: none; }
                QPushButton:hover { background-color: #81a1c1; }
            """)
            btn_start.setVisible(False)
            row.addWidget(btn_start, 0, Qt.AlignVCenter)

            outer.addWidget(card)
            self.controls_rows[key] = {
                "card": card, "toggle": toggle, "lbl_title": lbl_title,
                "lbl_desc": lbl_desc, "lbl_status": lbl_status,
                "btn_start": btn_start, "title_key": title_key, "desc_key": desc_key,
            }

        # xrBinder: eigene Karte im selben Stil, direkt ueber dem Bereich
        # „Controls per obah & xrBinder“ (OpenXR-Spiele stehen dort mit in der
        # Spieleliste, siehe core/tabs/xr_controls_mixin.py).
        from xrbinder_session import XrBinderSession
        from ui.xrbinder_panel import XrBinderCard
        self.xrbinder_session = XrBinderSession()
        self.xrbinder_card = XrBinderCard(self.xrbinder_session)
        outer.addWidget(self.xrbinder_card)

        outer.addWidget(self._build_obah_panel())
        outer.addStretch()

    def _build_obah_panel(self):
        """
        Einklappbarer Bereich „Controls per obah“: die drei Auswahlschritte
        von obah (Spiel -> Controller -> Bindings laden) als Dropdowns.
        Befuellt wird er von core/tabs/controls_mixin.py.
        """
        from PySide6.QtWidgets import QFrame, QComboBox, QGridLayout, QToolButton

        panel = QFrame()
        panel.setObjectName("obahpanel")
        panel.setStyleSheet("""
            QFrame#obahpanel { background-color: #21252b; border-radius: 6px;
                               border: 1px solid #2e3440; }
        """)
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 8, 12, 10)
        v.setSpacing(8)

        head = QHBoxLayout()
        self.btn_obah_expand = QToolButton()
        self.btn_obah_expand.setCheckable(True)
        self.btn_obah_expand.setCursor(Qt.PointingHandCursor)
        self.btn_obah_expand.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_obah_expand.setArrowType(Qt.RightArrow)
        self.btn_obah_expand.setText(tr("obah_panel_title").replace("&", "&&"))
        self.btn_obah_expand.setStyleSheet("""
            QToolButton { background: transparent; border: none; color: #eceff4;
                          font-size: 13px; font-weight: bold; padding: 2px; }
            QToolButton:hover { color: #88c0d0; }
        """)
        head.addWidget(self.btn_obah_expand)
        head.addStretch()
        self.btn_obah_refresh = QPushButton(tr("obah_refresh_btn"))
        self.btn_obah_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_obah_refresh.setFixedHeight(26)
        self.btn_obah_refresh.setStyleSheet("""
            QPushButton { background-color: #3b4252; color: #88c0d0; font-size: 11px;
                          padding: 0px 12px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #4c566a; }
            QPushButton:disabled { background-color: #2e3440; color: #4c566a; }
        """)
        self.btn_obah_refresh.setVisible(False)
        head.addWidget(self.btn_obah_refresh)
        v.addLayout(head)

        # ---- Hinweis: obah und/oder xrBinder fehlen (controls_mixin.
        #      update_controls_notice blendet die Zeilen ein/aus)
        self.obah_notice = QFrame()
        self.obah_notice.setObjectName("obahnotice")
        self.obah_notice.setStyleSheet("""
            QFrame#obahnotice { background-color: #2e2a22; border-radius: 5px;
                                border: 1px solid #5c4d2e; }
            QLabel { color: #ebcb8b; font-size: 12px; background: transparent; border: none; }
            QPushButton { background-color: #5e81ac; color: white; font-size: 11px;
                          font-weight: bold; padding: 0px 14px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #81a1c1; }
            QPushButton:disabled { background-color: #3b4252; color: #7b88a1; }
        """)
        notice_v = QVBoxLayout(self.obah_notice)
        notice_v.setContentsMargins(12, 8, 12, 8)
        notice_v.setSpacing(6)
        self.obah_notice_rows = {}
        for key in ("obah", "xrbinder"):
            row_w = QWidget()
            row_h = QHBoxLayout(row_w)
            row_h.setContentsMargins(0, 0, 0, 0)
            row_h.setSpacing(10)
            lbl = QLabel()
            lbl.setWordWrap(True)
            row_h.addWidget(lbl, 1)
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(26)
            row_h.addWidget(btn, 0, Qt.AlignVCenter)
            notice_v.addWidget(row_w)
            self.obah_notice_rows[key] = {"row": row_w, "label": lbl, "button": btn}
        self.obah_notice.setVisible(False)
        v.addWidget(self.obah_notice)

        self.obah_body = QWidget()
        self.obah_body.setVisible(False)
        body_v = QVBoxLayout(self.obah_body)
        body_v.setContentsMargins(0, 0, 0, 0)
        body_v.setSpacing(10)

        # ---- Profile: Anordnung UND Belegung unter eigenem Namen sichern
        prof_css = """
            QPushButton { background-color:#3b4252; color:#d8dee9; font-size:11px;
                          padding:5px 12px; border-radius:4px; border:none; }
            QPushButton:hover { background-color:#4c566a; }
            QPushButton:disabled { background-color:#2e3440; color:#4c566a; }
        """
        prof_row = QHBoxLayout()
        prof_row.setContentsMargins(22, 0, 0, 0)
        prof_row.setSpacing(8)
        self.lbl_obah_profile = QLabel(tr("obah_profile_label"))
        self.lbl_obah_profile.setStyleSheet("color:#d8dee9; font-size:12px; font-weight:bold;")
        self.lbl_obah_profile.setMinimumWidth(130)
        prof_row.addWidget(self.lbl_obah_profile)
        from ui.opaque_combo import make_opaque as _mk
        self.combo_obah_profile = _mk(QComboBox())
        self.combo_obah_profile.setMinimumWidth(240)
        self.combo_obah_profile.setStyleSheet("""
            QComboBox { background:#1c1f26; color:#d8dee9; border:1px solid #3b4252;
                        border-radius:4px; padding:5px 10px; font-size:12px; }
            QComboBox:hover { border-color:#5e81ac; }
            QComboBox:disabled { color:#4c566a; border-color:#2e3440; }
        """)
        prof_row.addWidget(self.combo_obah_profile, 1)
        self.btn_obah_profile_load = QPushButton(tr("obah_profile_load"))
        self.btn_obah_profile_save = QPushButton(tr("obah_profile_save"))
        self.btn_obah_profile_delete = QPushButton(tr("obah_profile_delete"))
        for b in (self.btn_obah_profile_load, self.btn_obah_profile_save,
                  self.btn_obah_profile_delete):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(prof_css)
            prof_row.addWidget(b)
        body_v.addLayout(prof_row)

        grid_host = QWidget()
        body_v.addWidget(grid_host)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(22, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(2, 1)

        combo_css = """
            QComboBox { background:#1c1f26; color:#d8dee9; border:1px solid #3b4252;
                        border-radius:4px; padding:5px 10px; font-size:12px; }
            QComboBox:hover { border-color:#5e81ac; }
            QComboBox:disabled { color:#4c566a; border-color:#2e3440; }
            QComboBox QAbstractItemView { background:#1c1f26; color:#d8dee9;
                        selection-background-color:#3b4252; selection-color:#88c0d0;
                        border:1px solid #3b4252; outline:none; }
        """
        self.obah_step_labels = []
        combos = []
        for row, key in enumerate(("obah_step_game", "obah_step_controller", "obah_step_source")):
            num = QLabel(str(row + 1))
            num.setFixedSize(22, 22)
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet("background:#5e81ac; color:white; border-radius:11px;"
                              " font-size:11px; font-weight:bold;")
            grid.addWidget(num, row, 0)
            lbl = QLabel(tr(key))
            lbl.setStyleSheet("color:#d8dee9; font-size:12px; font-weight:bold;")
            lbl.setMinimumWidth(130)
            grid.addWidget(lbl, row, 1)
            self.obah_step_labels.append((lbl, key))
            from ui.opaque_combo import make_opaque
            combo = make_opaque(QComboBox())
            combo.setStyleSheet(combo_css)
            combo.setMinimumWidth(320)
            combo.setEnabled(False)
            grid.addWidget(combo, row, 2)
            combos.append(combo)
        self.combo_obah_game, self.combo_obah_controller, self.combo_obah_source = combos

        # Action-Datei von Hand waehlen (wenn die Suche nichts findet)
        small_css = """
            QPushButton { background-color: #3b4252; color: #88c0d0; font-size: 11px;
                          padding: 0px 10px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #4c566a; }
            QPushButton:disabled { background-color: #2e3440; color: #4c566a; }
        """
        manifest_row = QHBoxLayout()
        manifest_row.setSpacing(6)
        self.btn_obah_pick_manifest = QPushButton(tr("obah_pick_manifest"))
        self.btn_obah_pick_manifest.setToolTip(tr("obah_pick_manifest_tip"))
        self.btn_obah_clear_manifest = QPushButton("✕")
        self.btn_obah_clear_manifest.setToolTip(tr("obah_clear_manifest_tip"))
        for b in (self.btn_obah_pick_manifest, self.btn_obah_clear_manifest):
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(28)
            b.setStyleSheet(small_css)
            b.setEnabled(False)
            manifest_row.addWidget(b)
        self.btn_obah_clear_manifest.setVisible(False)
        grid.addLayout(manifest_row, 0, 3)

        self.lbl_obah_hint = QLabel("")
        self.lbl_obah_hint.setWordWrap(True)
        self.lbl_obah_hint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_obah_hint.setStyleSheet("color:#7b88a1; font-size:11px; font-style:italic;")
        grid.addWidget(self.lbl_obah_hint, 3, 1, 1, 2)

        # ---- NEU in OpenXR-VR-Control: Spiele selbst eintragen, wenn Steam
        #      sie nicht als VR fuehrt (Logik: core/tabs/game_list_mixin.py)
        add_row = QHBoxLayout()
        add_row.setContentsMargins(22, 2, 0, 0)
        add_row.setSpacing(8)
        add_css = """
            QPushButton { background-color:#3b4252; color:#a3be8c; font-size:11px;
                          padding:5px 12px; border-radius:4px; border:none; font-weight:bold; }
            QPushButton:hover { background-color:#4c566a; }
            QPushButton:disabled { background-color:#2e3440; color:#4c566a; }
        """
        self.btn_add_steam_game = QPushButton(tr("lib_add_steam"))
        self.btn_add_steam_game.setToolTip(tr("lib_add_steam_tip"))
        self.btn_add_local_game = QPushButton(tr("lib_add_local"))
        self.btn_add_local_game.setToolTip(tr("lib_add_local_tip"))
        self.btn_remove_game = QPushButton(tr("lib_remove"))
        self.btn_remove_game.setToolTip(tr("lib_remove_tip"))
        for b in (self.btn_add_steam_game, self.btn_add_local_game, self.btn_remove_game):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(add_css)
            add_row.addWidget(b)
        self.btn_remove_game.setStyleSheet(add_css.replace("#a3be8c", "#bf616a"))
        self.btn_remove_game.setVisible(False)
        add_row.addStretch()
        body_v.addLayout(add_row)
        v.addWidget(self.obah_body)

        # ---- Bindings-Ansicht: Action Sets als Tabs, darunter beide Hände
        from PySide6.QtWidgets import QTabBar
        from ui.controller_view import ControllerBindingView

        self.obah_editor = QWidget()
        self.obah_editor.setVisible(False)
        ev = QVBoxLayout(self.obah_editor)
        ev.setContentsMargins(0, 6, 0, 0)
        ev.setSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#2e3440; background:#2e3440; max-height:1px;")
        ev.addWidget(sep)

        self.obah_set_tabs = QTabBar()
        self.obah_set_tabs.setExpanding(False)
        self.obah_set_tabs.setDrawBase(False)
        self.obah_set_tabs.setUsesScrollButtons(True)
        self.obah_set_tabs.setCursor(Qt.PointingHandCursor)
        self.obah_set_tabs.setStyleSheet("""
            QTabBar::tab { background:#2e3440; color:#a6b2c0; padding:6px 14px;
                           margin-right:4px; border-radius:5px; font-size:12px; }
            QTabBar::tab:hover:!selected { background:#3b4252; color:#d8dee9; }
            QTabBar::tab:selected { background:#5e81ac; color:white; font-weight:bold; }
        """)
        ev.addWidget(self.obah_set_tabs)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        # rechts etwas Luft, sonst stoesst der Pfeil des Speichern-Knopfes
        # an den Rand des Kastens
        status_row.setContentsMargins(0, 0, 6, 0)
        self.lbl_obah_editor_status = QLabel("")
        self.lbl_obah_editor_status.setWordWrap(True)
        self.lbl_obah_editor_status.setStyleSheet("color:#7b88a1; font-size:11px;")
        status_row.addWidget(self.lbl_obah_editor_status, 1)

        from PySide6.QtWidgets import QToolButton as _QToolButton, QMenu as _QMenu
        small_css = """
            QPushButton, QToolButton { background-color:#3b4252; color:#d8dee9; font-size:11px;
                          padding:5px 12px; border-radius:4px; border:none; }
            QPushButton:hover, QToolButton:hover { background-color:#4c566a; }
            QPushButton:disabled, QToolButton:disabled { background-color:#2e3440; color:#4c566a; }
        """
        # Aufgeraeumter Modus: die Karten zeigen nur noch den Namen der Taste.
        # Eingerastet = alle zu. Einzelne Karten gehen per Rechtsklick.
        self.btn_obah_tidy = QPushButton(tr("obah_tidy"))
        self.btn_obah_tidy.setCheckable(True)
        self.btn_obah_tidy.setCursor(Qt.PointingHandCursor)
        self.btn_obah_tidy.setToolTip(tr("obah_tidy_tip"))
        self.btn_obah_tidy.setStyleSheet(small_css + """
            QPushButton:checked { background-color:#5e81ac; color:white; font-weight:bold; }
            QPushButton:checked:hover { background-color:#81a1c1; }
        """)
        status_row.addWidget(self.btn_obah_tidy)

        self.btn_obah_layout_reset = QPushButton(tr("obah_layout_reset"))
        self.btn_obah_layout_reset.setCursor(Qt.PointingHandCursor)
        self.btn_obah_layout_reset.setStyleSheet(small_css)
        status_row.addWidget(self.btn_obah_layout_reset)
        self.btn_obah_discard = QPushButton(tr("obah_discard"))
        self.btn_obah_discard.setCursor(Qt.PointingHandCursor)
        self.btn_obah_discard.setStyleSheet(small_css)
        status_row.addWidget(self.btn_obah_discard)
        # Nur bei OpenXR-Spielen (xrBinder): alle Umbelegungen zuruecknehmen
        self.btn_xr_reset_all = QPushButton(tr("xrb_reset_all"))
        self.btn_xr_reset_all.setToolTip(tr("xrb_reset_all_tip"))
        self.btn_xr_reset_all.setCursor(Qt.PointingHandCursor)
        self.btn_xr_reset_all.setStyleSheet(small_css)
        self.btn_xr_reset_all.setVisible(False)
        status_row.addWidget(self.btn_xr_reset_all)
        # Nur bei OpenXR-Spielen ohne gemeldete Tasten (z. B. VRChat ueber xrizer)
        self.btn_xr_template = QPushButton(tr("xrb_template"))
        self.btn_xr_template.setToolTip(tr("xrb_template_tip"))
        self.btn_xr_template.setCursor(Qt.PointingHandCursor)
        self.btn_xr_template.setStyleSheet(small_css)
        self.btn_xr_template.setVisible(False)
        status_row.addWidget(self.btn_xr_template)
        # Speichern: Klick = Standardziel, Pfeil = Ziel waehlen (wie obahs Dialog)
        self.btn_obah_save = _QToolButton()
        self.btn_obah_save.setPopupMode(_QToolButton.MenuButtonPopup)
        self.btn_obah_save.setCursor(Qt.PointingHandCursor)
        self.btn_obah_save.setStyleSheet(small_css.replace("#3b4252", "#5e81ac", 1)
                                         + " QToolButton { color:white; font-weight:bold; }")
        self.menu_obah_save = _QMenu(self.btn_obah_save)
        self.menu_obah_save.setStyleSheet(
            "QMenu { background:#21252b; color:#d8dee9; border:1px solid #3b4252; }"
            " QMenu::item { padding:6px 18px; }"
            " QMenu::item:selected { background:#3b4252; color:#88c0d0; }")
        self.btn_obah_save.setMenu(self.menu_obah_save)
        status_row.addWidget(self.btn_obah_save)
        ev.addLayout(status_row)

        from ui.controller_view import ControllerPair
        self.obah_view_left = ControllerBindingView()
        self.obah_view_right = ControllerBindingView()
        # nebeneinander, bei schmalem Fenster untereinander
        self.obah_hands = ControllerPair(self.obah_view_left, self.obah_view_right)
        ev.addWidget(self.obah_hands)

        # ---- Posen/Haptik/Skelett und Chords (obah: "Other" / "Chords")
        # Eigener Aufklapp-Abschnitt: die beiden Kaesten brauchen viel Hoehe,
        # werden aber selten angefasst. Standardmaessig sind sie zu.
        self.btn_obah_aux_expand = QToolButton()
        self.btn_obah_aux_expand.setCheckable(True)
        self.btn_obah_aux_expand.setCursor(Qt.PointingHandCursor)
        self.btn_obah_aux_expand.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_obah_aux_expand.setArrowType(Qt.RightArrow)
        self.btn_obah_aux_expand.setText(tr("obah_aux_section"))
        self.btn_obah_aux_expand.setStyleSheet("""
            QToolButton { background: transparent; border: none; color: #d8dee9;
                          font-size: 12px; font-weight: bold; padding: 2px; }
            QToolButton:hover { color: #88c0d0; }
        """)
        aux_head = QHBoxLayout()
        aux_head.setContentsMargins(0, 2, 0, 0)
        aux_head.addWidget(self.btn_obah_aux_expand)
        aux_head.addStretch()
        ev.addLayout(aux_head)

        self.obah_aux_body = QWidget()
        self.obah_aux_body.setVisible(False)
        aux_row = QHBoxLayout(self.obah_aux_body)
        aux_row.setContentsMargins(0, 0, 0, 0)
        aux_row.setSpacing(16)
        self.obah_aux_lists = {}
        for key, title_key in (("paths", "obah_aux_title"), ("chords", "obah_chords_title")):
            box = QFrame()
            box.setObjectName("auxbox")
            box.setStyleSheet("""
                QFrame#auxbox { background-color:#21252b; border-radius:6px;
                                border:1px solid #2e3440; }
            """)
            bv = QVBoxLayout(box)
            bv.setContentsMargins(12, 10, 12, 10)
            bv.setSpacing(6)
            head = QLabel(tr(title_key))
            head.setStyleSheet("color:#7b88a1; font-size:11px; font-weight:bold;")
            bv.addWidget(head)
            host = QWidget()
            host.setStyleSheet("background:transparent;")
            rows = QVBoxLayout(host)
            rows.setContentsMargins(0, 0, 0, 0)
            rows.setSpacing(4)
            bv.addWidget(host)
            bv.addStretch()          # Inhalt oben halten, nicht mittig
            aux_row.addWidget(box, 1)
            self.obah_aux_lists[key] = {"box": box, "head": head, "rows": rows,
                                        "title_key": title_key}
        ev.addWidget(self.obah_aux_body)
        v.addWidget(self.obah_editor)
        return panel

