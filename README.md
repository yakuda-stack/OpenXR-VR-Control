<p align="center">
  <img src="assets/icon.png" alt="OpenXR/VR-Controls" width="112"/>
</p>

<h1 align="center">OpenXR/VR-Controls</h1>

<p align="center">
  <b>Remap your VR controller buttons on Linux — for OpenVR <i>and</i> OpenXR games, with a real UI.</b><br>
  <sub>No JSON editing, no terminal tools. Pick a game, click a button, choose what it does.</sub>
</p>

<p align="center">
  <a href="https://discord.gg/ShNKvvZu74"><img src="https://img.shields.io/badge/Discord-Join-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"/></a>
  <a href="https://ko-fi.com/yakuda_"><img src="https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white" alt="Ko-fi"/></a>
  <a href="https://github.com/yakuda-stack/OpenXR-VR-Control/releases"><img src="https://img.shields.io/badge/Version-v1.0.0-81a1c1?style=for-the-badge" alt="Version"/></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/Changelog-read-a3be8c?style=for-the-badge" alt="Changelog"/></a>
  <img src="https://img.shields.io/badge/License-GPL--3.0-4c566a?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  <a href="#-install">Install</a> ·
  <a href="#-english">English</a> ·
  <a href="#-deutsch">Deutsch</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

<table>
  <tr>
    <td align="center" width="50%"><b>OpenVR game (obah)</b><br><img src="assets/openvrcontrol.png" alt="OpenVR game" width="100%"/></td>
    <td align="center" width="50%"><b>OpenXR game (xrBinder)</b><br><img src="assets/openxrcontrol.png" alt="OpenXR game" width="100%"/></td>
  </tr>
</table>

---

## 📦 Install

| Your system | How |
|---|---|
| **Arch · CachyOS · EndeavourOS · Manjaro** | AUR: `yay -S openxr-vr-control` |
| **Fedora · Nobara** | curl installer (below) |
| **Debian · Ubuntu · Linux Mint · Pop!_OS** | curl installer (below) |
| **openSUSE** | curl installer (below) |
| **Any distro · Bazzite · SteamOS** | AppImage from the [Releases](https://github.com/yakuda-stack/OpenXR-VR-Control/releases) |

### curl installer (Fedora, Debian/Ubuntu, openSUSE — and Arch too)

```bash
bash <(curl -s https://raw.githubusercontent.com/yakuda-stack/OpenXR-VR-Control/main/install.sh)
```

- Installs PySide6 from your distro (or into its own venv if your distro has none) and puts the app in `/opt/openxr-vr-control`.
- Adds a menu entry *OpenXR/VR-Controls* and the command `openxr-vr-control`.
- **Update:** simply run the same command again. Your settings in `~/.config/openxr-vr-control` stay untouched.

<details>
<summary>Uninstall (curl installer)</summary>

```bash
sudo rm -rf /opt/openxr-vr-control /opt/openxr-vr-control-venv \
            /usr/local/bin/openxr-vr-control \
            /usr/share/applications/openxr-vr-control.desktop \
            /usr/share/icons/hicolor/scalable/apps/openxr-vr-control.svg \
            /usr/share/icons/hicolor/512x512/apps/openxr-vr-control.png
# optional: your settings
rm -rf ~/.config/openxr-vr-control ~/.cache/openxr-vr-control
```
</details>

### AppImage

```bash
chmod +x openxr-vr-control-*-x86_64.AppImage
./openxr-vr-control-*-x86_64.AppImage
```
Works with fuse2 and fuse3. No FUSE at all? Add `--appimage-extract-and-run`. Delta updates via AppImageUpdate / Gear Lever (`.zsync`).

### From source

```bash
git clone https://github.com/yakuda-stack/OpenXR-VR-Control.git
cd OpenXR-VR-Control
sudo pacman -S pyside6          # Fedora: sudo dnf install python3-pyside6
python3 starter.py
```

> **For remapping you'll also need** — the app installs these itself when you switch them on:
> **obah** (OpenVR games, via Cargo or yay/paru) and **xrBinder** (OpenXR games, needs `git`, `cmake` and a C++ compiler).

---

## 🇬🇧 English

### Who is this for?

For everyone playing VR on Linux **without** a Pico or Quest — Valve Index, HTC Vive and other headsets on **SteamVR** or **Monado**. It's the Controls tab from [Yakuda Connect](https://github.com/yakuda-stack/yakuda-connect) as a small standalone app. (Using a Pico/Quest with WiVRn? Then Yakuda Connect already has all of this built in.)

### ✨ Features

| | |
|---|---|
| 🎮 **One controller view** | Both controllers side by side, one card per button. Click a card to change what it does. |
| 🕹️ **OpenVR games** | Bindings via [obah](https://github.com/galister/obah) for xrizer, VapoR and OpenComposite. Profiles, poses, haptics and chords included. |
| 🧩 **OpenXR games** | E.g. Unreal games under Proton, via [xrBinder](https://gitlab.com/mittorn/xrBinder). Start the game once and it shows up in the list as `· OpenXR`. |
| ◎ **Deadzone against stick drift** | A slider for each stick, in OpenXR *and* OpenVR games. |
| ➕ **Add games yourself** | *Add Steam game* for titles that aren't detected as VR, *Add local game* for games without Steam (itch.io, GOG, your own builds). |
| 🔧 **Installs its own tools** | obah and xrBinder via Cargo or yay/paru, in a visible terminal so you can follow every step. |
| 🤝 **Works alongside Yakuda Connect** | If Yakuda Connect already built xrBinder or obah, that installation is reused. |
| 📜 **Changelog in the app** | **ⓘ Info → Changelog** shows what's new. |
| 🌍 **English / Deutsch** | Follows your system language and can be switched at the top right. |

### 🚀 How to use

1. Switch on **obah** (for OpenVR games) and/or **xrBinder** (for OpenXR games). If a tool is missing, the app asks how to install it.
2. Under **① Game**, pick your game. Missing? Use **+ Add Steam game** / **+ Add local game**.
3. Under **② Controller**, pick your controller and under **③ Load bindings**, pick where to start from.
4. Click the buttons you want to change, then press **Save**.

<p align="center">
  <img src="assets/screenshot_deadzone.png" alt="Deadzone" width="560"/>
</p>

> **Deadzone in OpenVR games:** saved as `deadzone_pct` in the binding file. xrizer doesn't evaluate that value yet — for xrizer games switch on xrBinder and use the deadzone of the game's `· OpenXR` entry instead.

### 📁 Where things are stored

| Path | Content |
|---|---|
| `~/.config/openxr-vr-control/` | settings, your game list, tool builds |
| `~/.cache/openxr-vr-control/app.log` | log (also reachable via **ⓘ Info → Open log folder**) |
| `~/.config/xrBinder/` | xrBinder config, shared with Yakuda Connect on purpose |

### 🧪 Development

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest -q tests
ruff check .
```

Code layout (and which parts come from Yakuda Connect): [`ARCHITEKTUR.md`](ARCHITEKTUR.md) · What changed: [`CHANGELOG.md`](CHANGELOG.md)

---

## 🇩🇪 Deutsch

### Für wen?

Für alle, die unter Linux VR spielen, aber **keine** Pico oder Quest haben: Valve Index, HTC Vive und andere Headsets unter **SteamVR** oder **Monado**. Es ist der Controls-Tab aus [Yakuda Connect](https://github.com/yakuda-stack/yakuda-connect) als kleines eigenes Programm.

### 📦 Installieren

- **Arch / CachyOS:** `yay -S openxr-vr-control`
- **Fedora, Debian/Ubuntu/Mint, openSUSE:**
  ```bash
  bash <(curl -s https://raw.githubusercontent.com/yakuda-stack/OpenXR-VR-Control/main/install.sh)
  ```
  Installiert PySide6 und legt die App nach `/opt/openxr-vr-control`. **Update:** denselben Befehl nochmal ausführen, deine Einstellungen bleiben erhalten.
- **Jede Distro, Bazzite, SteamOS:** AppImage aus den [Releases](https://github.com/yakuda-stack/OpenXR-VR-Control/releases)

### ✨ Funktionen

- 🎮 **Eine Controller-Ansicht:** beide Controller nebeneinander, je Taste eine Karte. Klick auf eine Karte ändert die Belegung.
- 🕹️ **OpenVR-Spiele** über obah (xrizer, VapoR, OpenComposite), 🧩 **OpenXR-Spiele** über xrBinder.
- ◎ **Deadzone gegen Stick-Drift**, bei OpenXR- und OpenVR-Spielen.
- ➕ **Steam-Spiel / Lokales Spiel hinzufügen**, wenn ein Spiel nicht automatisch erkannt wird.
- 🔧 **Installiert obah und xrBinder selbst** (Cargo oder yay/paru).
- 🤝 **Nutzt vorhandene Installationen aus Yakuda Connect mit.**
- 📜 **Changelog in der App:** ⓘ Info → Changelog.
- 🌍 **Deutsch / Englisch**

### 🚀 So geht's

1. **obah** und/oder **xrBinder** einschalten. Fehlt ein Werkzeug, fragt die App, wie es installiert werden soll.
2. Unter **① Spiel** das Spiel wählen. Fehlt es, über **+ Steam-Spiel** oder **+ Lokales Spiel** hinzufügen.
3. Unter **② Controller** den Controller wählen, unter **③ Bindings laden** den Ausgangspunkt.
4. Tasten anklicken, belegen und **Speichern**.

> Die Deadzone bei OpenVR-Spielen wird als `deadzone_pct` gespeichert. xrizer wertet diesen Wert noch nicht aus. Bei xrizer-Spielen deshalb xrBinder einschalten und die Deadzone im `· OpenXR`-Eintrag einstellen.

Was sich geändert hat: [CHANGELOG.md](CHANGELOG.md)

---

## 💜 More from yakuda

| | |
|---|---|
| **[Yakuda Connect](https://github.com/yakuda-stack/yakuda-connect)** | WiVRn dashboard for Pico & Quest on Linux: streaming, games, tools and controls in one app |
| **[OSC-DreamChatbox](https://github.com/yakuda-stack/OSC-DreamChatbox)** | VRChat chatbox with music, hardware info, speech-to-text & plugins, for Linux and Windows |

## 🙏 Thanks

[obah](https://github.com/galister/obah) by galister · [xrBinder](https://gitlab.com/mittorn/xrBinder) by mittorn · [xrizer](https://github.com/Supreeeme/xrizer)

<p align="center"><img src="assets/screenshot_about.png" alt="Info" width="380"/></p>

---

<p align="center"><sub>🤖 <b>Transparency note:</b> This project and its documentation are developed with the support of AI coding assistants (<b>Claude by Anthropic</b>). <b>Idea, architecture &amp; UX/UI design:</b> by me. The controls code comes from Yakuda Connect.</sub></p>
<p align="center"><sub>Licensed under GPL-3.0</sub></p>
