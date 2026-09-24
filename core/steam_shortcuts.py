#!/usr/bin/env python3
"""
core/steam_shortcuts.py — Nicht-Steam-Spiele aus Steams shortcuts.vdf
====================================================================
Was man in Steam über „Ein Nicht-Steam-Spiel hinzufügen" einträgt (Heroic-,
Lutris- und GOG-Starter, eigene Builds, Emulatoren), steht NICHT in den
``appmanifest_*.acf`` der Bibliotheken, sondern pro Steam-Konto in::

    <Steam>/userdata/<Konto-ID>/config/shortcuts.vdf

Diese Datei ist — anders als config.vdf und localconfig.vdf — BINAER. Der
Textparser in games.py (``_vdf_find_block``) kann sie nicht lesen.

Warum sich der Aufwand lohnt
----------------------------
Ein Nicht-Steam-Spiel hat in Steam eine vollwertige AppID, und damit geht
fast alles, was der Games-Tab fuer Steam-Spiele kann:

  * Proton waehlen   → CompatToolMapping in config.vdf, Schluessel = AppID
  * Prefix-Backup    → steamapps/compatdata/<AppID>
  * Starten          → steam://rungameid/<Spiel-ID>
  * Cover            → userdata/<Konto>/config/grid/<AppID>p.png

Nur zwei Dinge sind anders, und genau die regelt dieses Modul:

  1. **Startparameter** stehen nicht in localconfig.vdf, sondern im Feld
     ``LaunchOptions`` des Eintrags in shortcuts.vdf.
  2. **Gestartet** wird nicht mit ``-applaunch <AppID>`` (das kennt nur
     echte Steam-Spiele), sondern ueber die 64-Bit-Spiel-ID
     ``(AppID << 32) | 0x02000000``.

Die AppID
---------
Steam speichert sie als vorzeichenbehaftete 32-Bit-Zahl; CompatToolMapping,
compatdata und grid benutzen dieselben Bits VORZEICHENLOS. Nicht-Steam-IDs
haben immer das oberste Bit gesetzt (>= 2^31). Echte Steam-AppIDs liegen weit
darunter — daran unterscheidet ``is_shortcut_id`` die beiden, ohne dass die
App eine zweite ID-Art einfuehren muss. Gemerkte Proton-Auswahl,
Startschalter, „entfernt"-Liste: alles funktioniert unveraendert.

Sehr alte Eintraege haben kein ``appid``-Feld. Steam berechnet sie dann aus
CRC32 ueber Programmpfad + Name, mit gesetztem obersten Bit — das tut
``_legacy_appid`` ebenso.

Schreiben
---------
Beim Zurueckschreiben bleibt jedes Byte, das wir nicht aendern, exakt
erhalten (Test: lesen → schreiben ergibt dieselbe Datei). Unbekannte
Feldtypen fuehren zum Abbruch statt zu einer halb verstandenen Datei.
Vorher wird eine Sicherung ``shortcuts.vdf.bak.<Zeit>`` angelegt, geschrieben
wird atomar ueber eine Nebendatei.

Laeuft Steam, haelt es die Eintraege im Speicher und schreibt die Datei beim
naechsten Bearbeiten eines Nicht-Steam-Spiels selbst neu — eine Aenderung von
aussen kann dann verloren gehen. Der Games-Tab weist darauf hin.
"""
import datetime
import os
import re
import shutil
import struct
import zlib

import vr_environment as venv
from logging_setup import get_logger

log = get_logger("steam_shortcuts")

# Feldtypen des Binaerformats
T_MAP = 0x00
T_STRING = 0x01
T_INT32 = 0x02
T_FLOAT = 0x03
T_POINTER = 0x04
T_WSTRING = 0x05
T_COLOR = 0x06
T_UINT64 = 0x07
T_END = 0x08
T_INT64 = 0x0A

_FIXED = {T_INT32: "<i", T_FLOAT: "<f", T_POINTER: "<i", T_COLOR: "<i",
          T_UINT64: "<Q", T_INT64: "<q"}

SHORTCUT_BIT = 0x80000000
_GAMEID_FLAG = 0x02000000


class VdfError(ValueError):
    """Datei ist kein (verstandenes) Binaer-VDF."""


# --------------------------------------------------------------------------- #
#  Binaer-VDF: lesen und verlustfrei schreiben
# --------------------------------------------------------------------------- #
def _read_cstr(data, pos):
    end = data.find(b"\x00", pos)
    if end < 0:
        raise VdfError("Zeichenkette ohne Ende")
    # surrogateescape: auch kaputtes UTF-8 kommt beim Schreiben byte-genau
    # wieder heraus.
    return data[pos:end].decode("utf-8", "surrogateescape"), end + 1


def _parse_map(data, pos):
    """Liest Eintraege bis T_END. Rueckgabe: ([(typ, key, wert)], neue_pos)."""
    items = []
    while True:
        if pos >= len(data):
            raise VdfError("Datei endet mitten in einem Block")
        typ = data[pos]
        pos += 1
        if typ == T_END:
            return items, pos
        key, pos = _read_cstr(data, pos)
        if typ == T_MAP:
            value, pos = _parse_map(data, pos)
        elif typ == T_STRING:
            value, pos = _read_cstr(data, pos)
        elif typ in _FIXED:
            fmt = _FIXED[typ]
            size = struct.calcsize(fmt)
            if pos + size > len(data):
                raise VdfError("Zahl abgeschnitten")
            value = struct.unpack_from(fmt, data, pos)[0]
            pos += size
        else:
            raise VdfError(f"Unbekannter Feldtyp 0x{typ:02x}")
        items.append((typ, key, value))


def _parse_file(data):
    """Bytes → (Eintraege, Rest). Der Rest wird beim Schreiben wieder angehaengt."""
    items, pos = _parse_map(data, 0)
    trailer = data[pos:]
    # Manche Werkzeuge haengen ein weiteres T_END an. Alles andere waere
    # unverstanden — dann lieber gar nicht anfassen.
    if trailer not in (b"", b"\x08"):
        raise VdfError("Unerwartete Daten am Dateiende")
    return items, trailer


def parse(data):
    """Bytes → Liste von (typ, key, wert). Wirft VdfError."""
    return _parse_file(data)[0]


def _dump_map(items, out):
    for typ, key, value in items:
        out.append(bytes([typ]))
        out.append(key.encode("utf-8", "surrogateescape") + b"\x00")
        if typ == T_MAP:
            _dump_map(value, out)
        elif typ == T_STRING:
            out.append(value.encode("utf-8", "surrogateescape") + b"\x00")
        else:
            out.append(struct.pack(_FIXED[typ], value))
    out.append(bytes([T_END]))


def dump(items, trailer=b""):
    """Gegenstueck zu parse: dump(parse(x)) == x (bis auf ``trailer``)."""
    out = []
    _dump_map(items, out)
    out.append(trailer)
    return b"".join(out)


def _field(entry, name):
    """Wert eines Feldes, Gross-/Kleinschreibung egal (Steam ist uneinheitlich)."""
    low = name.lower()
    for _typ, key, value in entry:
        if key.lower() == low:
            return value
    return None


# --------------------------------------------------------------------------- #
#  IDs
# --------------------------------------------------------------------------- #
def is_shortcut_id(appid):
    """True fuer die AppID eines Nicht-Steam-Spiels (oberstes Bit gesetzt)."""
    text = str(appid or "")
    if not text.isdigit():
        return False
    value = int(text)
    return SHORTCUT_BIT <= value <= 0xFFFFFFFF


def game_id(appid):
    """64-Bit-Spiel-ID fuer steam://rungameid/ — nur so startet Steam Shortcuts."""
    return (int(appid) << 32) | _GAMEID_FLAG


def _legacy_appid(exe, name):
    crc = zlib.crc32((exe + name).encode("utf-8", "surrogateescape")) & 0xFFFFFFFF
    return crc | SHORTCUT_BIT


def _entry_appid(entry):
    raw = _field(entry, "appid")
    if isinstance(raw, int):
        return raw & 0xFFFFFFFF
    return _legacy_appid(_field(entry, "Exe") or "", _field(entry, "AppName") or "")


# --------------------------------------------------------------------------- #
#  Dateien finden und lesen
# --------------------------------------------------------------------------- #
def shortcuts_files(roots=None):
    """Alle shortcuts.vdf aller Steam-Konten (nativ + Flatpak), ohne Doppelte."""
    found, seen = [], set()
    for root in roots if roots is not None else venv.steam_data_roots():
        userdata = os.path.join(root, "userdata")
        try:
            uids = sorted(os.listdir(userdata))
        except OSError:
            continue
        for uid in uids:
            path = os.path.join(userdata, uid, "config", "shortcuts.vdf")
            if not os.path.isfile(path):
                continue
            # ~/.steam/steam ist meist ein Link auf ~/.local/share/Steam —
            # sonst stuende jeder Eintrag doppelt in der Liste.
            real = os.path.realpath(path)
            if real in seen:
                continue
            seen.add(real)
            found.append(path)
    return found


def _load_file(path):
    with open(path, "rb") as fh:
        data = fh.read()
    items, trailer = _parse_file(data)
    block = _field(items, "shortcuts")
    if not isinstance(block, list):
        raise VdfError("Kein 'shortcuts'-Block")
    return trailer, items, block


def list_shortcuts(roots=None):
    """
    Alle Nicht-Steam-Spiele.

    Rueckgabe: [{"appid", "name", "exe", "start_dir", "launch_options",
    "path"}] — appid als Text (vorzeichenlos). Dieselbe AppID in zwei
    Konten erscheint einmal (die erste gewinnt).
    """
    out, seen = [], set()
    for path in shortcuts_files(roots):
        try:
            _trailer, _items, block = _load_file(path)
        except (OSError, VdfError) as exc:
            log.warning("shortcuts.vdf nicht lesbar (%s): %s", path, exc)
            continue
        for typ, _key, entry in block:
            if typ != T_MAP:
                continue
            appid = str(_entry_appid(entry))
            if appid in seen:
                continue
            seen.add(appid)
            name = (_field(entry, "AppName") or "").strip()
            out.append({
                "appid": appid,
                "name": name or f"App {appid}",
                "exe": _field(entry, "Exe") or "",
                "start_dir": _field(entry, "StartDir") or "",
                "launch_options": _field(entry, "LaunchOptions") or "",
                "path": path,
            })
    return out


def get(appid, roots=None):
    appid = str(appid)
    return next((s for s in list_shortcuts(roots) if s["appid"] == appid), None)


# --------------------------------------------------------------------------- #
#  Startparameter schreiben
# --------------------------------------------------------------------------- #
def _backup(path):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        shutil.copy2(path, f"{path}.bak.{stamp}")
    except OSError as exc:
        log.debug("Sicherung von %s fehlgeschlagen: %s", path, exc)


def _set_string(entry, name, value):
    low = name.lower()
    for i, (typ, key, _old) in enumerate(entry):
        if key.lower() == low:
            if typ != T_STRING:
                raise VdfError(f"Feld {key} ist kein Text")
            entry[i] = (T_STRING, key, value)
            return
    entry.append((T_STRING, name, value))


def set_launch_options(appid, options, roots=None):
    """
    Schreibt ``LaunchOptions`` des Nicht-Steam-Spiels in jede shortcuts.vdf,
    die es enthaelt. Rueckgabe: (ok, fehlertext).
    """
    appid = str(appid)
    wrote, last_err = False, "Nicht-Steam-Spiel nicht gefunden"
    for path in shortcuts_files(roots):
        try:
            trailer, items, block = _load_file(path)
        except (OSError, VdfError) as exc:
            last_err = str(exc)
            continue
        hit = False
        for typ, _key, entry in block:
            if typ == T_MAP and str(_entry_appid(entry)) == appid:
                if (_field(entry, "LaunchOptions") or "") == options:
                    hit = None             # schon so — nichts schreiben
                    break
                _set_string(entry, "LaunchOptions", options)
                hit = True
                break
        if hit is None:
            wrote = True
            continue
        if not hit:
            continue
        new = dump(items, trailer)
        tmp = path + ".part"
        try:
            _backup(path)
            with open(tmp, "wb") as fh:
                fh.write(new)
            os.replace(tmp, path)
            wrote = True
        except OSError as exc:
            last_err = str(exc)
            try:
                os.remove(tmp)
            except OSError:
                pass
    return (True, "") if wrote else (False, last_err)


# --------------------------------------------------------------------------- #
#  Neues Nicht-Steam-Spiel anlegen („In Steam eintragen")
# --------------------------------------------------------------------------- #
# SteamID64 = Konto-ID + dieser Wert. userdata/ ist nach der Konto-ID benannt,
# loginusers.vdf fuehrt die SteamID64.
_STEAMID64_BASE = 76561197960265728


def _most_recent_account(root):
    """Konto-ID des zuletzt angemeldeten Nutzers laut config/loginusers.vdf."""
    path = os.path.join(root, "config", "loginusers.vdf")
    try:
        with open(path, errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return None
    for m in re.finditer(r'"(\d{17})"\s*\{([^{}]*)\}', text):
        if re.search(r'"MostRecent"\s+"1"', m.group(2), re.IGNORECASE):
            return str(int(m.group(1)) - _STEAMID64_BASE)
    return None


def target_shortcuts_file(roots=None):
    """
    In welche shortcuts.vdf ein NEUES Spiel gehoert.

    Mehrere Steam-Konten auf einem Rechner sind nicht selten (Familie,
    Zweitkonto). Ein Eintrag im falschen Konto waere fuer den Nutzer
    unsichtbar. Reihenfolge:
      1. das zuletzt angemeldete Konto (loginusers.vdf, "MostRecent")
      2. das einzige Konto
      3. das Konto mit der zuletzt geaenderten localconfig.vdf
    Die Datei muss noch nicht existieren — ``add_shortcut`` legt sie an.
    """
    candidates = []
    for root in roots if roots is not None else venv.steam_data_roots():
        userdata = os.path.join(root, "userdata")
        try:
            uids = [u for u in os.listdir(userdata)
                    if u.isdigit() and u != "0"
                    and os.path.isdir(os.path.join(userdata, u, "config"))]
        except OSError:
            continue
        recent = _most_recent_account(root)
        if recent in uids:
            return os.path.join(userdata, recent, "config", "shortcuts.vdf")
        for uid in uids:
            local = os.path.join(userdata, uid, "config", "localconfig.vdf")
            try:
                mtime = os.path.getmtime(local)
            except OSError:
                mtime = 0
            candidates.append((mtime, os.path.join(userdata, uid, "config", "shortcuts.vdf")))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def _unquote(text):
    text = (text or "").strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1]
    return text


def _new_entry(index, appid, name, exe, start_dir, launch_options):
    """Ein Eintrag mit genau den Feldern, die Steam selbst anlegt."""
    signed = appid - 0x100000000 if appid >= SHORTCUT_BIT else appid
    return (T_MAP, str(index), [
        (T_INT32, "appid", signed),
        (T_STRING, "AppName", name),
        # Steam setzt Pfade in Anfuehrungszeichen — sonst scheitern Pfade
        # mit Leerzeichen ("/home/x/Meine Spiele/spiel.exe").
        (T_STRING, "Exe", f'"{exe}"'),
        (T_STRING, "StartDir", f'"{start_dir}"'),
        (T_STRING, "icon", ""),
        (T_STRING, "ShortcutPath", ""),
        (T_STRING, "LaunchOptions", launch_options),
        (T_INT32, "IsHidden", 0),
        (T_INT32, "AllowDesktopConfig", 1),
        (T_INT32, "AllowOverlay", 1),
        (T_INT32, "OpenVR", 0),
        (T_INT32, "Devkit", 0),
        (T_STRING, "DevkitGameID", ""),
        (T_INT32, "DevkitOverrideAppID", 0),
        (T_INT32, "LastPlayTime", 0),
        (T_STRING, "FlatpakAppID", ""),
        (T_MAP, "tags", []),
    ])


def add_shortcut(name, exe, launch_options="", roots=None):
    """
    Traegt ein Programm als Nicht-Steam-Spiel in Steam ein.

    Rueckgabe: (appid, fehler)
      appid  : vorzeichenlos als Text (auch bei "exists": die vorhandene)
      fehler : "" | "exists" | "no_account" | "unreadable" | "write_failed"

    STEAM DARF DABEI NICHT LAUFEN — es wuerde die Datei beim Beenden mit
    seinem alten Stand ueberschreiben. Das prueft die Oberflaeche vorher
    (steam_close.py); hier wird nur geschrieben.

    Die AppID wird wie bei Steam ROM Manager aus CRC32(Exe + Name) mit
    gesetztem obersten Bit gebildet. Damit bekommt dasselbe Programm unter
    demselben Namen immer dieselbe ID — ein zweiter Klick legt keinen
    doppelten Eintrag an.
    """
    name = (name or "").strip()
    exe = os.path.abspath(os.path.expanduser((exe or "").strip()))
    path = target_shortcuts_file(roots)
    if not path:
        return None, "no_account"

    if os.path.isfile(path):
        try:
            trailer, items, block = _load_file(path)
        except (OSError, VdfError) as exc:
            log.warning("shortcuts.vdf nicht lesbar, nichts eingetragen (%s): %s", path, exc)
            return None, "unreadable"
    else:
        block = []
        items = [(T_MAP, "shortcuts", block)]
        trailer = b"\x08"

    used, indices = set(), []
    for typ, key, entry in block:
        if typ != T_MAP:
            continue
        if key.isdigit():
            indices.append(int(key))
        existing = _entry_appid(entry)
        used.add(existing)
        if (_unquote(_field(entry, "Exe")) == exe
                and (_field(entry, "AppName") or "").strip() == name):
            return str(existing), "exists"

    appid = _legacy_appid(f'"{exe}"', name)
    while appid in used:              # sehr unwahrscheinlich, aber moeglich
        appid = ((appid + 1) & 0x7FFFFFFF) | SHORTCUT_BIT
    index = max(indices) + 1 if indices else 0
    start_dir = os.path.dirname(exe).rstrip("/") + "/"
    block.append(_new_entry(index, appid, name, exe, start_dir, launch_options or ""))

    tmp = path + ".part"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.isfile(path):
            _backup(path)
        with open(tmp, "wb") as fh:
            fh.write(dump(items, trailer))
        os.replace(tmp, path)
    except OSError as exc:
        log.warning("Nicht-Steam-Spiel konnte nicht eingetragen werden: %s", exc)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None, "write_failed"
    log.info("Nicht-Steam-Spiel eingetragen: %s (AppID %s) in %s", name, appid, path)
    return str(appid), ""


# --------------------------------------------------------------------------- #
#  Bild (Steams Grid-Ordner)
# --------------------------------------------------------------------------- #
IMAGE_EXTS = (".png", ".jpg", ".jpeg")


def _grid_dirs(appid, roots=None):
    """grid-Ordner aller Konten, deren shortcuts.vdf dieses Spiel enthaelt."""
    appid = str(appid)
    dirs = []
    for sc in list_shortcuts_all(roots):
        if sc["appid"] == appid:
            d = os.path.join(os.path.dirname(sc["path"]), "grid")
            if d not in dirs:
                dirs.append(d)
    return dirs


def list_shortcuts_all(roots=None):
    """Wie list_shortcuts, aber OHNE Zusammenfassen gleicher AppIDs ueber
    Konten — fuer Bilder, die in jedem betroffenen Konto landen sollen."""
    out = []
    for path in shortcuts_files(roots):
        try:
            _trailer, _items, block = _load_file(path)
        except (OSError, VdfError):
            continue
        for typ, _key, entry in block:
            if typ == T_MAP:
                out.append({"appid": str(_entry_appid(entry)), "path": path})
    return out


def _remove_grid_portraits(grid, appid):
    for ext in IMAGE_EXTS:
        try:
            os.remove(os.path.join(grid, f"{appid}p{ext}"))
        except OSError:
            pass


def set_grid_image(appid, source, roots=None):
    """
    Legt ``source`` als Hochkant-Bild (``<appid>p.png``) in Steams grid-Ordner.

    Dasselbe Bild zeigt dann auch Steam selbst in der Bibliothek an. Andere
    Bildarten (Querformat, Hero, Logo) bleiben unberuehrt — die hat der
    Nutzer vielleicht bewusst ueber SteamGridDB gesetzt.

    Rueckgabe: (ok, fehler) — fehler "" | "bad_type" | "not_found" |
    "no_account" | "write_failed"
    """
    ext = os.path.splitext(source or "")[1].lower()
    if ext not in IMAGE_EXTS:
        return False, "bad_type"
    if not os.path.isfile(source or ""):
        return False, "not_found"
    grids = _grid_dirs(appid, roots)
    if not grids:
        return False, "no_account"
    for grid in grids:
        try:
            os.makedirs(grid, exist_ok=True)
            _remove_grid_portraits(grid, appid)
            shutil.copyfile(source, os.path.join(grid, f"{appid}p{'.jpg' if ext == '.jpeg' else ext}"))
        except OSError as exc:
            log.warning("Bild fuer %s nicht gesetzt: %s", appid, exc)
            return False, "write_failed"
    return True, ""


def clear_grid_image(appid, roots=None):
    for grid in _grid_dirs(appid, roots):
        _remove_grid_portraits(grid, appid)
    return True
