@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 build_exe.py %*
) else (
    python build_exe.py %*
)
if errorlevel 1 goto fail
start "" "%cd%\dist"
pause
exit /b 0
:fail
echo Build failed. Read the error above.
pause
exit /b 1
