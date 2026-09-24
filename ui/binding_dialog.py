#!/usr/bin/env python3
"""
ui/binding_dialog.py — Bindings einer Eingabe bearbeiten (wie obahs Popup)
==========================================================================
obah zeigt beim Enter auf einer Eingabe ein zweigeteiltes Fenster: links die
Liste der Bindings ("#1 joystick (Stick_Click, Move)", "[+] Add binding"),
rechts den gewaehlten Eintrag (Mode, je Feld eine Aktion, Parameter,
"[+] Add parameter"). Genau das, als Dialog:

  * Binding hinzufuegen / entfernen
  * Modus waehlen (nur die, die diese Eingabe kann)
  * je Feld eine passende Aktion waehlen (Typ wird geprueft) oder keine
  * Parameter hinzufuegen (bekannte mit Beschreibung, oder eigene),
    aendern, entfernen
  * Uebernehmen / Abbrechen
  * Tab „Deadzone“ (nur Stick/Trackpad): Regler 0–50 % fuer 'deadzone_pct'
    aller Bindings im Modus joystick/trackpad — wie bei OpenXR-Spielen

Gearbeitet wird auf Kopien (drafts). Erst "Uebernehmen" gibt sie zurueck;
geschrieben wird die Datei spaeter mit "Speichern" im Controls-Tab.
Alle Regeln stecken in core/obah_editor.py.
"""
import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QScrollArea, QSlider,
                               QTabBar, QToolButton, QVBoxLayout, QWidget)

import obah_editor as oe
from translations import get_language, tr
from ui.opaque_combo import make_opaque

# Modusnamen im Dropdown (kurz — die Karten sagen "Als ...")
MODE_NAMES = {
    "de": {"button": "Knopf", "toggle_button": "Umschalt-Knopf", "trigger": "Trigger",
           "joystick": "Joystick", "trackpad": "Trackpad", "dpad": "Steuerkreuz (D-Pad)",
           "grab": "Greifen", "scroll": "Scrollen", "scalar_constant": "Konstante"},
    "en": {"button": "Button", "toggle_button": "Toggle button", "trigger": "Trigger",
           "joystick": "Joystick", "trackpad": "Trackpad", "dpad": "D-pad",
           "grab": "Grab", "scroll": "Scroll", "scalar_constant": "Constant"},
}
INPUT_TEXTS = {
    "de": {"click": "Klick", "touch": "Berührung", "pull": "Ziehen", "position": "Position",
           "value": "Wert", "force": "Kraft", "grab": "Greifen", "toggle": "Umschalten",
           "north": "Oben", "south": "Unten", "east": "Rechts", "west": "Links",
           "center": "Mitte", "x": "X", "y": "Y"},
    "en": {"click": "Click", "touch": "Touch", "pull": "Pull", "position": "Position",
           "value": "Value", "force": "Force", "grab": "Grab", "toggle": "Toggle",
           "north": "North", "south": "South", "east": "East", "west": "West",
           "center": "Center", "x": "X", "y": "Y"},
}
# Deutsche Beschriftung der bekannten Parameter (englisch kommt aus obah)
PARAM_LABELS_DE = {
    "deadzone_pct": "Totzone (%)", "overlap_pct": "Richtungs-Überlappung (%)",
    "sub_mode": "Auslöser", "force_input": "Physische Komponente",
    "click_activate_threshold": "Klick-Schwelle (drücken)",
    "click_deactivate_threshold": "Klick-Schwelle (loslassen)",
    "touch_activate_threshold": "Berührungs-Schwelle (an)",
    "touch_deactivate_threshold": "Berührungs-Schwelle (aus)",
    "haptic_amplitude": "Vibration beim Auslösen",
    "force_hold_threshold": "Greifen: Halte-Schwelle",
    "force_release_threshold": "Greifen: Loslass-Schwelle",
    "maxzone_pct": "Maximalzone (%)", "invert": "Achse umkehren",
}

TAB_CSS = """
    QTabBar::tab { background:#2e3440; color:#a6b2c0; padding:5px 14px; margin-right:4px;
                   border:1px solid #3b4252; border-radius:4px; font-size:12px; }
    QTabBar::tab:hover { color:#88c0d0; }
    QTabBar::tab:selected { background:#3b4f63; color:#eceff4; border-color:#5e81ac; }
"""

DIALOG_CSS = """
QDialog { background:#1c1f26; }
QLabel { color:#d8dee9; }
QFrame#bdpanel { background:#21252b; border:1px solid #2e3440; border-radius:8px; }
QLabel#bdtitle { font-size:16px; font-weight:bold; color:#eceff4; }
QLabel#bdpath { color:#88c0d0; font-family:monospace; font-size:11px; }
QLabel#bdsection { color:#7b88a1; font-size:11px; font-weight:bold; letter-spacing:1px; }
QLabel#bdfield { color:#d8dee9; font-size:12px; }
QLabel#bdraw { color:#4c566a; font-size:10px; font-family:monospace; }
QLabel#bderror { color:#bf616a; font-size:11px; }
QListWidget { background:transparent; border:none; outline:none; color:#d8dee9; font-size:12px; }
QListWidget::item { padding:8px 10px; margin:2px 0; border-radius:6px; }
QListWidget::item:hover:!selected { background:#2e3440; }
QListWidget::item:selected { background:#3b4252; color:#88c0d0; }
QComboBox, QLineEdit { background:#1c1f26; color:#d8dee9; border:1px solid #3b4252;
                       border-radius:4px; padding:5px 8px; font-size:12px; min-height:18px; }
QComboBox:hover, QLineEdit:hover { border-color:#5e81ac; }
QComboBox QAbstractItemView { background:#1c1f26; color:#d8dee9; selection-background-color:#3b4252;
                              selection-color:#88c0d0; border:1px solid #3b4252; outline:none; }
QPushButton { background:#3b4252; color:#d8dee9; border:none; border-radius:5px;
              padding:7px 16px; font-size:12px; }
QPushButton:hover { background:#4c566a; }
QPushButton:disabled { background:#2e3440; color:#4c566a; }
QPushButton#bdprimary { background:#5e81ac; color:white; font-weight:bold; }
QPushButton#bdprimary:hover { background:#81a1c1; }
QPushButton#bddanger { background:transparent; color:#bf616a; }
QPushButton#bddanger:hover { background:#3b2a2e; }
QToolButton#bdadd { background:transparent; color:#88c0d0; border:1px dashed #3b4252;
                    border-radius:5px; padding:6px 10px; font-size:12px; }
QToolButton#bdadd:hover { border-color:#88c0d0; background:#232a33; }
QToolButton#bdx { background:transparent; color:#7b88a1; border:none; font-size:14px; padding:2px 6px; }
QToolButton#bdx:hover { color:#bf616a; }
QScrollArea { background:transparent; border:none; }
"""


def _lang():
    lang = get_language()
    return lang if lang in MODE_NAMES else "en"


def mode_name(mode):
    return MODE_NAMES[_lang()].get(mode, mode)


def input_name(inp):
    return INPUT_TEXTS[_lang()].get(inp, inp)


class BindingDialog(QDialog):
    """Bindings EINER Eingabe (eine Seite, ein Action Set) bearbeiten."""

    def __init__(self, parent, *, manifest, binding, controller_type, set_name,
                 set_label, input_def, side, drafts):
        super().__init__(parent)
        self.setObjectName("bindingDialog")
        self.setStyleSheet(DIALOG_CSS)
        self.setModal(True)
        self.resize(900, 560)

        self.manifest = manifest
        self.binding = binding
        self.controller = controller_type
        self.set_name = set_name
        self.d = input_def
        self.side = side
        self.drafts = [copy.deepcopy(x) for x in drafts]
        self._current = 0 if self.drafts else -1

        name = input_def.name[:1].upper() + input_def.name[1:]
        side_txt = {"left": tr("obah_left"), "right": tr("obah_right")}.get(side, "")
        self.setWindowTitle(tr("bd_window_title").format(input=name, set=set_label))

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        head = QVBoxLayout()
        head.setSpacing(2)
        t = QLabel(tr("bd_title").format(input=name, set=set_label)
                   + (f"  ·  {side_txt}" if side_txt else ""))
        t.setObjectName("bdtitle")
        head.addWidget(t)
        p = QLabel(tr("bd_source").format(
            path=oe.new_binding_path(input_def, side, controller_type, binding)))
        p.setObjectName("bdpath")
        p.setTextInteractionFlags(Qt.TextSelectableByMouse)
        head.addWidget(p)
        root.addLayout(head)

        # Nur bei Stick/Trackpad: Tabs „Belegung | Deadzone“ (wie OpenXR)
        self.tabs = None
        self.dz_panel = None
        if oe.deadzone_input(input_def):
            self.tabs = QTabBar()
            self.tabs.setDrawBase(False)
            self.tabs.setExpanding(False)
            self.tabs.setCursor(Qt.PointingHandCursor)
            self.tabs.setStyleSheet(TAB_CSS)
            self.tabs.addTab(tr("xrd_tab_bindings"))
            self.tabs.addTab("◎  " + tr("xrd_deadzone"))
            root.addWidget(self.tabs)

        self.body_host = QWidget()
        body = QHBoxLayout(self.body_host)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        # ---- links: Liste der Bindings
        left = QFrame()
        left.setObjectName("bdpanel")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(10, 10, 10, 10)
        lv.setSpacing(6)
        sec = QLabel(tr("bd_bindings").upper())
        sec.setObjectName("bdsection")
        lv.addWidget(sec)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_row)
        lv.addWidget(self.list, 1)
        self.btn_add = QToolButton()
        self.btn_add.setObjectName("bdadd")
        self.btn_add.setText("＋  " + tr("bd_add_binding"))
        self.btn_add.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setEnabled(bool(oe.supported_modes(input_def)))
        self.btn_add.clicked.connect(self._add_binding)
        lv.addWidget(self.btn_add)
        self.btn_remove = QPushButton("🗑  " + tr("bd_remove_binding"))
        self.btn_remove.setObjectName("bddanger")
        self.btn_remove.setCursor(Qt.PointingHandCursor)
        self.btn_remove.clicked.connect(self._remove_binding)
        lv.addWidget(self.btn_remove)
        left.setMinimumWidth(300)
        body.addWidget(left, 4)

        # ---- rechts: Editor des gewaehlten Bindings
        right = QFrame()
        right.setObjectName("bdpanel")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(14, 10, 14, 10)
        rv.setSpacing(6)
        self.lbl_editor = QLabel("")
        self.lbl_editor.setObjectName("bdsection")
        rv.addWidget(self.lbl_editor)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor_host = None
        self.editor = None
        rv.addWidget(self.scroll, 1)
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("bderror")
        self.lbl_error.setWordWrap(True)
        rv.addWidget(self.lbl_error)
        body.addWidget(right, 6)
        root.addWidget(self.body_host, 1)
        if self.tabs is not None:
            self.dz_panel = self._build_deadzone_panel()
            self.dz_panel.hide()
            root.addWidget(self.dz_panel, 1)
            self.tabs.currentChanged.connect(self._show_tab)

        # ---- unten
        foot = QHBoxLayout()
        hint = QLabel(tr("bd_footer_hint"))
        hint.setStyleSheet("color:#4c566a; font-size:11px;")
        foot.addWidget(hint, 1)
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

        self._fill_list()

    # ------------------------------------------------------------------ #
    #  Deadzone-Tab (nur Stick/Trackpad)
    # ------------------------------------------------------------------ #
    def _show_tab(self, index):
        dz = index == 1
        self.body_host.setVisible(not dz)
        self.dz_panel.setVisible(dz)
        if dz:
            self._sync_deadzone()
        else:
            self._fill_list()          # Parameterliste zeigt den neuen Wert

    def _build_deadzone_panel(self):
        panel = QFrame()
        panel.setObjectName("bdpanel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        intro = QLabel(tr("xrd_deadzone_tip"))
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#a6b2c0; font-size:11px;")
        lay.addWidget(intro)
        row = QHBoxLayout()
        row.setSpacing(10)
        side = {"left": tr("obah_left"), "right": tr("obah_right")}.get(self.side,
                                                                         tr("obah_single"))
        name = QLabel(side.upper())
        name.setObjectName("bdsection")
        name.setMinimumWidth(80)
        row.addWidget(name)
        self.dz_slider = QSlider(Qt.Horizontal)
        self.dz_slider.setRange(0, oe.DEADZONE_MAX_PCT)
        self.dz_slider.setPageStep(5)
        self.dz_slider.setToolTip(tr("xrd_deadzone_value_tip"))
        self.dz_slider.valueChanged.connect(self._dz_changed)
        row.addWidget(self.dz_slider, 1)
        self.dz_value = QLabel()
        self.dz_value.setMinimumWidth(44)
        self.dz_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.dz_value)
        self.dz_reset = QToolButton()
        self.dz_reset.setObjectName("bdx")
        self.dz_reset.setText("↺")
        self.dz_reset.setToolTip(tr("xrd_deadzone_reset_tip"))
        self.dz_reset.setCursor(Qt.PointingHandCursor)
        self.dz_reset.clicked.connect(lambda: self._dz_changed(0))
        row.addWidget(self.dz_reset)
        lay.addLayout(row)
        self.dz_info = QLabel()
        self.dz_info.setWordWrap(True)
        self.dz_info.setStyleSheet("color:#4c566a; font-size:11px; margin-left:90px;")
        lay.addWidget(self.dz_info)
        note = QLabel(tr("bd_deadzone_runtime_note"))
        note.setWordWrap(True)
        note.setStyleSheet("color:#ebcb8b; font-size:11px;")
        lay.addWidget(note)
        lay.addStretch()
        return panel

    def _dz_changed(self, value):
        if getattr(self, "_dz_syncing", False):
            return
        oe.set_drafts_deadzone(self.drafts, value)
        self._sync_deadzone()

    def _sync_deadzone(self):
        self._dz_syncing = True
        try:
            targets = oe.deadzone_drafts(self.drafts)
            vals = [oe.draft_deadzone(x) for x in targets]
            same = len(set(vals)) <= 1
            v = vals[0] if vals and same else 0
            self.dz_slider.setEnabled(bool(targets))
            self.dz_slider.setValue(min(v, oe.DEADZONE_MAX_PCT))
            if not vals:
                txt = "—"
            elif not same:
                txt = "≠"
            else:
                txt = f"{v} %" if v else tr("xrd_deadzone_off")
            self.dz_value.setText(txt)
            self.dz_reset.setEnabled(any(vals))
            if targets:
                names = ", ".join(filter(None, (oe.draft_summary(self.manifest, x, get_language())
                                                for x in targets))) or tr("bd_no_actions")
                self.dz_info.setText(tr("xrd_deadzone_affects").format(actions=names))
            else:
                self.dz_info.setText(tr("bd_deadzone_none"))
        finally:
            self._dz_syncing = False

    # ------------------------------------------------------------------ #
    #  Liste links
    # ------------------------------------------------------------------ #
    def _item_text(self, i, draft):
        summary = oe.draft_summary(self.manifest, draft, get_language())
        text = f"#{i + 1}   {mode_name(draft.get('mode', ''))}"
        return text + (f"   ·   {summary}" if summary else f"   ·   {tr('bd_no_actions')}")

    def _fill_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for i, draft in enumerate(self.drafts):
            self.list.addItem(QListWidgetItem(self._item_text(i, draft)))
        if self.drafts:
            self._current = min(max(self._current, 0), len(self.drafts) - 1)
            self.list.setCurrentRow(self._current)
        else:
            self._current = -1
        self.list.blockSignals(False)
        self.btn_remove.setEnabled(bool(self.drafts))
        self._build_editor()

    def _refresh_item(self):
        if 0 <= self._current < self.list.count():
            self.list.item(self._current).setText(self._item_text(self._current,
                                                                   self.drafts[self._current]))

    def _on_row(self, row):
        self._current = row
        self.lbl_error.setText("")
        self._build_editor()

    def _add_binding(self):
        draft = oe.new_draft(self.d, self.side, self.controller, self.binding)
        if draft is None:
            return
        self.drafts.append(draft)
        self._current = len(self.drafts) - 1
        self._fill_list()

    def _remove_binding(self):
        if 0 <= self._current < len(self.drafts):
            del self.drafts[self._current]
            self._current = min(self._current, len(self.drafts) - 1)
            self._fill_list()

    # ------------------------------------------------------------------ #
    #  Editor rechts
    # ------------------------------------------------------------------ #
    def _clear_editor(self):
        """
        Rechten Bereich komplett neu anlegen. Alte Elemente einzeln aus dem
        Layout zu nehmen hinterlaesst sie bis zum naechsten Event-Durchlauf
        sichtbar (doppelte Ueberschriften) — ein frisches Widget nicht.
        """
        old = self.scroll.takeWidget()
        if old is not None:
            old.hide()
            old.deleteLater()
        self.editor_host = QWidget()
        self.editor_host.setStyleSheet("background:transparent;")
        self.editor = QVBoxLayout(self.editor_host)
        self.editor.setContentsMargins(0, 4, 4, 0)
        self.editor.setSpacing(6)
        self.scroll.setWidget(self.editor_host)

    def _section(self, text):
        lbl = QLabel(text.upper())
        lbl.setObjectName("bdsection")
        lbl.setContentsMargins(0, 8, 0, 0)
        self.editor.addWidget(lbl)

    def _row(self, grid, r, label, raw, widget, extra=None):
        box = QVBoxLayout()
        box.setSpacing(0)
        lbl = QLabel(label)
        lbl.setObjectName("bdfield")
        box.addWidget(lbl)
        if raw and raw != label:
            rl = QLabel(raw)
            rl.setObjectName("bdraw")
            box.addWidget(rl)
        grid.addLayout(box, r, 0)
        grid.addWidget(widget, r, 1)
        if extra is not None:
            grid.addWidget(extra, r, 2)

    def _build_editor(self):
        self._clear_editor()
        if not (0 <= self._current < len(self.drafts)):
            self.lbl_editor.setText(tr("bd_binding").upper())
            empty = QLabel(tr("bd_empty"))
            empty.setWordWrap(True)
            empty.setStyleSheet("color:#7b88a1; font-style:italic; padding:20px 4px;")
            self.editor.addWidget(empty)
            self.editor.addStretch()
            return
        draft = self.drafts[self._current]
        self.lbl_editor.setText(f"{tr('bd_binding').upper()} #{self._current + 1}")
        mode = (draft.get("mode") or "").lower()

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, 150)

        # Modus
        combo_mode = make_opaque(QComboBox())
        modes = oe.supported_modes(self.d)
        if mode and mode not in modes:
            modes.append(mode)          # unbekannten Modus aus der Datei behalten
        for m in modes:
            combo_mode.addItem(mode_name(m), m)
        combo_mode.setCurrentIndex(max(combo_mode.findData(mode), 0))
        combo_mode.currentIndexChanged.connect(
            lambda _i, c=combo_mode: self._set_mode(c.currentData()))
        self._row(grid, 0, tr("bd_mode"), "", combo_mode)
        self.editor.addLayout(grid)

        # Eingaben
        inputs = oe.draft_inputs(self.d, draft)
        if inputs:
            self._section(tr("bd_inputs"))
            g2 = QGridLayout()
            g2.setHorizontalSpacing(12)
            g2.setVerticalSpacing(8)
            g2.setColumnStretch(1, 1)
            g2.setColumnMinimumWidth(0, 150)
            lang = get_language()
            for r, inp in enumerate(inputs):
                current = ((draft.get("inputs") or {}).get(inp) or {}).get("output")
                combo = make_opaque(QComboBox())
                for opt in oe.compatible_actions(self.manifest, self.set_name, mode, inp, current):
                    if opt is None:
                        combo.addItem(tr("bd_none"), "")
                    else:
                        combo.addItem(oe.localized(self.manifest, opt, lang), opt)
                        combo.setItemData(combo.count() - 1, opt, Qt.ToolTipRole)
                idx = 0
                if current:
                    idx = next((i for i in range(combo.count())
                                if (combo.itemData(i) or "").lower() == current.lower()), 0)
                combo.setCurrentIndex(idx)
                combo.currentIndexChanged.connect(
                    lambda _i, c=combo, n=inp: self._set_action(n, c.currentData()))
                self._row(g2, r, input_name(inp), inp, combo)
            self.editor.addLayout(g2)

        # Parameter
        self._section(tr("bd_parameters"))
        params = draft.get("parameters") or {}
        specs = {s[0].lower(): s for s in oe.known_parameter_specs(self.d, mode)}
        if params:
            g3 = QGridLayout()
            g3.setHorizontalSpacing(12)
            g3.setVerticalSpacing(8)
            g3.setColumnStretch(1, 1)
            g3.setColumnMinimumWidth(0, 150)
            for r, (pname, value) in enumerate(params.items()):
                spec = specs.get(pname.lower())
                editor = self._param_editor(pname, value, spec)
                x = QToolButton()
                x.setObjectName("bdx")
                x.setText("✕")
                x.setToolTip(tr("bd_remove_parameter"))
                x.setCursor(Qt.PointingHandCursor)
                x.clicked.connect(lambda _=False, n=pname: self._remove_param(n))
                self._row(g3, r, self._param_label(pname, spec), pname, editor, x)
            self.editor.addLayout(g3)

        add = QToolButton()
        add.setObjectName("bdadd")
        add.setText("＋  " + tr("bd_add_parameter"))
        add.setPopupMode(QToolButton.InstantPopup)
        add.setCursor(Qt.PointingHandCursor)
        menu = QMenu(add)
        menu.setStyleSheet("QMenu { background:#21252b; color:#d8dee9; border:1px solid #3b4252; }"
                           " QMenu::item { padding:6px 18px; }"
                           " QMenu::item:selected { background:#3b4252; color:#88c0d0; }")
        taken = {k.lower() for k in params}
        for name, label, default, _choices in oe.known_parameter_specs(self.d, mode):
            if name.lower() in taken:
                continue
            act = menu.addAction(f"{self._param_label(name, (name, label, default, []))}   ({name})")
            act.triggered.connect(lambda _=False, n=name, dv=default: self._add_param(n, dv))
        if menu.actions():
            menu.addSeparator()
        custom = menu.addAction(tr("bd_custom_parameter"))
        custom.triggered.connect(self._add_custom_param)
        add.setMenu(menu)
        row = QHBoxLayout()
        row.addWidget(add)
        row.addStretch()
        self.editor.addLayout(row)
        self.editor.addStretch()

    def _param_label(self, name, spec):
        if _lang() == "de" and name in PARAM_LABELS_DE:
            return PARAM_LABELS_DE[name]
        return spec[1] if spec else name

    def _param_editor(self, name, value, spec):
        choices = spec[3] if spec else []
        if choices and isinstance(value, str):
            combo = make_opaque(QComboBox())
            for c in choices:
                combo.addItem(c, c)
            if value not in choices:
                combo.addItem(value, value)
            combo.setCurrentIndex(combo.findData(value))
            combo.currentIndexChanged.connect(
                lambda _i, c=combo, n=name: self._set_param(n, c.currentData()))
            return combo
        edit = QLineEdit(oe.format_parameter_value(value))
        edit.setPlaceholderText(tr("bd_param_placeholder"))
        edit.setToolTip(tr("bd_param_tooltip"))
        edit.editingFinished.connect(lambda e=edit, n=name: self._commit_param_text(n, e))
        return edit

    # ------------------------------------------------------------------ #
    #  Aenderungen
    # ------------------------------------------------------------------ #
    def _draft(self):
        return self.drafts[self._current]

    def _set_mode(self, mode):
        oe.set_draft_mode(self.d, self._draft(), mode)
        self._refresh_item()
        self._build_editor()

    def _set_action(self, inp, output):
        oe.set_draft_action(self._draft(), inp, output or None)
        self._refresh_item()

    def _set_param(self, name, value):
        oe.set_draft_parameter(self._draft(), name, value, original=name)

    def _commit_param_text(self, name, edit):
        try:
            value = oe.parse_parameter_value(edit.text())
        except ValueError as exc:
            self.lbl_error.setText(tr("bd_param_invalid").format(name=name, error=exc))
            return
        self.lbl_error.setText("")
        oe.set_draft_parameter(self._draft(), name, value, original=name)

    def _add_param(self, name, default):
        try:
            oe.set_draft_parameter(self._draft(), name, default)
        except ValueError:
            self.lbl_error.setText(tr("bd_param_exists").format(name=name))
            return
        self._build_editor()

    def _add_custom_param(self):
        name, ok = QInputDialog.getText(self, tr("bd_custom_parameter"), tr("bd_custom_name"))
        if not ok or not name.strip():
            return
        try:
            oe.set_draft_parameter(self._draft(), name.strip(), "")
        except ValueError:
            self.lbl_error.setText(tr("bd_param_exists").format(name=name.strip()))
            return
        self.lbl_error.setText("")
        self._build_editor()

    def _remove_param(self, name):
        oe.remove_draft_parameter(self._draft(), name)
        self._build_editor()


# --------------------------------------------------------------------------- #
#  Posen, Haptik, Skelett (obah: "Other") und Chords
# --------------------------------------------------------------------------- #
PATH_KIND_TEXTS = {
    "de": {"poses": "Pose", "skeleton": "Skelett", "haptics": "Vibration"},
    "en": {"poses": "Pose", "skeleton": "Skeleton", "haptics": "Haptic"},
}
CHORD_KIND_TEXTS = {
    "de": {"held": "gehalten", "single": "einzeln", "click": "Klick", "touch": "Berührung"},
    "en": {"held": "held", "single": "single", "click": "click", "touch": "touch"},
}


def path_kind_name(kind):
    return PATH_KIND_TEXTS[_lang()].get(kind, kind)


def chord_kind_name(kind):
    return CHORD_KIND_TEXTS[_lang()].get(kind, kind)


class _SmallDialog(QDialog):
    """Gemeinsamer Rahmen: Titel, Inhalt, Entfernen / Abbrechen / Übernehmen."""

    def __init__(self, parent, title, subtitle=""):
        super().__init__(parent)
        self.setStyleSheet(DIALOG_CSS)
        self.setModal(True)
        self.deleted = False
        self.setWindowTitle(title)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)
        t = QLabel(title)
        t.setObjectName("bdtitle")
        root.addWidget(t)
        if subtitle:
            st = QLabel(subtitle)
            st.setObjectName("bdpath")
            st.setTextInteractionFlags(Qt.TextSelectableByMouse)
            root.addWidget(st)

        panel = QFrame()
        panel.setObjectName("bdpanel")
        self.body = QVBoxLayout(panel)
        self.body.setContentsMargins(14, 12, 14, 12)
        self.body.setSpacing(8)
        root.addWidget(panel, 1)

        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("bderror")
        self.lbl_error.setWordWrap(True)
        root.addWidget(self.lbl_error)

        foot = QHBoxLayout()
        self.btn_delete = QPushButton("🗑  " + tr("bd_remove_entry"))
        self.btn_delete.setObjectName("bddanger")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._delete)
        foot.addWidget(self.btn_delete)
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

    def _delete(self):
        self.deleted = True
        self.accept()

    def _field(self, label, widget):
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label)
        lbl.setObjectName("bdfield")
        lbl.setMinimumWidth(110)
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        self.body.addLayout(row)
        return widget


class PathBindingDialog(_SmallDialog):
    """Eine Pose / Vibration / Skelett-Zuordnung: Quelle -> Aktion."""

    def __init__(self, parent, *, manifest, set_name, set_label, kind, sources,
                 draft, is_new):
        title = tr("bd_path_title").format(kind=path_kind_name(kind), set=set_label)
        super().__init__(parent, title)
        self.draft = dict(draft)
        self.btn_delete.setVisible(not is_new)

        lang = get_language()
        self.combo_src = make_opaque(QComboBox())
        for s in sources:
            if s["kind"] == kind:
                self.combo_src.addItem(s["name"], s["path"])
                self.combo_src.setItemData(self.combo_src.count() - 1, s["path"], Qt.ToolTipRole)
        cur = self.draft.get("path", "")
        idx = self.combo_src.findData(cur)
        if idx < 0 and cur:
            self.combo_src.addItem(cur, cur)
            idx = self.combo_src.count() - 1
        self.combo_src.setCurrentIndex(max(idx, 0))
        self._field(tr("bd_path_source"), self.combo_src)

        action_type, direction = oe.PATH_KIND_ACTION[kind]
        self.combo_act = make_opaque(QComboBox())
        for a in oe.action_choices(manifest, set_name, action_type, direction,
                                   self.draft.get("output")):
            self.combo_act.addItem(oe.localized(manifest, a, lang), a)
            self.combo_act.setItemData(self.combo_act.count() - 1, a, Qt.ToolTipRole)
        ai = self.combo_act.findData(self.draft.get("output", ""))
        self.combo_act.setCurrentIndex(max(ai, 0))
        self._field(tr("bd_path_action"), self.combo_act)
        self.body.addStretch()

    def result_draft(self):
        return {**self.draft,
                "path": self.combo_src.currentData() or "",
                "output": self.combo_act.currentData() or ""}


class ChordBindingDialog(_SmallDialog):
    """Ein Chord: mehrere Tasten zusammen ergeben eine Aktion."""

    def __init__(self, parent, *, manifest, set_name, set_label, sources, draft, is_new):
        super().__init__(parent, tr("bd_chord_title").format(set=set_label),
                         tr("bd_chord_hint"))
        self.manifest = manifest
        self.sources = list(sources)
        self.draft = dict(draft)
        self.pairs = oe.chord_inputs(self.draft)
        self.btn_delete.setVisible(not is_new)

        lang = get_language()
        self.combo_act = make_opaque(QComboBox())
        for a in oe.action_choices(manifest, set_name, "boolean", "in", self.draft.get("output")):
            self.combo_act.addItem(oe.localized(manifest, a, lang), a)
            self.combo_act.setItemData(self.combo_act.count() - 1, a, Qt.ToolTipRole)
        ai = self.combo_act.findData(self.draft.get("output", ""))
        self.combo_act.setCurrentIndex(max(ai, 0))
        self._field(tr("bd_chord_action"), self.combo_act)

        sec = QLabel(tr("bd_chord_inputs").upper())
        sec.setObjectName("bdsection")
        self.body.addWidget(sec)
        self.rows_host = QWidget()
        self.rows_host.setStyleSheet("background:transparent;")
        self.rows = QVBoxLayout(self.rows_host)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(6)
        self.body.addWidget(self.rows_host)

        add = QToolButton()
        add.setObjectName("bdadd")
        add.setText("＋  " + tr("bd_chord_add_input"))
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(self._add_input)
        add_row = QHBoxLayout()
        add_row.addWidget(add)
        add_row.addStretch()
        self.body.addLayout(add_row)
        self.body.addStretch()
        self._rebuild_rows()

    def _rebuild_rows(self):
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for i, (path, kind) in enumerate(self.pairs):
            row = QWidget()
            row.setStyleSheet("background:transparent;")
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            src = make_opaque(QComboBox())
            for s in self.sources:
                src.addItem(s["name"], s["path"])
            if src.findData(path) < 0 and path:
                src.addItem(path, path)
            src.setCurrentIndex(max(src.findData(path), 0))
            src.currentIndexChanged.connect(
                lambda _i, c=src, n=i: self._set_pair(n, path=c.currentData()))
            h.addWidget(src, 3)
            kindc = make_opaque(QComboBox())
            for k in oe.CHORD_KINDS:
                kindc.addItem(chord_kind_name(k), k)
            if kindc.findData(kind) < 0 and kind:
                kindc.addItem(kind, kind)
            kindc.setCurrentIndex(max(kindc.findData(kind), 0))
            kindc.currentIndexChanged.connect(
                lambda _i, c=kindc, n=i: self._set_pair(n, kind=c.currentData()))
            h.addWidget(kindc, 2)
            x = QToolButton()
            x.setObjectName("bdx")
            x.setText("✕")
            x.setCursor(Qt.PointingHandCursor)
            x.setToolTip(tr("bd_chord_remove_input"))
            x.setEnabled(len(self.pairs) > 1)
            x.clicked.connect(lambda _=False, n=i: self._remove_input(n))
            h.addWidget(x)
            self.rows.addWidget(row)

    def _set_pair(self, index, path=None, kind=None):
        if 0 <= index < len(self.pairs):
            p, k = self.pairs[index]
            self.pairs[index] = (path if path is not None else p,
                                 kind if kind is not None else k)

    def _add_input(self):
        used = {p for p, _ in self.pairs}
        nxt = next((s["path"] for s in self.sources if s["path"] not in used), None)
        if nxt is None:
            self.lbl_error.setText(tr("bd_chord_no_more"))
            return
        self.lbl_error.setText("")
        self.pairs.append((nxt, "held"))
        self._rebuild_rows()

    def _remove_input(self, index):
        if 0 <= index < len(self.pairs) and len(self.pairs) > 1:
            del self.pairs[index]
            self._rebuild_rows()

    def result_draft(self):
        draft = dict(self.draft)
        draft["output"] = self.combo_act.currentData() or ""
        oe.set_chord_inputs(draft, self.pairs)
        return draft
