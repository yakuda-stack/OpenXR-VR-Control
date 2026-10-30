# Changelog — OpenXR/VR-Controls

Detailed changes per version. Short summary for users: [HIGHLIGHTS.md](HIGHLIGHTS.md).

### 🚀 v1.0.2 — 2026-10-30

**Deadzone update**
- New: "◎ Deadzone" button next to the action set tabs – deadzone of both sticks at a glance (OpenVR and OpenXR).
- New: checkbox "I don't use xrizer (e.g. SteamVR) – use deadzone_pct" (default: on). On: a 0–100 % slider writes `deadzone_pct` into every binding of the stick in "Joystick" mode, saved with "Apply" + "Save". Without such a binding the slider is locked.
- New: checkbox off → deadzone for OpenVR games via xrBinder, so it also works with xrizer. The matching xrBinder game is found automatically.
- New: "🧩 Use OpenXR template" button in the deadzone tab for games that report no buttons (e.g. VRChat via xrizer).
- Fix: The action set tabs (Global, Menu, Action Menu …) no longer switch by accident when scrolling with the mouse wheel.

### 🚀 v1.0.1 — 2026-10-21

**Small update**
- Info window: small "Thanks for your support!" note.
- AUR: fixed checksum error on install (new release tag).

### 🚀 v1.0.0 — 2026-09-24

**First release**
- The Controls tab from Yakuda Connect v1.3.7 as a standalone app: obah (OpenVR) and xrBinder (OpenXR) in one controller view.
- New: "+ Add Steam game" and "+ Add local game" for games not detected as VR; "Remove from list" for your own entries.
- New: Deadzone tab for OpenVR games too (stick/trackpad, saved as `deadzone_pct`).
- Installs obah and xrBinder itself (Cargo, yay/paru).
- Reuses existing xrBinder/obah installations from Yakuda Connect (shared per-game settings).
- Info window (Discord, Ko-fi, GitHub, log folder) and a "More from yakuda" footer.
- Own icon, DE/EN, settings in `~/.config/openxr-vr-control/`.
- Changelog right in the app (ⓘ Info → 📜 Changelog).
- Published as AUR package (`openxr-vr-control`), AppImage (delta updates via `.zsync`) and a curl installer for Fedora, Debian/Ubuntu and openSUSE.
