@echo off
REM Sincroniza la tabla reservas_con_extras
REM Uso: sync_reservas.bat [fecha_inicio] [fecha_fin] [--force]

python scripts/sync_reservas_con_extras.py %*
