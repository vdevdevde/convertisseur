@echo off
rem ================================================================
rem  Fabrique l'application Windows : dist\Convertisseur\Convertisseur.exe
rem  Double-clique sur ce fichier pour reconstruire apres une modification.
rem ================================================================
cd /d "%~dp0"

echo [1/2] Creation de l'icone...
.venv\Scripts\python.exe outils\creer_icone.py || goto erreur

echo [2/2] Fabrication de l'application (1 a 3 minutes)...
.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed ^
  --name Convertisseur ^
  --icon ressources\icone.ico ^
  --add-data "ressources;ressources" ^
  --collect-all imageio_ffmpeg ^
  --collect-all pillow_heif ^
  lancer.py || goto erreur

echo.
echo Termine ! L'application est dans : dist\Convertisseur\Convertisseur.exe
pause
exit /b 0

:erreur
echo.
echo Une erreur est survenue pendant la fabrication.
pause
exit /b 1
