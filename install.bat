@echo off
rem Double-click this file to install sortdl (Windows).
cd /d "%~dp0"
title sortdl installer

where py >nul 2>nul && goto usepy
where python >nul 2>nul && goto usepython
goto nopython

:usepy
py install.py
goto done

:usepython
python install.py
goto done

:nopython
echo.
echo Python was not found on this computer.
echo.
echo 1. A download page will open. Install Python from it.
echo 2. IMPORTANT: tick "Add python.exe to PATH" on the first installer screen.
echo 3. Then double-click install.bat again.
start https://www.python.org/downloads/

:done
echo.
pause
