"""
Script de resumen del sistema de costos de marketing
Muestra un ejemplo de cómo se ven los reportes con la nueva funcionalidad
"""
import psycopg
import sys
from pathlib import Path
from datetime import date, timedelta, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import get_settings

settings = get_settings()

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

print("\n" + "="*70)
print_section("SISTEMA DE UTILIDAD OPERATIVA - RESUMEN")

with psycopg.connect(settings.database_url) as conn:
    with conn.cursor() as cur:
        # 1. Estado de la base de datos
        print_section("ESTADO DE LA BASE DE DATOS")
        
        cur.execute("SELECT COUNT(*) FROM marketing_costs")
        total_marketing = cur.fetchone()[0]
        print(f"  [OK] Registros de marketing: {total_marketing:,}")
        
        cur.execute("""
            SELECT MIN(cost_date), MAX(cost_date)
            FROM marketing_costs
        """)
        min_date, max_date = cur.fetchone()
        print(f"  Rango de datos: {min_date} a {max_date}")
        
        cur.execute("""
            SELECT COUNT(DISTINCT cost_date)
            FROM marketing_costs
        """)
        unique_days = cur.fetchone()[0]
        print(f"  Dias con datos: {unique_days}")
        
        cur.execute("""
            SELECT SUM(amount_spent)
            FROM marketing_costs
        """)
        total_spent = cur.fetchone()[0] or 0
        print(f"  Gasto total registrado: ${total_spent:,.0f}")
        
        # 2. Ejemplo de un día
        print_section("EJEMPLO: DIA 18/01/2026")
        
        cur.execute("""
            SELECT 
                COUNT(*) as num_ads,
                SUM(amount_spent) as total_spent,
                SUM(reach) as total_reach,
                SUM(clicks) as total_clicks
            FROM marketing_costs
            WHERE cost_date = '2026-01-18'
        """)
        
        row = cur.fetchone()
        if row:
            num_ads, spent, reach, clicks = row
            print(f"  MARKETING:")
            print(f"     Anuncios activos: {num_ads}")
            print(f"     Gasto: ${spent:,.0f}")
            print(f"     Alcance: {reach:,} personas")
            print(f"     Clicks: {clicks}")
            
            # Obtener ingresos del día
            cur.execute("""
                SELECT 
                    COUNT(*) as num_reservations,
                    SUM(CAST(
                        REGEXP_REPLACE(
                            REPLACE(COALESCE(ba.raw->>'payment', '0'), '$', ''),
                            '[^0-9]',
                            '',
                            'g'
                        ) AS NUMERIC
                    )) as total_payment
                FROM booknetic_appointments ba
                WHERE DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = '2026-01-18'
            """)
            
            rev_row = cur.fetchone()
            if rev_row:
                num_res, total_payment = rev_row
                total_payment = total_payment or 0
                operational_profit = total_payment - spent
                margin = (operational_profit / total_payment * 100) if total_payment > 0 else 0
                
                print(f"\n  INGRESOS:")
                print(f"     Reservas: {num_res}")
                print(f"     Ingresos totales: ${total_payment:,.0f}")
                
                print(f"\n  UTILIDAD OPERATIVA:")
                print(f"     Ingresos: ${total_payment:,.0f}")
                print(f"     Marketing: -${spent:,.0f}")
                print(f"     {'='*30}")
                print(f"     UTILIDAD: ${operational_profit:,.0f}")
                print(f"     Margen: {margin:.1f}%")
                
                # Interpretación
                if margin >= 50:
                    status = "[EXCELENTE]"
                elif margin >= 30:
                    status = "[BUENO]"
                else:
                    status = "[BAJO]"
                print(f"\n  {status}")
        
        # 3. Resumen semanal
        # Verificar hasta qué fecha tenemos datos
        cur.execute("SELECT MAX(cost_date) FROM marketing_costs")
        max_date = cur.fetchone()[0]
        
        # Usar la última semana con datos (19-25 enero 2026)
        week_monday = date(2026, 1, 19)
        week_sunday = date(2026, 1, 25)
        
        print_section(f"ULTIMA SEMANA CON DATOS ({week_monday.strftime('%d/%m')}-{week_sunday.strftime('%d/%m')} ENE)")
        print(f"  (Datos disponibles hasta: {max_date})\n")
        
        # Primero obtener datos diarios
        cur.execute("""
            SELECT 
                mc.cost_date,
                SUM(mc.amount_spent) as marketing_cost,
                COUNT(mc.id) as num_ads,
                (
                    SELECT SUM(CAST(
                        REGEXP_REPLACE(
                            REPLACE(COALESCE(ba.raw->>'payment', '0'), '$', ''),
                            '[^0-9]',
                            '',
                            'g'
                        ) AS NUMERIC
                    ))
                    FROM booknetic_appointments ba
                    WHERE DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = mc.cost_date
                ) as daily_revenue,
                (
                    SELECT COUNT(*)
                    FROM booknetic_appointments ba
                    WHERE DATE(TO_TIMESTAMP(ba.raw->>'start_date', 'DD/MM/YYYY HH24:MI')) = mc.cost_date
                ) as num_reservations
            FROM marketing_costs mc
            WHERE mc.cost_date >= %s AND mc.cost_date <= %s
            GROUP BY mc.cost_date
            ORDER BY mc.cost_date
        """, (week_monday, week_sunday))
        
        # Convertir resultados a un diccionario por fecha
        data_by_date = {}
        for row in cur.fetchall():
            day_date, marketing_cost, num_ads, daily_revenue, num_res = row
            data_by_date[day_date] = {
                'marketing': marketing_cost,
                'revenue': daily_revenue or 0,
                'reservations': num_res or 0
            }
        
        print("\n  DESGLOSE DIARIO:")
        print(f"  {'-'*75}")
        print(f"  {'Fecha':<12} {'Marketing':>12} {'Reservas':>10} {'Ingresos':>15} {'Utilidad':>15}")
        print(f"  {'-'*75}")
        
        total_marketing_week = 0
        total_revenue_week = 0
        
        # Mapear días de la semana en español
        weekdays = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
        
        # Iterar por TODOS los días de lunes a domingo
        current_day = week_monday
        while current_day <= week_sunday:
            weekday_name = weekdays[current_day.weekday()]
            date_str = f"{weekday_name} {current_day.strftime('%d/%m')}"
            
            if current_day in data_by_date:
                # Hay datos para este día
                marketing_cost = data_by_date[current_day]['marketing']
                daily_revenue = data_by_date[current_day]['revenue']
                num_res = data_by_date[current_day]['reservations']
            else:
                # No hay datos, mostrar como $0
                marketing_cost = 0
                daily_revenue = 0
                num_res = 0
            
            daily_profit = daily_revenue - marketing_cost
            
            total_marketing_week += marketing_cost
            total_revenue_week += daily_revenue
            
            # Marcar si no hay datos
            suffix = " (sin datos)" if current_day not in data_by_date else ""
            
            print(f"  {date_str:<12} ${marketing_cost:>11,.0f} {num_res:>10} ${daily_revenue:>14,.0f} ${daily_profit:>14,.0f}{suffix}")
            
            current_day += timedelta(days=1)
        
        print(f"  {'-'*75}")
        profit_week = total_revenue_week - total_marketing_week
        margin_week = (profit_week / total_revenue_week * 100) if total_revenue_week > 0 else 0
        
        print(f"\n  TOTALES SEMANALES:")
        print(f"  Ingresos Totales: ${total_revenue_week:,.0f}")
        print(f"  Marketing Total: ${total_marketing_week:,.0f}")
        print(f"  {'='*35}")
        print(f"  UTILIDAD: ${profit_week:,.0f}")
        print(f"  Margen: {margin_week:.1f}%")
        
        # 4. Funcionalidades disponibles
        print_section("FUNCIONALIDADES DISPONIBLES")
        
        print("""  [OK] Actualizar datos de marketing (metodo simple):
     1. Guarda tu CSV en: inputs/marketing/marketing_costs.csv
     2. python scripts/update_marketing.py
  
  [OK] Verificar datos importados:
     python scripts/simple_verify_marketing.py
  
  [OK] Reporte diario (con utilidad operativa):
     python scripts/review_date_report.py 2026-01-18
  
  [OK] Reporte semanal actual:
     python scripts/test_weekly_monthly_report.py weekly current
  
  [OK] Reporte mensual actual:
     python scripts/test_weekly_monthly_report.py monthly current
  
  [DOC] Documentacion completa:
     docs/MARKETING_COSTS.md
""")

print_section("*** SISTEMA COMPLETADO EXITOSAMENTE ***")
print("\n" + "="*70 + "\n")
