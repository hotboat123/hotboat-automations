"""
Script simple para verificar datos de marketing
"""
import psycopg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import get_settings

settings = get_settings()

print("\n" + "="*70)
print("VERIFICACIÓN DE DATOS DE MARKETING")
print("="*70 + "\n")

with psycopg.connect(settings.database_url) as conn:
    with conn.cursor() as cur:
        # Total de registros
        cur.execute("SELECT COUNT(*) FROM marketing_costs")
        total = cur.fetchone()[0]
        print(f"Total de registros en marketing_costs: {total}")
        
        # Datos del 18 de enero
        cur.execute("""
            SELECT 
                cost_date,
                COUNT(*) as num_ads,
                SUM(amount_spent) as total_spent
            FROM marketing_costs
            WHERE cost_date = '2026-01-18'
            GROUP BY cost_date
        """)
        
        row = cur.fetchone()
        if row:
            print(f"\nDatos del 18/01/2026:")
            print(f"  Anuncios: {row[1]}")
            print(f"  Gasto Total: ${row[2]:,.0f}")
        else:
            print("\nNo hay datos para el 18/01/2026")
        
        # Resumen por semana
        cur.execute("""
            SELECT 
                cost_date,
                SUM(amount_spent) as daily_spent
            FROM marketing_costs
            WHERE cost_date >= '2026-01-20' AND cost_date <= '2026-01-26'
            GROUP BY cost_date
            ORDER BY cost_date
        """)
        
        print(f"\n{'='*70}")
        print("RESUMEN SEMANAL (20-26 enero)")
        print("="*70)
        
        total_week = 0
        for row in cur.fetchall():
            daily_spent = row[1]
            total_week += daily_spent
            print(f"  {row[0]}: ${daily_spent:,.0f}")
        
        print(f"\nTotal semana: ${total_week:,.0f}")
        
        print("\n" + "="*70 + "\n")
