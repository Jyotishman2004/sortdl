"""sortdl - sorts your Downloads folder into category folders (Windows, macOS, Linux).

1. On startup, sweeps the files already in Downloads: recent ones go to "Latest",
   older ones go straight into their category folder.
2. Then watches Downloads (via watchdog). New files land in "Latest" and stay there
   for a while (default 24 hours) before being moved into their category folder.

Usage:
    python sortdl.py                      run in the console (Ctrl+C to stop)
    python sortdl.py --keep-hours 6       keep new downloads in "Latest" for 6 hours
    python sortdl.py --keep-hours 0       no "Latest" folder: sort new files immediately
    python sortdl.py --install-startup    start automatically at login, and start now
    python sortdl.py --uninstall-startup  remove auto-start
    python sortdl.py --path "/some/folder"  organize a different folder

For a one-step setup (virtual environment, watchdog, auto-start) use install.py.
"""
import argparse
import importlib
import json
import logging
import os
import plistlib
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("watchdog not found - installing it...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "watchdog"])
    importlib.invalidate_caches()
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
SELF = Path(__file__).resolve()

CATEGORIES = {
    "Images": {"jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"},
    "Videos": {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm"},
    "Documents": {"pdf", "docx", "doc", "txt", "xlsx", "pptx", "csv"},
    "Music": {"mp3", "wav", "flac", "aac", "m4a"},
    "Archives": {"zip", "rar", "7z", "tar", "gz"},
    "Installers": {"exe", "msi"},
}
OTHERS = "Others"
LATEST = "Latest"                      # holds new downloads for a while
STATE_FILE = SELF.with_name("sortdl_state.json")  # when each file arrived in Latest
LEGACY_STATE_NAME = ".sortdl_times.json"          # older versions kept this inside Latest
DEFAULT_KEEP_HOURS = 24.0

# Browsers write to these while a download is in progress; skip until renamed.
TEMP_SUFFIXES = {".crdownload", ".part", ".tmp", ".download", ".partial", ".opdownload"}

SETTLE_SECONDS = 1.0       # initial wait for a new file
MAX_WAIT_SECONDS = 600     # give up waiting on a file that keeps changing/locked
EXPIRY_CHECK_SECONDS = 60  # how often Latest is checked for files that are due
STARTUP_NAME = "sortdl.vbs"            # Windows Startup-folder launcher
LAUNCH_LABEL = "com.sortdl"            # macOS LaunchAgent label
UNIT_NAME = "sortdl.service"           # Linux systemd user unit
INSTANCE_PORT = 47653      # local port held open to ensure only one copy runs

log = logging.getLogger("sortdl")
_state_lock = threading.Lock()


def get_downloads_folder() -> Path:
    """Locate the Downloads folder without hardcoding the username.

    Windows: Known Folder API (handles a relocated Downloads folder).
    Linux:   XDG user-dirs setting.
    Otherwise (and as fallback): ~/Downloads.
    """
    if IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            # FOLDERID_Downloads {374DE290-123F-4565-9164-39C4925E467B}
            guid = GUID(0x374DE290, 0x123F, 0x4565,
                        (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
            buf = ctypes.c_wchar_p()
            res = ctypes.windll.shell32.SHGetKnownFolderPath(
                ctypes.byref(guid), 0, None, ctypes.byref(buf))
            if res == 0 and buf.value:
                path = Path(buf.value)
                ctypes.windll.ole32.CoTaskMemFree(buf)
                return path
        except Exception:
            pass
    elif not IS_MAC:
        try:
            cfg = _config_home() / "user-dirs.dirs"
            for line in cfg.read_text(encoding="utf-8").splitlines():
                if line.startswith("XDG_DOWNLOAD_DIR="):
                    value = line.split("=", 1)[1].strip().strip('"')
                    return Path(value.replace("$HOME", str(Path.home())))
        except OSError:
            pass
    return Path.home() / "Downloads"


def category_for(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    for folder, exts in CATEGORIES.items():
        if ext in exts:
            return folder
    return OTHERS


def unique_destination(dest_dir: Path, name: str) -> Path:
    """Return dest_dir/name, or 'name (1).ext', 'name (2).ext'... if taken."""
    candidate = dest_dir / name
    if not candidate.exists():
        return candidate
    stem, suffix = Path(name).stem, Path(name).suffix
    n = 1
    while True:
        candidate = dest_dir / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def is_temp(path: Path) -> bool:
    return path.suffix.lower() in TEMP_SUFFIXES


def wait_until_ready(path: Path) -> bool:
    """Wait 1s, then until the file stops growing and can be opened.

    Returns False if the file vanished or never became ready.
    """
    time.sleep(SETTLE_SECONDS)
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    last_size = -1
    while time.monotonic() < deadline:
        try:
            size = path.stat().st_size
            if size == last_size:
                with open(path, "ab"):  # fails with PermissionError if still locked
                    pass
                return True
            last_size = size
        except FileNotFoundError:
            return False
        except OSError:
            pass
        time.sleep(1)
    return False


def move_file(path: Path, root: Path) -> None:
    """Move a file into its category folder."""
    dest_dir = root / category_for(path)
    try:
        dest_dir.mkdir(exist_ok=True)
        dest = unique_destination(dest_dir, path.name)
        shutil.move(str(path), str(dest))
        log.info("Moved: %s -> %s", path.name, dest.relative_to(root))
    except FileNotFoundError:
        pass  # file disappeared (e.g. browser renamed it) - nothing to do
    except OSError as e:
        log.warning("Could not move %s: %s", path.name, e)


# ------------------------------------------------------------ "Latest" folder

def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _load_state(root: Path) -> dict:
    """Arrival times (file name -> epoch seconds) for the files in root/Latest.

    Kept next to sortdl.py, not in Downloads, so no extra files show up there.
    """
    state = _read_json(STATE_FILE).get(str(root))
    state = state if isinstance(state, dict) else {}
    legacy = root / LATEST / LEGACY_STATE_NAME
    if legacy.exists():  # older versions kept the times inside Latest: import and remove
        for name, arrived in _read_json(legacy).items():
            state.setdefault(name, arrived)
        _save_state(root, state)
        try:
            legacy.unlink()
        except OSError:
            pass
    return state


def _save_state(root: Path, state: dict) -> None:
    data = _read_json(STATE_FILE)
    if state:
        data[str(root)] = state
    else:
        data.pop(str(root), None)
    try:
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, STATE_FILE)
    except OSError:
        pass


def move_to_latest(path: Path, root: Path, arrived=None) -> None:
    """Move a file into Latest and remember when it arrived (default: now)."""
    dest_dir = root / LATEST
    try:
        dest_dir.mkdir(exist_ok=True)
        dest = unique_destination(dest_dir, path.name)
        shutil.move(str(path), str(dest))
    except FileNotFoundError:
        return
    except OSError as e:
        log.warning("Could not move %s: %s", path.name, e)
        return
    with _state_lock:
        state = _load_state(root)
        state[dest.name] = time.time() if arrived is None else arrived
        _save_state(root, state)
    log.info("Moved: %s -> %s", path.name, dest.relative_to(root))


def expire_latest(root: Path, keep_seconds: float) -> None:
    """Move files that have been in Latest long enough into their category folder."""
    folder = root / LATEST
    if not folder.is_dir():
        return
    now = time.time()
    with _state_lock:
        state = _load_state(root)
        present = {}
        for entry in sorted(folder.iterdir()):
            if entry.name.startswith(".") or not entry.is_file():
                continue
            # A file dropped in by hand (or lost state) starts its clock now.
            arrived = state.get(entry.name, now)
            if now - arrived >= keep_seconds:
                move_file(entry, root)
                if not entry.exists():
                    continue
            present[entry.name] = arrived  # not due yet, or the move failed: retry later
        if present != state:
            _save_state(root, present)


def is_candidate(path: Path, root: Path) -> bool:
    """Only loose files directly inside root; ignore our folders, temp and hidden files."""
    try:
        if path.parent != root or not path.is_file():
            return False
    except OSError:
        return False
    if path.resolve() == SELF or is_temp(path):
        return False
    if path.name.startswith(".") or path.name.lower() == "desktop.ini":
        return False
    return True


def initial_sweep(root: Path, keep_seconds: float) -> None:
    log.info("Sweeping existing files in %s ...", root)
    count = 0
    now = time.time()
    for entry in sorted(root.iterdir()):
        if not is_candidate(entry, root):
            continue
        try:
            modified = entry.stat().st_mtime
        except OSError:
            continue
        if keep_seconds > 0 and now - modified < keep_seconds:
            move_to_latest(entry, root, arrived=min(modified, now))
        else:
            move_file(entry, root)
        count += 1
    log.info("Initial sweep done (%d file(s) moved).", count)


class Handler(FileSystemEventHandler):
    def __init__(self, root: Path, keep_seconds: float):
        self.root = root
        self.keep_seconds = keep_seconds
        self._pending = set()
        self._lock = threading.Lock()

    def _schedule(self, p):
        path = Path(p)
        if not is_candidate(path, self.root):
            return
        with self._lock:
            if path in self._pending:
                return
            self._pending.add(path)
        threading.Thread(target=self._process, args=(path,), daemon=True).start()

    def _process(self, path: Path):
        try:
            if wait_until_ready(path) and path.exists():
                if self.keep_seconds > 0:
                    move_to_latest(path, self.root)
                else:
                    move_file(path, self.root)
        finally:
            with self._lock:
                self._pending.discard(path)

    def on_created(self, event):
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_moved(self, event):  # e.g. report.pdf.crdownload -> report.pdf
        if not event.is_directory:
            self._schedule(event.dest_path)


# ---------------------------------------------------------------- auto-start

def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def _startup_python() -> str:
    exe = Path(sys.executable)
    if IS_WIN and exe.with_name("pythonw.exe").exists():
        return str(exe.with_name("pythonw.exe"))  # no console window
    return str(exe)


def _launch_args(keep_hours: float) -> list:
    """Extra command-line arguments to bake into the auto-start entry."""
    return [] if keep_hours == DEFAULT_KEEP_HOURS else ["--keep-hours", f"{keep_hours:g}"]


def _run(cmd) -> int:
    try:
        return subprocess.run(cmd, capture_output=True).returncode
    except OSError:
        return 127


def start_now(extra=()) -> None:
    """Launch a detached background copy of this script."""
    kwargs = dict(cwd=str(SELF.parent), stdin=subprocess.DEVNULL,
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if IS_WIN:
        kwargs["creationflags"] = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([_startup_python(), str(SELF), *extra], **kwargs)


def _win_startup_file() -> Path:
    appdata = os.environ["APPDATA"]
    return Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup" / STARTUP_NAME


def _mac_plist() -> Path:
    return Path.home() / "Library/LaunchAgents" / f"{LAUNCH_LABEL}.plist"


def _systemd_unit() -> Path:
    return _config_home() / "systemd/user" / UNIT_NAME


def _autostart_file() -> Path:
    return _config_home() / "autostart/sortdl.desktop"


def install_startup(keep_hours: float = DEFAULT_KEEP_HOURS) -> None:
    py = _startup_python()
    extra = _launch_args(keep_hours)
    tail = "".join(f" {a}" for a in extra)
    if IS_WIN:
        # .vbs launches with no console window
        vbs = f'CreateObject("WScript.Shell").Run """{py}"" ""{SELF}""{tail}", 0, False\r\n'
        target = _win_startup_file()
        target.write_text(vbs, encoding="utf-8")
        start_now(extra)
        print(f"Installed. sortdl is running and will start at every login:\n  {target}")
    elif IS_MAC:
        plist = _mac_plist()
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_bytes(plistlib.dumps({
            "Label": LAUNCH_LABEL,
            "ProgramArguments": [py, str(SELF), *extra],
            "WorkingDirectory": str(SELF.parent),
            "RunAtLoad": True,
            "KeepAlive": {"SuccessfulExit": False},  # restart only after a crash
        }))
        domain = f"gui/{os.getuid()}"
        _run(["launchctl", "bootout", f"{domain}/{LAUNCH_LABEL}"])  # replace an older copy
        if _run(["launchctl", "bootstrap", domain, str(plist)]) != 0:
            start_now(extra)
        print(f"Installed. sortdl is running and will start at every login:\n  {plist}")
    else:
        unit = _systemd_unit()
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text(
            "[Unit]\nDescription=sortdl - Downloads folder organizer\n\n"
            f'[Service]\nExecStart="{py}" "{SELF}"{tail}\nRestart=on-failure\nRestartSec=10\n\n'
            "[Install]\nWantedBy=default.target\n", encoding="utf-8")
        if (_run(["systemctl", "--user", "daemon-reload"]) == 0
                and _run(["systemctl", "--user", "enable", "--now", UNIT_NAME]) == 0):
            print(f"Installed. sortdl is running and will start at every login:\n  {unit}")
            return
        # No systemd user session available: fall back to a desktop autostart entry.
        unit.unlink(missing_ok=True)
        desktop = _autostart_file()
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(
            "[Desktop Entry]\nType=Application\nName=sortdl\n"
            f'Exec="{py}" "{SELF}"{tail}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n',
            encoding="utf-8")
        start_now(extra)
        print(f"Installed. sortdl is running and will start at every login:\n  {desktop}")


def uninstall_startup() -> None:
    if IS_WIN:
        target = _win_startup_file()
        removed = target.exists()
        target.unlink(missing_ok=True)
    elif IS_MAC:
        plist = _mac_plist()
        removed = plist.exists()
        _run(["launchctl", "bootout", f"gui/{os.getuid()}/{LAUNCH_LABEL}"])
        plist.unlink(missing_ok=True)
    else:
        unit, desktop = _systemd_unit(), _autostart_file()
        removed = unit.exists() or desktop.exists()
        if unit.exists():
            _run(["systemctl", "--user", "disable", "--now", UNIT_NAME])
            unit.unlink(missing_ok=True)
            _run(["systemctl", "--user", "daemon-reload"])
        desktop.unlink(missing_ok=True)
    print("Auto-start removed." if removed else "Auto-start was not installed.")


# ---------------------------------------------------------------------- main

def setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s  %(message)s", "%Y-%m-%d %H:%M:%S")
    log.setLevel(logging.INFO)
    if sys.stdout is not None:  # pythonw has no stdout
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(fmt)
        log.addHandler(h)
    try:
        fh = logging.FileHandler(SELF.with_name("sortdl.log"), encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError:
        pass


def non_negative_float(text: str) -> float:
    value = float(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be 0 or more")
    return value


def main() -> None:
    ap = argparse.ArgumentParser(description="Organize the Downloads folder automatically.")
    ap.add_argument("--path", type=Path, help="folder to organize (default: your Downloads)")
    ap.add_argument("--keep-hours", type=non_negative_float, default=DEFAULT_KEEP_HOURS,
                    help=f"hours new downloads stay in '{LATEST}' before being sorted "
                         f"(default {DEFAULT_KEEP_HOURS:g}; 0 = sort immediately)")
    ap.add_argument("--install-startup", action="store_true",
                    help="start automatically at login (and start now)")
    ap.add_argument("--uninstall-startup", action="store_true", help="remove the auto-start entry")
    args = ap.parse_args()

    if args.install_startup:
        return install_startup(args.keep_hours)
    if args.uninstall_startup:
        return uninstall_startup()

    root = (args.path or get_downloads_folder()).resolve()
    if not root.is_dir():
        sys.exit(f"Folder not found: {root}")
    keep_seconds = args.keep_hours * 3600

    setup_logging()

    # Single-instance guard: a second copy would fight over the same files.
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", INSTANCE_PORT))
    except OSError:
        log.info("sortdl is already running - exiting.")
        return
    if keep_seconds > 0:
        log.info("sortdl started. Watching: %s (new files stay in %s for %g hour(s))",
                 root, LATEST, args.keep_hours)
    else:
        log.info("sortdl started. Watching: %s", root)

    initial_sweep(root, keep_seconds)

    observer = Observer()
    observer.schedule(Handler(root, keep_seconds), str(root), recursive=False)
    observer.start()
    check_every = min(EXPIRY_CHECK_SECONDS, max(1.0, keep_seconds / 2))
    last_check = float("-inf")
    try:
        while observer.is_alive():
            observer.join(timeout=1)
            if time.monotonic() - last_check >= check_every:
                expire_latest(root, keep_seconds)  # with 0 hours this also empties Latest
                last_check = time.monotonic()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
