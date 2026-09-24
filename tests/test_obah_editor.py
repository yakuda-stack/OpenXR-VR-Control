#!/usr/bin/env python3
"""
tests/test_obah_editor.py — Bindings-Ansicht (Action Sets, Controller, Linien)
=============================================================================
Testdaten im Stil von VRChat: Action Sets global (L/R), one_hand, menu,
ActionMenu, drone (L/R); Bindings fuer Oculus/Meta Touch als xrizer-Datei.
"""
import json
import os
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import obah_bindings as ob  # noqa: E402
import obah_editor as oe  # noqa: E402

A = "/actions/"


def _src(path, mode, inputs):
    return {"path": path, "mode": mode, "inputs": {k: {"output": A + v} for k, v in inputs.items()}}


@pytest.fixture
def vrchat(tmp_path):
    sa = tmp_path / "steamapps"
    game = sa / "common" / "VRChat"
    svr = game / "VRChat_Data" / "StreamingAssets" / "SteamVR"
    svr.mkdir(parents=True)
    (game / "xrizer").mkdir()
    manifest = {
        "actions": [{"name": A + n, "type": t} for n, t in (
            ("global/in/Jump", "boolean"), ("global/in/Move", "vector2"),
            ("global/in/Look", "vector2"), ("global/in/Use", "boolean"),
            ("global/in/Run", "vector1"), ("drone/in/Fly", "vector2"))],
        "action_sets": [
            {"name": "/actions/global", "usage": "leftright"},
            {"name": "/actions/one_hand", "usage": "single"},
            {"name": "/actions/menu"},
            {"name": "/actions/ActionMenu", "usage": "single"},
            {"name": "/actions/drone", "usage": "leftright"}],
        "default_bindings": [],
        "localization": [
            {"language_tag": "en_US", "/actions/global/in/Look": "Turn"},
            {"language_tag": "de_DE", "/actions/global/in/Look": "Drehen"}],
    }
    (svr / "actions.json").write_text(json.dumps(manifest))
    L, R = "/user/hand/left/input/", "/user/hand/right/input/"
    binding = {"controller_type": "oculus_touch", "bindings": {
        "/actions/global": {"sources": [
            _src(L + "joystick", "joystick", {"position": "global/in/Move"}),
            _src(R + "joystick", "joystick", {"position": "global/in/Look"}),
            _src(R + "a", "button", {"click": "global/in/Jump"}),
            _src(R + "trigger", "trigger", {"pull": "global/in/Run", "click": "global/in/Use"}),
        ]},
        # Gross/klein und '/' am Ende wie in echten Dateien
        "/actions/Drone/": {"sources": [_src(L + "joystick", "joystick", {"position": "drone/in/Fly"})]},
    }}
    (game / "xrizer" / "oculustouch.json").write_text(json.dumps(binding))
    apps = [{"appid": "438100", "name": "VRChat", "installdir": "VRChat", "steamapps": str(sa)}]
    return ob.list_games(apps=apps)[0]


def test_action_set_tabs_like_obah(vrchat):
    m = oe.load_manifest(vrchat.actions_json)
    assert [oe.set_label(m, a) for a in m.action_sets] == \
        ["Global (L/R)", "One Hand", "Menu", "Action Menu", "Drone (L/R)"]


def test_sides_follow_profile():
    left = [d.path for d in oe.inputs_for_side("oculus_touch", "left")]
    right = [d.path for d in oe.inputs_for_side("oculus_touch", "right")]
    assert "/input/x" in left and "/input/a" not in left
    assert "/input/a" in right and "/input/x" not in right
    assert "/input/joystick" in left and "/input/joystick" in right
    # Posen/Skelett/Vibration zeigt obah in dieser Liste nicht
    assert not any(p.startswith("/pose") for p in left)
    assert oe.is_handed("oculus_touch") and not oe.is_handed("gamepad")


def test_build_view_matches_obah(vrchat):
    m = oe.load_manifest(vrchat.actions_json)
    b = oe.load_binding(ob.binding_file(vrchat, "oculus_touch", "xrizer"))
    right = {v.input.path: v for v in oe.build_view(m, b, "oculus_touch", "/actions/global", "right")}
    trig = right["/input/trigger"].bindings[0]
    assert trig.mode == "trigger"
    # erwartete Zeilen (pull, touch) plus unbekannte aus der Datei (click)
    assert [(r.input, r.label) for r in trig.inputs] == [("pull", "Run"), ("touch", ""), ("click", "Use")]
    assert right["/input/joystick"].bindings[0].inputs[0].label == "Turn"   # lokalisiert
    assert right["/input/a"].bound and not right["/input/b"].bound
    left = {v.input.path: v for v in oe.build_view(m, b, "oculus_touch", "/actions/global", "left")}
    assert left["/input/joystick"].bindings[0].inputs[0].label == "Move"
    assert not left["/input/trigger"].bindings          # rechts belegt, links nicht


def test_localization_prefers_app_language(vrchat):
    m = oe.load_manifest(vrchat.actions_json)
    assert oe.localized(m, "/actions/global/in/Look", "de") == "Drehen"
    assert oe.localized(m, "/actions/global/in/Look", "en") == "Turn"
    assert oe.localized(m, "/actions/global/in/Jump", "de") == "Jump"   # Fallback: Pfad


def test_set_name_matching_is_lenient(vrchat):
    m = oe.load_manifest(vrchat.actions_json)
    b = oe.load_binding(ob.binding_file(vrchat, "oculus_touch", "xrizer"))
    left = {v.input.path: v for v in oe.build_view(m, b, "oculus_touch", "/actions/drone", "left")}
    assert left["/input/joystick"].bindings[0].inputs[0].action.endswith("drone/in/Fly")


def test_scratch_is_empty(vrchat):
    m = oe.load_manifest(vrchat.actions_json)
    views = oe.build_view(m, oe.load_binding(None), "oculus_touch", "/actions/global", "left")
    assert views and not any(v.bindings for v in views)


def test_broken_manifest_raises_readable_error(tmp_path):
    bad = tmp_path / "actions.json"
    bad.write_text("{kaputt")
    with pytest.raises(ValueError, match="actions.json"):
        oe.load_manifest(str(bad))
    bad.write_text(json.dumps({"actions": []}))
    with pytest.raises(ValueError, match="Action Sets"):
        oe.load_manifest(str(bad))


# --------------------------------------------------------------------------- #
#  Oberflaeche
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def app(qapp, tmp_path_factory):
    os.environ["HOME"] = str(tmp_path_factory.mktemp("home"))
    from PySide6.QtWidgets import QMessageBox
    for m in ("warning", "information", "critical"):
        setattr(QMessageBox, m, staticmethod(lambda *a, **k: QMessageBox.Ok))
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    from main import ControlsWindow as VRApp
    window = VRApp()
    window.resize(1400, 900)
    yield window
    window.close()


def test_first_open_presets_vrchat_touch_xrizer(app, qapp, vrchat, monkeypatch):
    other = ob.ObahGame(name="Aaa Game", appid="1", game_folder=vrchat.game_folder,
                        actions_json=vrchat.actions_json)
    monkeypatch.setattr(ob, "list_games", lambda cancelled=None: [other, vrchat])
    app.refresh_controls_status()                    # = Tab zum ersten Mal geoeffnet
    if app._obah_scan_worker:
        app._obah_scan_worker.wait(5000)
    for _ in range(20):
        qapp.processEvents()
    ui = app.ui
    assert ui.btn_obah_expand.isChecked()
    assert ui.combo_obah_game.currentText() == "VRChat"          # nicht der erste Eintrag
    assert ui.combo_obah_controller.currentData() == "oculus_touch"
    assert ui.combo_obah_source.currentData() == "xrizer"

    tabs = [ui.obah_set_tabs.tabText(i) for i in range(ui.obah_set_tabs.count())]
    assert tabs == ["Global (L/R)", "One Hand", "Menu", "Action Menu", "Drone (L/R)"]
    assert ui.obah_view_left.card_count() == len(oe.inputs_for_side("oculus_touch", "left"))
    assert ui.obah_view_right.card_count() == len(oe.inputs_for_side("oculus_touch", "right"))

    # Tab wechseln -> Ansicht zeigt das Drone-Set
    ui.obah_set_tabs.setCurrentIndex(4)
    left = ui.obah_view_left
    texts = [line for i in range(left.card_count()) for line in left.card_lines(i)]
    assert ("row", "Position", "Fly") in texts


def test_points_sit_on_the_drawing(app):
    """Jeder Punkt liegt in der Zeichnung, jede Karte ausserhalb davon."""
    for view in (app.ui.obah_view_left, app.ui.obah_view_right):
        img = view._img_rect
        for i in range(view.card_count()):
            assert img.adjusted(-2, -2, 2, 2).contains(view.point_of(i))
            assert not view.card_rect(i).intersects(img)


def test_cards_do_not_overlap(app):
    view = app.ui.obah_view_left
    rects = sorted((view.card_rect(i) for i in range(view.card_count())), key=lambda r: r.top())
    for a, b in zip(rects, rects[1:]):
        assert a.bottom() <= b.top()


def test_pair_stacks_when_narrow(app, qapp):
    pair = app.ui.obah_hands
    pair.resize(1300, pair.height())
    pair.relayout()
    assert not pair.is_stacked()
    pair.resize(700, pair.height())
    pair.relayout()
    assert pair.is_stacked()


# --------------------------------------------------------------------------- #
#  Deadzone (Tab im Binding-Dialog)
# --------------------------------------------------------------------------- #
def test_deadzone_helpers_only_touch_stick_modes():
    drafts = [{"mode": "joystick", "path": "/user/hand/left/input/joystick"},
              {"mode": "dpad", "path": "/user/hand/left/input/joystick",
               "parameters": {"deadzone_pct": "25"}},
              {"mode": "trackpad", "parameters": {"deadzone_pct": "abc"}}]
    assert [d["mode"] for d in oe.deadzone_drafts(drafts)] == ["joystick", "trackpad"]
    assert [oe.draft_deadzone(d) for d in drafts] == [0, 25, 0]
    oe.set_drafts_deadzone(drafts, 15)
    assert drafts[0]["parameters"] == {"deadzone_pct": "15"}
    assert drafts[1]["parameters"] == {"deadzone_pct": "25"}      # dpad bleibt
    assert drafts[2]["parameters"]["deadzone_pct"] == "15"
    oe.set_drafts_deadzone(drafts, 99)                               # auf Maximum begrenzt
    assert oe.draft_deadzone(drafts[0]) == oe.DEADZONE_MAX_PCT
    oe.set_drafts_deadzone(drafts, 0)                                # aus -> Parameter weg
    assert "parameters" not in drafts[0]


def test_binding_dialog_has_deadzone_tab_only_for_sticks(qapp):
    from ui.binding_dialog import BindingDialog
    stick = next(d for d in oe.inputs_for_side("oculus_touch", "left") if d.type == "joystick")
    button = next(d for d in oe.inputs_for_side("oculus_touch", "left") if d.type == "button")
    manifest = oe.Manifest(path="", action_sets=[], actions={}, localization={})
    kw = dict(manifest=manifest, binding={}, controller_type="oculus_touch", set_name="/actions/main",
              set_label="Main", side="left")
    dlg = BindingDialog(None, input_def=stick, drafts=[{"mode": "joystick", "inputs": {}}], **kw)
    assert dlg.tabs is not None
    dlg.tabs.setCurrentIndex(1)
    dlg.dz_slider.setValue(20)
    assert dlg.drafts[0]["parameters"]["deadzone_pct"] == "20"
    dlg.dz_reset.click()
    assert "parameters" not in dlg.drafts[0]
    dlg2 = BindingDialog(None, input_def=button, drafts=[], **kw)
    assert dlg2.tabs is None
