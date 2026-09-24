#!/usr/bin/env python3
"""
core/paths.py — Zentrale Pfade (XDG-konform)
============================================
Alle Einstellungen von OpenXR-VR-Control liegen getrennt von Yakuda Connect:

    ~/.config/openxr-vr-control/          Einstellungen (config/*.json, tools/)
    ~/.cache/openxr-vr-control/app.log    Log

Dieses Modul hat bewusst KEINE Importe aus dem Projekt — es muss von jedem
anderen Modul importierbar sein, ohne Ringimporte zu erzeugen.
"""
import os

APP_NAME = "openxr-vr-control"

_HOME = os.path.expanduser("~")


def _xdg(env_var: str, default_rel: str) -> str:
    """Basisordner laut XDG-Spezifikation, mit Rueckfall auf den Standard."""
    base = os.environ.get(env_var, "").strip()
    if not base or not os.path.isabs(base):
        base = os.path.join(_HOME, default_rel)
    return base


def config_root() -> str:
    """Wurzelordner fuer Einstellungen (~/.config/openxr-vr-control)."""
    return os.path.join(_xdg("XDG_CONFIG_HOME", ".config"), APP_NAME)


def cache_root() -> str:
    """Wurzelordner fuer Zwischenspeicher (~/.cache/openxr-vr-control)."""
    return os.path.join(_xdg("XDG_CACHE_HOME", ".cache"), APP_NAME)


def config_dir() -> str:
    """Unterordner 'config', in dem die JSON-Dateien liegen."""
    return os.path.join(config_root(), "config")


def config_file(name: str) -> str:
    """Vollstaendiger Pfad einer Konfigurationsdatei im config-Unterordner."""
    return os.path.join(config_dir(), name)


def cache_file(name: str) -> str:
    """Vollstaendiger Pfad einer Datei im Zwischenspeicher."""
    return os.path.join(cache_root(), name)


def tools_dir() -> str:
    """Hier baut die App obah und xrBinder hin."""
    return os.path.join(config_root(), "tools")


def log_file() -> str:
    """Pfad der Programm-Logdatei (wird vom Logging-Setup benutzt)."""
    return os.path.join(cache_root(), "app.log")


def ensure_dirs() -> None:
    """Legt Konfig- und Cache-Ordner an."""
    os.makedirs(config_dir(), exist_ok=True)
    os.makedirs(cache_root(), exist_ok=True)
