"""
Script de demostracion del sistema de actualizacion de marketing
"""

print("""
==================================================================
  NUEVO SISTEMA DE ACTUALIZACION DE MARKETING
==================================================================

ESTRUCTURA DE CARPETAS:

hotboat-automations/
  inputs/
    marketing/
      - marketing_costs.csv  <- Coloca tu CSV aqui
      - README.md            (instrucciones)
  
  scripts/
    - update_marketing.py      <- Script simple de actualizacion
    - import_marketing_costs.py (script avanzado)


PROCESO DE ACTUALIZACION (3 PASOS):

------------------------------------------------------------------
PASO 1: Exportar desde Meta Business Suite
------------------------------------------------------------------
1. Ve a Meta Business Suite -> Administrador de anuncios
2. Selecciona el periodo que deseas
3. Exporta como CSV

------------------------------------------------------------------
PASO 2: Guardar en la carpeta correcta
------------------------------------------------------------------
Guarda el archivo exportado como:
  inputs/marketing/marketing_costs.csv

(Reemplazando el archivo anterior)

------------------------------------------------------------------
PASO 3: Ejecutar script de actualizacion
------------------------------------------------------------------
  python scripts/update_marketing.py

El script:
  [OK] Detecta automaticamente el archivo
  [OK] Te pide confirmacion
  [OK] Reemplaza los datos existentes
  [OK] Muestra resumen de importacion


VENTAJAS DEL NUEVO SISTEMA:

  [OK] No necesitas escribir rutas largas
  [OK] Siempre sabes donde poner el archivo
  [OK] Un solo comando para actualizar
  [OK] Confirmacion antes de reemplazar datos
  [OK] Los archivos CSV no se suben a Git (seguridad)


VERIFICAR DATOS ACTUALIZADOS:

  python scripts/simple_verify_marketing.py
  python scripts/marketing_summary.py


==================================================================

TIP: Guarda tus CSV con fecha antes de reemplazarlos
     Ejemplo: marketing_backup_2026-01-27.csv

==================================================================
""")
