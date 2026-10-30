# sortdl

Automatically sorts your **Downloads** folder into category folders on **Windows, macOS and Linux**, and keeps doing it in the background every time you log in.

- Puts every new download in one **`Latest`** folder, so you never have to dig through category folders for something you just downloaded.
- After 24 hours (you can change this), moves each file from `Latest` into its category folder.
- Sorts the files already in Downloads when you start it.
- Runs in the background and uses very little CPU.
- Starts by itself when you log in.

## How the `Latest` folder works

1. You download a file. A moment later sortdl moves it into `Downloads/Latest`.
2. It stays there for **24 hours**, so everything from the last day is in one place.
3. After that, sortdl moves it into its category folder (table below). Nothing is deleted.

Files already in Downloads when sortdl first starts are handled the same way: anything changed in the last 24 hours goes to `Latest`, and older files are sorted straight into their category folders.

You can change the time when you install:

| Command | Effect |
|---------|--------|
| `python install.py` | Keep new downloads in `Latest` for 24 hours (default). |
| `python install.py --keep-hours 6` | Keep them for 6 hours. Decimals work too, like `0.5` for 30 minutes. |
| `python install.py --keep-hours 168` | Keep them for a week. |
| `python install.py --keep-hours 0` | Turn `Latest` off. New files are sorted immediately. |

(Use `python3` on macOS / Linux.) To change the time later, just run the installer again with a new value. If you drop a file into `Latest` yourself, it gets its own 24-hour timer. sortdl keeps a small hidden file in `Latest` (`.sortdl_times.json`) to remember when each file arrived. Don't delete it unless you don't mind the timers restarting.

## What goes where

After their time in `Latest`, files are sorted like this:

| Folder        | File types |
|---------------|------------|
| `Images`      | jpg, jpeg, png, gif, bmp, svg, webp |
| `Videos`      | mp4, mkv, avi, mov, wmv, flv, webm |
| `Documents`   | pdf, docx, doc, txt, xlsx, pptx, csv |
| `Music`       | mp3, wav, flac, aac, m4a |
| `Archives`    | zip, rar, 7z, tar, gz |
| `Installers`  | exe, msi |
| `Others`      | everything else, including files with no extension |

The folders are created inside your Downloads folder. If a file with the same name is already in the destination, the new one is renamed (`report (1).pdf`) and nothing is overwritten. Half-finished downloads (`.crdownload`, `.part`, `.tmp`) and hidden files are left alone until they're complete.

## Requirements

- **Python 3.8 or newer**
  - Windows: install from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH**.
  - macOS: install from python.org or with Homebrew (`brew install python`).
  - Linux: usually preinstalled. On Debian/Ubuntu you also need `sudo apt install python3-venv`.

`watchdog` (a file-watching library) is installed automatically into a private environment during setup, so nothing is installed system-wide.

## Setup (one time)

### Windows: two clicks

1. **Get the project.** Click the green **Code** button on GitHub, then **Download ZIP**. Right-click the ZIP and choose **Extract All** (do not run it from inside the ZIP).
2. **Double-click `install.bat`** in the extracted folder.

A window shows the progress and finishes with `Done. sortdl is running now...`. Press any key to close it. If Windows shows a blue "Windows protected your PC" box, click **More info**, then **Run anyway**. The file is plain text, so you can open it in Notepad to check what it does.

If it says Python was not found, install Python from the page it opens (tick **Add python.exe to PATH**), then double-click `install.bat` again.

### macOS and Linux

1. **Get the project.** Download the ZIP and extract it, or run `git clone https://github.com/Jyotishman2004/sortdl.git`.
2. **Open Terminal in that folder** (`cd` into it) and run:
   ```
   python3 install.py
   ```

### Windows from the command line (optional)

If you prefer a terminal: click the File Explorer address bar, type `cmd`, press Enter, and run `python install.py`.

The installer:
1. stops any older copy that's running,
2. copies `sortdl.py` to a per-user folder (table below),
3. creates a private Python environment there and installs `watchdog`,
4. sets sortdl to start automatically at login,
5. starts it now, which also sorts everything already in Downloads.

You can delete the downloaded folder afterwards. The installed copy is self-contained.

| System | Installed to | Starts at login via |
|--------|--------------|---------------------|
| Windows | `%LOCALAPPDATA%\sortdl` | a launcher in your Startup folder |
| macOS | `~/Library/Application Support/sortdl` | a LaunchAgent (`~/Library/LaunchAgents/com.sortdl.plist`) |
| Linux | `~/.local/share/sortdl` | a systemd user service, or a desktop autostart entry if systemd isn't available |

## Checking that it works

- Download any file. It should move into its category folder within a few seconds.
- Open the log file (`sortdl.log`) in the install folder from the table above. Every move is recorded there with a timestamp.

## Uninstall

Run this from the project folder:

| System | How |
|--------|-----|
| Windows | Double-click `uninstall.bat` |
| macOS / Linux | `python3 install.py --uninstall` |

This stops sortdl, removes auto-start and deletes the installed copy. Your sorted files and folders are left alone.

## Other commands

Run these from the project folder (use `python3` on macOS / Linux):

| Command | What it does |
|---------|--------------|
| `python sortdl.py` | Run in the console without installing. Press Ctrl+C to stop. |
| `python sortdl.py --path "/some/folder"` | Organize a different folder instead of Downloads. |
| `python sortdl.py --keep-hours 6` | Keep new downloads in `Latest` for 6 hours (`0` = sort immediately). |
| `python sortdl.py --install-startup` | Register auto-start and start now (uses the Python you ran it with, so use `install.py` for normal setup). |
| `python sortdl.py --uninstall-startup` | Remove auto-start. |

## Stopping it temporarily

| System | How |
|--------|-----|
| Windows | Task Manager > find `pythonw.exe` > **End task** |
| macOS | `launchctl bootout gui/$(id -u)/com.sortdl` |
| Linux | `systemctl --user stop sortdl` (or `pkill -f sortdl.py` if you're using the autostart fallback) |

It starts again at your next login unless you uninstall it.

## Notes for macOS

macOS protects the Downloads folder. The first time sortdl runs you may see a prompt asking to allow access to Downloads. Click **Allow**. If files aren't moving and the log shows `Operation not permitted`, open **System Settings > Privacy & Security > Files and Folders** (or **Full Disk Access**) and allow the Python used by sortdl: `~/Library/Application Support/sortdl/venv/bin/python`.

## Updating to a newer version

Download the new files and run the installer again (double-click `install.bat` on Windows, or run `python3 install.py` on macOS / Linux). It replaces the old copy and keeps your settings only if you pass them again, such as `--keep-hours 6`.

## Upgrading from the earlier Windows-only version

If you set up the earlier `downloads_organizer.py` version, remove it first so two copies don't run:

1. Press **Win+R**, type `shell:startup`, press Enter, and delete `DownloadsOrganizer.vbs`.
2. Delete the folder `%LOCALAPPDATA%\DownloadsOrganizer`.
3. End any `pythonw.exe` process in Task Manager.

Then follow the setup steps above.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `'python' is not recognized` (Windows) | Reinstall Python and tick **Add python.exe to PATH**, or use `py install.py`. |
| `Could not create the virtual environment` (Linux) | Run `sudo apt install python3-venv`, then run the installer again. |
| `sortdl is already running - exiting.` in the log | Normal. Only one copy runs at a time. |
| A new download isn't in its category folder | That's expected: it's in `Latest` until its time is up (24 hours by default). |
| I want files sorted immediately | Run the installer with `--keep-hours 0`. |
| Files aren't moving | Check `sortdl.log`. Files still downloading (`.crdownload`, `.part`) are skipped until they finish. |
| `Folder not found` | Your Downloads folder doesn't exist or is in a non-standard place. Use `--path` to point at it. |
| Installer says it can't find `sortdl.py` | Run the installer from inside the project folder, where `sortdl.py` is also located. |
| Nothing happens after a reboot (Windows) | Check that `sortdl.vbs` is in the Startup folder (Win+R, `shell:startup`). If not, run the installer again. |
| Nothing happens after a reboot (Linux) | Check `systemctl --user status sortdl`, or look for `~/.config/autostart/sortdl.desktop`. |

## Files in this project

- `sortdl.py`: the organizer. Sorts existing files, then watches Downloads for new ones.
- `install.py`: one-step installer and uninstaller for all three systems.
- `install.bat` / `uninstall.bat`: double-click versions of the installer and uninstaller for Windows.
- `README.md`: this file.
