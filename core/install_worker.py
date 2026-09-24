"""
core/install_worker.py — Terminal finden + Paketinstallation (yay/paru/dnf/apt/flatpak)
Aus Yakuda Connect uebernommen, gekuerzt auf das, was OpenXR-VR-Control braucht.
"""
import subprocess
import shutil
import time
from PySide6.QtCore import QThread, Signal

from logging_setup import get_logger

log = get_logger("install_worker")


# Terminalemulatoren nach Priorität — erster gefundener wird benutzt.
# Jeder Eintrag: (binary, argument_um_befehl_auszuführen)
# Die meisten benutzen "-e", kitty/foot benutzen direkt den Befehl ohne Flag.
TERMINAL_CANDIDATES = [
    # KDE
    ("konsole",      ["-e"]),
    # GNOME / GTK
    ("gnome-terminal", ["--"]),
    # Hyprland / wlroots
    ("kitty",        []),
    ("foot",         []),
    ("alacritty",    ["-e"]),
    ("wezterm",      ["start", "--"]),
    # XFCE
    ("xfce4-terminal", ["-e"]),
    # Weitere verbreitete
    ("xterm",        ["-e"]),
    ("lxterminal",   ["-e"]),
    ("tilix",        ["-e"]),
    ("urxvt",        ["-e"]),
]

def find_terminal():
    """Gibt (binary, exec_flag_list) des ersten verfügbaren Terminals zurück."""
    for binary, flags in TERMINAL_CANDIDATES:
        if shutil.which(binary):
            return binary, flags
    return None, None



class InstallWorker(QThread):
    status_signal = Signal(str)
    finished_signal = Signal(bool)

    def __init__(self, packages, helper="yay", copr_map=None, ppa="", flatpak_user=False):
        super().__init__()
        self.packages = packages
        # Flatpak nur fuer den eigenen Benutzer (--user). Auf SteamOS noetig:
        # eine System-Installation fragt per polkit nach einem Passwort, und
        # der Benutzer 'deck' hat ab Werk keins.
        self.flatpak_user = bool(flatpak_user)
        # 'flatpak' ist hier nur noch für den TOOLS-Tab erlaubt (ProtonPlus etc.),
        # die WiVRn-Runtime im Installations-Tab läuft ausschließlich nativ.
        self.helper = helper if helper in ("yay", "paru", "dnf", "apt", "flatpak") else "yay"
        # {paketname: copr-kennung} — nur für dnf. Steht ein Paket hier drin,
        # wird das COPR im selben Terminalfenster aktiviert, bevor installiert
        # wird. Der Nutzer muss also nichts mehr von Hand kopieren.
        self.copr_map = dict(copr_map or {})
        # PPA für apt-Systeme, z. B. 'ppa:lvra/wivrn'. Gleiche Idee wie copr_map,
        # nur gilt sie für den ganzen Durchlauf: eine PPA bringt alle Pakete mit.
        self.ppa = ppa or ""

    def build_bash_command(self, pkg, index, total_pkgs):
        """
        Die Befehlszeile, die im Terminalfenster laeuft.

        Bewusst als eigene Methode (statt inline in run()): so laesst sie sich
        im Test pruefen, ohne dass ein Terminal geoeffnet werden muss.
        """
        tail = ("echo ''; "
                "echo 'Fertig. Dieses Fenster schließt sich gleich automatisch...'; "
                "sleep 2")

        if self.helper == "flatpak":
            # remote-add zuerst: auf Mint ist Flathub eingerichtet, auf einem
            # nackten Debian nicht. '--if-not-exists' aendert nichts, wenn es
            # das Remote schon gibt.
            scope = "--user " if self.flatpak_user else ""
            return (f"echo '=== Installiere {pkg} (Flatpak) ==='; "
                    f"flatpak remote-add {scope}--if-not-exists flathub "
                    f"https://flathub.org/repo/flathub.flatpakrepo; "
                    f"flatpak install {scope}-y flathub {pkg}; " + tail)

        if self.helper == "apt":
            ppa_cmd = ""
            if self.ppa:
                # 'add-apt-repository' steckt in software-properties-common —
                # auf einer schlanken Debian-Installation fehlt es. Es wird
                # deshalb bei Bedarf vorher nachgezogen.
                #
                # Auf Linux Mint ist ausserdem wichtig, dass genau dieses
                # Werkzeug benutzt wird: 'lsb_release -cs' liefert dort den
                # Mint-Namen (z. B. 'zena'), nicht den Ubuntu-Codenamen
                # ('noble'). Eine von Hand geschriebene sources-Zeile zeigte
                # damit ins Leere; add-apt-repository loest das selbst auf.
                ppa_cmd = (
                    f"echo '--- Aktiviere {self.ppa} ---'; "
                    f"command -v add-apt-repository >/dev/null || "
                    f"sudo apt-get install -y software-properties-common; "
                    f"sudo add-apt-repository -y {self.ppa}; "
                )
            return (f"echo '=== Installiere {pkg} ({index}/{total_pkgs}) mit apt ==='; "
                    f"{ppa_cmd}"
                    f"sudo apt-get update; "
                    f"sudo apt-get install -y {pkg}; " + tail)

        if self.helper == "dnf":
            copr = self.copr_map.get(pkg)
            copr_cmd = ""
            if copr:
                # 'dnf copr' steckt bei dnf4 im Plugin-Paket dnf-plugins-core,
                # bei dnf5 (Fedora 41+) ist es eingebaut. Schlaegt der erste
                # Versuch fehl, wird das Plugin nachinstalliert und ein zweites
                # Mal probiert — sonst saehe der Nutzer auf aelteren Systemen
                # wieder eine Fehlermeldung statt einer Installation.
                copr_cmd = (f"echo '--- Aktiviere COPR {copr} ---'; "
                            f"sudo dnf copr enable -y {copr} || {{ "
                            f"sudo dnf install -y dnf-plugins-core && "
                            f"sudo dnf copr enable -y {copr}; }}; ")
            return (f"echo '=== Installiere {pkg} ({index}/{total_pkgs}) mit dnf ==='; "
                    f"{copr_cmd}sudo dnf install -y {pkg}; " + tail)

        return (f"echo '=== Installiere {pkg} ({index}/{total_pkgs}) mit {self.helper} ==='; "
                f"{self.helper} -S {pkg}; " + tail)

    def run(self):
        if not self.packages:
            self.finished_signal.emit(True)
            return

        terminal, exec_flags = find_terminal()
        if terminal is None:
            self.status_signal.emit("Fehler: Kein unterstütztes Terminal gefunden (konsole, kitty, foot, alacritty ...)!")
            self.finished_signal.emit(False)
            return

        total_pkgs = len(self.packages)
        success = True

        for index, pkg in enumerate(self.packages, start=1):
            self.status_signal.emit(f"Installiere Paket {index} von {total_pkgs}: {pkg}...")

            bash_cmd = self.build_bash_command(pkg, index, total_pkgs)

            # Befehlsaufbau je nach Terminal-Syntax
            cmd = [terminal] + exec_flags + ["bash", "-c", bash_cmd]

            try:
                process = subprocess.Popen(cmd)
                process.wait()

                if process.returncode != 0:
                    log.warning(f"Fehler oder Abbruch bei Paket: {pkg} (Terminal: {terminal})")
                    success = False
            except Exception as e:
                log.warning(f"Fehler beim Öffnen von '{terminal}' für {pkg}: {e}")
                success = False

            time.sleep(0.5)

        if success:
            self.status_signal.emit("Alle ausgewählten Programme erfolgreich installiert!")
            self.finished_signal.emit(True)
        else:
            self.status_signal.emit("Installation abgeschlossen (einige Pakete wurden übersprungen oder abgebrochen).")
            self.finished_signal.emit(False)
