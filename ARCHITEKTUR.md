# Architektur – OpenXR/VR-Controls

Stand: v0.1.0. Der Controls-Code ist aus **Yakuda Connect v1.3.7** kopiert.
Regel: Änderungen zuerst in Yakuda Connect, dann hierher nachziehen.

```
starter.py                    Einstieg (Logging, --version, --selftest)
 └─ core/main.py  ControlsWindow   Hauptfenster
     ├─ ui/ui_main.py              baut alle Widgets (Aufbau aus Yakuda Connect + Kopfzeile/Sprache + Spiel-Knöpfe)
     ├─ core/tabs/controls_mixin.py     obah / Schalter / Installation   (aus YC, Installation ohne Tools-Tab)
     ├─ core/tabs/xr_controls_mixin.py  OpenXR-Spiele über xrBinder       (aus YC, unverändert)
     └─ core/tabs/game_list_mixin.py    NEU: Steam-/Lokales Spiel hinzufügen, Entfernen
```

| Was | Datei | Herkunft |
|---|---|---|
| Spieleliste (VR-Erkennung, Handeinträge) | `core/game_library.py` | NEU (Erkennung aus YC `games.py`) |
| Dialoge „Spiel hinzufügen“ | `ui/add_game_dialog.py` | NEU |
| obah-Auswahl / Bindings | `core/obah_bindings.py` (`import games` → `game_library`), `core/obah_editor.py` | YC |
| OpenXR-Regeln, xrBinder, IPC | `core/xr_bindings.py`, `core/xrbinder*.py` | YC, unverändert |
| Deadzone-Tab für OpenVR (Stick/Trackpad) | `ui/binding_dialog.py` (Tab), `core/obah_editor.py` (`set_drafts_deadzone` …) | NEU |
| Icon | `assets/icon.svg` / `icon.png` | NEU |
| Info-Dialog (Discord, Ko-fi, GitHub, Credits) | `ui/about_dialog.py`, Knopf `btn_info` in `ui/ui_main.py` | NEU |
| Fußleiste „Mehr von yakuda“ | `ui/ui_main.py` (`footer`, `_retranslate_footer`) | NEU |
| Alle Links | `core/links.py` | NEU |
| Controller-Zeichnung, Dialoge | `ui/controller_view.py`, `ui/binding_dialog.py`, `ui/xr_button_dialog.py`, `ui/xrbinder_panel.py` | YC (`ToggleSwitch` → `ui/widgets.py`) |
| Installation | `core/cargo_installer.py`, `core/appimage_installer.py`, `core/install_worker.py` (gekürzt), `core/programs.py` (gekürzt), `config/tools.json` (nur obah) | YC |
| Pfade | `core/paths.py` → `~/.config/openxr-vr-control/` | YC, angepasst |
| Texte | `locales/de.json`, `locales/en.json` (nur benutzte Schlüssel + `lib_*`) | YC + NEU |

**Gemeinsame Installation:** `xrbinder.tool_root()` nimmt den xrBinder-Build von Yakuda Connect
(`~/.config/yakuda-connect/tools/xrbinder`), wenn hier keiner existiert; `state_dir()` nutzt dann
auch dessen Spiel-Stände. Neuerer Patch-Stand von YC wird nicht „zurückgebaut“ (`needs_rebuild`).
obah aus YCs Cargo-Ordner zählen als installiert (`appimage_installer.installed_locally`).

Absichtlich **gleich** wie in Yakuda Connect gelassen (`core/xrbinder.py`): Layer-Name,
`MANAGED_MARK`, `~/.config/xrBinder/` — damit beide Programme dieselbe xrBinder-Konfiguration
lesen und sich nicht gegenseitig als „fremde Installation“ sehen.

Nachziehen aus Yakuda Connect: Dateien mit Herkunft „YC, unverändert“ einfach kopieren;
bei den angepassten Dateien die Änderung per Diff übernehmen.
