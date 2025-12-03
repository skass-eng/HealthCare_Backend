@echo off
REM ============================================================
REM   HealthCare AI - Démarrage Worker
REM   Usage: start_worker.bat [mode]
REM   Modes: auto, celery, standalone
REM ============================================================

setlocal

REM Définir le mode (défaut: auto)
set MODE=%1
if "%MODE%"=="" set MODE=auto

REM Se placer dans le répertoire du script
cd /d "%~dp0"

echo ============================================================
echo   HealthCare AI - Worker
echo ============================================================
echo   Mode: %MODE%
echo ============================================================
echo.

REM Activer l'environnement virtuel si présent
if exist "venv\Scripts\activate.bat" (
    echo Activation de l'environnement virtuel...
    call venv\Scripts\activate.bat
)

REM Démarrer le worker
python start_worker.py --mode %MODE%

endlocal
