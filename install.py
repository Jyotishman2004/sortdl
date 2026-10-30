"""One-step installer for sortdl (Windows, macOS, Linux).

Keep this file in the same folder as sortdl.py, then run:
    python install.py              install + start now      (python3 on macOS/Linux)
    python install.py --uninstall  stop, remove auto-start and installed files
    python install.py --keep-hours 6   keep new downloads in "Latest" for 6 hours
                                       (default 24, 0 = no Latest folder)

What install does:
  1. copies sortdl.py to a per-user folder (see INSTALL_DIR below)
  2. creates a private virtual environment there and installs watchdog into it
  3. stops any older copy that is already running
  4. registers it to start automatically at login
  5. starts it right now, which also sweeps your existing downloads
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path

SCRIPT_NAME = "sortdl.py"
LEGACY_SCRIPT = "downloads_organizer.py"  # name used by the very first (Windows-only) version
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"


def install_dir() -> Path:
    if IS_WIN:
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "sortdl"
    if IS_MAC:
        return Path.home() / "Library/Application Support/sortdl"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "sortdl"


def venv_python(base: Path) -> Path:
    return base / "venv" / ("Scripts/python.exe" if IS_WIN else "bin/python")


def stop_running_copies(target: Path) -> None:
    try:
        if IS_WIN:
            ps = (
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.Name -match '^pythonw?\\.exe$' -and "
                f"($_.CommandLine -like '*{SCRIPT_NAME}*' -or "
                f"$_.CommandLine -like '*{LEGACY_SCRIPT}*') }} | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, check=False)
        else:
            subprocess.run(["pkill", "-f", re.escape(str(target))],
                           capture_output=True, check=False)
    except OSError:
        pass  # pkill/powershell missing - the single-instance guard still protects us


def remove_legacy() -> None:
    """Windows: remove the auto-start entry and folder of the very first version."""
    if not IS_WIN:
        return
    appdata, local = os.environ.get("APPDATA"), os.environ.get("LOCALAPPDATA")
    if appdata:
        (Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup"
         / "DownloadsOrganizer.vbs").unlink(missing_ok=True)
    if local:
        shutil.rmtree(Path(local) / "DownloadsOrganizer", ignore_errors=True)


def install(keep_hours: float) -> None:
    source = Path(__file__).resolve().with_name(SCRIPT_NAME)
    if not source.exists():
        sys.exit(f"Can't find {SCRIPT_NAME} next to this installer ({source.parent}).")

    base = install_dir()
    target = base / SCRIPT_NAME
    vpy = venv_python(base)

    print("[1/5] Stopping any older copy...")
    if target.exists():  # let the old copy unregister itself cleanly
        subprocess.run([str(vpy) if vpy.exists() else sys.executable, str(target),
                        "--uninstall-startup"], capture_output=True, check=False)
    stop_running_copies(target)
    remove_legacy()

    print(f"[2/5] Copying {SCRIPT_NAME} to {base} ...")
    base.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

    print("[3/5] Creating a private Python environment...")
    if not vpy.exists():
        try:
            venv.create(base / "venv", with_pip=True)
        except Exception as e:
            hint = "\nOn Debian/Ubuntu run: sudo apt install python3-venv" if not (IS_WIN or IS_MAC) else ""
            sys.exit(f"Could not create the virtual environment: {e}{hint}")

    print("[4/5] Installing watchdog...")
    subprocess.check_call([str(vpy), "-m", "pip", "install", "--disable-pip-version-check",
                           "-q", "watchdog"])

    print("[5/5] Registering auto-start and starting sortdl...")
    subprocess.check_call([str(vpy), str(target), "--install-startup",
                           "--keep-hours", f"{keep_hours:g}"])

    print("\nDone. sortdl is running now and will start automatically at every login.")
    print(f"Log file: {base / 'sortdl.log'}")
    print("You can delete the original download; the installed copy is self-contained.")


def uninstall() -> None:
    base = install_dir()
    target = base / SCRIPT_NAME
    vpy = venv_python(base)
    print("Stopping sortdl...")
    if target.exists():
        subprocess.run([str(vpy) if vpy.exists() else sys.executable, str(target),
                        "--uninstall-startup"], check=False)
    stop_running_copies(target)
    shutil.rmtree(base, ignore_errors=True)
    print("Uninstalled. Your sorted folders and files were left untouched.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Install sortdl.")
    ap.add_argument("--uninstall", action="store_true", help="remove it completely")
    ap.add_argument("--keep-hours", type=float, default=24.0,
                    help="hours new downloads stay in the Latest folder before being "
                         "sorted (default 24; 0 = sort immediately)")
    args = ap.parse_args()
    if args.keep_hours < 0:
        ap.error("--keep-hours must be 0 or more")
    uninstall() if args.uninstall else install(args.keep_hours)


if __name__ == "__main__":
    main()
