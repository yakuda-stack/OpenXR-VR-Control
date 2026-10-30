# Changelog — OpenXR/VR-Controls

Ausführliche Änderungen je Version (DE + EN). Kurzfassung für Nutzer: [HIGHLIGHTS.md](HIGHLIGHTS.md).

### 🚀 v1.0.2 — 2026-10-30

**🇩🇪 Deadzone-Update**
- Neu: Knopf „◎ Deadzone“ neben den Action-Set-Tabs – Deadzone beider Sticks auf einen Blick (OpenVR und OpenXR).
- Neu: Haken „Ich nutze nicht xrizer (z. B. SteamVR) – deadzone_pct verwenden“ (Standard: an). An: Regler 0–100 % schreibt `deadzone_pct` in alle Belegungen des Sticks im Modus „Joystick“, gespeichert mit „Übernehmen“ + „Speichern“. Ohne passende Belegung ist der Regler gesperrt.
- Neu: Haken aus → Deadzone für OpenVR-Spiele über xrBinder, wirkt so auch bei xrizer. Das passende xrBinder-Spiel wird automatisch gefunden.
- Neu: Knopf „🧩 OpenXR-Vorlage verwenden“ im Deadzone-Tab für Spiele ohne gemeldete Tasten (z. B. VRChat über xrizer).
- Fix: Die Action-Set-Tabs (Global, Menu, Action Menu …) wechseln nicht mehr versehentlich beim Scrollen mit dem Mausrad.

**🇬🇧 Deadzone update**
- New: "◎ Deadzone" button next to the action set tabs – deadzone of both sticks at a glance (OpenVR and OpenXR).
- New: checkbox "I don't use xrizer (e.g. SteamVR) – use deadzone_pct" (default: on). On: a 0–100 % slider writes `deadzone_pct` into every binding of the stick in "Joystick" mode, saved with "Apply" + "Save". Without such a binding the slider is locked.
- New: checkbox off → deadzone for OpenVR games via xrBinder, so it also works with xrizer. The matching xrBinder game is found automatically.
- New: "🧩 Use OpenXR template" button in the deadzone tab for games that report no buttons (e.g. VRChat via xrizer).
- Fix: The action set tabs (Global, Menu, Action Menu …) no longer switch by accident when scrolling with the mouse wheel.

### 🚀 v1.0.1 — 2026-10-21

**🇩🇪 Kleines Update**
- Info-Fenster: kleiner Dankestext „Danke für deine Unterstützung!“.
- AUR: Prüfsummen-Fehler beim Installieren behoben (neuer Release-Tag).

**🇬🇧 Small update**
- Info window: small "Thanks for your support!" note.
- AUR: fixed checksum error on install (new release tag).

### 🚀 v1.0.0 — 2026-09-24

**🇩🇪 Erste Version**
- Controls-Tab aus Yakuda Connect v1.3.7 als eigenes Programm: obah (OpenVR) und xrBinder (OpenXR) in einer Controller-Ansicht.
- Neu: „+ Steam-Spiel hinzufügen“ und „+ Lokales Spiel hinzufügen“ für Spiele, die nicht als VR erkannt werden; „Aus Liste entfernen“ für eigene Einträge.
- Neu: Deadzone-Tab auch für OpenVR-Spiele (Stick/Trackpad, gespeichert als `deadzone_pct`).
- Installiert obah und xrBinder selbst (Cargo, yay/paru) — ohne Tools-Tab.
- Nutzt vorhandene xrBinder-/obah-Installationen aus Yakuda Connect mit (gemeinsame Einstellungen je Spiel).
- Info-Fenster (Discord, Ko-fi, GitHub, Log-Ordner) und Fußleiste „Mehr von yakuda“.
- Eigenes Icon, DE/EN, Einstellungen unter `~/.config/openxr-vr-control/`.
- Changelog direkt in der App (ⓘ Info → 📜 Changelog).
- Veröffentlicht als AUR-Paket (`openxr-vr-control`), AppImage (mit Delta-Updates über `.zsync`) und curl-Installer für Fedora, Debian/Ubuntu und openSUSE.

**🇬🇧 First release**
- The Controls tab from Yakuda Connect v1.3.7 as a standalone app: obah (OpenVR) and xrBinder (OpenXR) in one controller view.
- New: "+ Add Steam game" and "+ Add local game" for games not detected as VR; "Remove from list" for your own entries.
- New: Deadzone tab for OpenVR games too (stick/trackpad, saved as `deadzone_pct`).
- Installs obah and xrBinder itself (Cargo, yay/paru).
- Reuses existing xrBinder/obah installations from Yakuda Connect (shared per-game settings).
- Info window (Discord, Ko-fi, GitHub, log folder) and a "More from yakuda" footer.
- Own icon, DE/EN, settings in `~/.config/openxr-vr-control/`.
- Changelog right in the app (ⓘ Info → 📜 Changelog).
- Published as AUR package (`openxr-vr-control`), AppImage (delta updates via `.zsync`) and a curl installer for Fedora, Debian/Ubuntu and openSUSE.
