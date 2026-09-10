@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" DaisyMo.py
    goto END
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python DaisyMo.py
    goto END
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 DaisyMo.py
    goto END
)

echo [Error] Python not found. Please install Python 3.10+ from https://www.python.org/
pause
exit /b 1

:END
if errorlevel 1 pause

