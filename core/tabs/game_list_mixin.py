#!/usr/bin/env python3
"""
core/tabs/game_list_mixin.py — Spiele von Hand in die Liste holen
=================================================================
NEU in OpenXR-VR-Control (gibt es in Yakuda Connect nicht, dort erledigt
das der Games-Tab). Drei Knoepfe unter der Spieleauswahl:

  * „+ Steam-Spiel hinzufügen“  -> SteamGameDialog  -> game_library
  * „+ Lokales Spiel hinzufügen“ -> LocalGameDialog -> game_library
  * „Aus Liste entfernen“        -> nur bei Handeintraegen sichtbar

Danach wird die Spieleliste neu gesucht und das neue Spiel ausgewaehlt.
Arbeitet auf demselben self wie ControlsTabMixin (steht in der
Vererbung davor und haengt sich in zwei Methoden ein).
"""
from PySide6.QtWidgets import QDialog, QMessageBox

import game_library as lib
from logging_setup import get_logger
from translations import tr

log = get_logger("game_list")


class GameListMixin:

    def setup_game_list(self):
        self._select_after_scan = None
        ui = self.ui
        ui.btn_add_steam_game.clicked.connect(lambda: self.add_steam_game())
        ui.btn_add_local_game.clicked.connect(lambda: self.add_local_game())
        ui.btn_remove_game.clicked.connect(lambda: self.remove_current_game())

    # ------------------------------------------------------------------ #
    #  Hinzufuegen
    # ------------------------------------------------------------------ #
    def add_steam_game(self, choice=None):
        """choice: fuer Tests ({"id", "name", "kind"}), sonst Dialog."""
        if choice is None:
            from ui.add_game_dialog import SteamGameDialog
            dlg = SteamGameDialog(self, exclude={g.ident for g in self._obah_games})
            if dlg.exec() != QDialog.Accepted:
                return False
            choice = dlg.selected()
        if not choice:
            return False
        lib.add_manual_steam_appid(choice["id"])
        log.info("Steam-Spiel von Hand eingetragen: %s (%s)", choice["name"], choice["id"])
        self._rescan_and_select(f"{choice['kind']}:{choice['id']}")
        return True

    def add_local_game(self, values=None):
        """values: fuer Tests ((name, exe)), sonst Dialog."""
        if values is None:
            from ui.add_game_dialog import LocalGameDialog
            dlg = LocalGameDialog(self)
            if dlg.exec() != QDialog.Accepted:
                return False
            values = dlg.values()
        ok, result = lib.add_local_game(*values)
        if not ok:
            QMessageBox.warning(self, tr("lib_local_title"), tr("lib_err_" + result))
            return False
        log.info("Lokales Spiel eingetragen: %s -> %s", values[0], values[1])
        self._rescan_and_select(f"{lib.KIND_LOCAL}:{result}")
        return True

    def _rescan_and_select(self, ident):
        self._select_after_scan = ident
        if not self.ui.btn_obah_expand.isChecked():
            self.ui.btn_obah_expand.setChecked(True)     # startet die Suche selbst
        else:
            self.start_obah_game_scan()

    # ------------------------------------------------------------------ #
    #  Entfernen
    # ------------------------------------------------------------------ #
    def _current_manual_game(self):
        game = self._current_obah_game()
        if game is None or not lib.is_manual(game.appid, game.kind):
            return None
        return game

    def remove_current_game(self, confirm=True):
        game = self._current_manual_game()
        if game is None:
            return False
        if confirm:
            reply = QMessageBox.question(
                self, tr("lib_remove"), tr("lib_remove_confirm").format(name=game.name),
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
        lib.remove_game(game.appid, game.kind)
        log.info("Spiel aus der Liste genommen: %s (%s)", game.name, game.ident)
        self._obah_last_game = None
        self.start_obah_game_scan()
        return True

    # ------------------------------------------------------------------ #
    #  Einhaengen in ControlsTabMixin
    # ------------------------------------------------------------------ #
    def _on_obah_game_changed(self, index):
        super()._on_obah_game_changed(index)
        self.ui.btn_remove_game.setVisible(self._current_manual_game() is not None)

    def _on_obah_games_found(self, games):
        super()._on_obah_games_found(games)
        ident, self._select_after_scan = getattr(self, "_select_after_scan", None), None
        if ident:
            j = next((j for j, g in enumerate(self._obah_games) if g.ident == ident), -1)
            idx = self._obah_combo_index(j)
            if idx >= 0:
                self.ui.combo_obah_game.setCurrentIndex(idx)
        self.ui.btn_remove_game.setVisible(self._current_manual_game() is not None)
