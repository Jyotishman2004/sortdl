# sortdl

Keeps your **Downloads** folder tidy, by itself. Works on Windows, macOS and Linux.

**What it does**

- Every new download goes into one folder called **`Latest`**, so your newest files are always easy to find.
- After 24 hours, each file moves into its own folder: Images, Videos, Documents and so on.
- It runs quietly in the background and starts again every time you log in.
- Nothing is ever deleted.

## Install on Windows

1. On this page, click the green **Code** button, then **Download ZIP**.
2. Right-click the ZIP file and choose **Extract All**.
3. Open the new folder and **double-click `install.bat`**, a security box will appear click on **RUN**.
4. Wait until it says `Done. sortdl is running now`. Press any key to close.

That's it. Download something and look for it in `Downloads\Latest`.

**Need Python?** sortdl runs on Python 3.8 or newer. If you don't have it, `install.bat` opens the download page for you. During the Python install, tick **Add python.exe to PATH**, then double-click `install.bat` again.

**Blue "Windows protected your PC" box?** Click **More info**, then **Run anyway**. The file is plain text, so you can open it in Notepad to see what it does.

## Install on macOS or Linux

1. Click **Code**, then **Download ZIP**, and extract it.
2. Open Terminal in that folder and run:
   ```
   python3 install.py
   ```

On Debian or Ubuntu Linux, if it asks for it, first run `sudo apt install python3-venv`.

## Where your files go

| Folder | What goes in it |
|--------|-----------------|
| `Latest` | Everything new, for the first 24 hours |
| `Images` | jpg, jpeg, png, gif, bmp, svg, webp |
| `Videos` | mp4, mkv, avi, mov, wmv, flv, webm |
| `Documents` | pdf, docx, doc, txt, xlsx, pptx, csv |
| `Music` | mp3, wav, flac, aac, m4a |
| `Archives` | zip, rar, 7z, tar, gz |
| `Installers` | exe, msi |
| `Others` | everything else |

- These folders are created inside your Downloads folder.
- If two files have the same name, the new one is renamed, like `report (1).pdf`. Nothing is overwritten.
- Files that are still downloading are left alone until they finish.
- The first time you install, files already in Downloads are handled too. Ones from the last 24 hours go to `Latest`, and older ones go straight to their folder.

## Change how long files stay in Latest

Run the installer again with the number of hours you want. On Windows, open Command Prompt in the folder (type `cmd` in the File Explorer address bar) and run one of these. On macOS and Linux, use `python3` instead of `python`.

| Command | Result |
|---------|--------|
| `python install.py --keep-hours 6` | Keep files in `Latest` for 6 hours |
| `python install.py --keep-hours 168` | Keep them for a week |
| `python install.py --keep-hours 0` | No `Latest` folder. New files are sorted right away. |

## Remove it

- **Windows:** double-click `uninstall.bat`.
- **macOS / Linux:** run `python3 install.py --uninstall`.

This stops sortdl and removes it from startup. Your files and folders stay as they are.

## Update to a new version

Download the new ZIP, extract it, and run the installer again (double-click `install.bat` on Windows). It replaces the old copy automatically, including the earlier `downloads_organizer.py` version.

## Something not working?

| Problem | What to do |
|---------|------------|
| A new download isn't in its category folder | That's normal. It's in `Latest` for 24 hours first. |
| `Latest` never appears | Run the installer again. If it still doesn't appear, end every `pythonw.exe` in Task Manager first, then run it again. |
| `install.bat` says Python was not found | Install Python from python.org and tick **Add python.exe to PATH**. |
| `'python' is not recognized` (Command Prompt) | Use `py install.py`, or reinstall Python with **Add python.exe to PATH** ticked. |
| I want to see what it did | Open `sortdl.log` in the install folder (see below). Every move is listed there. |

<details>
<summary><b>More details (optional)</b></summary>

### Where it installs

| System | Installed to | Starts at login with |
|--------|--------------|----------------------|
| Windows | `%LOCALAPPDATA%\sortdl` | a launcher in your Startup folder |
| macOS | `~/Library/Application Support/sortdl` | a LaunchAgent (`com.sortdl`) |
| Linux | `~/.local/share/sortdl` | a systemd user service, or a desktop autostart entry |

The log file `sortdl.log` is in that folder. You can delete the extracted ZIP folder after installing.

### Stop it for now

It starts again at your next login unless you uninstall.

| System | How |
|--------|-----|
| Windows | Task Manager, find `pythonw.exe`, **End task** |
| macOS | `launchctl bootout gui/$(id -u)/com.sortdl` |
| Linux | `systemctl --user stop sortdl` (or `pkill -f sortdl.py`) |

### Run it without installing

```
python sortdl.py                        run in this window, Ctrl+C to stop
python sortdl.py --keep-hours 6         same, with a 6 hour Latest
python sortdl.py --path "/some/folder"  sort a different folder
```

### How `Latest` remembers time

A small hidden file, `.sortdl_times.json`, inside `Latest` records when each file arrived. If you delete it, the timers start over. A file you drop into `Latest` yourself gets its own 24 hour timer.

### macOS permission

macOS protects the Downloads folder. If it asks for access, click **Allow**. If files aren't moving and `sortdl.log` says `Operation not permitted`, open **System Settings > Privacy & Security > Files and Folders** (or **Full Disk Access**) and allow `~/Library/Application Support/sortdl/venv/bin/python`.

### Files in this project

- `sortdl.py`: the program that sorts your files.
- `install.py`: the installer and uninstaller (all systems).
- `install.bat` and `uninstall.bat`: double-click versions for Windows.
- `README.md`: this file.

</details>
