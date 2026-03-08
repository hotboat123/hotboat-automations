"""
Script simple para actualizar los costos de marketing
Busca automáticamente el archivo en inputs/marketing/marketing_costs.csv
"""
import asyncio
import sys
from pathlib import Path

# Fix para Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import DatabaseManager
from app.config import get_settings
from app.logger import logger

# Importar la función del script original
from scripts.import_marketing_costs import import_marketing_csv


async def update_marketing():
    """Actualiza los datos de marketing desde el archivo en inputs/"""
    
    # Ruta al archivo en la carpeta inputs
    input_file = Path("inputs/marketing/marketing_costs.csv")
    
    print("\n" + "="*70)
    print("  ACTUALIZACION DE DATOS DE MARKETING")
    print("="*70 + "\n")
    
    # Verificar que existe el archivo
    if not input_file.exists():
        print(f"ERROR: No se encontro el archivo en:")
        print(f"  {input_file.absolute()}")
        print(f"\nPor favor:")
        print(f"  1. Exporta el CSV desde Meta Business Suite")
        print(f"  2. Guardalo como 'marketing_costs.csv' en la carpeta inputs/marketing/")
        print(f"  3. Ejecuta este script nuevamente")
        return
    
    print(f"Archivo encontrado:")
    print(f"  {input_file.absolute()}")
    print(f"  Tamano: {input_file.stat().st_size / 1024:.1f} KB")
    print(f"  Ultima modificacion: {input_file.stat().st_mtime}")
    print()
    
    # Preguntar confirmación
    print("Este script va a:")
    print("  1. ELIMINAR todos los datos de marketing existentes")
    print("  2. IMPORTAR los nuevos datos desde el archivo CSV")
    print()
    
    respuesta = input("Continuar? (si/no): ").lower().strip()
    
    if respuesta not in ['si', 's', 'yes', 'y']:
        print("\nOperacion cancelada.")
        return
    
    print("\nIniciando importacion...\n")
    
    # Llamar a la función de importación con replace=True
    await import_marketing_csv(str(input_file), replace_existing=True)
    
    print("\n" + "="*70)
    print("  ACTUALIZACION COMPLETADA")
    print("="*70 + "\n")
    print("Los reportes diarios, semanales y mensuales ahora usaran")
    print("los datos actualizados de marketing.")
    print()


if __name__ == "__main__":
    asyncio.run(update_marketing())
