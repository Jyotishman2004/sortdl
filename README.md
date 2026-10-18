# sortdl

Automatically sorts your **Downloads** folder into category folders on **Windows, macOS and Linux**, and keeps doing it in the background every time you log in.

- Sorts the files already in Downloads when you start it.
- Sorts new downloads as they arrive.
- Runs in the background and uses very little CPU.
- Starts by itself when you log in.

## What goes where

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

1. **Get the project.** Click the green **Code** button on GitHub, then **Download ZIP**, and extract it. Or run `git clone https://github.com/Jyotishman2004/sortdl.git`.
2. **Open a terminal in that folder.**
   - Windows: click the File Explorer address bar, type `cmd`, press Enter.
   - macOS / Linux: open Terminal and `cd` into the folder.
3. **Run the installer:**

   | System | Command |
   |--------|---------|
   | Windows | `python install.py` |
   | macOS / Linux | `python3 install.py` |

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

| System | Command |
|--------|---------|
| Windows | `python install.py --uninstall` |
| macOS / Linux | `python3 install.py --uninstall` |

This stops sortdl, removes auto-start and deletes the installed copy. Your sorted files and folders are left alone.

## Other commands

Run these from the project folder (use `python3` on macOS / Linux):

| Command | What it does |
|---------|--------------|
| `python sortdl.py` | Run in the console without installing. Press Ctrl+C to stop. |
| `python sortdl.py --path "/some/folder"` | Organize a different folder instead of Downloads. |
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
| Files aren't moving | Check `sortdl.log`. Files still downloading (`.crdownload`, `.part`) are skipped until they finish. |
| `Folder not found` | Your Downloads folder doesn't exist or is in a non-standard place. Use `--path` to point at it. |
| Installer says it can't find `sortdl.py` | Run the installer from inside the project folder, where `sortdl.py` is also located. |
| Nothing happens after a reboot (Windows) | Check that `sortdl.vbs` is in the Startup folder (Win+R, `shell:startup`). If not, run the installer again. |
| Nothing happens after a reboot (Linux) | Check `systemctl --user status sortdl`, or look for `~/.config/autostart/sortdl.desktop`. |

## Files in this project

- `sortdl.py`: the organizer. Sorts existing files, then watches Downloads for new ones.
- `install.py`: one-step installer and uninstaller for all three systems.
- `README.md`: this file.
