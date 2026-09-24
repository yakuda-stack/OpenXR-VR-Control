#!/usr/bin/env python3
"""
tests/test_obah_edit.py — Bindings bearbeiten, speichern, Anordnung
===================================================================
  * Regeln wie in obah: Modi je Eingabe, passende Aktionen, Parameter
  * Popup: Binding hinzufuegen/entfernen, Modus, Aktion, Parameter
  * Controls-Tab: Uebernehmen -> ungespeichert -> Speichern (mit .bak)
  * Karten wachsen mit, Karten/Controller lassen sich verschieben
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


def _d(path, ct="oculus_touch", side="left"):
    return next(x for x in oe.inputs_for_side(ct, side) if x.path == path)


@pytest.fixture
def game(tmp_path):
    g = tmp_path / "VRChat"
    svr = g / "VRChat_Data" / "StreamingAssets" / "SteamVR"
    svr.mkdir(parents=True)
    (g / "xrizer").mkdir()
    manifest = {
        "actions": [{"name": A + n, "type": t} for n, t in (
            ("global/in/Move", "vector2"), ("global/in/Jump", "boolean"),
            ("global/in/Stick_Click", "boolean"), ("global/in/Run", "vector1"),
            ("menu/in/Select", "boolean"))],
        "action_sets": [{"name": "/actions/global", "usage": "leftright"},
                        {"name": "/actions/menu"}],
        "default_bindings": [],
    }
    (svr / "actions.json").write_text(json.dumps(manifest))
    binding = {"controller_type": "oculus_touch", "bindings": {"/actions/global": {"sources": [
        {"path": "/user/hand/left/input/trigger", "mode": "button",
         "inputs": {"click": {"output": A + "global/in/Jump"}}},
        {"path": "/user/hand/left/input/joystick", "mode": "joystick",
         "inputs": {"position": {"output": A + "global/in/Move"}}},
        {"path": "/user/hand/right/input/joystick", "mode": "joystick", "inputs": {}},
    ]}}}
    (g / "xrizer" / "oculustouch.json").write_text(json.dumps(binding))
    return ob.ObahGame(name="VRChat", appid="438100", game_folder=str(g),
                       actions_json=str(svr / "actions.json"))


# --------------------------------------------------------------------------- #
#  Regeln
# --------------------------------------------------------------------------- #
def test_supported_modes_like_obah():
    assert oe.supported_modes(_d("/input/joystick")) == \
        ["button", "toggle_button", "joystick", "dpad", "scroll"]
    assert oe.supported_modes(_d("/input/trigger")) == ["button", "toggle_button", "trigger"]
    assert oe.supported_modes(_d("/input/x")) == ["button", "toggle_button"]


def test_compatible_actions_filter_by_type_and_set(game):
    m = oe.load_manifest(game.actions_json)
    pos = oe.compatible_actions(m, "/actions/global", "joystick", "position")
    assert pos == [None, A + "global/in/Move"]                     # nur vector2
    click = oe.compatible_actions(m, "/actions/global", "joystick", "click")
    assert A + "global/in/Jump" in click and A + "global/in/Move" not in click
    assert A + "menu/in/Select" not in click                       # anderes Action Set
    pull = oe.compatible_actions(m, "/actions/global", "trigger", "pull")
    assert pull == [None, A + "global/in/Run"]
    # unbekannte eingetragene Aktion bleibt waehlbar
    keep = oe.compatible_actions(m, "/actions/global", "button", "click", "/actions/x/in/old")
    assert keep[-1] == "/actions/x/in/old"


def test_mode_change_drops_foreign_inputs():
    d = _d("/input/joystick")
    draft = {"path": "p", "mode": "joystick",
             "inputs": {"position": {"output": "a"}, "click": {"output": "b"}}}
    oe.set_draft_mode(d, draft, "dpad")
    assert draft["inputs"] == {}                  # dpad kennt position/click nicht
    draft = {"path": "p", "mode": "joystick", "inputs": {"click": {"output": "b"}}}
    oe.set_draft_mode(d, draft, "button")
    assert draft["inputs"] == {"click": {"output": "b"}}


def test_parameters(game):
    d = _d("/input/joystick")
    names = [s[0] for s in oe.known_parameter_specs(d, "joystick")]
    assert names == ["deadzone_pct", "maxzone_pct", "invert"]
    draft = {"mode": "joystick", "inputs": {}}
    oe.set_draft_parameter(draft, "deadzone_pct", "10")
    with pytest.raises(ValueError):
        oe.set_draft_parameter(draft, "DEADZONE_PCT", "5")          # doppelt
    oe.set_draft_parameter(draft, "deadzone_pct", "12", original="deadzone_pct")
    assert draft["parameters"] == {"deadzone_pct": "12"}
    assert oe.parse_parameter_value("json:0.5") == 0.5
    assert oe.parse_parameter_value("x") == "x"
    assert oe.format_parameter_value(True) == "json:true"
    with pytest.raises(ValueError):
        oe.parse_parameter_value("json:{kaputt")
    oe.remove_draft_parameter(draft, "deadzone_pct")
    assert "parameters" not in draft


def test_new_binding_path():
    assert oe.new_binding_path(_d("/input/x"), "left", "oculus_touch", {}) == "/user/hand/left/input/x"
    gp = next(x for x in oe.inputs_for_side("gamepad", "single") if x.path == "/input/a")
    b = {"bindings": {"/actions/m": {"sources": [{"path": "/user/gamepad/input/b"}]}}}
    assert oe.new_binding_path(gp, "single", "gamepad", b) == "/user/gamepad/input/a"


def test_apply_drafts_keeps_position_and_other_side(game):
    b = oe.load_binding(ob.binding_file(game, "oculus_touch", "xrizer"))
    d = _d("/input/joystick")
    drafts = oe.source_drafts(b, "/actions/global", d, "left")
    assert len(drafts) == 1
    extra = oe.new_draft(d, "left", "oculus_touch", b)
    oe.set_draft_mode(d, extra, "dpad")
    oe.apply_drafts(b, "/actions/global", d, "left", drafts + [extra])
    paths = [(s["path"], s["mode"]) for s in b["bindings"]["/actions/global"]["sources"]]
    assert paths == [("/user/hand/left/input/trigger", "button"),
                     ("/user/hand/left/input/joystick", "joystick"),
                     ("/user/hand/left/input/joystick", "dpad"),
                     ("/user/hand/right/input/joystick", "joystick")]
    # neues Action Set wird angelegt
    oe.apply_drafts(b, "/actions/menu", d, "left", [extra])
    assert b["bindings"]["/actions/menu"]["sources"][0]["mode"] == "dpad"


def test_save_writes_json_and_backup(game):
    path = oe.save_path(game, "oculus_touch", "xrizer")
    assert path.endswith("xrizer/oculustouch.json")
    b = oe.load_binding(path)
    b["bindings"]["/actions/global"]["sources"].pop()
    oe.save_binding(b, path, "oculus_touch")
    assert os.path.isfile(path + ".bak")
    assert len(json.load(open(path + ".bak"))["bindings"]["/actions/global"]["sources"]) == 3
    assert len(json.load(open(path))["bindings"]["/actions/global"]["sources"]) == 2
    oc = oe.save_path(game, "oculus_touch", "opencomposite")
    oe.save_binding(b, oc, "oculus_touch")               # Ordner wird angelegt
    assert os.path.isfile(oc) and not os.path.exists(oc + ".bak")


# --------------------------------------------------------------------------- #
#  Popup
# --------------------------------------------------------------------------- #
def test_dialog_add_edit_remove(qapp, game):
    from ui.binding_dialog import BindingDialog
    m = oe.load_manifest(game.actions_json)
    b = oe.load_binding(ob.binding_file(game, "oculus_touch", "xrizer"))
    d = _d("/input/joystick")
    dlg = BindingDialog(None, manifest=m, binding=b, controller_type="oculus_touch",
                        set_name="/actions/global", set_label="Global (L/R)",
                        input_def=d, side="left",
                        drafts=oe.source_drafts(b, "/actions/global", d, "left"))
    assert dlg.list.count() == 1
    dlg._add_binding()
    assert dlg.list.count() == 2 and dlg._current == 1
    assert dlg.drafts[1]["path"] == "/user/hand/left/input/joystick"
    assert dlg.drafts[1]["mode"] == "button"                # erster unterstuetzter Modus
    dlg._set_action("click", A + "global/in/Stick_Click")
    assert "Stick_Click" in dlg.list.item(1).text()
    dlg._set_mode("joystick")
    assert dlg.drafts[1]["inputs"] == {"click": {"output": A + "global/in/Stick_Click"}}
    dlg._add_param("invert", "n")
    assert dlg.drafts[1]["parameters"] == {"invert": "n"}
    dlg._remove_param("invert")
    dlg.list.setCurrentRow(0)
    dlg._remove_binding()
    assert len(dlg.drafts) == 1 and dlg.drafts[0]["inputs"]["click"]["output"].endswith("Stick_Click")
    # Original unveraendert, bis uebernommen wird
    assert len(oe.source_drafts(b, "/actions/global", d, "left")) == 1


# --------------------------------------------------------------------------- #
#  Controls-Tab
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


@pytest.fixture
def loaded(app, qapp, game, monkeypatch, tmp_path):
    # eigene Anordnungs-Datei: paths zeigt auf den echten Config-Ordner
    layout_file = str(tmp_path / "controls_layout.json")
    monkeypatch.setattr(app, "_obah_layout_file", lambda: layout_file)
    monkeypatch.setattr(ob, "list_games", lambda cancelled=None: [game])
    app._obah_scanned = False
    app._obah_user_source = None
    app._obah_user_controller = "oculus_touch"
    app._set_obah_dirty(False)
    app.ui.btn_obah_expand.setChecked(False)
    app.ui.btn_obah_expand.setChecked(True)
    app.start_obah_game_scan()
    app._obah_scan_worker.wait(5000)
    for _ in range(20):
        qapp.processEvents()
    assert app.ui.combo_obah_source.currentData() == "xrizer"
    return app


def _edit_via_dialog(app, monkeypatch, view, path, change):
    import ui.binding_dialog as bd

    def fake_exec(dlg):
        change(dlg)
        return bd.BindingDialog.Accepted
    monkeypatch.setattr(bd.BindingDialog, "exec", fake_exec)
    app.open_obah_binding_dialog(view, path)


def test_card_click_edit_marks_dirty_and_card_grows(loaded, monkeypatch):
    app = loaded
    view = app.ui.obah_view_left
    idx = next(i for i in range(view.card_count())
               if view._layout[i][2].input.path == "/input/joystick")
    h_before = view.card_rect(idx).height()

    def change(dlg):
        dlg._add_binding()
        dlg._set_mode("joystick")
        dlg._set_action("click", A + "global/in/Stick_Click")
    _edit_via_dialog(app, monkeypatch, view, "/input/joystick", change)

    assert app._obah_dirty
    assert app.ui.btn_obah_save.isEnabled()
    assert "●" in app.ui.lbl_obah_editor_status.text()
    idx = next(i for i in range(view.card_count())
               if view._layout[i][2].input.path == "/input/joystick")
    assert view.card_rect(idx).height() > h_before           # Karte ist gewachsen
    modes = [t[1] for t in view.card_lines(idx) if t[0] == "mode"]
    assert len(modes) == 2


def test_cancel_changes_nothing(loaded, monkeypatch):
    import ui.binding_dialog as bd
    monkeypatch.setattr(bd.BindingDialog, "exec", lambda dlg: bd.BindingDialog.Rejected)
    loaded.open_obah_binding_dialog(loaded.ui.obah_view_left, "/input/x")
    assert not loaded._obah_dirty


def test_save_writes_file_and_reloads(loaded, monkeypatch, game):
    app = loaded
    _edit_via_dialog(app, monkeypatch, app.ui.obah_view_right, "/input/a",
                     lambda dlg: (dlg._add_binding(), dlg._set_action("click", A + "global/in/Jump")))
    assert app._obah_dirty
    app.save_obah_binding(None)
    assert not app._obah_dirty
    path = ob.xrizer_path(game.game_folder, "oculus_touch")
    data = json.load(open(path))
    srcs = data["bindings"]["/actions/global"]["sources"]
    assert {"path": "/user/hand/right/input/a", "mode": "button",
            "inputs": {"click": {"output": A + "global/in/Jump"}}} in srcs
    assert os.path.isfile(path + ".bak")
    assert "✔" in app.ui.lbl_obah_editor_status.text()


def test_leaving_with_unsaved_changes_asks(loaded, monkeypatch, game):
    from PySide6.QtWidgets import QMessageBox
    app = loaded
    _edit_via_dialog(app, monkeypatch, app.ui.obah_view_left, "/input/y",
                     lambda dlg: dlg._add_binding())
    asked = []

    def fake_box_exec(box):
        asked.append(box.windowTitle())
        for b in box.buttons():
            if box.buttonRole(b) == QMessageBox.DestructiveRole:
                b.click()
        return 0
    monkeypatch.setattr(QMessageBox, "exec", fake_box_exec)
    combo = app.ui.combo_obah_controller
    combo.setCurrentIndex(combo.findData("knuckles"))
    assert asked and not app._obah_dirty
    data = json.load(open(ob.xrizer_path(game.game_folder, "oculus_touch")))
    assert not any(s["path"].endswith("/left/input/y")
                   for s in data["bindings"]["/actions/global"]["sources"])


def test_drag_card_reorders_and_never_overlaps(loaded, qapp):
    """Karte ziehen = Platz tauschen. Es ueberlappt nie etwas."""
    from PySide6.QtCore import QPointF, QRectF, QEvent, Qt
    from PySide6.QtGui import QMouseEvent
    app = loaded
    view = app.ui.obah_view_left

    def mouse(kind, pos):
        ev = QMouseEvent(kind, QPointF(pos), QPointF(pos), Qt.LeftButton,
                         Qt.LeftButton if kind != QEvent.MouseButtonRelease else Qt.NoButton,
                         Qt.NoModifier)
        {QEvent.MouseButtonPress: view.mousePressEvent,
         QEvent.MouseMove: view.mouseMoveEvent,
         QEvent.MouseButtonRelease: view.mouseReleaseEvent}[kind](ev)

    def no_overlap():
        rects = sorted((view.card_rect(i) for i in range(view.card_count())),
                       key=lambda r: r.top())
        return all(a.bottom() <= b.top() for a, b in zip(rects, rects[1:]))

    clicked = []
    view.card_clicked.disconnect()          # nicht das echte (modale) Popup oeffnen
    view.card_clicked.connect(clicked.append)
    assert no_overlap()
    order_before = view.card_order()
    first = order_before[0]
    start = view.card_rect(0).center()

    mouse(QEvent.MouseButtonPress, start)
    mouse(QEvent.MouseMove, start + QPointF(5, 170))
    assert view._gap_rect is not None       # Luecke zeigt, wo sie landet
    mouse(QEvent.MouseButtonRelease, start + QPointF(5, 170))

    assert not clicked                      # Ziehen ist kein Klick
    order_after = view.card_order()
    assert order_after != order_before
    assert order_after.index(first) > 0     # nach unten gewandert
    assert sorted(order_after) == sorted(order_before)   # keine verloren/doppelt
    assert no_overlap()

    # Controller verschieben: die Karten bleiben stehen, die Punkte wandern mit
    tops = [view.card_rect(i).top() for i in range(view.card_count())]
    img = QRectF(view._img_rect)
    pt_before = view.point_of(0)
    p = QPointF(img.left() + 3, img.bottom() - 3)       # Ecke: kein Punkt, keine Karte
    mouse(QEvent.MouseButtonPress, p)
    mouse(QEvent.MouseMove, p + QPointF(-20, 40))
    mouse(QEvent.MouseButtonRelease, p + QPointF(-20, 40))
    assert abs(view._img_rect.top() - (img.top() + 40)) < 1
    assert [view.card_rect(i).top() for i in range(view.card_count())] == tops
    assert abs((view.point_of(0) - pt_before).y() - 40) < 1

    # gemerkt und nach erneutem Rendern wieder da
    saved = app._load_obah_layout("oculus_touch", "left")
    assert saved["order"] == order_after and saved["image"]
    app._render_obah_views()
    assert view.card_order() == order_after
    assert abs(view._img_rect.top() - (img.top() + 40)) < 1
    assert app.ui.btn_obah_layout_reset.isEnabled()

    # Klick ohne Bewegung oeffnet das Popup
    c = view.card_rect(1).center()
    mouse(QEvent.MouseButtonPress, c)
    mouse(QEvent.MouseButtonRelease, c)
    assert clicked == [view.card_order()[1]]
    view.card_clicked.disconnect()
    view.card_clicked.connect(lambda path, v=view: app.open_obah_binding_dialog(v, path))

    app.reset_obah_layout()
    assert not view.has_manual_layout()
    assert app._load_obah_layout("oculus_touch", "left") == {}
    assert no_overlap()


def test_old_free_positions_become_an_order(qapp):
    """Aeltere Dateien hatten freie x/y — daraus wird die Reihenfolge."""
    from ui.controller_view import ControllerBindingView
    view = ControllerBindingView()
    view.resize(620, 800)
    views = [oe.InputView(input=d) for d in oe.inputs_for_side("oculus_touch", "left")]
    view.set_data("oculus_touch", "left", views, {})
    view.set_layout({"cards": {"/input/grip": [30, 10], "/input/x": [30, 400]}})
    order = view.card_order()
    assert order[0] == "/input/grip" and order.index("/input/x") == 1
    assert view.layout_state()["order"][:2] == ["/input/grip", "/input/x"]
