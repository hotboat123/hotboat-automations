@echo off
REM Script para iniciar HotBoat Automations en Windows

echo ========================================
echo  HotBoat Automations - Sistema Iniciando
echo ========================================
echo.

REM Cambiar al directorio del script
cd /d "%~dp0"

REM Verificar que existe el entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Entorno virtual no encontrado
    echo Por favor ejecuta: python -m venv venv
    echo Y luego: venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activar entorno virtual
echo [1/3] Activando entorno virtual...
call venv\Scripts\activate.bat

REM Verificar que existe .env
if not exist ".env" (
    echo [ERROR] Archivo .env no encontrado
    echo Por favor copia env.example a .env y configuralo
    pause
    exit /b 1
)

REM Verificar dependencias
echo [2/3] Verificando dependencias...
python -c "import telegram, psycopg" 2>nul
if errorlevel 1 (
    echo [AVISO] Algunas dependencias faltan. Instalando...
    pip install -r requirements.txt
)

REM Ejecutar el sistema
echo [3/3] Iniciando sistema de automatizaciones...
echo.
python main.py

REM Si hay error
if errorlevel 1 (
    echo.
    echo [ERROR] El sistema termino con errores
    echo Revisa logs/automation.log para mas detalles
    pause
)

