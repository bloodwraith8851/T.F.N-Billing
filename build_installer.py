"""
build_installer.py  —  T.F.N Billing v2.2.0 Build Script
========================================================
Builds the main application bundle (launcher.spec) then
packages it into a single-file installer EXE.

Usage:
    python build_installer.py
"""

import os
import subprocess
import shutil
import sys
import json

# ── Helpers ──────────────────────────────────────────────────────────────────

def _version() -> str:
    try:
        with open("version.json") as f:
            return json.load(f).get("version", "?")
    except Exception:
        return "?"

def _run(cmd: list, label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    subprocess.run(cmd, check=True)

# ── Step 1 — Main application ────────────────────────────────────────────────

def build_app():
    """Compile launcher.py + web/ + assets/ into dist/Thunderstorm Billing/"""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=Thunderstorm Billing",
        "--add-data=web;web",
        "--add-data=assets;assets",
        "--add-data=version.json;.",
        "--hidden-import=eel",
        "--hidden-import=bottle",
        "--hidden-import=bottle_websocket",
        "--hidden-import=geventwebsocket",
        "--hidden-import=gevent",
        "--hidden-import=reportlab",
        "--hidden-import=PIL",
        "launcher.py"
    ]
    if os.path.exists(os.path.join("assets", "logo.ico")):
        cmd.insert(-1, "--icon=assets/logo.ico")
        
    _run(cmd, "Building main application...")
    print("[OK] Application built  -->  dist/Thunderstorm Billing/")

# ── Step 2 — Installer EXE ─────────────────────────────────────────────────

def build_installer():
    """Package dist/payload.zip + installer_web into a single Setup EXE."""
    dist_path = os.path.join("dist", "Thunderstorm Billing")
    if not os.path.isdir(dist_path):
        print(f"ERROR: {dist_path!r} not found — run build_app() first.")
        sys.exit(1)
        
    print("Compressing application bundle into payload.zip...")
    archive_base = os.path.join("dist", "payload")
    shutil.make_archive(archive_base, 'zip', dist_path)
    payload_zip = archive_base + ".zip"

    ver = _version()
    out_name = f"Thunderstorm_Billing_v{ver}_Setup"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        # ── bundled data ──
        f"--add-data={payload_zip};payload",              # zipped app bundle
        "--add-data=installer_web;installer_web",         # installer UI (HTML/CSS/JS)
        "--add-data=version.json;.",                      # for version label in installer
        # ── hidden imports (eel + win32com) ──
        "--hidden-import=eel",
        "--hidden-import=bottle",
        "--hidden-import=bottle_websocket",
        "--hidden-import=geventwebsocket",
        "--hidden-import=gevent",
        "--hidden-import=whichcraft",
        "--hidden-import=win32com",
        "--hidden-import=win32com.client",
        "--hidden-import=pythoncom",
        "--hidden-import=pywintypes",
        # ── output ──
        f"--name={out_name}",
        "installer_setup.py",
    ]

    # Bundle existing icon if available
    if os.path.exists(os.path.join("assets", "logo.ico")):
        cmd.insert(-1, "--icon=assets/logo.ico")

    # Optionally pre-seed settings so first-run has correct defaults
    if os.path.exists("settings.json"):
        cmd.insert(-1, "--add-data=settings.json;.")

    _run(cmd, f"Building installer EXE  (v{ver})...")
    print(f"[OK] Installer built  -->  dist/{out_name}.exe")

# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        # Verify PyInstaller is available
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            check=True, capture_output=True
        )

        build_app()
        build_installer()

        ver = _version()
        print(f"\n{'='*60}")
        print(f"  BUILD COMPLETE -- T.F.N Billing v{ver}")
        print(f"  Installer: dist/Thunderstorm_Billing_v{ver}_Setup.exe")
        print(f"{'='*60}\n")

    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
