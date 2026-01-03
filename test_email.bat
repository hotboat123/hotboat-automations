@echo off
REM Script para probar el envío de email de nueva reserva en Windows

echo =====================================================
echo  Prueba de Email - Nueva Reserva HotBoat
echo =====================================================
echo.

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
)

REM Ejecutar el script de prueba
echo.
echo Enviando email de prueba...
echo.
python scripts\test_new_appointment_email.py

echo.
pause

