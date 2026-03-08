@echo off
:: ============================================================
:: Launch Image Modification GUI
:: Run from the folder that contains support_modules\
:: ============================================================

set VENV_DIR=%~dp0.venv_image_gui

:: Create virtual-env on first run
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [Setup] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Python not found. Install Python 3.8+ and try again.
        pause
        exit /b 1
    )
    echo [Setup] Installing dependencies...
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip -q
    "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%~dp0requirements_image_gui.txt"
    if errorlevel 1 (
        echo ERROR: pip install failed. See output above.
        pause
        exit /b 1
    )
    echo [Setup] Done.
)

:: Launch the GUI
"%VENV_DIR%\Scripts\python.exe" "%~dp0support_modules\ImageModificationWindow.py"
