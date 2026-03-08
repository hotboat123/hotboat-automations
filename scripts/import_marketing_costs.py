"""
Script para importar costos de marketing desde CSV
Uso: python scripts/import_marketing_costs.py <ruta_al_csv>
"""
import asyncio
import sys
import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import json

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


async def import_marketing_csv(csv_path: str, replace_existing: bool = False):
    """
    Importa datos de marketing desde un CSV
    
    Args:
        csv_path: Ruta al archivo CSV
        replace_existing: Si es True, elimina los datos existentes antes de importar
    """
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url)
    await db.initialize()
    
    try:
        # Si replace_existing es True, eliminar datos existentes
        if replace_existing:
            logger.info("🗑️  Eliminando datos existentes de marketing_costs...")
            await db.execute_non_query("DELETE FROM marketing_costs")
            logger.info("✅ Datos eliminados")
        
        # Leer el CSV
        logger.info(f"📄 Leyendo CSV: {csv_path}")
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        logger.info(f"📊 Total de filas en CSV: {len(rows)}")
        
        # Preparar datos para insertar
        records_to_insert = []
        errors = []
        skipped = 0
        
        for idx, row in enumerate(rows, 1):
            try:
                # Parsear fecha (formato esperado: YYYY-MM-DD)
                date_str = row.get('Día', '').strip()
                if not date_str:
                    skipped += 1
                    continue
                
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    errors.append(f"Fila {idx}: Fecha inválida '{date_str}'")
                    continue
                
                # Parsear monto gastado
                amount_str = row.get('Importe gastado (CLP)', '0').strip().replace(',', '')
                try:
                    amount_spent = Decimal(amount_str) if amount_str else Decimal('0')
                except:
                    errors.append(f"Fila {idx}: Monto inválido '{amount_str}'")
                    continue
                
                # Extraer otros campos
                ad_name = row.get('Nombre del anuncio', '').strip()
                campaign_name = row.get('Nombre de la campaña', '').strip()
                adset_name = row.get('Nombre del conjunto de anuncios', '').strip()
                
                # Parsear métricas numéricas (pueden estar vacías)
                def parse_int(value):
                    try:
                        return int(str(value).strip().replace(',', '')) if value else None
                    except:
                        return None
                
                reach = parse_int(row.get('Alcance'))
                impressions = parse_int(row.get('Impresiones'))
                clicks = parse_int(row.get('Clics en el enlace'))
                purchases = parse_int(row.get('Compras'))
                
                # Guardar el row completo como JSON
                raw_data = dict(row)
                
                records_to_insert.append({
                    'cost_date': date_obj,
                    'ad_name': ad_name,
                    'campaign_name': campaign_name,
                    'adset_name': adset_name,
                    'amount_spent': float(amount_spent),
                    'currency': 'CLP',
                    'reach': reach,
                    'impressions': impressions,
                    'clicks': clicks,
                    'purchases': purchases,
                    'raw': json.dumps(raw_data)
                })
                
            except Exception as e:
                errors.append(f"Fila {idx}: Error procesando: {e}")
        
        # Mostrar resumen antes de insertar
        logger.info(f"\n{'='*70}")
        logger.info(f"RESUMEN DE IMPORTACIÓN")
        logger.info(f"{'='*70}")
        logger.info(f"Total filas procesadas: {len(rows)}")
        logger.info(f"Registros válidos: {len(records_to_insert)}")
        logger.info(f"Filas omitidas (sin fecha): {skipped}")
        logger.info(f"Errores: {len(errors)}")
        
        if errors:
            logger.warning(f"\n⚠️  Errores encontrados:")
            for error in errors[:10]:  # Mostrar solo los primeros 10
                logger.warning(f"  - {error}")
            if len(errors) > 10:
                logger.warning(f"  ... y {len(errors) - 10} más")
        
        if not records_to_insert:
            logger.error("❌ No hay registros válidos para insertar")
            return
        
        # Calcular totales
        total_spent = sum(r['amount_spent'] for r in records_to_insert)
        unique_dates = len(set(r['cost_date'] for r in records_to_insert))
        date_range = f"{min(r['cost_date'] for r in records_to_insert)} a {max(r['cost_date'] for r in records_to_insert)}"
        
        logger.info(f"\n💰 Total a importar: ${total_spent:,.0f} CLP")
        logger.info(f"📅 Rango de fechas: {date_range}")
        logger.info(f"📆 Días únicos: {unique_dates}")
        
        # Insertar registros
        logger.info(f"\n💾 Insertando {len(records_to_insert)} registros...")
        
        insert_query = """
            INSERT INTO marketing_costs 
            (cost_date, ad_name, campaign_name, adset_name, amount_spent, currency, 
             reach, impressions, clicks, purchases, raw)
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        inserted_count = 0
        for record in records_to_insert:
            try:
                await db.execute_non_query(
                    insert_query,
                    (
                        record['cost_date'],
                        record['ad_name'],
                        record['campaign_name'],
                        record['adset_name'],
                        record['amount_spent'],
                        record['currency'],
                        record['reach'],
                        record['impressions'],
                        record['clicks'],
                        record['purchases'],
                        record['raw']
                    )
                )
                inserted_count += 1
                
                if inserted_count % 100 == 0:
                    logger.info(f"  Insertados {inserted_count}/{len(records_to_insert)}...")
                    
            except Exception as e:
                logger.error(f"Error insertando registro {inserted_count + 1}: {e}")
        
        logger.info(f"\n✅ Importación completada!")
        logger.info(f"📊 {inserted_count} registros insertados exitosamente")
        
        # Mostrar resumen por día
        summary_query = """
            SELECT 
                cost_date,
                COUNT(*) as num_ads,
                SUM(amount_spent) as total_spent
            FROM marketing_costs
            WHERE cost_date >= %s AND cost_date <= %s
            GROUP BY cost_date
            ORDER BY cost_date DESC
            LIMIT 10
        """
        
        first_date = min(r['cost_date'] for r in records_to_insert)
        last_date = max(r['cost_date'] for r in records_to_insert)
        
        summary = await db.execute_query(summary_query, (first_date, last_date))
        
        if summary:
            logger.info(f"\n{'='*70}")
            logger.info(f"RESUMEN POR DÍA (últimos 10 días)")
            logger.info(f"{'='*70}")
            logger.info(f"{'FECHA':<15} {'ANUNCIOS':>10} {'GASTO TOTAL':>20}")
            logger.info(f"{'-'*70}")
            
            for row in summary:
                date_str = row['cost_date'].strftime('%Y-%m-%d')
                num_ads = row['num_ads']
                total = row['total_spent']
                logger.info(f"{date_str:<15} {num_ads:>10} ${total:>19,.0f}")
    
    finally:
        await db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_marketing_costs.py <ruta_al_csv> [--replace]")
        print("")
        print("Argumentos:")
        print("  <ruta_al_csv>  Ruta al archivo CSV con datos de marketing")
        print("  --replace      (Opcional) Eliminar datos existentes antes de importar")
        print("")
        print("Ejemplo:")
        print('  python scripts/import_marketing_costs.py "C:\\Users\\Downloads\\marketing.csv"')
        sys.exit(1)
    
    csv_path = sys.argv[1]
    replace_existing = '--replace' in sys.argv
    
    if not Path(csv_path).exists():
        print(f"❌ Error: El archivo no existe: {csv_path}")
        sys.exit(1)
    
    asyncio.run(import_marketing_csv(csv_path, replace_existing))
