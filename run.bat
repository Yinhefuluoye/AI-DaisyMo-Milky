@echo off
cd /d "%~dp0"
echo Starting AI-DaisyMo...
".venv\Scripts\python.exe" DaisyMo.py
if errorlevel 1 pause