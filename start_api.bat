@echo off
REM ============================================================
REM   HealthCare AI - Démarrage API Server
REM   Usage: start_api.bat [port]
REM ============================================================

setlocal

REM Définir le port (défaut: 8000)
set PORT=%1
if "%PORT%"=="" set PORT=8000

REM Se placer dans le répertoire du script
cd /d "%~dp0"

echo ============================================================
echo   HealthCare AI - API Server
echo ============================================================
echo   Port: %PORT%
echo   Documentation: http://localhost:%PORT%/docs
echo ============================================================
echo.

REM Activer l'environnement virtuel si présent
if exist "venv\Scripts\activate.bat" (
    echo Activation de l'environnement virtuel...
    call venv\Scripts\activate.bat
)

REM Démarrer le serveur
python start_api.py --port %PORT%

endlocal
