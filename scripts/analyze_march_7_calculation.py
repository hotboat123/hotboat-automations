"""
Script para analizar el cálculo de ingresos del 7 de marzo
"""
import sys
import os
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def analyze_march_7():
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    await db.initialize()
    
    try:
        # 1. Ver la Informacion Reservas del 7 de marzo a las 18:00
        print("\n" + "="*80)
        print("EXTRAS EN INFORMACION RESERVAS (7 marzo, 18:00)")
        print("="*80 + "\n")
        
        query = """
            SELECT 
                id,
                raw->>'n°_de_adultos' as adultos,
                raw->>'n°_niños' as ninos,
                raw
            FROM "Informacion Reservas"
            WHERE TO_DATE(raw->>'fecha', 'DD/MM/YYYY') = '2026-03-07'
              AND raw->>'horario_salida' = '18:00:00'
        """
        
        reservas = await db.execute_query(query)
        
        if reservas:
            res = reservas[0]
            raw = res['raw']
            
            print(f"Adultos: {res['adultos']}")
            print(f"Niños: {res['ninos']}")
            print(f"\nExtras encontrados:")
            
            # Buscar todos los campos con valores
            extras_con_valor = {}
            for key, value in raw.items():
                if value and str(value).strip() and str(value).strip() not in ['', '0']:
                    # Filtrar solo extras relevantes
                    if any(prefix in key.lower() for prefix in ['extras_tipo', 'tablas_', 'otros_alcoholes_', 'bebidas_y_jugos_', 'cervezas_']):
                        extras_con_valor[key] = value
            
            for key, value in sorted(extras_con_valor.items()):
                print(f"  {key}: {value}")
        
        # 2. Ver precios de extras en la BD
        print(f"\n" + "="*80)
        print("PRECIOS DE ESOS EXTRAS EN LA BD")
        print("="*80 + "\n")
        
        # Mapear los nombres
        extras_a_buscar = [
            ('modo_romantico', 'romantic'),
            ('champaña_riccadonna_ruby', 'Champaña Riccadona'),
            ('tabla_2_personas', 'Tabla 2'),
        ]
        
        for extra_name, precio_name in extras_a_buscar:
            precio_query = """
                SELECT 
                    raw->>'Extra' as extra,
                    raw->>'Precio' as precio,
                    raw->>'costo' as costo
                FROM "Precios Extras"
                WHERE LOWER(raw->>'Extra') LIKE %s
                LIMIT 1
            """
            
            precios = await db.execute_query(precio_query, (f'%{precio_name.lower()}%',))
            if precios:
                p = precios[0]
                print(f"{extra_name}:")
                print(f"  Nombre en BD: {p['extra']}")
                print(f"  Precio: ${p['precio']}")
                print(f"  Costo: ${p['costo']}")
            else:
                print(f"{extra_name}: NO ENCONTRADO")
            print()
        
        # 3. Ver precios base HotBoat
        print("="*80)
        print("PRECIOS BASE HOTBOAT (según número de personas)")
        print("="*80 + "\n")
        
        hotboat_query = """
            SELECT 
                raw->>'Extra' as servicio,
                raw->>'Precio' as precio,
                raw->>'costo' as costo
            FROM "Precios Extras"
            WHERE LOWER(raw->>'Extra') LIKE '%hotboat%'
            ORDER BY raw->>'Extra'
        """
        
        hotboats = await db.execute_query(hotboat_query)
        for hb in hotboats:
            print(f"{hb['servicio']}: Precio=${hb['precio']}, Costo=${hb['costo']}")
        
        # 4. Calcular correctamente
        print(f"\n" + "="*80)
        print("CALCULO CORRECTO PARA 7 MARZO")
        print("="*80 + "\n")
        
        num_personas = 2
        ingreso_base = 139990  # Para 2 personas
        
        print(f"Número de personas: {num_personas}")
        print(f"Ingreso Base (HotBoat {num_personas}p): ${ingreso_base:,.0f}")
        print(f"\nExtras:")
        print(f"  - Romantic (modo_romantico): 1 x $20.000 = $20.000")
        print(f"  - Champaña Riccadonna Ruby: 1 x $22.000 = $22.000")
        print(f"  - Tabla 2 personas: 1 x $20.000 = $20.000")
        print(f"  - Sharing Platter (según Booknetic): 1 x $20.000 = $20.000")
        print(f"\nTotal Extras: $65.000")
        print(f"Ingreso Total: ${ingreso_base:,.0f} + $65.000 = ${ingreso_base + 65000:,.0f}")
        
        print(f"\n¿Por qué el sistema calcula $35.000 en vez de $65.000?")
        print(f"Posibles razones:")
        print(f"  1. No encuentra todos los extras en 'Precios Extras'")
        print(f"  2. La normalización de nombres no coincide")
        print(f"  3. Falta mapear algunos extras")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(analyze_march_7())
