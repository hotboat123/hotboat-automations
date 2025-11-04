#!/bin/bash
# Script para probar la configuración en Linux/Mac

echo "========================================"
echo " Test de Configuración - HotBoat"
echo "========================================"
echo ""

cd "$(dirname "$0")"

if [ ! -f "venv/bin/activate" ]; then
    echo "[ERROR] Entorno virtual no encontrado"
    exit 1
fi

source venv/bin/activate

python test_config.py

