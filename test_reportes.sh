#!/bin/bash
# Genera reportes de prueba
# Uso: 
#   ./test_reportes.sh             # Todos los reportes
#   ./test_reportes.sh diario      # Solo diario
#   ./test_reportes.sh semanal     # Solo semanal
#   ./test_reportes.sh mensual     # Solo mensual

python scripts/test_reportes.py ${1:+--tipo $1}
