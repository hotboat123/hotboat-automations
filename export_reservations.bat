@echo off
REM Script para exportar información completa de reservas a CSV (Windows)

if "%1"=="" (
    echo.
    echo =====================================================================
    echo   EXPORTAR INFORMACION COMPLETA DE RESERVAS
    echo =====================================================================
    echo.
    echo Uso: export_reservations.bat ^<fecha_inicio^> [fecha_fin]
    echo.
    echo Ejemplos:
    echo   export_reservations.bat 2026-01-01 2026-01-31   # Rango
    echo   export_reservations.bat 2026-01-01              # Solo un dia
    echo.
    echo Formato de fecha: YYYY-MM-DD
    echo.
    exit /b 1
)

set START_DATE=%1
set END_DATE=%2
if "%END_DATE%"=="" set END_DATE=%START_DATE%

echo.
echo =====================================================================
echo   EXPORTANDO RESERVAS
echo =====================================================================
echo.
echo Fecha inicio: %START_DATE%
echo Fecha fin:    %END_DATE%
echo.

REM Ejecutar el script
python scripts/export_reservations_full.py %START_DATE% %END_DATE%
