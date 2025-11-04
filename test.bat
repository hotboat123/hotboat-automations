@echo off
REM Script para probar la configuración

echo ========================================
echo  Test de Configuracion - HotBoat
echo ========================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Entorno virtual no encontrado
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

python test_config.py

pause

