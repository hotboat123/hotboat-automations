#!/bin/bash
# Script para exportar información completa de reservas a CSV

# Obtener fecha de inicio y fin
if [ $# -eq 0 ]; then
    echo ""
    echo "====================================================================="
    echo "  EXPORTAR INFORMACIÓN COMPLETA DE RESERVAS"
    echo "====================================================================="
    echo ""
    echo "Uso: ./export_reservations.sh <fecha_inicio> [fecha_fin]"
    echo ""
    echo "Ejemplos:"
    echo "  ./export_reservations.sh 2026-01-01 2026-01-31   # Rango"
    echo "  ./export_reservations.sh 2026-01-01              # Solo un día"
    echo ""
    echo "Formato de fecha: YYYY-MM-DD"
    echo ""
    exit 1
fi

START_DATE=$1
END_DATE=${2:-$START_DATE}

echo ""
echo "====================================================================="
echo "  EXPORTANDO RESERVAS"
echo "====================================================================="
echo ""
echo "Fecha inicio: $START_DATE"
echo "Fecha fin:    $END_DATE"
echo ""

# Ejecutar el script
python scripts/export_reservations_full.py "$START_DATE" "$END_DATE"
