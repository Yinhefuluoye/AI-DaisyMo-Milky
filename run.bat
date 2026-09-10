@echo off
chcp 65001 >nul
title AI-DaisyMo (AI墨小菊)
cd /d "%~dp0"

echo ===================================================
echo           AI-DaisyMo (AI墨小菊) 启动器
echo ===================================================

:: 1. 优先使用本地已存在的虚拟环境
if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
    goto RUN_APP
)

:: 2. 检测系统中的 Python
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_SYSTEM=python"
    goto CHECK_ENV
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_SYSTEM=py -3"
    goto CHECK_ENV
)

:: 3. 未找到任何 Python
echo [错误] 未检测到 Python 环境！
echo 请先安装 Python 3.10 或更高版本：https://www.python.org/downloads/
echo 注意：安装时请务必勾选 "Add python.exe to PATH"（添加到系统环境变量）！
echo.
pause
exit /b 1

:CHECK_ENV
echo [提示] 检测到系统 Python，正在检查运行依赖...
%PY_SYSTEM% -c "import pygame, requests, cv2" >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=%PY_SYSTEM%"
    goto RUN_APP
)

echo [提示] 首次运行尚未安装依赖，正在为您自动创建 .venv 虚拟环境...
%PY_SYSTEM% -m venv .venv
if %errorlevel% neq 0 (
    echo [警告] 创建虚拟环境失败，尝试直接使用系统 Python 安装依赖...
    set "PIP_CMD=%PY_SYSTEM% -m pip"
    set "PY_CMD=%PY_SYSTEM%"
) else (
    set "PIP_CMD=.venv\Scripts\python.exe -m pip"
    set "PY_CMD=.venv\Scripts\python.exe"
)

echo [提示] 正在从清华镜像源高速安装必要运行依赖 (pygame, requests, opencv-python)...
%PIP_CMD% install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败，请检查网络或手动执行: pip install -r requirements.txt
    pause
    exit /b 1
)

:RUN_APP
echo [提示] 正在启动 AI-DaisyMo...
echo.
%PY_CMD% DaisyMo.py
if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序非正常退出 (退出码: %errorlevel%)
    pause
)