#!/usr/bin/env python3
"""
tests/test_yc_shared.py — xrBinder/obah von Yakuda Connect erkennen
===================================================================
Hat Yakuda Connect xrBinder schon gebaut, benutzt OpenXR-VR-Control diese
Installation (kein zweiter Build, gleiche Einstellungen je Spiel).
"""
import json
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

import appimage_installer as appimg  # noqa: E402
import xrbinder as xb  # noqa: E402


def _fake_build(root, patch=None):
    out = pathlib.Path(root) / "build" / xb.LAYER_NAME
    out.mkdir(parents=True)
    (out / "libxrBinder_module.so").write_text("so")
    ipc = out / "ipc_server"
    ipc.write_text("#!/bin/sh\n")
    ipc.chmod(0o755)
    if patch is not None:
        (pathlib.Path(root) / xb.PATCH_FILE).write_text(patch)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(xb, "TOOLS_DIR", str(tmp_path / ".config/openxr-vr-control/tools"))
    return tmp_path


def test_without_yakuda_connect_everything_is_own(home):
    assert xb.yc_config_root() == ""
    assert xb.tool_root() == xb.own_tool_root()
    assert not xb.is_built()
    assert "openxr-vr-control" in xb.state_dir()


def test_uses_yakuda_connect_build_and_state(home):
    yc = home / ".config/yakuda-connect"
    _fake_build(yc / "tools/xrbinder", patch=xb.PATCH_LEVEL)
    assert xb.is_built()
    assert xb.uses_yakuda_connect_build()
    assert xb.tool_root() == str(yc / "tools/xrbinder")
    assert xb.state_dir() == str(yc / "xrbinder")
    assert not xb.needs_rebuild()


def test_newer_patch_from_yc_is_not_downgraded(home):
    yc = home / ".config/yakuda-connect"
    _fake_build(yc / "tools/xrbinder", patch=str(int(xb.PATCH_LEVEL) + 1))
    assert not xb.needs_rebuild()
    (yc / "tools/xrbinder" / xb.PATCH_FILE).write_text("1")
    assert xb.needs_rebuild()                       # aelter -> neu bauen ok


def test_both_built_follows_manifest(home):
    yc = home / ".config/yakuda-connect/tools/xrbinder"
    _fake_build(yc, patch=xb.PATCH_LEVEL)
    _fake_build(xb.own_tool_root(), patch=xb.PATCH_LEVEL)
    assert xb.tool_root() == xb.own_tool_root()     # ohne Manifest: eigener
    os.makedirs(xb.implicit_dir())
    lib = yc / "build" / xb.LAYER_NAME / "libxrBinder_module.so"
    with open(xb.manifest_path(), "w") as fh:
        json.dump({"api_layer": {"library_path": str(lib)}}, fh)
    assert xb.tool_root() == str(yc)
    assert xb.layer_enabled()


def test_obah_built_by_yakuda_connect_counts_as_installed(home, monkeypatch):
    monkeypatch.setattr(appimg.shutil, "which", lambda _c: None)
    monkeypatch.setattr(appimg, "HOME", str(home))
    monkeypatch.setattr(appimg, "LOCAL_BIN", str(home / ".local/bin"))
    monkeypatch.setattr(appimg, "available_aur_helpers", lambda: [])
    tool = {"key": "obah", "start_cmd": "obah", "install_methods": ["cargo"], "crate": "obah"}
    assert not appimg.installed_locally(tool)
    b = home / ".config/yakuda-connect/tools/cargo/obah/bin"
    b.mkdir(parents=True)
    (b / "obah").write_text("x")
    (b / "obah").chmod(0o755)
    assert appimg.installed_locally(tool)
