@echo off
echo Clearing Python cache files...
cd /d "c:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion"

:: Delete all __pycache__ directories
for /d /r %%i in (__pycache__) do (
    if exist "%%i" (
        echo Deleting: %%i
        rd /s /q "%%i"
    )
)

:: Delete all .pyc files
for /r %%i in (*.pyc) do (
    if exist "%%i" (
        echo Deleting: %%i
        del /q "%%i"
    )
)

:: Delete all .pyo files
for /r %%i in (*.pyo) do (
    if exist "%%i" (
        echo Deleting: %%i
        del /q "%%i"
    )
)

echo.
echo Python cache cleared!
echo Please restart your Python application now.
pause
