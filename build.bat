@echo off
chcp 65001 >nul
title AI-DaisyMo Release 打包构建器
cd /d "%~dp0"

echo ===================================================
echo        AI-DaisyMo Release 一键打包构建
echo ===================================================

if exist ".venv\Scripts\python.exe" (
    set "PY_BIN=.venv\Scripts\python.exe"
) else (
    set "PY_BIN=python"
)

%PY_BIN% scripts/build_release.py
if errorlevel 1 (
    echo.
    echo [构建失败] 请检查上方错误输出。
    pause
    exit /b 1
)

echo.
echo [构建成功] 产物已生成在 dist 目录下！
pause
