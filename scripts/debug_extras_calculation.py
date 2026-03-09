"""
Script para debuggear el cálculo de extras del 7 de marzo
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar las funciones del script de sincronización
from scripts.sync_reservas_con_extras import (
    normalize_text, 
    find_price_for_extra,
    find_cost_for_extra,
    extract_extras_dict
)
import psycopg
from app.config import get_settings

settings = get_settings()
conn = psycopg.connect(settings.database_url)

# Cargar precios
print("Cargando precios de extras...")
costs_dict = {}
prices_dict = {}

with conn.cursor() as cur:
    cur.execute('SELECT raw FROM "Precios Extras"')
    
    for row in cur.fetchall():
        raw = row[0]
        if not raw:
            continue
        
        extra_name = raw.get('Extra', '')
        costo_str = raw.get('costo', '0')
        precio_str = raw.get('Precio', '0')
        
        if not extra_name:
            continue
        
        try:
            costo = float(str(costo_str).replace('.', '').replace(',', '').strip()) if costo_str else 0
        except (ValueError, AttributeError):
            costo = 0
        
        try:
            precio = float(str(precio_str).replace('.', '').replace(',', '').strip())
        except (ValueError, AttributeError):
            precio = 0
        
        normalized = normalize_text(extra_name)
        costs_dict[normalized] = costo
        prices_dict[normalized] = precio

print(f"Cargados {len(prices_dict)} precios\n")

# Obtener extras del 7 de marzo
with conn.cursor() as cur:
    cur.execute("""
        SELECT raw
        FROM "Informacion Reservas"
        WHERE TO_DATE(raw->>'fecha', 'DD/MM/YYYY') = '2026-03-07'
          AND raw->>'horario_salida' = '18:00:00'
        LIMIT 1
    """)
    
    result = cur.fetchone()
    if result:
        extras_json = result[0]
        
        print("="*80)
        print("EXTRAS EN INFORMACION RESERVAS")
        print("="*80 + "\n")
        
        # Mostrar todos los extras con valor
        for key, value in sorted(extras_json.items()):
            if value and str(value).strip() and str(value).strip() not in ['', '0']:
                if any(prefix in key.lower() for prefix in ['extras_tipo', 'tablas_', 'otros_alcoholes_', 'bebidas_y_jugos_', 'cervezas_']):
                    print(f"{key}: {value}")
        
        print("\n" + "="*80)
        print("PROCESAMIENTO DE EXTRAS (lógica del script)")
        print("="*80 + "\n")
        
        # Simular el procesamiento
        import re
        extra_prefixes = ['extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 'otros_alcoholes', 'cha']
        
        print("REVISANDO TODOS LOS CAMPOS:")
        for key, value in sorted(extras_json.items()):
            key_lower = key.lower()
            
            # Ver si pasa el filtro de prefijos
            pasa_filtro = any(key_lower.startswith(prefix) for prefix in extra_prefixes)
            
            if pasa_filtro:
                try:
                    quantity = int(str(value).strip()) if value and str(value).strip() else 0
                except (ValueError, AttributeError):
                    quantity = 0
                
                print(f"\n{key}:")
                print(f"  Pasa filtro: {pasa_filtro}")
                print(f"  Valor raw: '{value}'")
                print(f"  Cantidad: {quantity}")
                
                if quantity <= 0:
                    print(f"  SKIP: cantidad = 0")
                    continue
        
        print("\n" + "="*80)
        print("EXTRAS CON CANTIDAD > 0")
        print("="*80)
        
        for key, value in sorted(extras_json.items()):
            key_lower = key.lower()
            
            if not any(key_lower.startswith(prefix) for prefix in extra_prefixes):
                continue
            
            try:
                quantity = int(str(value).strip()) if value and str(value).strip() else 0
            except (ValueError, AttributeError):
                quantity = 0
            
            if quantity <= 0:
                continue
            
            # Extraer alias
            alias_match = re.search(r'\[(.+?)\]', key)
            if alias_match:
                alias = alias_match.group(1)
            else:
                alias = key
            
            # Buscar precio
            price = find_price_for_extra(alias, prices_dict)
            cost = find_cost_for_extra(alias, costs_dict)
            
            print(f"\nExtra encontrado: {alias}")
            print(f"  Cantidad: {quantity}")
            print(f"  Alias normalizado: {normalize_text(alias)}")
            print(f"  Precio encontrado: ${price:,.0f}")
            print(f"  Costo encontrado: ${cost:,.0f}")
            print(f"  Total ingreso: ${price * quantity:,.0f}")
            print(f"  Total costo: ${cost * quantity:,.0f}")
        
        print("\n" + "="*80)
        print("CALCULO FINAL CON extract_extras_dict()")
        print("="*80 + "\n")
        
        resultado = extract_extras_dict(extras_json, costs_dict, prices_dict)
        print(f"Extras detectados: {resultado['extras']}")
        print(f"Ingreso Total Extras: ${resultado['ingreso_extras']:,.0f}")
        print(f"Costo Total Extras: ${resultado['costo_extras']:,.0f}")

conn.close()
