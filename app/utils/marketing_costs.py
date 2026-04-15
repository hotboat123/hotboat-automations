"""Costos de marketing: compatible con vista marketing_costs_daily o daily_marketing_summary, y con la tabla marketing_costs."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple, Optional

from app.logger import logger


def _empty() -> Dict[str, Any]:
    return {"total_marketing": 0.0, "num_ads": 0}


def _row_to_dict(row: Any) -> Dict[str, Any]:
    if not row:
        return _empty()
    return {
        "total_marketing": float(row.get("total_marketing") or 0),
        "num_ads": int(row.get("num_ads") or 0),
    }


async def _try_queries(db, queries: List[Tuple[str, tuple]], context: str) -> Dict[str, Any]:
    """Ejecuta consultas en orden hasta que una devuelva fila sin error."""
    for sql, params in queries:
        try:
            row = await db.execute_single(sql, params)
            if row is not None:
                return _row_to_dict(row)
        except Exception as e:
            logger.debug("marketing %s: omitiendo consulta (%s)", context, e)
            continue
    logger.warning(
        "marketing %s: ninguna consulta devolvió datos (¿tabla/vista marketing o migración distinta?)",
        context,
    )
    return _empty()


async def fetch_marketing_for_date(db, target_date: date) -> Dict[str, Any]:
    """
    Totales del día: prueba en orden
    1) Vista marketing_costs_daily (migración 004)
    2) Vista daily_marketing_summary (migración 003)
    3) Tabla marketing_costs con cost_date + amount_spent (004)
    4) Tabla marketing_costs con dia + importe_gastado (003)
    """
    queries: List[Tuple[str, tuple]] = [
        (
            """
            SELECT COALESCE(total_spent, 0) AS total_marketing, COALESCE(num_ads, 0) AS num_ads
            FROM marketing_costs_daily
            WHERE cost_date = %s
            """,
            (target_date,),
        ),
        (
            """
            SELECT COALESCE(costo_total, 0) AS total_marketing, COALESCE(num_anuncios, 0) AS num_ads
            FROM daily_marketing_summary
            WHERE dia = %s
            """,
            (target_date,),
        ),
        (
            """
            SELECT COALESCE(SUM(amount_spent), 0) AS total_marketing, COUNT(*)::bigint AS num_ads
            FROM marketing_costs
            WHERE cost_date = %s
            """,
            (target_date,),
        ),
        (
            """
            SELECT COALESCE(SUM(importe_gastado), 0) AS total_marketing, COUNT(*)::bigint AS num_ads
            FROM marketing_costs
            WHERE dia = %s
            """,
            (target_date,),
        ),
    ]
    return await _try_queries(db, queries, f"día {target_date}")


async def fetch_marketing_by_day(db, start_date: date, end_date: date) -> Dict[date, float]:
    """
    Gasto de marketing por día en el rango (clave = date, valor = float CLP).
    Prueba las dos migraciones posibles; devuelve {} si no hay datos o la tabla no existe.
    """
    queries_multi: List[Tuple[str, tuple]] = [
        (
            """
            SELECT cost_date AS dia, COALESCE(SUM(amount_spent), 0) AS spend
            FROM marketing_costs
            WHERE cost_date BETWEEN %s AND %s
            GROUP BY cost_date
            """,
            (start_date, end_date),
        ),
        (
            """
            SELECT dia, COALESCE(SUM(importe_gastado), 0) AS spend
            FROM marketing_costs
            WHERE dia BETWEEN %s AND %s
            GROUP BY dia
            """,
            (start_date, end_date),
        ),
    ]
    for sql, params in queries_multi:
        try:
            rows = await db.execute_query(sql, params)
            if rows:
                return {r["dia"]: float(r["spend"] or 0) for r in rows}
        except Exception as e:
            logger.debug("marketing_by_day: omitiendo consulta (%s)", e)
    return {}


async def fetch_marketing_for_period(db, start_date: date, end_date: date) -> Dict[str, Any]:
    """Totales del periodo (mismas fuentes que fetch_marketing_for_date)."""
    queries: List[Tuple[str, tuple]] = [
        (
            """
            SELECT COALESCE(SUM(total_spent), 0) AS total_marketing, COALESCE(SUM(num_ads), 0) AS num_ads
            FROM marketing_costs_daily
            WHERE cost_date BETWEEN %s AND %s
            """,
            (start_date, end_date),
        ),
        (
            """
            SELECT COALESCE(SUM(costo_total), 0) AS total_marketing, COALESCE(SUM(num_anuncios), 0) AS num_ads
            FROM daily_marketing_summary
            WHERE dia BETWEEN %s AND %s
            """,
            (start_date, end_date),
        ),
        (
            """
            SELECT COALESCE(SUM(amount_spent), 0) AS total_marketing, COUNT(*)::bigint AS num_ads
            FROM marketing_costs
            WHERE cost_date BETWEEN %s AND %s
            """,
            (start_date, end_date),
        ),
        (
            """
            SELECT COALESCE(SUM(importe_gastado), 0) AS total_marketing, COUNT(*)::bigint AS num_ads
            FROM marketing_costs
            WHERE dia BETWEEN %s AND %s
            """,
            (start_date, end_date),
        ),
    ]
    return await _try_queries(db, queries, f"periodo {start_date}..{end_date}")
