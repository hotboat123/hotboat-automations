#!/bin/bash
# Script para exportar reservas con extras en formato JSON

if [ $# -eq 0 ]; then
    echo ""
    echo "====================================================================="
    echo "  EXPORTAR RESERVAS CON EXTRAS (JSON)"
    echo "====================================================================="
    echo ""
    echo "Uso: ./export_reservas_extras.sh <fecha_inicio> [fecha_fin]"
    echo ""
    echo "Ejemplos:"
    echo "  ./export_reservas_extras.sh 2026-01-01 2026-01-31   # Rango"
    echo "  ./export_reservas_extras.sh 2026-01-18              # Solo un día"
    echo ""
    echo "Formato de fecha: YYYY-MM-DD"
    echo ""
    exit 1
fi

START_DATE=$1
END_DATE=${2:-$START_DATE}

echo ""
echo "====================================================================="
echo "  EXPORTANDO RESERVAS CON EXTRAS"
echo "====================================================================="
echo ""
echo "Fecha inicio: $START_DATE"
echo "Fecha fin:    $END_DATE"
echo ""

python scripts/export_reservas_con_extras.py "$START_DATE" "$END_DATE"
