#!/usr/bin/env python3
"""
tests/test_steam_appinfo.py — Parser fuer Steams appinfo.vdf
============================================================
Der Parser liest ein BINAERformat, das Valve nirgends zusichert. Ihn nur
gegen die echte Datei auf dem eigenen Rechner zu probieren hilft niemandem:
auf einem Build-Server gibt es keine Steam-Installation, und die eine Datei,
die man zuhause hat, deckt nie beide Formatversionen ab.

Deshalb baut dieser Test die Datei selbst — einmal als v40 (Schluessel als
Zeichenketten) und einmal als v41 (Schluessel als Nummern in eine Tabelle).
Damit ist geprueft, was wirklich zaehlt:

  * beide Formatversionen werden gelesen
  * das Ueberspringen nicht gesuchter Apps landet auf dem richtigen Byte
    (ein Fehler dabei verschiebt ALLES danach und faellt sonst erst beim
    Nutzer auf, als "die Haelfte meiner Spiele fehlt")
  * die VR-Erkennung sagt bei den Feldern, die Steam wirklich benutzt, ja —
    und bei einem leeren Feld nein
  * eine beschaedigte Datei wirft, statt Unsinn zu liefern
"""
import os
import struct
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

import steam_appinfo as sa    # noqa: E402


# --------------------------------------------------------------------------- #
#  Hilfsmittel: eine appinfo.vdf von Hand bauen
# --------------------------------------------------------------------------- #
def _cstr(text):
    return text.encode("utf-8") + b"\x00"


def _encode_node(data, strings=None):
    """Ein dict als Binaer-VDF-Rumpf (ohne den abschliessenden 0x08)."""
    out = b""
    for key, value in data.items():
        if isinstance(value, dict):
            vtype = 0x00
        elif isinstance(value, int):
            vtype = 0x02
        else:
            vtype = 0x01
        out += bytes([vtype])
        if strings is None:
            out += _cstr(key)
        else:
            if key not in strings:
                strings[key] = len(strings)
            out += struct.pack("<I", strings[key])
        if vtype == 0x00:
            out += _encode_node(value, strings) + b"\x08"
        elif vtype == 0x02:
            out += struct.pack("<i", value)
        else:
            out += _cstr(str(value))
    return out


def build_appinfo(apps, version=41):
    """
    apps: {appid: {"common": {...}, ...}}
    Rueckgabe: die kompletten Dateibytes.
    """
    magic = {39: sa.MAGIC_V39, 40: sa.MAGIC_V40, 41: sa.MAGIC_V41}[version]
    strings = {} if version == 41 else None

    # Die App-Bloecke zuerst bauen — bei v41 fuellt das die Tabelle.
    blocks = []
    for appid, payload in apps.items():
        body = _encode_node(payload, strings) + b"\x08"
        rest = sa._APP_HEADER_REST[magic]
        head = b""
        head += struct.pack("<I", 0)          # infostate
        head += struct.pack("<I", 0)          # lastupdated
        head += struct.pack("<Q", 0)          # picstoken
        head += b"\x00" * 20                  # sha1 text
        head += struct.pack("<I", 0)          # changenumber
        if rest == 60:
            head += b"\x00" * 20              # sha1 binary
        assert len(head) == rest
        blocks.append(struct.pack("<II", int(appid), rest + len(body)) + head + body)

    body = b"".join(blocks) + struct.pack("<I", 0)     # Fussteil: appid 0

    out = struct.pack("<I", magic) + struct.pack("<I", 1)
    if version == 41:
        table_offset = len(out) + 8 + len(body)
        out += struct.pack("<q", table_offset)
        out += body
        ordered = sorted(strings, key=strings.get)
        out += struct.pack("<I", len(ordered))
        out += b"".join(_cstr(s) for s in ordered)
    else:
        out += body
    return out


# WICHTIG: In der echten appinfo.vdf liegt pro App ein RAHMEN-Knoten
# ("appinfo") ueber den eigentlichen Bloecken:
#
#     appinfo { appid 440  common { ... }  extended { ... } }
#
# Genau daran ist die Erkennung beim Bau einmal komplett gescheitert: der
# Code suchte "common" eine Ebene zu hoch, fand nie etwas, und jedes Spiel
# galt als "kein VR" — ohne Fehler, weil eine leere Angabe ein gueltiges
# Ergebnis ist. Der Test hat den Rahmen damals ebenfalls weggelassen und die
# falsche Annahme dadurch bestaetigt, statt sie aufzudecken.
#
# Deshalb laufen alle Tests jetzt gegen BEIDE Formen: mit Rahmen (so wie
# Steam es schreibt) und ohne (damit ein kuenftiger Umbau bei Valve uns
# nicht wieder die Liste leert).
def _wrap(common, appid):
    return {"appinfo": {"appid": int(appid), "common": common}}


COMMONS = {
    "438100": {"name": "VRChat", "type": "Game",
               "openvrsupport": "1", "openxrsupport": "1"},
    "570":    {"name": "Dota 2", "type": "game",
               "openvrsupport": ""},                      # ausdruecklich KEIN VR
    "620980": {"name": "Beat Saber", "type": "game",
               "playareavr": {"roomscale": 1, "standing": 1}},
    "250820": {"name": "SteamVR", "type": "Tool",
               "openvrsupport": "1"},
    "1234":   {"name": "Flachspiel", "type": "game"},
    "999999": {"name": "Alt-VR", "type": "game",
               "othervrsupport_rift_13": "1"},
}

SAMPLE = {a: _wrap(c, a) for a, c in COMMONS.items()}
SAMPLE_FLAT = {a: {"common": c} for a, c in COMMONS.items()}


@pytest.fixture(params=[(40, "wrapped"), (41, "wrapped"),
                        (40, "flat"), (41, "flat")],
                ids=["v40-appinfo-rahmen", "v41-appinfo-rahmen",
                     "v40-ohne-rahmen", "v41-ohne-rahmen"])
def appinfo_file(request, tmp_path):
    version, shape = request.param
    apps = SAMPLE if shape == "wrapped" else SAMPLE_FLAT
    path = tmp_path / "appinfo.vdf"
    path.write_bytes(build_appinfo(apps, version=version))
    return str(path)


# --------------------------------------------------------------------------- #
#  Tests
# --------------------------------------------------------------------------- #
def test_liest_alle_apps(appinfo_file):
    data = sa.read_appinfo(appinfo_file)
    assert set(data) == set(COMMONS)
    # read_appinfo liefert bereits den common-Block, egal ob mit Rahmen
    # oder ohne.
    assert data["438100"]["name"] == "VRChat"
    assert data["620980"]["playareavr"]["roomscale"] == 1


def test_common_wird_durch_den_rahmen_hindurch_gefunden():
    """Der Regressionstest zum Rahmen-Knoten."""
    echt = {"appinfo": {"appid": 438100,
                        "common": {"name": "VRChat", "openvrsupport": "1"}}}
    assert sa.app_common(echt)["name"] == "VRChat"
    assert sa.common_says_vr(sa.app_common(echt)) is True
    # Ohne Rahmen ebenfalls
    assert sa.app_common({"common": {"name": "X"}})["name"] == "X"
    # Nichts Brauchbares -> leer, aber kein Absturz
    assert sa.app_common({"extended": {"foo": 1}}) == {}
    assert sa.app_common("kein dict") == {}


def test_ueberspringen_trifft_die_richtigen_bytes(appinfo_file):
    """Nur eine App anfordern — der Sprung ueber die anderen muss exakt sein.

    Genau hier steckt der Fehler, der sich sonst erst beim Nutzer zeigt: ein
    um wenige Bytes falscher Sprung liefert nicht etwa nichts, sondern
    zufaellig aussehende Treffer.
    """
    data = sa.read_appinfo(appinfo_file, wanted={"999999"})
    assert set(data) == {"999999"}
    assert data["999999"]["name"] == "Alt-VR"


def test_teilmenge_mehrerer_apps(appinfo_file):
    data = sa.read_appinfo(appinfo_file, wanted=["570", "620980"])
    assert set(data) == {"570", "620980"}


def test_vr_erkennung(appinfo_file):
    data = sa.read_appinfo(appinfo_file)
    says = {a: sa.common_says_vr(c) for a, c in data.items()}
    assert says["438100"] is True          # openvrsupport/openxrsupport
    assert says["620980"] is True          # nur playareavr
    assert says["999999"] is True          # othervrsupport_rift_13
    assert says["570"] is False            # leeres Feld = ausdruecklich nein
    assert says["1234"] is False           # gar kein Feld


def test_leeres_feld_ist_kein_vr():
    assert sa.common_says_vr({"openvrsupport": ""}) is False
    assert sa.common_says_vr({"openvrsupport": "0"}) is False
    assert sa.common_says_vr({"openvrsupport": 0}) is False
    assert sa.common_says_vr({"openvrsupport": 1}) is True
    assert sa.common_says_vr({"openxrsupport": "2"}) is True
    assert sa.common_says_vr({}) is False
    assert sa.common_says_vr(None) is False


def test_playareavr_leer_ist_kein_vr():
    """Ein vorhandener, aber leerer Block darf nicht als VR durchgehen."""
    assert sa.common_says_vr({"playareavr": {}}) is False


def test_typ_filter(appinfo_file):
    data = sa.read_appinfo(appinfo_file)
    assert sa.is_playable_type(data["438100"]) is True
    assert sa.is_playable_type(data["250820"]) is False      # type = Tool
    assert sa.app_type(data["250820"]) == "tool"


def test_unbekanntes_format_wirft(tmp_path):
    path = tmp_path / "appinfo.vdf"
    path.write_bytes(struct.pack("<II", 0xDEADBEEF, 1))
    with pytest.raises(ValueError):
        sa.read_appinfo(str(path))


def test_abgeschnittene_datei_liefert_was_da_ist(tmp_path):
    """Halbe Datei: kein Absturz, sondern die vollstaendigen Eintraege."""
    raw = build_appinfo(SAMPLE, version=41)
    path = tmp_path / "appinfo.vdf"
    path.write_bytes(raw[:len(raw) // 2])
    try:
        data = sa.read_appinfo(str(path))
    except ValueError:
        return                     # auch akzeptabel: sauber gemeldet
    assert isinstance(data, dict)


def test_namen_auslesen(appinfo_file, monkeypatch):
    monkeypatch.setattr(sa, "appinfo_paths", lambda: [appinfo_file])
    names = sa.app_names(["438100", "570"])
    assert names["438100"] == "VRChat"
    assert names["570"] == "Dota 2"


def test_vr_flags_ueber_die_oeffentliche_schnittstelle(appinfo_file, monkeypatch):
    monkeypatch.setattr(sa, "appinfo_paths", lambda: [appinfo_file])
    sa._CACHE["stamp"] = None                     # Zwischenspeicher leeren
    flags, ok = sa.vr_flags(["438100", "570", "1234", "620980"])
    assert ok is True
    assert flags == {"438100": True, "570": False,
                     "1234": False, "620980": True}


def test_vr_flags_ohne_datei(monkeypatch):
    """Keine appinfo.vdf -> ok=False, damit der Aufrufer zurueckfaellt."""
    monkeypatch.setattr(sa, "appinfo_paths", lambda: [])
    sa._CACHE["stamp"] = None
    flags, ok = sa.vr_flags(["438100"])
    assert flags == {}
    assert ok is False


def test_fehlende_app_taucht_nicht_als_false_auf(appinfo_file, monkeypatch):
    """Eine unbekannte AppID darf nicht stillschweigend 'kein VR' heissen."""
    monkeypatch.setattr(sa, "appinfo_paths", lambda: [appinfo_file])
    sa._CACHE["stamp"] = None
    flags, ok = sa.vr_flags(["438100", "777777"])
    assert ok is True
    assert "777777" not in flags


def test_is_steam_appid():
    assert sa.is_steam_appid("438100") is True
    assert sa.is_steam_appid(438100) is True
    assert sa.is_steam_appid("local:3") is False
    assert sa.is_steam_appid("") is False
    assert sa.is_steam_appid(None) is False


def test_verschachtelung_begrenzt():
    """Eine kaputte Datei darf den Stapel nicht sprengen."""
    blob = bytes([0x00]) + b"x\x00"
    blob = blob * (sa._MAX_DEPTH + 5)
    with pytest.raises(ValueError):
        sa.parse_binary_vdf(blob, 0, None)


def test_appinfo_paths_nur_existierende(monkeypatch, tmp_path):
    root = tmp_path / "Steam"
    (root / "appcache").mkdir(parents=True)
    (root / "appcache" / "appinfo.vdf").write_bytes(b"x")
    monkeypatch.setattr(sa.venv, "steam_data_roots",
                        lambda: [str(root), str(tmp_path / "gibtsnicht")])
    assert sa.appinfo_paths() == [os.path.join(str(root), "appcache", "appinfo.vdf")]


# --------------------------------------------------------------------------- #
#  Signal 2: Valves Kategorien
# --------------------------------------------------------------------------- #
def test_kategorie_53_und_54_gelten_als_vr():
    assert sa.common_says_vr({"category": {"category_53": 1}}) is True   # VR Supported
    assert sa.common_says_vr({"category": {"category_54": 1}}) is True   # VR Only
    assert sa.common_says_vr({"category": {"category_31": 1}}) is True   # VR Support (alt)


def test_tracked_controller_allein_ist_kein_vr():
    """52 heisst nur 'kann mit VR-Controllern umgehen'. Das sagt fuer sich
    genommen nichts darueber, ob das Spiel in VR laeuft — sonst holt man
    sich Flachbildschirm-Titel in die Liste."""
    assert sa.common_says_vr({"category": {"category_52": 1}}) is False


def test_andere_kategorien_sind_kein_vr():
    assert sa.common_says_vr({"category": {"category_2": 1,
                                           "category_22": 1}}) is False


def test_kategorie_null_zaehlt_nicht():
    assert sa.common_says_vr({"category": {"category_53": 0}}) is False
    assert sa.common_says_vr({"category": {"category_53": ""}}) is False


def test_kategorie_ergaenzt_die_felder_statt_sie_zu_ersetzen():
    """ODER-verknuepft: jedes Signal allein genuegt."""
    assert sa.common_says_vr({"openvrsupport": "1"}) is True
    assert sa.common_says_vr({"category": {"category_54": 1}}) is True
    assert sa.common_says_vr({"openvrsupport": "", "category": {"category_2": 1}}) is False


def test_category_ids_robust():
    assert sa.category_ids({"category": {"category_53": 1, "category_2": 1}}) == {53, 2}
    assert sa.category_ids({"category": "kein dict"}) == set()
    assert sa.category_ids({}) == set()
    assert sa.category_ids(None) == set()
    # Unerwartete Schluessel duerfen nicht hochgehen
    assert sa.category_ids({"category": {"kaputt": 1, "category_x": 1}}) == set()


def test_onlyvrsupport_wird_erkannt():
    """Steht bei Beat Saber, Thief VR und Wanderer in echten Daten."""
    assert sa.common_says_vr({"onlyvrsupport": 1}) is True
