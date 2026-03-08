@echo off
REM Genera reportes de prueba
REM Uso: 
REM   test_reportes.bat             # Todos los reportes
REM   test_reportes.bat diario      # Solo diario
REM   test_reportes.bat semanal     # Solo semanal
REM   test_reportes.bat mensual     # Solo mensual

if "%1"=="" (
    python scripts/test_reportes.py
) else (
    python scripts/test_reportes.py --tipo %1
)
