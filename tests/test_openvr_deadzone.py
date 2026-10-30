#!/usr/bin/env python3
"""Tests: Deadzone in der OpenVR-Ansicht (xrBinder, sonst Fallback deadzone_pct)."""
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "core"))

import obah_bindings as ob  # noqa: E402
import obah_editor as oe  # noqa: E402
import xr_openvr_link as link  # noqa: E402

L = "/user/hand/left/input/"
R = "/user/hand/right/input/"
STATE = {
    "actions": [{"name": "move", "type": 3, "hands": ["left", "right"], "description": "Move"}],
    "bindings": {"move": [L + "thumbstick", R + "thumbstick"]},
    "sources": {},
}


def _game(folder):
    return ob.ObahGame(name="Test", appid="123", game_folder=str(folder), actions_json="x.json")


def test_find_app_by_exe(tmp_path, monkeypatch):
    monkeypatch.setattr(link.xb, "state_dir", lambda: str(tmp_path / "state"))
    (tmp_path / "game" / "bin").mkdir(parents=True)
    (tmp_path / "game" / "bin" / "MyGame.exe").write_text("")
    assert link.find_app(_game(tmp_path / "game"), ["Other", "MyGame"]) == "MyGame"


def test_find_app_unreal_path(tmp_path, monkeypatch):
    monkeypatch.setattr(link.xb, "state_dir", lambda: str(tmp_path / "state"))
    p = tmp_path / "game" / "GG" / "Binaries" / "Win64"
    p.mkdir(parents=True)
    (p / "GG-Win64-Shipping.exe").write_text("")
    name = "GG/Binaries/Win64/GG-Win64-Shipping"
    assert link.find_app(_game(tmp_path / "game"), [name]) == name


def test_find_app_none(tmp_path, monkeypatch):
    monkeypatch.setattr(link.xb, "state_dir", lambda: str(tmp_path / "state"))
    (tmp_path / "game").mkdir()
    assert link.find_app(_game(tmp_path / "game"), ["Nope"]) is None


def _dialog(dz):
    from ui.binding_dialog import BindingDialog
    d = next(i for i in oe.inputs_for_side("oculus_touch", "left") if i.type == "joystick")
    return BindingDialog(None, manifest={}, binding={}, controller_type="oculus_touch",
                         set_name="/actions/main", set_label="Main", input_def=d,
                         side="left", drafts=[], deadzone=dz)


def test_joystick_dialog_has_deadzone_tab(qapp):
    before = {}
    dlg = _dialog({"state": STATE, "mappings": before, "game": "Test"})
    assert dlg.tabs is not None and dlg.tabs.count() == 2
    dlg.dz_check.setChecked(False)
    dlg.tabs.setCurrentIndex(1)
    assert dlg.dz_panel.isVisibleTo(dlg) and not dlg.body_host.isVisibleTo(dlg)
    dlg.dz_rows["left"]["slider"].setValue(20)
    assert dlg.dz_mappings[("move", "left")]["deadzone"] == 0.2
    assert before == {}                      # Original bleibt unberuehrt
    dlg.deleteLater()


def test_joystick_dialog_note_without_app(qapp):
    dlg = _dialog({"note": "Spiel einmal starten"})
    assert dlg.tabs.count() == 2 and dlg.dz_mappings is None
    assert dlg.dz_slider is not None
    dlg.deleteLater()


def test_joystick_dialog_fallback_without_data(qapp):
    dlg = _dialog(None)
    assert dlg.tabs.count() == 2 and dlg.dz_mappings is None
    assert dlg.dz_slider is not None
    dlg.deleteLater()


NO_KEYS = {
    "actions": [{"name": "move", "type": 3, "hands": ["left", "right"], "description": "Move"},
                {"name": "jump", "type": 1, "hands": [], "description": "Jump"}],
    "bindings": {},
    "sources": {},
}


def test_template_button_unlocks_sliders(qapp):
    from ui.xr_deadzone_panel import DeadzonePanel
    maps = {}
    panel = DeadzonePanel(NO_KEYS, maps)
    assert not panel.rows["left"]["slider"].isEnabled()
    assert panel.btn_template.isVisibleTo(panel) or not panel.btn_template.isHidden()
    panel.btn_template.click()
    assert maps
    assert panel.btn_template.isHidden()
    assert panel.rows["left"]["slider"].isEnabled()
    panel.rows["left"]["slider"].setValue(20)
    assert maps[("move", "left")]["deadzone"] == 0.2
    panel.deleteLater()


def _stick_dialog(drafts, dz=None):
    from ui.binding_dialog import BindingDialog
    d = next(i for i in oe.inputs_for_side("oculus_touch", "left") if i.type == "joystick")
    manifest = oe.Manifest(path="", action_sets=[], actions={}, localization={})
    return BindingDialog(None, manifest=manifest, binding={}, controller_type="oculus_touch",
                         set_name="/actions/main", set_label="Main", input_def=d,
                         side="left", drafts=drafts, deadzone=dz)


def test_use_pct_is_default_and_remembered(qapp):
    import deadzone_pref
    deadzone_pref.set_use_pct(True)
    dlg = _stick_dialog([], {"state": STATE, "mappings": {}, "game": "Test"})
    assert dlg.dz_check.isChecked() and dlg.dz_use_pct
    assert dlg.dz_panel.pct_panel.isVisibleTo(dlg.dz_panel)
    assert not dlg.dz_panel.xr_box.isVisibleTo(dlg.dz_panel)
    dlg.dz_check.setChecked(False)
    assert not deadzone_pref.use_pct() and not dlg.dz_use_pct
    assert dlg.dz_panel.xr_box.isVisibleTo(dlg.dz_panel)
    deadzone_pref.set_use_pct(True)
    dlg.deleteLater()


def test_pct_only_touches_joystick_mode(qapp):
    import deadzone_pref
    deadzone_pref.set_use_pct(True)
    drafts = [{"mode": "joystick", "inputs": {}}, {"mode": "dpad", "inputs": {}},
              {"mode": "trackpad", "inputs": {}}]
    dlg = _stick_dialog(drafts)
    assert dlg.dz_slider.maximum() == 100
    dlg.dz_slider.setValue(80)
    assert dlg.drafts[0]["parameters"]["deadzone_pct"] == "80"
    assert "parameters" not in dlg.drafts[1] and "parameters" not in dlg.drafts[2]
    dlg.deleteLater()


def test_pct_slider_locked_without_joystick_binding(qapp):
    import deadzone_pref
    deadzone_pref.set_use_pct(True)
    dlg = _stick_dialog([{"mode": "dpad", "inputs": {}}])
    assert not dlg.dz_slider.isEnabled()
    info = dlg.dz_panel.pct_panel.rows["left"]["info"].text()
    assert info
    dlg.deleteLater()


def test_deadzone_dialog_both_sticks(qapp):
    import deadzone_pref
    from ui.deadzone_dialog import DeadzoneDialog
    deadzone_pref.set_use_pct(True)
    manifest = oe.Manifest(path="", action_sets=[], actions={}, localization={})
    left = [{"mode": "joystick", "inputs": {}}]
    right = [{"mode": "joystick", "inputs": {}}]
    dlg = DeadzoneDialog(None, title="Main", manifest=manifest,
                         sides=[("left", "L", left, ("joystick",)),
                                ("right", "R", right, ("joystick",))],
                         xr={"note": "x"}, controller_type="oculus_touch")
    dlg.chooser.pct_panel.rows["both"]["slider"].setValue(15)
    assert dlg.drafts_of("left")[0]["parameters"]["deadzone_pct"] == "15"
    assert dlg.drafts_of("right")[0]["parameters"]["deadzone_pct"] == "15"
    assert left == [{"mode": "joystick", "inputs": {}}]      # Original unberuehrt
    dlg.deleteLater()


def test_deadzone_dialog_openxr(qapp):
    from ui.deadzone_dialog import DeadzoneDialog
    maps = {}
    dlg = DeadzoneDialog(None, title="Main", controller_type="oculus_touch",
                         xr_state=STATE, xr_mappings=maps)
    dlg.panel.rows["left"]["slider"].setValue(20)
    assert dlg.xr_mappings[("move", "left")]["deadzone"] == 0.2
    assert maps == {}
    dlg.deleteLater()


def test_deadzone_button_writes_both_sticks(qapp, monkeypatch):
    import deadzone_pref
    from types import SimpleNamespace
    from PySide6.QtWidgets import QLabel, QTabBar, QWidget
    from tabs.controls_mixin import ControlsTabMixin
    from ui.deadzone_dialog import DeadzoneDialog
    deadzone_pref.set_use_pct(True)

    class Host(QWidget, ControlsTabMixin):
        dirty = False

        def _set_obah_dirty(self, dirty):
            self.dirty = dirty

        def _render_obah_views(self):
            pass

        def _current_obah_game(self):
            return None

        def xr_openvr_deadzone(self, game):
            return None, {"note": "x"}

    host = Host()
    tabs = QTabBar()
    tabs.addTab("Main")
    tabs.setTabData(0, "/actions/main")
    host.ui = SimpleNamespace(obah_set_tabs=tabs, lbl_obah_editor_status=QLabel())
    manifest = oe.Manifest(path="", action_sets=[], actions={}, localization={})
    binding = {}
    host._obah_edit = {"manifest": manifest, "binding": binding, "controller": "oculus_touch"}
    for side in ("left", "right"):
        d = oe.deadzone_input_for_side("oculus_touch", side)
        draft = dict(oe.new_draft(d, side, "oculus_touch", binding), mode="joystick")
        oe.apply_drafts(binding, "/actions/main", d, side, [draft])

    def fake_exec(dlg):
        dlg.chooser.pct_panel.rows["both"]["slider"].setValue(12)
        return DeadzoneDialog.Accepted
    monkeypatch.setattr(DeadzoneDialog, "exec", fake_exec)
    host.open_obah_deadzone_dialog()
    for side in ("left", "right"):
        d = oe.deadzone_input_for_side("oculus_touch", side)
        drafts = oe.source_drafts(binding, "/actions/main", d, side)
        assert drafts[0]["parameters"]["deadzone_pct"] == "12"
    assert host.dirty


def test_set_tabs_ignore_mouse_wheel(qapp):
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from ui.no_wheel import NoWheelTabBar
    bar = NoWheelTabBar()
    for t in ("Global", "Menu", "Action Menu"):
        bar.addTab(t)
    ev = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120),
                     Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    bar.wheelEvent(ev)
    assert bar.currentIndex() == 0 and not ev.isAccepted()
    bar.deleteLater()
