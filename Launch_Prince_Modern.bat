@echo off
cd /d "%~dp0"
".conda\python.exe" "%~dp0Prince_Modern.py" %*
if errorlevel 1 pause
