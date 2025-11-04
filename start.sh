#!/bin/bash
# Script para iniciar HotBoat Automations en Linux/Mac

echo "========================================"
echo " HotBoat Automations - Sistema Iniciando"
echo "========================================"
echo ""

# Cambiar al directorio del script
cd "$(dirname "$0")"

# Verificar que existe el entorno virtual
if [ ! -f "venv/bin/activate" ]; then
    echo "[ERROR] Entorno virtual no encontrado"
    echo "Por favor ejecuta: python3 -m venv venv"
    echo "Y luego: source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activar entorno virtual
echo "[1/3] Activando entorno virtual..."
source venv/bin/activate

# Verificar que existe .env
if [ ! -f ".env" ]; then
    echo "[ERROR] Archivo .env no encontrado"
    echo "Por favor copia env.example a .env y configuralo"
    exit 1
fi

# Verificar dependencias
echo "[2/3] Verificando dependencias..."
python -c "import telegram, psycopg" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[AVISO] Algunas dependencias faltan. Instalando..."
    pip install -r requirements.txt
fi

# Ejecutar el sistema
echo "[3/3] Iniciando sistema de automatizaciones..."
echo ""
python main.py

# Verificar código de salida
if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] El sistema terminó con errores"
    echo "Revisa logs/automation.log para más detalles"
fi

