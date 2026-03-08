#!/bin/bash
# Sincroniza la tabla reservas_con_extras
# Uso: ./sync_reservas.sh [fecha_inicio] [fecha_fin] [--force]

python scripts/sync_reservas_con_extras.py "$@"
