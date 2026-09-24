#!/usr/bin/env python3
"""
steam_appinfo.py — Steams eigene App-Daten lesen (appcache/appinfo.vdf)
======================================================================
Warum es diese Datei gibt
-------------------------
Bis v1.2.8 hat der Games-Tab VR-Spiele daran erkannt, dass im
Installationsordner irgendwo eine ``openvr_api.dll`` oder ein
``openxr_loader`` herumliegt. Das hat zwei Nachteile, die beide direkt beim
Nutzer ankommen:

  * **Es ist langsam.** Fuer jedes Spiel laeuft ein Verzeichnis-Durchlauf
    ueber tausende Ordner. Bei einer grossen Bibliothek dauert ein Scan
    zweistellige Sekunden — viel zu lang, um ihn beim Oeffnen des Tabs
    automatisch anzustossen.
  * **Es raet.** Ein Flachbildschirm-Spiel mit optionalem VR-Modus liefert
    dieselben Dateien aus wie ein reines VR-Spiel, und manche VR-Spiele
    verstecken den Loader so tief, dass der Durchlauf ihn nie findet.

Steam selbst weiss es dagegen genau: In der Bibliothek gibt es einen
VR-Filter. Dessen Datenquelle liegt lokal auf der Platte, in

    <Steam>/appcache/appinfo.vdf

Das ist Steams Zwischenspeicher der sogenannten PICS-Daten. Pro App steht
dort ein ``common``-Block, und darin die Felder, die auch der Store fuer
seine VR-Kennzeichnung benutzt: ``openvrsupport``, ``openxrsupport``,
``osvrsupport``, ``othervrsupport`` (samt Varianten wie
``othervrsupport_rift_13``) und ``playareavr``.

Diese Datei liest genau das — offline, ohne Netz, ohne Steam-Login, in
Millisekunden statt Sekunden.

Bewusst NICHT benutzt: die Kategorie-Nummern
--------------------------------------------
Im ``common``-Block steht ausserdem ``category`` mit Eintraegen der Form
``category_53``. Welche Nummer welchem Store-Merkmal entspricht, steht
nirgends in der Datei — die Zuordnung ist reine Ueberlieferung. Eine falsch
geratene Nummer wuerde stillschweigend Flachbildschirm-Spiele in die
VR-Liste spuelen, und niemand koennte den Fehler an der Datei selbst sehen.
Die ``*vrsupport``-Felder sind dagegen selbsterklaerend. Deshalb
entscheiden nur sie.

Dateiformat (Stand v40/v41)
---------------------------
    Kopf:  magic(4) universe(4) [v41: string_table_offset(8)]
    dann je App, bis appid == 0:
        appid(4) size(4) infostate(4) lastupdated(4) picstoken(8)
        sha1_text(20) changenumber(4) [ab v40: sha1_binary(20)]
        danach das Binaer-VDF, Laenge = size - 40 (v39) bzw. - 60 (v40/41)

Ab v41 sind die SCHLUESSEL im Binaer-VDF keine Zeichenketten mehr, sondern
Nummern in eine Zeichenketten-Tabelle am Dateiende (deshalb der Offset im
Kopf). Werte bleiben in beiden Faellen inline.

Robustheit
----------
Valve kann das Format jederzeit aendern; es ist ein interner Zwischenspeicher
und keine zugesicherte Schnittstelle. Jede Funktion hier faengt deshalb ihre
Fehler ab und liefert im Zweifel ``None`` bzw. ein leeres Ergebnis. Der
Aufrufer (games.py) faellt dann auf die alte Dateierkennung zurueck — die App
wird langsamer, aber nie kaputt.
"""

import os
import re
import struct

import vr_environment as venv

from logging_setup import get_logger

log = get_logger("steam_appinfo")


# --------------------------------------------------------------------------- #
#  Formatkonstanten
# --------------------------------------------------------------------------- #
MAGIC_V39 = 0x07564427      # alt: Schluessel als Zeichenketten, kein Tabellen-Offset
MAGIC_V40 = 0x07564428      # wie v39, aber zusaetzlicher SHA1 im App-Kopf
MAGIC_V41 = 0x07564429      # Schluessel als Nummern in die Zeichenketten-Tabelle

# Groesse des App-Kopfes NACH dem size-Feld (davon haengt ab, wo das VDF beginnt)
_APP_HEADER_REST = {MAGIC_V39: 40, MAGIC_V40: 60, MAGIC_V41: 60}

# Binaer-VDF-Knotentypen
_T_OBJECT = 0x00
_T_STRING = 0x01
_T_INT32 = 0x02
_T_FLOAT32 = 0x03
_T_POINTER = 0x04
_T_WSTRING = 0x05
_T_COLOR = 0x06
_T_UINT64 = 0x07
_T_END = 0x08
_T_INT64 = 0x0A
_T_END_ALT = 0x0B

# Sicherheitsnetz gegen eine beschaedigte Datei: ohne Grenze koennte ein
# kaputtes Byte eine Endlosverschachtelung vortaeuschen und den Stapel
# sprengen. Echte appinfo-Daten bleiben weit darunter.
_MAX_DEPTH = 32


# --------------------------------------------------------------------------- #
#  VR-Erkennung: welche common-Felder zaehlen
# --------------------------------------------------------------------------- #
# Signal 1 — Valves eigene VR-Felder im common-Block.
def _is_vr_field(key):
    """True fuer die common-Felder, mit denen Steam VR-Unterstuetzung angibt.

    Abgedeckt sind:
        openvrsupport, osvrsupport, othervrsupport, onlyvrsupport,
        othervrsupport_rift_13 (und weitere Varianten mit Zusatz),
        openxrsupport
    """
    k = (key or "").lower()
    return (k.endswith("vrsupport")
            or k.startswith("othervrsupport")
            or k == "openxrsupport")


# Signal 2 — Valves Kategorien (common/category -> {"category_53": 1, ...}).
#
# Die Zuordnung der Nummern steht nicht in der Datei. Belegt ist sie ueber
# die Feature-Filterliste auf SteamDB, die genau diese Nummern den
# Store-Merkmalen zuordnet:
#
#     31 = VR Support (alt)   52 = Tracked Controller Support
#     53 = VR Supported       54 = VR Only
#
# Aufgenommen sind 31/53/54. NICHT 52: "Tracked Controller Support" heisst
# nur, dass ein Spiel mit VR-Controllern umgehen kann — das sagt fuer sich
# genommen nichts darueber, ob es in VR laeuft.
#
# ACHTUNG, das ist etwas anderes als der User-Tag "VR" (tagid 21978). Der
# wird von Spielern vergeben und steht unter anderem an OBS Studio,
# VoiceAttack und einer Reihe Visual Novels. Als Signal waere er unbrauchbar;
# die Kategorien hier kommen vom Entwickler ueber Steamworks.
VR_CATEGORY_IDS = {31, 53, 54}

_CATEGORY_KEY_RE = re.compile(r"^category_(\d+)$", re.IGNORECASE)


def category_ids(common):
    """Die Kategorie-Nummern einer App als Menge von int."""
    if not isinstance(common, dict):
        return set()
    cats = common.get("category")
    if not isinstance(cats, dict):
        return set()
    out = set()
    for key, value in cats.items():
        m = _CATEGORY_KEY_RE.match(str(key))
        if m and _is_truthy(value):
            out.add(int(m.group(1)))
    return out


def _is_truthy(value):
    """Ein gesetztes VDF-Feld von einem leeren unterscheiden.

    Steam traegt hier je nach Alter des Eintrags "1", 1 oder auch "2" ein
    (zweiteres bei mehreren unterstuetzten Laufzeiten). Ein leerer String und
    die Null bedeuten dagegen ausdruecklich "nein" — sie kommen vor und
    duerfen NICHT als VR durchgehen.
    """
    if value is None:
        return False
    if isinstance(value, dict):
        return bool(value)          # z. B. playareavr mit Unterfeldern
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    return text not in ("", "0", "false", "none")


def common_says_vr(common):
    """True, wenn Steams common-Block dieses Spiel als VR kennzeichnet.

    Drei ODER-verknuepfte Signale, alle aus derselben Datei und demselben
    Durchlauf — die Erkennung kostet damit keine Millisekunde mehr als mit
    nur einem davon:

      1. die ``*vrsupport``-Felder (openvrsupport, onlyvrsupport, ...)
      2. Valves Kategorien 31/53/54 (VR Support / VR Supported / VR Only)
      3. ``playareavr`` — eine angegebene VR-Spielflaeche

    Warum mehrere: die Felder aus (1) sind gewachsen und bei aelteren oder
    nachtraeglich um VR ergaenzten Titeln nicht immer gesetzt. Die Kategorie
    aus (2) haengt dagegen an dem, was der Entwickler im Store angibt. Kein
    Signal deckt fuer sich alles ab, zusammen aber deutlich mehr.
    """
    if not isinstance(common, dict):
        return False
    for key, value in common.items():
        if _is_vr_field(key) and _is_truthy(value):
            return True
    if category_ids(common) & VR_CATEGORY_IDS:
        return True
    # playareavr steht getrennt: ein Spiel mit angegebener VR-Spielflaeche
    # (sitzend/stehend/raumfuellend) ist ein VR-Spiel, auch wenn die
    # *vrsupport-Felder aus einem alten Eintrag stammen und fehlen.
    return _is_truthy(common.get("playareavr"))


# --------------------------------------------------------------------------- #
#  Binaer-VDF
# --------------------------------------------------------------------------- #
def _read_cstr(buf, pos):
    """Nullterminierte UTF-8-Zeichenkette ab pos. Rueckgabe: (text, neue_pos)."""
    end = buf.find(b"\x00", pos)
    if end < 0:
        raise ValueError("unterminierte Zeichenkette")
    return buf[pos:end].decode("utf-8", "replace"), end + 1


def parse_binary_vdf(buf, pos=0, strings=None, depth=0):
    """
    Liest EIN Binaer-VDF-Objekt ab ``pos``. Rueckgabe: (dict, neue_position).

    ``strings`` ist die Zeichenketten-Tabelle (v41). Ist sie None, stehen die
    Schluessel nullterminiert im Datenstrom (v39/v40).
    """
    if depth > _MAX_DEPTH:
        raise ValueError("VDF zu tief verschachtelt")

    out = {}
    size = len(buf)
    while pos < size:
        vtype = buf[pos]
        pos += 1
        if vtype in (_T_END, _T_END_ALT):
            return out, pos

        # --- Schluessel ---
        if strings is None:
            key, pos = _read_cstr(buf, pos)
        else:
            idx = int.from_bytes(buf[pos:pos + 4], "little")
            pos += 4
            if idx >= len(strings):
                raise ValueError(f"Schluessel-Nummer {idx} ausserhalb der Tabelle")
            key = strings[idx]

        # --- Wert ---
        if vtype == _T_OBJECT:
            value, pos = parse_binary_vdf(buf, pos, strings, depth + 1)
        elif vtype == _T_STRING:
            value, pos = _read_cstr(buf, pos)
        elif vtype in (_T_INT32, _T_COLOR, _T_POINTER):
            value = int.from_bytes(buf[pos:pos + 4], "little", signed=(vtype == _T_INT32))
            pos += 4
        elif vtype == _T_FLOAT32:
            value = struct.unpack_from("<f", buf, pos)[0]
            pos += 4
        elif vtype == _T_WSTRING:
            end = pos
            while end + 1 < size and buf[end:end + 2] != b"\x00\x00":
                end += 2
            value = buf[pos:end].decode("utf-16-le", "replace")
            pos = end + 2
        elif vtype == _T_UINT64:
            value = int.from_bytes(buf[pos:pos + 8], "little")
            pos += 8
        elif vtype == _T_INT64:
            value = int.from_bytes(buf[pos:pos + 8], "little", signed=True)
            pos += 8
        else:
            raise ValueError(f"unbekannter VDF-Typ 0x{vtype:02x} an Position {pos - 1}")

        out[key] = value
    return out, pos


# --------------------------------------------------------------------------- #
#  appinfo.vdf finden und lesen
# --------------------------------------------------------------------------- #
def appinfo_paths():
    """Alle in Frage kommenden appinfo.vdf (nativ + Flatpak), existierende zuerst."""
    found = []
    for root in venv.steam_data_roots():
        path = os.path.join(root, "appcache", "appinfo.vdf")
        if os.path.isfile(path) and path not in found:
            found.append(path)
    return found


def _read_string_table(fh, offset):
    """Die Zeichenketten-Tabelle am Dateiende (nur v41)."""
    fh.seek(offset)
    count = int.from_bytes(fh.read(4), "little")
    raw = fh.read()
    parts = raw.split(b"\x00")
    # Das letzte Element hinter dem abschliessenden Null-Byte ist leer und
    # gehoert nicht zur Tabelle.
    if parts and parts[-1] == b"":
        parts.pop()
    if len(parts) < count:
        raise ValueError(f"Zeichenketten-Tabelle unvollstaendig "
                         f"({len(parts)} von {count})")
    return [p.decode("utf-8", "replace") for p in parts[:count]]


def app_common(data):
    """
    Holt den ``common``-Block aus den Nutzdaten EINER App.

    Warum das eine eigene Funktion ist — und der Fehler, der beim Bau
    dieser Erkennung den Games-Tab restlos geleert hat:

    Die Nutzdaten einer App sind nicht direkt ``{"common": ...}``. Der erste
    Knoten ist ein Rahmen, den Steam ``appinfo`` nennt, und erst darin liegen
    ``appid``, ``common``, ``extended`` und ``depots``:

        appinfo
        {
            appid    440
            common   { name "Team Fortress 2"  openvrsupport "1"  ... }
            extended { ... }
        }

    Ein schlichtes ``data.get("common")`` liefert deshalb IMMER ein leeres
    Dict — und damit gilt jedes einzelne Spiel als "kein VR". Die Liste ist
    dann leer, ohne dass irgendwo ein Fehler auftaucht: leere Angaben sind
    ein gueltiges Ergebnis, kein Ausnahmefall. Genau deshalb steht hier eine
    benannte Funktion mit Test und nicht ein Einzeiler mitten im Parser.

    Gesucht wird darum in zwei Stufen: erst oben, dann eine Ebene tiefer in
    jedem Kindknoten, der ein ``common`` traegt. Damit ist es egal, ob der
    Rahmen ``appinfo`` heisst, anders heisst oder ganz fehlt.
    """
    if not isinstance(data, dict):
        return {}
    common = data.get("common")
    if isinstance(common, dict):
        return common
    for value in data.values():
        if isinstance(value, dict) and isinstance(value.get("common"), dict):
            return value["common"]
    return {}


def read_appinfo(path, wanted=None, limit_common=True):
    """
    Liest appinfo.vdf und liefert ``{appid(str): common_dict}``.

    ``wanted``       : Menge von AppIDs (str oder int). Alle anderen Eintraege
                       werden im Datenstrom UEBERSPRUNGEN, ohne sie zu
                       zerlegen — deshalb ist der Aufruf auch bei einer
                       100-MB-Datei schnell. None = alle.
    ``limit_common`` : nur den ``common``-Block behalten (alles Weitere ist
                       fuer uns Ballast und kostet nur Speicher).

    Wirft bei einem unbekannten Format — der Aufrufer entscheidet, was dann
    passiert.
    """
    want = None
    if wanted is not None:
        want = {str(a) for a in wanted}
        if not want:
            return {}

    result = {}
    with open(path, "rb") as fh:
        magic = int.from_bytes(fh.read(4), "little")
        if magic not in _APP_HEADER_REST:
            raise ValueError(f"unbekanntes appinfo-Format 0x{magic:08x}")
        fh.read(4)                                   # universe, ungenutzt

        strings = None
        if magic == MAGIC_V41:
            table_offset = int.from_bytes(fh.read(8), "little")
            resume = fh.tell()
            strings = _read_string_table(fh, table_offset)
            fh.seek(resume)

        rest = _APP_HEADER_REST[magic]
        while True:
            head = fh.read(8)
            if len(head) < 8:
                break                                # Datei zu Ende (kein Fussteil)
            appid, size = struct.unpack("<II", head)
            if appid == 0:
                break                                # regulaerer Fussteil
            if size < rest:
                raise ValueError(f"unplausible Eintragsgroesse {size} bei App {appid}")

            key = str(appid)
            if want is not None and key not in want:
                fh.seek(size, os.SEEK_CUR)           # ueberspringen, nicht lesen
                continue

            blob = fh.read(size)
            if len(blob) < size:
                break                                # abgeschnittene Datei
            try:
                data, _ = parse_binary_vdf(blob, rest, strings)
            except Exception as exc:
                # Ein einzelner kaputter Eintrag darf nicht den ganzen Scan
                # kippen — die restlichen Apps sind davon unberuehrt.
                log.debug("appinfo: App %s uebersprungen — %s", appid, exc)
                continue
            result[key] = app_common(data) if limit_common else data

            if want is not None and len(result) >= len(want):
                break                                # alles Gesuchte beisammen
    return result


# --------------------------------------------------------------------------- #
#  Zwischenspeicher (die Datei aendert sich nur, wenn Steam sie schreibt)
# --------------------------------------------------------------------------- #
_CACHE = {"stamp": None, "data": None}


def _stamp(path):
    try:
        st = os.stat(path)
        return (path, st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def commons(appids):
    """
    Steams ``common``-Bloecke fuer eine Menge von AppIDs.

    Rueckgabe: ``(daten, ok)``
        daten : {appid(str): common_dict} — NUR fuer Apps, die wirklich in
                appinfo.vdf stehen. Eine fehlende AppID taucht gar nicht auf;
                der Aufrufer kann sie dann gezielt anders behandeln, statt
                ein falsches "kein VR" untergeschoben zu bekommen.
        ok    : False, wenn keine appinfo.vdf lesbar war (Format geaendert,
                Steam nie gestartet, Datei fehlt). Dann ist ``daten`` leer und
                der Aufrufer muss auf die Dateierkennung zurueckfallen.

    Die Datei wird EINMAL komplett gelesen und dann anhand von
    Aenderungszeit und Groesse zwischengespeichert. Waehrend eines Scans
    fragt games.py fuer jedes Spiel einzeln nach — ohne den Zwischenspeicher
    waere das pro Spiel ein Durchlauf durch eine Datei von 100 MB und mehr.
    """
    want = {str(a) for a in appids}
    if not want:
        return {}, True

    paths = appinfo_paths()
    any_read = False
    for path in paths:
        stamp = _stamp(path)
        data = None
        if stamp is not None and _CACHE["stamp"] == stamp:
            data = _CACHE["data"]
        if data is None:
            try:
                data = read_appinfo(path)
            except Exception as exc:
                log.info("appinfo.vdf nicht lesbar (%s) — %s", path, exc)
                continue
            _CACHE["stamp"] = stamp
            _CACHE["data"] = data
        any_read = True

        hit = {a: c for a, c in data.items() if a in want}
        if hit:
            return hit, True
        # Datei gelesen, aber keine der gesuchten Apps drin: gueltiges
        # Ergebnis (z. B. eine zweite, leere Steam-Installation) — weiter zur
        # naechsten Wurzel.
    return {}, any_read


def vr_flags(appids):
    """
    Steams VR-Kennzeichnung als ``({appid: True/False}, ok)``.

    Duenne Huelle um :func:`commons` — dieselben Zusicherungen: fehlende
    AppIDs tauchen nicht auf, ``ok=False`` heisst "Steams Daten nicht
    verfuegbar, bitte anders erkennen".
    """
    data, ok = commons(appids)
    return {a: common_says_vr(c) for a, c in data.items()}, ok


def app_names(appids=None):
    """``{appid: Anzeigename}`` aus Steams Daten. Leer, wenn nicht lesbar."""
    for path in appinfo_paths():
        try:
            data = read_appinfo(path, wanted=appids)
        except Exception as exc:
            log.debug("app_names: %s uebersprungen — %s", path, exc)
            continue
        out = {}
        for appid, common in data.items():
            name = common.get("name") if isinstance(common, dict) else None
            if name:
                out[appid] = str(name)
        if out:
            return out
    return {}


def app_type(common):
    """Der ``type``-Eintrag aus common, klein geschrieben ('game', 'tool', ...)."""
    if not isinstance(common, dict):
        return ""
    return str(common.get("type", "")).strip().lower()


# Apps, die zwar in der Bibliothek stehen, aber keine spielbaren Titel sind.
# Steam schreibt den Typ selbst in common/type — wir muessen ihn also nicht
# am Namen erraten.
NON_GAME_TYPES = {"tool", "config", "dlc", "music", "video", "media",
                  "series", "hardware", "franchise"}


def is_playable_type(common):
    """False fuer Werkzeuge, DLC, Soundtracks & Co."""
    t = app_type(common)
    return t not in NON_GAME_TYPES


_APPID_RE = re.compile(r"^\d+$")


def is_steam_appid(value):
    """True fuer eine echte Steam-AppID (rein numerisch).

    Gebraucht wird das, seit im Games-Tab auch EIGENE Eintraege stehen
    koennen ('local:3'). Alles, was eine AppID erwartet — Cover-Download,
    CompatToolMapping, steam -applaunch —, muss die beiden auseinanderhalten.
    """
    return bool(_APPID_RE.match(str(value or "")))
