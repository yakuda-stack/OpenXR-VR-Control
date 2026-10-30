#!/usr/bin/env python3
"""
core/deadzone_pref.py — Haken „Ich nutze nicht xrizer – deadzone_pct verwenden“
==============================================================================
Gilt fuer alle OpenVR-Spiele (Binding-Dialog und Deadzone-Knopf).
Standard: AN. Gespeichert in ~/.config/openxr-vr-control/config/config.json.
"""
import paths
from jsonio import read_json, update_json

KEY = "deadzone_use_pct"


def _file():
    return paths.config_file("config.json")


def use_pct():
    data = read_json(_file(), default={})
    if not isinstance(data, dict):
        return True
    return bool(data.get(KEY, True))


def set_use_pct(on):
    update_json(_file(), {KEY: bool(on)})
