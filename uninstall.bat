@echo off
rem Double-click this file to remove sortdl (Windows).
cd /d "%~dp0"
title sortdl uninstaller

where py >nul 2>nul && goto usepy
where python >nul 2>nul && goto usepython
goto nopython

:usepy
py install.py --uninstall
goto done

:usepython
python install.py --uninstall
goto done

:nopython
echo.
echo Python was not found, so sortdl cannot be uninstalled with this file.
echo Open Task Manager, end "pythonw.exe", then delete sortdl.vbs from the
echo Startup folder (press Win+R, type shell:startup, press Enter).

:done
echo.
pause
