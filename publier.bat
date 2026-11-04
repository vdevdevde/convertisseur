@echo off
rem Publie une nouvelle version sur GitHub (voir outils\publier.ps1)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File outils\publier.ps1
pause
