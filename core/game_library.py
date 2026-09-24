#!/usr/bin/env python3
"""
core/game_library.py — Spieleliste fuer die Controls-Ansicht
============================================================
Yakuda Connect holt die Spiele aus seinem Games-Tab. OpenXR-VR-Control hat
keinen Games-Tab — dieses Modul liefert dieselbe Liste
(``games_tab_entries()``, gleiches Format), aber schlank:

  * **Automatisch**: installierte Steam-Spiele, die Steam selbst als VR
    fuehrt (appinfo.vdf, siehe steam_appinfo.py). Sagt Steam nichts, wird
    im Spielordner nach OpenVR-/OpenXR-Loadern gesucht (Ergebnis gecacht).
  * **Steam-Spiel hinzufuegen**: ein installiertes Steam-Spiel oder ein
    Nicht-Steam-Spiel aus Steam, das nicht als VR erkannt wurde.
  * **Lokales Spiel hinzufuegen**: ein Spiel ganz ohne Steam (Name +
    Programmdatei). Die Action-Datei wird im Ordner der Programmdatei gesucht.
  * **Entfernen**: Handeintraege loeschen bzw. erkannte Spiele ausblenden.

Gespeichert wird in ~/.config/openxr-vr-control/config/config.json.
Die Such- und Erkennungslogik ist aus Yakuda Connect (core/games.py)
uebernommen, damit beide Programme dieselben Spiele finden.
"""
import glob
import os
import re

import paths
import steam_appinfo
import steam_shortcuts
import vr_environment as venv
from jsonio import read_json, update_json
from logging_setup import get_logger

log = get_logger("game_library")

APP_CONFIG = paths.config_file("config.json")

KIND_STEAM = "steam"
KIND_SHORTCUT = "shortcut"
KIND_LOCAL = "local"
LOCAL_PREFIX = "local:"


def _load_app_config():
    data = read_json(APP_CONFIG, default={})
    return data if isinstance(data, dict) else {}


# --------------------------------------------------------------------------- #
#  Steam-Bibliotheken (aus Yakuda Connect core/games.py)
# --------------------------------------------------------------------------- #
def _steamapps_dirs():
    """
    Alle steamapps-Ordner: Standard-Bibliotheken (nativ + Flatpak) und
    zusätzliche Bibliotheken aus libraryfolders.vdf (z. B. zweite Platte).
    """
    dirs = []
    for root in venv.steam_data_roots():
        sa = os.path.join(root, "steamapps")
        if os.path.isdir(sa):
            dirs.append(sa)
        # Zusätzliche Bibliotheken aus libraryfolders.vdf
        vdf = os.path.join(sa, "libraryfolders.vdf")
        if os.path.isfile(vdf):
            try:
                with open(vdf, errors="ignore") as f:
                    content = f.read()
                # "path"  "/mnt/spiele/SteamLibrary"
                for m in re.finditer(r'"path"\s+"([^"]+)"', content):
                    extra = os.path.join(m.group(1), "steamapps")
                    if os.path.isdir(extra):
                        dirs.append(extra)
            except Exception as exc:
                log.debug("_steamapps_dirs: ignoriert — %s", exc)
    # Duplikate entfernen, Reihenfolge erhalten
    seen, unique = set(), []
    for d in dirs:
        real = os.path.realpath(d)
        if real not in seen:
            seen.add(real)
            unique.append(d)
    return unique


# Steam-eigene Tools, die zwar VR-Bibliotheken enthalten, aber keine Spiele
# sind (würden die Heuristik sonst täuschen).
_APPID_BLACKLIST = {
    "250820",    # SteamVR
    "228980",    # Steamworks Common Redistributables
    "1493710",   # Proton Experimental
    "1070560",   # Steam Linux Runtime
    "1391110",   # Steam Linux Runtime - Soldier
    "1628350",   # Steam Linux Runtime - Sniper
}

# Zusätzlicher Filter über den NAMEN — fängt alle Proton-Versionen (auch neue
# wie "Proton 10.0", "Proton 9.0 (Beta)") und Steam-Runtimes ab, ohne dass man
# jede appid einzeln pflegen muss. Proton-Installationen enthalten OpenVR-
# Dateien und würden sonst als VR-"Spiel" im Games-Tab auftauchen.
_TOOL_NAME_RE = re.compile(
    r"^\s*("
    r"proton\s+(experimental|hotfix|next|\d|easyanticheat|battleye)"
    r"|steam\s+linux\s+runtime"
    r"|steamworks\s+common"
    r"|steamvr"
    r")",
    re.IGNORECASE,
)


def _is_steam_tool(name):
    """True für Proton-Versionen/Steam-Runtimes (keine echten Spiele)."""
    return bool(name and _TOOL_NAME_RE.match(name))

# Dateien, an denen wir ein VR-Spiel erkennen (OpenVR-/OpenXR-Loader im
# Installationsordner). Funktioniert komplett offline.
_VR_MARKER_FILES = {
    # OpenVR / SteamVR
    "openvr_api.dll", "libopenvr_api.so", "openvr_api64.dll",
    # OpenXR
    "openxr_loader.dll", "libopenxr_loader.so",
    # Unity XR-Plugins (manche Spiele liefern nur diese aus)
    "unityopenxr.dll", "libunityopenxr.so",
    "openvr_api.dll.meta", "unityopenvr.dll",
    # Oculus/Meta-Plugins (native Oculus-Spiele ohne OpenXR-Loader)
    "libovrplatform.so", "ovrplugin.dll", "libovrplugin.so",
}

# Bekannte Ablageorte des Loaders — werden ZUERST direkt geprüft (ohne Walk).
# Wichtig für Unreal Engine: dort liegt der Loader tief in Engine/Binaries/...,
# was ein flacher Walk niemals findet.
_VR_MARKER_GLOBS = [
    # Unreal Engine 4/5
    "Engine/Binaries/ThirdParty/OpenXR/*/openxr_loader.dll",
    "Engine/Binaries/ThirdParty/OpenXR/*/*/openxr_loader.dll",
    "Engine/Binaries/ThirdParty/OpenVR/*/*/openvr_api.dll",
    "Engine/Plugins/Runtime/OpenXR/*",
    "Engine/Plugins/Runtime/Oculus/*",
    "*/Binaries/Win64/openxr_loader.dll",
    "*/Plugins/*/Binaries/ThirdParty/OpenXR/*/openxr_loader.dll",
    # Unity
    "*_Data/Plugins/x86_64/openvr_api.dll",
    "*_Data/Plugins/x86_64/UnityOpenXR.dll",
    "*_Data/Plugins/x86_64/openxr_loader.dll",
    "*_Data/Plugins/openvr_api.dll",
    "*_Data/Plugins/x86_64/OVRPlugin.dll",
    # Godot / sonstige, die den Loader neben die Binary legen
    "openxr_loader.dll",
    "openvr_api.dll",
]

# Ordner, die beim Walk übersprungen werden: dort liegen nie Loader-Dateien,
# sie fressen aber das Scan-Budget auf (UE-'Content' hat gern 10.000+ Ordner).
_VR_SCAN_SKIP_DIRS = {
    "content", "contents", "saved", "intermediate", "derivedatacache",
    "streamingassets", "movies", "videos", "audio", "sounds", "music",
    "textures", "localization", "paks", "cache", "logs", "screenshots",
}

_VR_SCAN_MAX_DIRS = 6000   # großzügig: UE-Spiele haben sehr viele Ordner
_VR_SCAN_MAX_DEPTH = 7     # UE: Engine/Binaries/ThirdParty/OpenXR/win64/... = 5+


def _parse_acf(path):
    """Liest appid, name und installdir aus einer appmanifest_<id>.acf."""
    try:
        with open(path, errors="ignore") as f:
            content = f.read()
    except Exception:
        return None
    def field(key):
        m = re.search(r'"%s"\s+"([^"]*)"' % key, content)
        return m.group(1) if m else ""
    appid = field("appid")
    if not appid:
        m = re.match(r"appmanifest_(\d+)\.acf$", os.path.basename(path))
        appid = m.group(1) if m else ""
    return {"appid": appid, "name": field("name"),
            "installdir": field("installdir")}


def _looks_like_vr_game(steamapps_dir, installdir, quick=False):
    """
    True, wenn der Installationsordner OpenVR-/OpenXR-Loader enthält.

    Zwei Stufen:
      1. Gezielte Prüfung bekannter Engine-Pfade (_VR_MARKER_GLOBS) — schnell
         und findet vor allem Unreal-Engine-Spiele, bei denen der Loader tief
         unter Engine/Binaries/ThirdParty/OpenXR/<platform>/ liegt.
      2. Fallback: begrenzter Walk. Uninteressante Riesenordner (Content, Saved,
         ...) werden übersprungen, damit das Budget für die Binaries reicht.

    ``quick=True`` laesst Stufe 2 aus — fuer Faelle, in denen die Dauer
    wichtiger ist als die Vollstaendigkeit. Im Scan selbst wird das nicht
    mehr gebraucht (dort faengt der Ergebnis-Cache die Dauer ab), der
    Schalter bleibt aber fuer Aufrufer, die schnell eine grobe Antwort
    wollen.
    """
    if not installdir:
        return False
    root = os.path.join(steamapps_dir, "common", installdir)
    if not os.path.isdir(root):
        return False

    # --- Stufe 1: bekannte Engine-Pfade direkt abklopfen ------------------- #
    for pattern in _VR_MARKER_GLOBS:
        try:
            if glob.glob(os.path.join(root, pattern)):
                return True
        except Exception as exc:
            log.debug("_looks_like_vr_game: ignoriert — %s", exc)

    if quick:
        return False

    # --- Stufe 2: begrenzter Walk als Fallback ---------------------------- #
    root_depth = root.rstrip(os.sep).count(os.sep)
    visited = 0
    try:
        for cur, dirs, files in os.walk(root):
            visited += 1
            if visited > _VR_SCAN_MAX_DIRS:
                break          # Budget alle -> abbrechen, aber NICHT als "kein VR"
                               # werten; Stufe 1 hat die üblichen Pfade schon geprüft.
            if cur.count(os.sep) - root_depth >= _VR_SCAN_MAX_DEPTH:
                dirs[:] = []   # nicht tiefer absteigen
            else:
                # Content-/Asset-Ordner überspringen: dort liegen nie Loader.
                dirs[:] = [d for d in dirs if d.lower() not in _VR_SCAN_SKIP_DIRS]
            for f in files:
                if f.lower() in _VR_MARKER_FILES:
                    return True
    except Exception as exc:
        log.debug("_looks_like_vr_game: ignoriert — %s", exc)
    return False


def installed_steam_apps():
    """
    Alle installierten Steam-Apps aus den appmanifest_<id>.acf.

    Rückgabe: Liste von {"appid", "name", "installdir", "steamapps"} —
    ohne Proton-Versionen und Steam-Runtimes, aber sonst ungefiltert.
    Doppelte AppIDs (dieselbe App in zwei Bibliotheken) erscheinen einmal.
    """
    apps = {}
    for sa in _steamapps_dirs():
        try:
            fnames = os.listdir(sa)
        except Exception:
            continue
        for fname in fnames:
            if not re.match(r"appmanifest_\d+\.acf$", fname):
                continue
            info = _parse_acf(os.path.join(sa, fname))
            if not info or not info["appid"]:
                continue
            appid = info["appid"]
            if appid in apps:
                continue
            if appid in _APPID_BLACKLIST or _is_steam_tool(info["name"]):
                continue
            apps[appid] = {
                "appid": appid,
                "name": info["name"] or f"App {appid}",
                "installdir": info["installdir"],
                "steamapps": sa,
            }
    return list(apps.values())



_VR_FILECHECK_VERSION = 2       # hochzaehlen, wenn sich die Erkennung aendert


def _install_stamp(steamapps_dir, installdir):
    """Kennung des Installationsordners — aendert sie sich, wird neu geprueft.

    Genommen wird die Aenderungszeit des Ordners selbst. Die springt, wenn
    Steam Dateien darin anlegt, loescht oder ersetzt, also bei jedem Update
    und jeder Neuinstallation. Ein Durchlauf durch den ganzen Baum waere
    genauer, koestete aber wieder genau das, was der Cache einsparen soll.
    """
    if not installdir:
        return None
    path = os.path.join(steamapps_dir, "common", installdir)
    try:
        st = os.stat(path)
    except OSError:
        return None
    return f"{st.st_mtime_ns}:{path}"


def load_vr_filecheck_cache():
    """Gemerkte Ergebnisse der Dateierkennung: {appid: {"stamp", "vr"}}."""
    data = _load_app_config().get("games_vr_filecheck", {})
    if not isinstance(data, dict):
        return {}
    # Aendert sich die Erkennung, ist jedes alte Ergebnis wertlos — dann
    # lieber einmal neu pruefen als dauerhaft eine veraltete Antwort geben.
    if data.get("version") != _VR_FILECHECK_VERSION:
        return {}
    apps = data.get("apps")
    return apps if isinstance(apps, dict) else {}


def save_vr_filecheck_cache(entries):
    if not update_json(APP_CONFIG, {"games_vr_filecheck": {
            "version": _VR_FILECHECK_VERSION, "apps": entries}}):
        log.warning("Cache der Dateierkennung konnte nicht gespeichert werden.")




# --------------------------------------------------------------------------- #
#  Handeintraege
# --------------------------------------------------------------------------- #
def _str_list(key):
    data = _load_app_config().get(key, [])
    return [str(a) for a in data if str(a)] if isinstance(data, list) else []


def load_manual_steam_appids():
    """Steam-Spiele und Nicht-Steam-Spiele (Shortcut-IDs), von Hand eingetragen."""
    return [a for a in _str_list("games_manual_steam") if a.isdigit()]


def load_hidden_games():
    """Kennungen, die der Nutzer aus der Liste entfernt hat."""
    return _str_list("games_hidden")


def _save(key, value):
    if not update_json(APP_CONFIG, {key: value}):
        log.warning("Spieleliste konnte nicht gespeichert werden (%s).", key)
        return False
    return True


def add_manual_steam_appid(appid):
    """Steam- oder Nicht-Steam-Spiel eintragen. True = war neu."""
    appid = str(appid)
    if not appid.isdigit():
        return False
    unhide_game(appid)
    current = load_manual_steam_appids()
    if appid in current:
        return False
    current.append(appid)
    return _save("games_manual_steam", current)


def unhide_game(gid):
    current = load_hidden_games()
    if str(gid) not in current:
        return False
    current.remove(str(gid))
    return _save("games_hidden", current)


def load_local_games():
    """[{"id", "name", "exe"}] — Spiele ganz ohne Steam, nach Name sortiert."""
    data = _load_app_config().get("games_local", [])
    out = []
    for e in data if isinstance(data, list) else []:
        if not isinstance(e, dict):
            continue
        gid = str(e.get("id", "") or "")
        name = str(e.get("name", "") or "").strip()
        exe = str(e.get("exe", "") or "").strip()
        if gid.startswith(LOCAL_PREFIX) and name and exe:
            out.append({"id": gid, "name": name, "exe": exe})
    out.sort(key=lambda g: g["name"].lower())
    return out


def _next_local_id(entries):
    used = set()
    for e in entries:
        m = re.match(re.escape(LOCAL_PREFIX) + r"(\d+)$", e.get("id", ""))
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return f"{LOCAL_PREFIX}{n}"


def add_local_game(name, exe):
    """
    Eigenes Spiel anlegen. Rueckgabe: (ok, kennung_oder_fehlerschluessel)
    Fehlerschluessel: "no_name" | "no_exe" | "not_found" | "save_failed"
    """
    name = (name or "").strip()
    exe = (exe or "").strip()
    if not name:
        return False, "no_name"
    if not exe:
        return False, "no_exe"
    exe = os.path.abspath(os.path.expanduser(exe))
    if not os.path.exists(exe):
        return False, "not_found"
    entries = load_local_games()
    gid = _next_local_id(entries)
    entries.append({"id": gid, "name": name, "exe": exe})
    if not _save("games_local", entries):
        return False, "save_failed"
    return True, gid


def remove_game(gid, kind):
    """
    Spiel aus der Liste nehmen.
      local    : Eintrag loeschen
      steam/shortcut : Handeintrag loeschen und ausblenden (sonst kaeme ein
                 erkanntes VR-Spiel beim naechsten Suchen zurueck)
    """
    gid = str(gid)
    if kind == KIND_LOCAL:
        entries = [e for e in load_local_games() if e["id"] != gid]
        return _save("games_local", entries)
    manual = load_manual_steam_appids()
    if gid in manual:
        manual.remove(gid)
        _save("games_manual_steam", manual)
    hidden = load_hidden_games()
    if gid not in hidden:
        hidden.append(gid)
        return _save("games_hidden", hidden)
    return True


def is_manual(gid, kind):
    """Steht das Spiel durch einen Handeintrag in der Liste?"""
    if kind == KIND_LOCAL:
        return True
    return str(gid) in load_manual_steam_appids()


# --------------------------------------------------------------------------- #
#  VR-Erkennung + Liste
# --------------------------------------------------------------------------- #
def _is_vr(app, common, cache, fresh):
    if common is not None and not steam_appinfo.is_playable_type(common):
        return False                      # Werkzeug/DLC/Soundtrack
    if common and steam_appinfo.common_says_vr(common):
        return True
    stamp = _install_stamp(app["steamapps"], app["installdir"])
    hit = cache.get(app["appid"])
    if stamp and isinstance(hit, dict) and hit.get("stamp") == stamp:
        return bool(hit.get("vr"))
    is_vr = _looks_like_vr_game(app["steamapps"], app["installdir"])
    if stamp:
        fresh[app["appid"]] = {"stamp": stamp, "vr": is_vr}
    return is_vr


def _shortcut_names():
    try:
        return {sc["appid"]: sc["name"] for sc in steam_shortcuts.list_shortcuts()}
    except Exception as exc:  # noqa: BLE001
        log.warning("Nicht-Steam-Spiele nicht lesbar: %s", exc)
        return {}


def games_tab_entries(apps=None):
    """
    Die Spiele fuer die Controls-Ansicht — gleiches Format wie in Yakuda
    Connect: [{"id", "name", "kind", "exe"}], kind = steam | shortcut | local.
    """
    apps = installed_steam_apps() if apps is None else apps
    manual = set(load_manual_steam_appids())
    hidden = set(load_hidden_games())
    tags, ok = steam_appinfo.commons([a["appid"] for a in apps])
    if not ok:
        log.info("Steams appinfo.vdf nicht verfuegbar — nur Dateierkennung.")
    cache = load_vr_filecheck_cache()
    fresh = {}
    out = []
    for app in apps:
        appid = app["appid"]
        if appid in hidden:
            continue
        if appid in manual or _is_vr(app, tags.get(appid), cache, fresh):
            out.append({"id": appid, "name": app["name"], "kind": KIND_STEAM, "exe": ""})
    if fresh:
        cache.update(fresh)
        save_vr_filecheck_cache(cache)

    manual_sc = [a for a in manual if steam_shortcuts.is_shortcut_id(a) and a not in hidden]
    if manual_sc:
        present = _shortcut_names()
        for appid in manual_sc:
            if appid in present:
                out.append({"id": appid, "name": present[appid], "kind": KIND_SHORTCUT,
                            "exe": ""})
    for e in load_local_games():
        out.append({"id": e["id"], "name": e["name"], "kind": KIND_LOCAL, "exe": e["exe"]})
    out.sort(key=lambda g: g["name"].lower())
    return out


def steam_candidates(exclude=()):
    """
    Auswahl fuer „Steam-Spiel hinzufuegen“: alle installierten Steam-Spiele
    und Nicht-Steam-Spiele aus Steam, die noch NICHT in der Liste stehen.
    exclude: weitere Kennungen "<kind>:<id>", die schon in der Liste stehen
             (z. B. Steam-Spiele, die obah ueber ihre Action-Datei fand).
    Rueckgabe: [{"id", "name", "kind"}] nach Name.
    """
    apps = installed_steam_apps()
    listed = {e["id"] for e in games_tab_entries(apps)}
    listed |= {x.split(":", 1)[1] for x in exclude if ":" in x}
    out = [{"id": a["appid"], "name": a["name"], "kind": KIND_STEAM}
           for a in apps if a["appid"] not in listed]
    for appid, name in _shortcut_names().items():
        if appid not in listed:
            out.append({"id": appid, "name": name, "kind": KIND_SHORTCUT})
    out.sort(key=lambda g: g["name"].lower())
    return out
