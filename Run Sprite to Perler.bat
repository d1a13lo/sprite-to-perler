@echo off
rem Opens the Sprite-to-Perler app. A PNG or GIF dropped onto this file opens directly.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m perler_app %1
