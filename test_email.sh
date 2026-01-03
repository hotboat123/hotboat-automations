#!/bin/bash
# Script para probar el envío de email de nueva reserva en Linux/Mac

echo "====================================================="
echo "  Prueba de Email - Nueva Reserva HotBoat"
echo "====================================================="
echo ""

# Activar entorno virtual si existe
if [ -f "venv/bin/activate" ]; then
    echo "Activando entorno virtual..."
    source venv/bin/activate
fi

# Ejecutar el script de prueba
echo ""
echo "Enviando email de prueba..."
echo ""
python scripts/test_new_appointment_email.py

echo ""
read -p "Presiona Enter para continuar..."

