"""
Script para gestionar precios de extras
Permite ver, agregar y actualizar precios en la tabla "Precios Extras"
"""

import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Fix para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.config import get_settings
from app.database import DatabaseManager

async def list_prices():
    """Lista todos los precios configurados"""
    print(f"\n{'='*60}")
    print("PRECIOS DE EXTRAS CONFIGURADOS")
    print(f"{'='*60}\n")
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url)
    await db.initialize()
    
    try:
        query = 'SELECT * FROM "Precios Extras" ORDER BY id'
        results = await db.execute_query(query)
        
        if not results:
            print("No hay precios configurados.\n")
            return
        
        print(f"{'ID':<5} {'EXTRA':<40} {'PRECIO':>15}")
        print(f"{'-'*60}")
        
        for row in results:
            row_id = row.get('id', '')
            raw = row.get('raw', {})
            extra_name = raw.get('Extra', 'Sin nombre')
            precio_str = raw.get('Precio', '0')
            
            # Limpiar precio
            try:
                precio = float(str(precio_str).replace('.', '').replace(',', '').strip())
            except (ValueError, AttributeError):
                precio = 0
            
            print(f"{row_id:<5} {extra_name:<40} ${precio:>14,.0f}")
        
        print(f"\nTotal: {len(results)} precios configurados\n")
    
    finally:
        await db.close()


async def add_price(extra_name: str, price: float):
    """Agrega un nuevo precio"""
    print(f"\n{'='*60}")
    print("AGREGANDO NUEVO PRECIO")
    print(f"{'='*60}\n")
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url)
    await db.initialize()
    
    try:
        # Verificar si ya existe
        check_query = """
            SELECT id FROM "Precios Extras" 
            WHERE raw->>'Extra' = %s
        """
        existing = await db.execute_query(check_query, (extra_name,))
        
        if existing:
            print(f"ERROR: Ya existe un precio para '{extra_name}'")
            print(f"Usa el comando 'update' para modificarlo.\n")
            return
        
        # Insertar nuevo precio
        # Generar ID usando SHA-1 del nombre del extra (como lo hace la aplicación)
        import hashlib
        extra_id = hashlib.sha1(extra_name.encode('utf-8')).hexdigest()
        
        insert_query = """
            INSERT INTO "Precios Extras" (id, raw, created_at)
            VALUES (%s, %s::jsonb, NOW())
        """
        
        raw_data = {
            "Extra": extra_name,
            "Precio": str(int(price))
        }
        
        import json
        await db.execute_query(insert_query, (extra_id, json.dumps(raw_data)))
        
        print(f"OK: Precio agregado exitosamente")
        print(f"  Extra: {extra_name}")
        print(f"  Precio: ${price:,.0f}\n")
    
    except Exception as e:
        print(f"ERROR: {e}\n")
    
    finally:
        await db.close()


async def update_price(extra_name: str, new_price: float):
    """Actualiza un precio existente"""
    print(f"\n{'='*60}")
    print("ACTUALIZANDO PRECIO")
    print(f"{'='*60}\n")
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url)
    await db.initialize()
    
    try:
        # Verificar si existe
        check_query = """
            SELECT id, raw FROM "Precios Extras" 
            WHERE raw->>'Extra' = %s
        """
        existing = await db.execute_query(check_query, (extra_name,))
        
        if not existing:
            print(f"ERROR: No existe un precio para '{extra_name}'")
            print(f"Usa el comando 'add' para agregarlo.\n")
            return
        
        row_id = existing[0]['id']
        old_raw = existing[0]['raw']
        old_price = old_raw.get('Precio', '0')
        
        # Actualizar precio
        update_query = """
            UPDATE "Precios Extras" 
            SET raw = jsonb_set(raw, '{Precio}', %s::jsonb),
                updated_at = NOW()
            WHERE id = %s
        """
        
        import json
        await db.execute_query(update_query, (json.dumps(str(int(new_price))), row_id))
        
        print(f"OK: Precio actualizado exitosamente")
        print(f"  Extra: {extra_name}")
        print(f"  Precio anterior: ${old_price}")
        print(f"  Precio nuevo: ${new_price:,.0f}\n")
    
    except Exception as e:
        print(f"ERROR: {e}\n")
    
    finally:
        await db.close()


async def delete_price(extra_name: str):
    """Elimina un precio"""
    print(f"\n{'='*60}")
    print("ELIMINANDO PRECIO")
    print(f"{'='*60}\n")
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url)
    await db.initialize()
    
    try:
        # Verificar si existe
        check_query = """
            SELECT id FROM "Precios Extras" 
            WHERE raw->>'Extra' = %s
        """
        existing = await db.execute_query(check_query, (extra_name,))
        
        if not existing:
            print(f"ERROR: No existe un precio para '{extra_name}'\n")
            return
        
        # Eliminar
        delete_query = 'DELETE FROM "Precios Extras" WHERE raw->>\'Extra\' = %s'
        await db.execute_query(delete_query, (extra_name,))
        
        print(f"OK: Precio eliminado exitosamente")
        print(f"  Extra: {extra_name}\n")
    
    except Exception as e:
        print(f"ERROR: {e}\n")
    
    finally:
        await db.close()


def print_usage():
    """Muestra cómo usar el script"""
    print("""
Uso: python manage_prices.py [comando] [argumentos]

Comandos:
  list                           - Lista todos los precios
  add "Nombre Extra" precio      - Agrega un nuevo precio
  update "Nombre Extra" precio   - Actualiza un precio existente
  delete "Nombre Extra"          - Elimina un precio

Ejemplos:
  python scripts/manage_prices.py list
  python scripts/manage_prices.py add "Coca-Cola" 2000
  python scripts/manage_prices.py update "Cerveza Artesanal" 7000
  python scripts/manage_prices.py delete "Foto con Marco"

Nota: Los nombres de extras con espacios deben ir entre comillas.
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        asyncio.run(list_prices())
    
    elif command == "add":
        if len(sys.argv) < 4:
            print("ERROR: Faltan argumentos para 'add'")
            print("Uso: python manage_prices.py add \"Nombre Extra\" precio")
            sys.exit(1)
        
        extra_name = sys.argv[2]
        try:
            price = float(sys.argv[3])
        except ValueError:
            print(f"ERROR: '{sys.argv[3]}' no es un precio válido")
            sys.exit(1)
        
        asyncio.run(add_price(extra_name, price))
    
    elif command == "update":
        if len(sys.argv) < 4:
            print("ERROR: Faltan argumentos para 'update'")
            print("Uso: python manage_prices.py update \"Nombre Extra\" precio")
            sys.exit(1)
        
        extra_name = sys.argv[2]
        try:
            price = float(sys.argv[3])
        except ValueError:
            print(f"ERROR: '{sys.argv[3]}' no es un precio válido")
            sys.exit(1)
        
        asyncio.run(update_price(extra_name, price))
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("ERROR: Falta el nombre del extra")
            print("Uso: python manage_prices.py delete \"Nombre Extra\"")
            sys.exit(1)
        
        extra_name = sys.argv[2]
        asyncio.run(delete_price(extra_name))
    
    else:
        print(f"ERROR: Comando '{command}' no reconocido")
        print_usage()
        sys.exit(1)
