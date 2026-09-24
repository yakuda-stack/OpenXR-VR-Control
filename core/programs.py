#!/usr/bin/env python3
"""
core/programs.py — Werkzeugliste (obah)
=================================================
Die Eintraege stehen in ``config/tools.json`` (gleiches Format wie bei
Yakuda Connect). Eine Nutzerkopie unter
``~/.config/openxr-vr-control/config/tools.json`` darf einzelne Eintraege
ueberschreiben (gleicher ``key``) oder neue anhaengen.
"""
import json
import os

import paths
from logging_setup import get_logger

log = get_logger("programs")

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON_BUNDLED = os.path.join(APP_DIR, "config", "tools.json")
TOOLS_JSON_USER = paths.config_file("tools.json")


def _read_tools_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001 — kaputte Nutzerdatei darf nichts sprengen
        log.warning("tools.json nicht lesbar (%s) — %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _merge_tools(base, extra):
    """Haengt extra an base an; gleicher 'key' ersetzt den bestehenden Eintrag."""
    out = list(base)
    index = {t.get("key"): i for i, t in enumerate(out) if isinstance(t, dict)}
    for entry in extra:
        if not isinstance(entry, dict) or not entry.get("key"):
            continue
        pos = index.get(entry["key"])
        if pos is None:
            index[entry["key"]] = len(out)
            out.append(entry)
        else:
            out[pos] = entry
    return out


def load_tools_config():
    bundled = _read_tools_json(TOOLS_JSON_BUNDLED)
    user = _read_tools_json(TOOLS_JSON_USER)
    return _merge_tools(bundled.get("apps", []) or [], user.get("apps", []) or [])


TOOLS_APPS = load_tools_config()


def all_tools():
    return list(TOOLS_APPS)


def tool(key):
    """Eintrag zu einem Schluessel, {} wenn es ihn nicht gibt."""
    return next((t for t in TOOLS_APPS if t.get("key") == key), {})
