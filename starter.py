#!/usr/bin/env python3
"""Einstieg von OpenXR/VR-Controls (Prozessname, Logging, --version / --selftest)."""
import os
import sys

APP_ID = "openxr-vr-control"
sys.argv[0] = APP_ID
try:
    from setproctitle import setproctitle
    setproctitle(APP_ID)
except ImportError:
    pass
try:
    import ctypes
    ctypes.CDLL("libc.so.6", use_errno=True).prctl(15, APP_ID[:15].encode(), 0, 0, 0)
except Exception:  # noqa: BLE001 — nur Kosmetik
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "core"))

from logging_setup import install_excepthook, setup_logging  # noqa: E402

_log = setup_logging()
install_excepthook()

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from version import APP_VERSION  # noqa: E402


def _desktop_file_installed():
    """Liegt openxr-vr-control.desktop in einem XDG-Anwendungsordner?"""
    home = os.path.expanduser("~")
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    data_dirs = (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    return any(os.path.isfile(os.path.join(d, "applications", APP_ID + ".desktop"))
               for d in [data_home] + data_dirs if d)


def main():
    if "--version" in sys.argv:
        print(f"{APP_ID} {APP_VERSION}")
        return 0

    if "--selftest" in sys.argv:
        # Fuer build_appimage.sh / CI: baut die ganze Oberflaeche ohne Fenster.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QMessageBox
        for name in ("warning", "information", "critical"):
            setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
        try:
            QApplication([APP_ID])
            from main import ControlsWindow
            ControlsWindow()
            print(f"selftest ok — {APP_ID} {APP_VERSION}", flush=True)
            os._exit(0)
        except Exception:  # noqa: BLE001
            _log.exception("Selbsttest fehlgeschlagen")
            print("selftest FEHLGESCHLAGEN — Details siehe Log", file=sys.stderr)
            return 1

    _log.info("%s %s startet (Python %s)", APP_ID, APP_VERSION, sys.version.split()[0])
    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName("OpenXR/VR-Controls")
    # Nur setzen, wenn es die .desktop-Datei wirklich gibt — sonst meldet
    # KDE/xdg-desktop-portal beim Start "App info not found" (harmlos, aber
    # stoert im Terminal). Bei AUR/Installation liegt sie dann im System.
    if _desktop_file_installed():
        app.setDesktopFileName(APP_ID)
    icon = os.path.join(_HERE, "assets", "icon.svg")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))

    from main import ControlsWindow
    window = ControlsWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
