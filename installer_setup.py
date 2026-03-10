import os
import sys
import json
import time
import shutil
import threading
import subprocess
import eel
from tkinter import filedialog, Tk
from win32com.client import Dispatch

# ─── Module-level state ───────────────────────────────────────────────────────
_install_target_dir: str = ''       # set by _run_install, read by launch_app
_is_browsing: bool = False          # prevents concurrent browse dialogs

# ─── Paths ────────────────────────────────────────────────────────────────────
def _base() -> str:
    """Return base directory: _MEIPASS when frozen, else script dir."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def _ver() -> str:
    try:
        with open(os.path.join(_base(), 'version.json')) as f:
            return json.load(f).get('version', '?')
    except Exception:
        return '?'


# ─── Eel init ─────────────────────────────────────────────────────────────────
eel.init(os.path.join(_base(), 'installer_web'))


# ─── Exposed to JS ───────────────────────────────────────────────────────────
@eel.expose
def get_version() -> str:
    return _ver()


@eel.expose
def get_default_path() -> str:
    return os.path.join(
        os.environ.get('ProgramFiles', 'C:\\Program Files'),
        'Thunderstorm Billing'
    )


@eel.expose
def browse_install_dir() -> str:
    """Open a folder picker; guard against concurrent calls."""
    global _is_browsing
    if _is_browsing:
        return ''
    _is_browsing = True
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title='Choose install folder')
        root.destroy()
        return folder or ''
    except Exception:
        return ''
    finally:
        _is_browsing = False


@eel.expose
def cancel_install():
    """Abort the installer."""
    os._exit(0)


@eel.expose
def launch_app():
    """Launch the installed application then exit the installer."""
    global _install_target_dir
    if _install_target_dir:
        exe = os.path.join(_install_target_dir, 'Thunderstorm Billing.exe')
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe], cwd=_install_target_dir)
            except Exception as e:
                print(f'Launch error: {e}')
    os._exit(0)


@eel.expose
def start_install(target_dir: str):
    """Begin installation in a background thread."""
    threading.Thread(
        target=_run_install, args=(target_dir,), daemon=True
    ).start()


# ─── Installation worker ──────────────────────────────────────────────────────
def _run_install(target_dir: str):
    global _install_target_dir
    try:
        os.makedirs(target_dir, exist_ok=True)

        # Locate source files
        if getattr(sys, 'frozen', False):
            source = os.path.join(sys._MEIPASS, 'Thunderstorm Billing')  # type: ignore[attr-defined]
            if not os.path.exists(source):
                source = sys._MEIPASS  # type: ignore[attr-defined]
        else:
            source = r'd:\T.F.N Billing\dist\Thunderstorm Billing'

        if not os.path.isdir(source):
            eel.install_error(f'Source directory not found:\n{source}')()
            return

        # Enumerate all files
        all_files: list[str] = []
        for root, _, fnames in os.walk(source):
            for fn in fnames:
                all_files.append(os.path.join(root, fn))

        if not all_files:
            eel.install_error('No application files found to install.')()
            return

        total = len(all_files)
        last_update = 0.0          # throttle: track last JS push time

        for i, src in enumerate(all_files):
            rel  = os.path.relpath(src, source)
            dest = os.path.join(target_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)

            pct  = (i + 1) / total
            now  = time.monotonic()

            # Push UI update at most every 50 ms, always push the last file
            if (now - last_update) >= 0.05 or pct == 1.0:
                short = rel if len(rel) <= 55 else '…' + rel[-52:]
                eel.update_progress(pct, short)()
                last_update = now

        # Create desktop shortcut (non-critical)
        _create_shortcut(target_dir)

        # Store path so launch_app can use it
        _install_target_dir = target_dir
        eel.install_complete(target_dir)()

    except PermissionError as e:
        eel.install_error(
            f'Permission denied — try running the installer as Administrator.\n\nDetail: {e}'
        )()
    except OSError as e:
        eel.install_error(f'File system error:\n{e}')()
    except Exception as e:
        eel.install_error(str(e))()


def _create_shortcut(target_dir: str):
    try:
        shell   = Dispatch('WScript.Shell')
        desktop = shell.SpecialFolders('Desktop')
        lnk     = os.path.join(desktop, 'Thunderstorm Billing.lnk')
        target  = os.path.join(target_dir, 'Thunderstorm Billing.exe')
        icon    = os.path.join(target_dir, 'assets', 'logo.ico')
        sc = shell.CreateShortCut(lnk)
        sc.Targetpath       = target
        sc.WorkingDirectory = target_dir
        if os.path.exists(icon):
            sc.IconLocation = icon
        sc.save()
    except Exception as e:
        print(f'Shortcut error (non-critical): {e}')


# ─── Entry point ──────────────────────────────────────────────────────────────
_EEL_START_OPTS = dict(
    size=(820, 620),
    disable_cache=True,
    block=True,
)

if __name__ == '__main__':
    # Try Chrome first, then Edge, then fall back to system default browser.
    for mode in ('chrome', 'edge', 'default'):
        try:
            eel.start('installer.html', mode=mode, **_EEL_START_OPTS)
            break                       # success — stop trying
        except EnvironmentError:
            if mode == 'default':
                raise                   # nothing left to try
            print(f'Browser mode "{mode}" unavailable, trying next…')
        except SystemExit:
            break                       # normal window close
