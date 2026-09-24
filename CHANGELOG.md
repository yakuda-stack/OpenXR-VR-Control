# Changelog — OpenXR/VR-Controls

Ausführliche Änderungen je Version (DE + EN). Kurzfassung für Nutzer: [HIGHLIGHTS.md](HIGHLIGHTS.md).

### 🚀 v0.1.0 — 2026-09-24

**🇩🇪 Erste Version**
- Controls-Tab aus Yakuda Connect v1.3.7 als eigenes Programm: obah (OpenVR) und xrBinder (OpenXR) in einer Controller-Ansicht.
- Neu: „+ Steam-Spiel hinzufügen“ und „+ Lokales Spiel hinzufügen“ für Spiele, die nicht als VR erkannt werden; „Aus Liste entfernen“ für eigene Einträge.
- Neu: Deadzone-Tab auch für OpenVR-Spiele (Stick/Trackpad, gespeichert als `deadzone_pct`).
- Installiert obah und xrBinder selbst (Cargo, yay/paru) — ohne Tools-Tab.
- Nutzt vorhandene xrBinder-/obah-Installationen aus Yakuda Connect mit (gemeinsame Einstellungen je Spiel).
- Info-Fenster (Discord, Ko-fi, GitHub, Log-Ordner) und Fußleiste „Mehr von yakuda“.
- Eigenes Icon, DE/EN, Einstellungen unter `~/.config/openxr-vr-control/`.

**🇬🇧 First release**
- The Controls tab from Yakuda Connect v1.3.7 as a standalone app: obah (OpenVR) and xrBinder (OpenXR) in one controller view.
- New: "+ Add Steam game" and "+ Add local game" for games not detected as VR; "Remove from list" for your own entries.
- New: Deadzone tab for OpenVR games too (stick/trackpad, saved as `deadzone_pct`).
- Installs obah and xrBinder itself (Cargo, yay/paru).
- Reuses existing xrBinder/obah installations from Yakuda Connect (shared per-game settings).
- Info window (Discord, Ko-fi, GitHub, log folder) and a "More from yakuda" footer.
- Own icon, DE/EN, settings in `~/.config/openxr-vr-control/`.
