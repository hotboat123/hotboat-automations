@echo off
REM Script para exportar reservas con extras en formato JSON (Windows)

if "%1"=="" (
    echo.
    echo =====================================================================
    echo   EXPORTAR RESERVAS CON EXTRAS (JSON^)
    echo =====================================================================
    echo.
    echo Uso: export_reservas_extras.bat ^<fecha_inicio^> [fecha_fin]
    echo.
    echo Ejemplos:
    echo   export_reservas_extras.bat 2026-01-01 2026-01-31   # Rango
    echo   export_reservas_extras.bat 2026-01-18              # Solo un dia
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
echo   EXPORTANDO RESERVAS CON EXTRAS
echo =====================================================================
echo.
echo Fecha inicio: %START_DATE%
echo Fecha fin:    %END_DATE%
echo.

python scripts/export_reservas_con_extras.py %START_DATE% %END_DATE%
