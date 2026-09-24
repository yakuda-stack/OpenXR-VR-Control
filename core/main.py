#!/usr/bin/env python3
"""
core/main.py — Hauptfenster von OpenXR/VR-Controls
==================================================
Eigenstaendige Fassung des Controls-Tabs aus Yakuda Connect — fuer alle, die
kein Pico/Quest-Headset (und damit kein WiVRn/Yakuda Connect) benutzen, ihre
Controller unter Linux aber trotzdem mit einer Oberflaeche belegen wollen:

  * OpenVR-Spiele   -> obah-Bindings (core/tabs/controls_mixin.py)
  * OpenXR-Spiele   -> xrBinder      (core/tabs/xr_controls_mixin.py)
  * Spiele von Hand -> Steam/lokal   (core/tabs/game_list_mixin.py)

Aufbau wie in Yakuda Connect: Widgets in ui/ui_main.py, Logik in den
Mixins (alle arbeiten auf demselben self).
"""
from PySide6.QtCore import QLocale, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

import paths
from jsonio import read_json, update_json
from logging_setup import get_logger
from tabs.controls_mixin import ControlsTabMixin
from tabs.game_list_mixin import GameListMixin
from tabs.xr_controls_mixin import XrControlsMixin
from translations import available_languages, get_language, set_language
from ui.ui_main import Ui_MainWindow

log = get_logger("main")


def _initial_language():
    """Gespeicherte Sprache, sonst Systemsprache (de/en), sonst Englisch."""
    saved = read_json(paths.config_file("config.json"), default={})
    lang = saved.get("language") if isinstance(saved, dict) else None
    if lang in available_languages():
        return lang
    system = QLocale.system().name().split("_")[0]
    return system if system in available_languages() else "en"


class ControlsWindow(GameListMixin, ControlsTabMixin, XrControlsMixin, QMainWindow):

    # Laufende Threads, auf die beim Schliessen gewartet wird
    _BACKGROUND_WORKERS = ("_obah_scan_worker", "tool_worker")

    def __init__(self):
        super().__init__()
        paths.ensure_dirs()
        from ui import no_wheel
        no_wheel.install(QApplication.instance())
        set_language(_initial_language())

        self.tool_worker = None
        self._closing = False
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        idx = self.ui.combo_language.findData(get_language())
        self.ui.combo_language.setCurrentIndex(max(idx, 0))
        self.ui.combo_language.currentIndexChanged.connect(self.on_language_changed)
        self.ui.btn_info.clicked.connect(self.show_about)

        self.setup_controls_tab_logic()
        self.setup_game_list()
        # Beim Start gleich aufklappen und Spiele suchen — das ist die
        # einzige Seite, es gibt nichts anderes zu sehen.
        QTimer.singleShot(0, self.refresh_controls_status)

    # ------------------------------------------------------------------ #
    #  Sprache
    # ------------------------------------------------------------------ #
    def on_language_changed(self, index):
        lang = self.ui.combo_language.itemData(index) or "en"
        set_language(lang)
        if not update_json(paths.config_file("config.json"), {"language": lang}):
            log.warning("Sprache konnte nicht gespeichert werden.")
        self.ui.retranslate_ui()
        for key in self.ui.controls_rows:
            if key not in self._controls_pending:
                self._render_control(key, self._control_installed(key))
        self.obah_retranslate()

    def show_about(self):
        from ui.about_dialog import AboutDialog
        AboutDialog(self).exec()

    # ------------------------------------------------------------------ #
    #  Beenden
    # ------------------------------------------------------------------ #
    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return
        if getattr(self, "_obah_dirty", False) and not self.confirm_obah_close():
            event.ignore()
            return
        self._closing = True
        try:
            self.ui.xrbinder_card.shutdown()
        except Exception as exc:  # noqa: BLE001
            log.debug("closeEvent (xrbinder): ignoriert — %s", exc)
        for name in self._BACKGROUND_WORKERS:
            worker = getattr(self, name, None)
            if worker is None or not worker.isRunning():
                continue
            if hasattr(worker, "cancel"):
                worker.cancel()
            if not worker.wait(3000):
                log.warning("Thread %s haengt — wird beendet.", name)
                worker.terminate()
                worker.wait(1000)
        event.accept()
