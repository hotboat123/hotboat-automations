"""
Script para verificar el matching de precios de champañas
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sync_reservas_con_extras import normalize_text, load_costs_and_prices_from_db
import psycopg
from app.config import get_settings

settings = get_settings()
conn = psycopg.connect(settings.database_url)

# Cargar precios usando la función oficial
costs_dict, prices_dict, hotboat_prices = load_costs_and_prices_from_db(conn)

print("Precios de champañas:")
print("="*60)
for key, value in prices_dict.items():
    if 'champana' in key:
        print(f"{key}: ${value:,.0f}")

conn.close()

print("\n" + "="*80)
print("TESTING: champaña_riccadonna_ruby")
print("="*80 + "\n")

test_name = "champaña_riccadonna_ruby"
normalized = normalize_text(test_name)
print(f"Normalizado: {normalized}")

# Buscar precio usando la lógica de mappings
from scripts.sync_reservas_con_extras import find_price_for_extra
precio = find_price_for_extra(test_name, prices_dict)
print(f"Precio encontrado: ${precio:,.0f}")
