"""
Script para calcular ingresos diarios de ventas
Cruza booknetic_payments con Información Reservas y lee precios de Precios Extras

Uso:
    python calculate_daily_revenue.py                    # Calcula para hoy
    python calculate_daily_revenue.py 2026-01-15        # Calcula para una fecha específica
    python calculate_daily_revenue.py 2026-01-01 2026-01-31  # Rango de fechas
"""
import asyncio
import sys
import csv
import unicodedata
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Set
import argparse
import re

# Fix para Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.logger import logger
from app.database import DatabaseManager


def normalize_text(text: str) -> str:
    """
    Normaliza texto removiendo tildes, espacios y caracteres especiales
    """
    # Remover tildes y diacríticos
    nfkd = unicodedata.normalize('NFKD', text)
    text_without_accents = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    
    # Convertir a minúsculas y reemplazar espacios/guiones por guiones bajos
    normalized = text_without_accents.lower().replace(' ', '_').replace('-', '_')
    
    return normalized


def get_category_aliases() -> Dict[str, List[str]]:
    """
    Define aliases/variantes de nombres que mapean a las mismas categorías.
    Cada clave es el nombre de la categoría en "Precios Extras", 
    y los valores son listas de posibles variantes encontradas en "Informacion Reservas".
    
    Returns:
        Dict con categorías y sus aliases
    """
    return {
        # Champañas
        'champana_riccadona': [
            'champana_riccadonna_ruby',
            'champana_riccadonna_moscato_rose',
            'champana_riccadonna_asti',
            'champana_riccadonna',
            'riccadonna_ruby',
            'riccadonna_moscato_rose',
            'riccadonna_asti',
            'riccadonna'
        ],
        'champana_undurraga_demi_sec': [
            'champana_undurraga',
            'undurraga_demi_sec',
            'demi_sec'
        ],
        
        # Cervezas
        'cerveza_artesanal': [
            'cerveza_artesanal_ambar',
            'cerveza_artesanal_negra',
            'artesanal_ambar',
            'artesanal_negra'
        ],
        'cerveza_premium': [
            'cerveza_austral_calafate',
            'cerveza_austral_lager',
            'cerveza_kunstman_valdivia',
            'cerveza_kunstman_torobayo',
            'austral_calafate',
            'austral_lager',
            'kunstman_valdivia',
            'kunstman_torobayo'
        ],
        'cerveza_normal': [
            'cerveza_royal',
            'royal'
        ],
        
        # Vinos
        'vino_casillero_del_diablo': [
            'vino_carmenere',
            'vino_cabernet_sauvignon',
            'vino_merlot',
            'carmenere',
            'cabernet_sauvignon',
            'merlot'
        ],
        
        # Bebidas
        'lata_bebida': [
            'coca_cola',
            'coca-cola',
            'fanta',
            'sprite',
            'bebida_lata'
        ],
        'jugo_1l': [
            'jugo_mango_naranja',
            'jugo_naranja',
            'jugo_berries',
            'mango_naranja',
            'naranja',
            'berries'
        ],
        'agua_1_5l': [
            'agua',
            'agua_mineral'
        ],
        
        # Licores
        'lemon_stone': [
            'lemon_stone_normal',
            'maracuya_stone',
            'maracuya_stone_'
        ],
        
        # Tablas
        'tabla_1': [
            'tabla_2_personas',
            'tabla_2'
        ],
        'tabla_2': [
            'tabla_4_personas',
            'tabla_4'
        ],
        
        # Extras especiales
        'romantic': [
            'modo_romantico',
            'romantico',
            'modo_romantico'
        ],
        'video_15_seg': [
            'video_15_segundos',
            'video_15'
        ],
        'video_1_min': [
            'video_60_segundos',
            'video_60'
        ],
        
        # Otros
        'poncho': [
            'toalla_poncho'
        ]
    }


async def load_prices_from_db(db: DatabaseManager) -> Dict[str, float]:
    """
    Carga los precios desde la tabla "Precios Extras"
    
    Returns:
        Dict con nombre normalizado -> precio
    """
    logger.info("Cargando precios desde base de datos...")
    
    query = 'SELECT * FROM "Precios Extras"'
    results = await db.execute_query(query)
    
    prices = {}
    
    for row in results:
        raw = row.get('raw', {})
        if not raw:
            continue
        
        extra_name = raw.get('Extra', '')
        precio_str = raw.get('Precio', '0')
        
        if not extra_name:
            continue
        
        # Limpiar precio (remover puntos y convertir)
        try:
            precio = float(str(precio_str).replace('.', '').replace(',', '').strip())
        except (ValueError, AttributeError):
            precio = 0
        
        # Normalizar nombre
        name_normalized = normalize_text(extra_name)
        prices[name_normalized] = precio
        
        logger.info(f"   Cargado: {extra_name} -> ${precio:,.0f}")
    
    logger.info(f"Total de precios cargados: {len(prices)}")
    
    return prices


def find_price_for_extra(
    extra_name: str,
    prices: Dict[str, float],
    category_aliases: Dict[str, List[str]]
) -> tuple[float, str]:
    """
    Busca el precio para un extra, usando categorías y aliases
    
    Args:
        extra_name: Nombre del extra a buscar
        prices: Dict de precios cargados de la BD
        category_aliases: Dict de categorías y sus aliases
    
    Returns:
        Tupla (precio, nombre_categoria_usada)
    """
    extra_normalized = normalize_text(extra_name)
    
    # 1. Búsqueda directa
    if extra_normalized in prices:
        return prices[extra_normalized], extra_normalized
    
    # 2. Búsqueda por aliases (el extra es un alias de una categoría)
    for category, aliases in category_aliases.items():
        aliases_normalized = [normalize_text(a) for a in aliases]
        if extra_normalized in aliases_normalized:
            if category in prices:
                return prices[category], category
    
    # 3. Búsqueda parcial (el extra contiene el nombre de una categoría)
    for category in prices.keys():
        if category in extra_normalized or extra_normalized in category:
            return prices[category], category
    
    # No se encontró precio
    return 0.0, ""


def extract_extras_from_json(
    raw_json: Dict[str, Any],
    prices: Dict[str, float],
    category_aliases: Dict[str, List[str]],
    missing_prices: Set[str]
) -> List[Dict[str, Any]]:
    """
    Extrae los extras del campo raw de Informacion Reservas
    
    Args:
        raw_json: JSON raw de la reserva
        prices: Dict de precios
        category_aliases: Dict de categorías
        missing_prices: Set para acumular extras sin precio
    
    Returns:
        Lista de diccionarios con {nombre, cantidad, precio, subtotal, categoria}
    """
    if not raw_json:
        return []
    
    extras_list = []
    
    # Prefijos de campos que contienen extras
    extra_prefixes = [
        'extras', 'cervezas', 'tablas', 'bebidas_y_jugos', 
        'otros_alcoholes', 'cha'
    ]
    
    for key, value in raw_json.items():
        # Verificar si la clave es de un extra
        key_lower = key.lower()
        is_extra = any(key_lower.startswith(prefix) for prefix in extra_prefixes)
        
        if not is_extra:
            continue
        
        # Intentar obtener cantidad
        try:
            quantity = int(str(value).strip()) if value and str(value).strip() else 0
        except (ValueError, AttributeError):
            quantity = 0
        
        if quantity <= 0:
            continue
        
        # Extraer alias del extra: campo_[alias]
        alias_match = re.search(r'\[(.+?)\]', key)
        if alias_match:
            alias = alias_match.group(1)
        else:
            alias = key
        
        # Buscar precio
        price, category_used = find_price_for_extra(alias, prices, category_aliases)
        
        # Si no se encontró precio, agregarlo al conjunto de faltantes
        if price == 0:
            missing_prices.add(alias)
        
        subtotal = price * quantity
        
        extras_list.append({
            'nombre': alias,
            'cantidad': quantity,
            'precio_unitario': price,
            'subtotal': subtotal,
            'categoria': category_used
        })
    
    return extras_list


async def calculate_daily_revenue(
    db: DatabaseManager,
    target_date: date,
    prices: Dict[str, float],
    category_aliases: Dict[str, List[str]],
    missing_prices: Set[str]
) -> Dict[str, Any]:
    """
    Calcula los ingresos diarios cruzando las tablas
    """
    
    logger.info(f"\nCalculando ingresos para {target_date.strftime('%Y-%m-%d')}...")
    
    # Query que cruza booknetic_payments con Informacion Reservas
    query = """
        WITH payments_data AS (
            SELECT 
                bp.id as payment_id,
                CAST(
                    REGEXP_REPLACE(
                        REPLACE(bp.raw->>'total_amount', '$', ''),
                        '[^0-9]',
                        '',
                        'g'
                    ) AS NUMERIC
                ) as total_amount,
                TO_TIMESTAMP(
                    bp.raw->>'appointment_date',
                    'DD/MM/YYYY HH24:MI'
                ) as appointment_datetime,
                bp.status,
                bp.raw->>'customer' as customer_name,
                bp.raw->>'customer_email' as customer_email,
                bp.raw as payment_raw
            FROM booknetic_payments bp
            WHERE bp.raw->>'appointment_date' IS NOT NULL
              AND DATE(
                  TO_TIMESTAMP(
                      bp.raw->>'appointment_date',
                      'DD/MM/YYYY HH24:MI'
                  )
              ) = %s
        ),
        reservations_with_extras AS (
            SELECT DISTINCT ON (reservation_date, horario_salida)
                ir.id as reservation_id,
                TO_DATE(ir.raw->>'fecha', 'DD/MM/YYYY') as reservation_date,
                ir.raw->>'horario_salida' as horario_salida,
                ir.email,
                ir.raw as extras_json
            FROM "Informacion Reservas" ir
            WHERE ir.raw->>'fecha' IS NOT NULL
            ORDER BY reservation_date, horario_salida, ir.created_at DESC
        )
        SELECT DISTINCT ON (pd.payment_id)
            pd.payment_id,
            pd.total_amount,
            pd.appointment_datetime,
            pd.status,
            pd.customer_name,
            pd.customer_email,
            r.reservation_id,
            r.email,
            r.extras_json,
            pd.payment_raw
        FROM payments_data pd
        LEFT JOIN reservations_with_extras r 
            ON DATE(pd.appointment_datetime) = r.reservation_date
            AND TO_CHAR(pd.appointment_datetime, 'HH24:MI:SS') = r.horario_salida
        ORDER BY pd.payment_id, pd.appointment_datetime
    """
    
    try:
        results = await db.execute_query(query, (target_date,))
        
        total_reservations = len(results)
        total_revenue_reservations = Decimal('0')
        total_revenue_extras = Decimal('0')
        
        revenue_details = []
        
        for row in results:
            reservation_total = Decimal(str(row.get('total_amount', 0) or 0))
            total_revenue_reservations += reservation_total
            
            # Extraer y calcular extras
            extras_json = row.get('extras_json')
            extras_list = extract_extras_from_json(
                extras_json, 
                prices, 
                category_aliases,
                missing_prices
            ) if extras_json else []
            
            extras_total = sum(extra['subtotal'] for extra in extras_list)
            total_revenue_extras += Decimal(str(extras_total))
            
            revenue_details.append({
                'payment_id': row.get('payment_id'),
                'customer_name': row.get('customer_name'),
                'email': row.get('email'),
                'appointment_datetime': row.get('appointment_datetime'),
                'status': row.get('status'),
                'reservation_total': float(reservation_total),
                'extras': extras_list,
                'extras_total': extras_total,
                'total_with_extras': float(reservation_total) + extras_total,
                'reservation_id': row.get('reservation_id')
            })
        
        total_revenue = total_revenue_reservations + total_revenue_extras
        
        result = {
            'date': target_date.strftime('%Y-%m-%d'),
            'total_reservations': total_reservations,
            'revenue_reservations': float(total_revenue_reservations),
            'revenue_extras': float(total_revenue_extras),
            'total_revenue': float(total_revenue),
            'details': revenue_details
        }
        
        logger.info(f"\nResumen de ingresos:")
        logger.info(f"   Total de reservas: {total_reservations}")
        logger.info(f"   Ingresos por reservas: ${total_revenue_reservations:,.0f}")
        logger.info(f"   Ingresos por extras: ${total_revenue_extras:,.0f}")
        logger.info(f"   TOTAL: ${total_revenue:,.0f}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error al calcular ingresos: {e}", exc_info=True)
        raise


def export_to_csv(revenue_data: Dict[str, Any], filename: str = None):
    """Exporta los resultados a un archivo CSV"""
    
    if filename is None:
        filename = f"ingresos_{revenue_data['date']}.csv"
    
    output_path = Path("scripts") / filename
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            writer.writerow(['Payment ID', 'Cliente', 'Email', 'Fecha/Hora', 'Estado', 
                           'Total Reserva', 'Extras', 'Total Extras', 'TOTAL'])
            
            for detail in revenue_data['details']:
                extras_str = '; '.join([
                    f"{e['nombre']} x{e['cantidad']} (${e['subtotal']:,.0f})"
                    for e in detail['extras']
                ]) if detail['extras'] else ''
                
                writer.writerow([
                    detail['payment_id'],
                    detail['customer_name'],
                    detail.get('email', ''),
                    detail['appointment_datetime'],
                    detail['status'],
                    f"${detail['reservation_total']:,.0f}",
                    extras_str,
                    f"${detail['extras_total']:,.0f}",
                    f"${detail['total_with_extras']:,.0f}"
                ])
            
            writer.writerow([])
            writer.writerow(['RESUMEN'])
            writer.writerow(['Fecha', revenue_data['date']])
            writer.writerow(['Total Reservas', revenue_data['total_reservations']])
            writer.writerow(['Ingresos Reservas', f"${revenue_data['revenue_reservations']:,.0f}"])
            writer.writerow(['Ingresos Extras', f"${revenue_data['revenue_extras']:,.0f}"])
            writer.writerow(['TOTAL', f"${revenue_data['total_revenue']:,.0f}"])
        
        logger.info(f"\n[INFO] Resultados exportados a: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"[ERROR] Error al exportar CSV: {e}")
        return None


async def main(start_date: date = None, end_date: date = None, export_csv_flag: bool = True):
    """Función principal"""
    
    logger.info("=== Iniciando calculo de ingresos diarios ===")
    
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = start_date
    
    settings = get_settings()
    db = DatabaseManager(settings.database_url, auto_setup=False)
    await db.initialize()
    
    # Set para acumular extras sin precio
    missing_prices: Set[str] = set()
    
    try:
        # Cargar precios desde BD
        prices = await load_prices_from_db(db)
        category_aliases = get_category_aliases()
        
        logger.info(f"\n{len(category_aliases)} categorias con aliases configuradas")
        logger.info("\n" + "="*60)
        
        # Procesar fechas
        current_date = start_date
        all_revenue_data = []
        
        while current_date <= end_date:
            revenue_data = await calculate_daily_revenue(
                db, 
                current_date, 
                prices, 
                category_aliases,
                missing_prices
            )
            all_revenue_data.append(revenue_data)
            
            # Mostrar detalles
            if revenue_data['details']:
                logger.info(f"\n[Detalles de reservas]")
                for i, detail in enumerate(revenue_data['details'], 1):
                    logger.info(f"\n   Reserva {i}:")
                    logger.info(f"      Payment ID: {detail['payment_id']}")
                    logger.info(f"      Cliente: {detail['customer_name']}")
                    logger.info(f"      Estado: {detail['status']}")
                    logger.info(f"      Fecha/Hora: {detail['appointment_datetime']}")
                    logger.info(f"      Total reserva: ${detail['reservation_total']:,.0f}")
                    
                    if detail['extras']:
                        logger.info(f"      Extras:")
                        for extra in detail['extras']:
                            categoria_info = f" [Cat: {extra['categoria']}]" if extra['categoria'] else " [SIN PRECIO]"
                            logger.info(
                                f"         - {extra['nombre']}: {extra['cantidad']} x "
                                f"${extra['precio_unitario']:,.0f} = ${extra['subtotal']:,.0f}{categoria_info}"
                            )
                        logger.info(f"      Total extras: ${detail['extras_total']:,.0f}")
                    
                    logger.info(f"      TOTAL CON EXTRAS: ${detail['total_with_extras']:,.0f}")
            else:
                logger.info("\n[INFO] No se encontraron reservas para la fecha especificada")
            
            if export_csv_flag and revenue_data['details']:
                export_to_csv(revenue_data)
            
            current_date += timedelta(days=1)
            if current_date <= end_date:
                logger.info("\n" + "="*60)
        
        # Resumen total si es un rango
        if start_date != end_date:
            logger.info("\n" + "="*60)
            logger.info("[RESUMEN TOTAL DEL RANGO]")
            total_reservations = sum(rd['total_reservations'] for rd in all_revenue_data)
            total_revenue = sum(rd['total_revenue'] for rd in all_revenue_data)
            total_extras = sum(rd['revenue_extras'] for rd in all_revenue_data)
            
            logger.info(f"   Periodo: {start_date} a {end_date}")
            logger.info(f"   Total reservas: {total_reservations}")
            logger.info(f"   Ingresos por reservas: ${sum(rd['revenue_reservations'] for rd in all_revenue_data):,.0f}")
            logger.info(f"   Ingresos por extras: ${total_extras:,.0f}")
            logger.info(f"   TOTAL: ${total_revenue:,.0f}")
        
        # Mostrar extras sin precio
        if missing_prices:
            logger.warning("\n" + "="*60)
            logger.warning("[ALERTA] EXTRAS SIN PRECIO ASIGNADO")
            logger.warning(f"Se encontraron {len(missing_prices)} extras sin precio:")
            for extra in sorted(missing_prices):
                logger.warning(f"   - {extra}")
            logger.warning("\nPor favor, actualice estos extras en:")
            logger.warning("   1. La tabla 'Precios Extras' de la base de datos, O")
            logger.warning("   2. La funcion get_category_aliases() en el script")
        
        logger.info("\n=== Proceso completado exitosamente ===")
        
    except Exception as e:
        logger.error(f"[ERROR] Error en el proceso: {e}", exc_info=True)
    finally:
        await db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Calcular ingresos diarios de ventas',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Ejemplos:
  python calculate_daily_revenue.py                    # Calcula para hoy
  python calculate_daily_revenue.py 2026-01-15        # Calcula para una fecha
  python calculate_daily_revenue.py 2026-01-01 2026-01-31  # Rango de fechas
  python calculate_daily_revenue.py 2026-01-15 --no-csv    # Sin exportar CSV
        '''
    )
    
    parser.add_argument(
        'start_date',
        nargs='?',
        type=str,
        help='Fecha de inicio (formato: YYYY-MM-DD). Por defecto: hoy'
    )
    
    parser.add_argument(
        'end_date',
        nargs='?',
        type=str,
        help='Fecha de fin (formato: YYYY-MM-DD). Por defecto: igual a start_date'
    )
    
    parser.add_argument(
        '--no-csv',
        action='store_true',
        help='No exportar resultados a CSV'
    )
    
    args = parser.parse_args()
    
    # Parsear fechas
    start_date = None
    end_date = None
    
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Fecha invalida '{args.start_date}'. Use formato YYYY-MM-DD")
            sys.exit(1)
    
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Fecha invalida '{args.end_date}'. Use formato YYYY-MM-DD")
            sys.exit(1)
    
    asyncio.run(main(start_date, end_date, export_csv_flag=not args.no_csv))
