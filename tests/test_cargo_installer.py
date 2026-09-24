#!/usr/bin/env python3
"""Tests fuer core/cargo_installer.py (Cargo-Installationsweg, z. B. obah)."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

import appimage_installer as appimg  # noqa: E402
import cargo_installer as ci  # noqa: E402

OBAH = {"key": "obah", "crate": "obah", "start_cmd": "obah", "pkg": "obah-git",
        "install_methods": ["aur", "cargo"]}


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Alle Pfade in ein Wegwerf-Home umbiegen."""
    tools = tmp_path / ".config/yakuda-connect/tools"
    monkeypatch.setattr(ci, "CARGO_TOOLS_DIR", str(tools / "cargo"))
    monkeypatch.setattr(ci, "LOCAL_BIN", str(tmp_path / ".local/bin"))
    return tmp_path


def _fake_install(tool, version="0.1.1"):
    """So sieht der Ordner nach einem erfolgreichen 'cargo install --root' aus."""
    root = ci.tool_root(tool)
    os.makedirs(os.path.join(root, "bin"), exist_ok=True)
    binp = ci.binary_path(tool)
    with open(binp, "w") as fh:
        fh.write("#!/bin/sh\n")
    os.chmod(binp, 0o755)
    with open(os.path.join(root, ".crates2.json"), "w") as fh:
        json.dump({"installs": {
            f"{ci.crate_name(tool)} {version} (registry+https://github.com/rust-lang/crates.io-index)": {}
        }}, fh)


def test_paths_live_in_tools_cargo_folder(home):
    assert ci.tool_root(OBAH).endswith(".config/yakuda-connect/tools/cargo/obah")
    assert ci.binary_path(OBAH) == os.path.join(ci.tool_root(OBAH), "bin", "obah")
    assert ci.link_path(OBAH).endswith(".local/bin/obah")


def test_cargo_method_is_offered_everywhere():
    assert "cargo" in appimg.detect_install_methods(OBAH)
    # Ohne 'cargo' in install_methods kein Cargo-Weg
    assert "cargo" not in appimg.detect_install_methods({**OBAH, "install_methods": ["aur"]})


@pytest.mark.parametrize("lang", ["de", "en"])
def test_script_is_valid_bash(home, lang, tmp_path):
    script = tmp_path / "install.sh"
    script.write_text(ci.build_script(OBAH, lang))
    res = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_script_builds_into_tool_folder_and_links(home):
    s = ci.build_script(OBAH, "de")
    assert 'cargo install --locked "$CRATE" --root "$ROOT"' in s
    assert 'ln -sfn "$BIN" "$LINK"' in s
    # Fehler duerfen das Fenster nicht einfach schliessen
    assert "read -rp" in s
    # Protokoll fuer spaeter
    assert 'tee "$LOG"' in s


def test_status_version_and_uninstall(home):
    assert ci.local_status(OBAH) == (False, "")
    _fake_install(OBAH, "0.1.1")
    assert ci.local_status(OBAH) == (True, "0.1.1")

    os.makedirs(os.path.dirname(ci.link_path(OBAH)), exist_ok=True)
    os.symlink(ci.binary_path(OBAH), ci.link_path(OBAH))
    ci.uninstall(OBAH)
    assert ci.local_status(OBAH) == (False, "")
    assert not os.path.lexists(ci.link_path(OBAH))
    assert not os.path.exists(ci.tool_root(OBAH))


def test_uninstall_keeps_foreign_binary(home):
    """Ein obah aus dem AUR-Paket o. Ae. unter gleichem Namen bleibt stehen."""
    _fake_install(OBAH)
    link = ci.link_path(OBAH)
    os.makedirs(os.path.dirname(link), exist_ok=True)
    with open(link, "w") as fh:
        fh.write("fremd")
    ci.uninstall(OBAH)
    assert os.path.exists(link)


def test_gnome_terminal_waits():
    cmd = ci.terminal_command("gnome-terminal", ["--"], "/x/install.sh")
    assert cmd == ["gnome-terminal", "--wait", "--", "bash", "/x/install.sh"]
    assert ci.terminal_command("kitty", [], "/x/install.sh") == ["kitty", "bash", "/x/install.sh"]


def _run_worker(monkeypatch, script_body):
    """Worker mit einem 'Terminal', das das Skript direkt ausfuehrt."""
    import install_worker
    monkeypatch.setattr(install_worker, "find_terminal", lambda: ("env", []))
    monkeypatch.setattr(ci, "build_script", lambda tool, lang="de": script_body)
    w = ci.CargoInstallWorker(OBAH, lang="de")
    results = []
    w.finished_signal.connect(results.append)
    w.run()   # synchron, ohne Thread
    return results


def test_worker_reports_success(home, monkeypatch):
    root = ci.tool_root(OBAH)
    body = (f"mkdir -p '{root}/bin'; printf '#!/bin/sh\\n' > '{ci.binary_path(OBAH)}'; "
            f"chmod +x '{ci.binary_path(OBAH)}'; echo ok > '{root}/{ci.STATUS_NAME}'\n")
    assert _run_worker(monkeypatch, body) == [True]


def test_worker_reports_failure(home, monkeypatch):
    root = ci.tool_root(OBAH)
    body = f"echo fail > '{root}/{ci.STATUS_NAME}'; exit 1\n"
    assert _run_worker(monkeypatch, body) == [False]


def test_compute_status_includes_cargo(home, monkeypatch):
    monkeypatch.setattr(ci, "latest_version", lambda tool, timeout=8: "0.2.0")
    _fake_install(OBAH, "0.1.1")
    st = appimg.compute_status(OBAH)
    assert st["cargo_installed"] is True
    assert st["cargo_version"] == "0.1.1"
    assert st["cargo_has_update"] is True


# --------------------------------------------------------------------------- #
#  Git-Quelle + Systembibliotheken (XR HOTAS)
# --------------------------------------------------------------------------- #
XRH = {"key": "xr-hotas", "start_cmd": "xr-hotas", "install_methods": ["cargo"],
       "cargo_git": "https://github.com/galister/xr-hotas.git",
       "cargo_sys_deps": {"arch": ["openxr"], "fedora": ["openxr-devel"],
                          "debian": ["libopenxr-dev"], "suse": ["openxr-devel"]}}
REV = "ade190094cac9eec107c956989a13ec001e801e4"


def _fake_git_install(tool, rev=REV):
    root = ci.tool_root(tool)
    os.makedirs(os.path.join(root, "bin"), exist_ok=True)
    binp = ci.binary_path(tool)
    with open(binp, "w") as fh:
        fh.write("#!/bin/sh\n")
    os.chmod(binp, 0o755)
    with open(os.path.join(root, ".crates2.json"), "w") as fh:
        json.dump({"installs": {
            f"xr-hotas 0.1.0 (git+https://github.com/galister/xr-hotas.git#{rev})": {}}}, fh)


@pytest.mark.parametrize("lang", ["de", "en"])
def test_git_script_is_valid_bash(home, lang, tmp_path):
    script = tmp_path / "install.sh"
    script.write_text(ci.build_script(XRH, lang))
    res = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_git_script_uses_git_and_deps(home):
    s = ci.build_script(XRH, "de")
    assert "cargo install --locked --git https://github.com/galister/xr-hotas.git --force" in s
    assert "libopenxr-dev" in s and "openxr-devel" in s
    assert "1/4" in s and "4/4" in s          # Zusatzschritt Systembibliotheken
    # kein '&&' nach apt-get update — ein kaputtes Fremd-Repo darf nicht blockieren
    assert "apt-get update &&" not in s


def test_registry_script_has_three_steps(home):
    s = ci.build_script(OBAH, "de")
    assert "3/3" in s and "4/4" not in s
    assert "--git" not in s


def test_git_version_and_revision(home):
    _fake_git_install(XRH)
    assert ci.installed_version(XRH) == "0.1.0"
    assert ci.installed_revision(XRH) == REV
    assert ci.local_status(XRH) == (True, "0.1.0 · ade1900")


def test_git_update_detection(home, monkeypatch):
    _fake_git_install(XRH)
    monkeypatch.setattr(ci, "latest_revision", lambda tool, timeout=8: REV)
    assert ci.update_available(XRH) is False
    monkeypatch.setattr(ci, "latest_revision", lambda tool, timeout=8: "f" * 40)
    assert ci.update_available(XRH) is True
    # kein Netz -> kein (falsches) Update
    monkeypatch.setattr(ci, "latest_revision", lambda tool, timeout=8: "")
    assert ci.update_available(XRH) is False
