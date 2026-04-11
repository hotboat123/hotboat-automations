"""
Analisis semanal de Meta Ads: hallazgos y recomendaciones automaticas.
Se integra al reporte semanal via fetch_and_analyze().
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from app.logger import logger


# ─── Queries ──────────────────────────────────────────────────────────────────

async def _fetch_adsets(db, start: date, end: date) -> List[Dict]:
    try:
        return await db.execute_query(
            """
            SELECT
              COALESCE(NULLIF(TRIM("Nombre del conjunto de anuncios"),''),'(sin conjunto)') AS nombre,
              SUM("Importe gastado (CLP)")                          AS spend,
              SUM("Impresiones")                                    AS impressions,
              SUM("Clics en el enlace")                             AS link_clicks,
              SUM("Conversaciones con mensajes iniciadas")          AS conversations,
              SUM("Alcance")                                        AS reach
            FROM v_meta_ads_analytics
            WHERE "Día" BETWEEN %s AND %s
            GROUP BY 1
            ORDER BY 2 DESC
            """,
            (start, end),
        ) or []
    except Exception as e:
        logger.debug("meta_ads_analysis adsets: %s", e)
        return []


async def _fetch_ads(db, start: date, end: date) -> List[Dict]:
    try:
        return await db.execute_query(
            """
            SELECT
              COALESCE(NULLIF(TRIM("Nombre del anuncio"),''),'(sin nombre)') AS nombre,
              SUM("Importe gastado (CLP)")                          AS spend,
              SUM("Impresiones")                                    AS impressions,
              SUM("Clics en el enlace")                             AS link_clicks,
              SUM("Conversaciones con mensajes iniciadas")          AS conversations,
              SUM("Alcance")                                        AS reach
            FROM v_meta_ads_analytics
            WHERE "Día" BETWEEN %s AND %s
            GROUP BY 1
            ORDER BY 2 DESC
            """,
            (start, end),
        ) or []
    except Exception as e:
        logger.debug("meta_ads_analysis ads: %s", e)
        return []


# ─── Metricas derivadas ────────────────────────────────────────────────────────

def _f(x: Any) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _enrich(rows: List[Dict]) -> List[Dict]:
    for r in rows:
        sp  = _f(r.get("spend"))
        imp = _f(r.get("impressions"))
        clk = _f(r.get("link_clicks"))
        cv  = _f(r.get("conversations"))
        r["ctr"]          = (clk / imp * 100) if imp > 0 else 0.0
        r["cpc"]          = (sp  / clk)        if clk > 0 else 0.0
        r["cpm"]          = (sp  / imp * 1000) if imp > 0 else 0.0
        r["cost_per_msg"] = (sp  / cv)          if cv  > 0 else None
        r["convs_per_1k"] = (cv  / sp  * 1000) if sp  > 0 else 0.0
    return rows


# ─── Hallazgos y recomendaciones ──────────────────────────────────────────────

def _generate_text(
    adset_rows: List[Dict],
    ad_rows: List[Dict],
    total_ventas: int,
) -> str:
    """Genera el bloque de texto para el email semanal."""

    total_spend = sum(_f(r.get("spend")) for r in adset_rows)
    total_convs = sum(_f(r.get("conversations")) for r in adset_rows)

    # Filtrados con suficientes datos para ser significativos
    adsets_ok = [r for r in adset_rows if _f(r.get("conversations")) >= 5  and r.get("cost_per_msg")]
    ads_ok    = [r for r in ad_rows    if _f(r.get("conversations")) >= 3  and r.get("cost_per_msg")]

    best_adset  = min(adsets_ok, key=lambda r: r["cost_per_msg"]) if adsets_ok else None
    worst_adset = max(adsets_ok, key=lambda r: r["cost_per_msg"]) if len(adsets_ok) > 1 else None
    best_ad     = min(ads_ok,    key=lambda r: r["cost_per_msg"]) if ads_ok    else None
    worst_ad    = max(ads_ok,    key=lambda r: r["cost_per_msg"]) if len(ads_ok) > 1 else None

    # Anuncios con CTR alto pero pocas conversaciones
    high_ctr_low_conv = [
        r for r in ad_rows
        if r.get("ctr", 0) >= 3.0
        and _f(r.get("conversations")) < 5
        and _f(r.get("impressions")) >= 500
    ]

    # Anuncios que consumen >15% del gasto con menos de 5 conversaciones
    threshold = total_spend * 0.15
    wasteful = [
        r for r in ad_rows
        if _f(r.get("spend")) >= threshold
        and _f(r.get("conversations")) < 5
        and total_spend > 0
    ]

    # Anuncio mas eficiente en convs/$
    efficiency = sorted(
        [(r, r["convs_per_1k"]) for r in ad_rows if _f(r.get("spend")) > 0 and _f(r.get("conversations")) >= 3],
        key=lambda x: x[1],
        reverse=True,
    )

    # ── Encabezado ──
    lines = [
        "",
        "=" * 40,
        "META ADS — HALLAZGOS Y RECOMENDACIONES",
        "",
        f"Gasto Meta en el periodo: ${total_spend:,.0f} CLP",
        f"Conversaciones en mensajes: {total_convs:.0f}",
        f"Reservas confirmadas: {total_ventas}",
    ]
    if total_spend > 0 and total_ventas > 0:
        lines.append(f"Costo Meta por reserva: ${total_spend / total_ventas:,.0f} CLP")

    # ── Hallazgos ──
    lines += ["", "--- HALLAZGOS CLAVE ---"]
    n = 1
    findings: List[str] = []

    if best_adset:
        findings.append(
            f"{n}. Mejor publico: '{best_adset['nombre']}' "
            f"— ${best_adset['cost_per_msg']:,.0f}/msg "
            f"({_f(best_adset['conversations']):.0f} conversaciones)"
        )
        n += 1

    if worst_adset and best_adset and worst_adset["nombre"] != best_adset["nombre"]:
        ratio = worst_adset["cost_per_msg"] / best_adset["cost_per_msg"]
        findings.append(
            f"{n}. Publico menos eficiente: '{worst_adset['nombre']}' "
            f"— ${worst_adset['cost_per_msg']:,.0f}/msg "
            f"({ratio:.1f}x mas caro que el mejor publico)"
        )
        n += 1

    if best_ad:
        findings.append(
            f"{n}. Mejor anuncio: '{best_ad['nombre']}' "
            f"— ${best_ad['cost_per_msg']:,.0f}/msg"
        )
        n += 1

    if worst_ad and best_ad and worst_ad["nombre"] != best_ad["nombre"]:
        ratio_ad = worst_ad["cost_per_msg"] / best_ad["cost_per_msg"]
        findings.append(
            f"{n}. Anuncio menos eficiente: '{worst_ad['nombre']}' "
            f"— ${worst_ad['cost_per_msg']:,.0f}/msg "
            f"({ratio_ad:.1f}x vs el mejor)"
        )
        n += 1

    for r in high_ctr_low_conv[:2]:
        findings.append(
            f"{n}. '{r['nombre']}' tiene CTR {r['ctr']:.1f}% "
            f"pero solo {_f(r.get('conversations')):.0f} conversaciones — "
            f"el clic no se convierte en mensaje"
        )
        n += 1

    for r in wasteful[:2]:
        pct = _f(r.get("spend")) / total_spend * 100
        findings.append(
            f"{n}. '{r['nombre']}' consume el {pct:.0f}% del gasto total "
            f"(${_f(r.get('spend')):,.0f}) con solo "
            f"{_f(r.get('conversations')):.0f} conversaciones"
        )
        n += 1

    if not findings:
        findings.append("Sin datos suficientes para hallazgos esta semana.")

    lines += findings

    # ── Recomendaciones ──
    lines += ["", "--- RECOMENDACIONES ---"]
    n = 1
    recs: List[str] = []

    if best_adset:
        recs.append(
            f"{n}. Aumentar presupuesto en '{best_adset['nombre']}': "
            f"es el publico con menor costo/msg (${best_adset['cost_per_msg']:,.0f})"
        )
        n += 1

    if worst_adset and best_adset and worst_adset["nombre"] != best_adset["nombre"]:
        recs.append(
            f"{n}. Reducir o pausar '{worst_adset['nombre']}': "
            f"costo/msg {ratio:.1f}x superior al mejor publico"
        )
        n += 1

    if high_ctr_low_conv:
        r = high_ctr_low_conv[0]
        recs.append(
            f"{n}. '{r['nombre']}' genera clics ({r['ctr']:.1f}% CTR) "
            f"pero pocas conversaciones — probar CTA directo a WhatsApp/DM "
            f"o agregar boton de contacto"
        )
        n += 1

    if wasteful:
        r = wasteful[0]
        recs.append(
            f"{n}. Revisar creatividad de '{r['nombre']}': "
            f"alto gasto con muy pocas conversaciones — "
            f"probar nuevo copy/imagen o pausar"
        )
        n += 1

    if efficiency:
        top = efficiency[0][0]
        recs.append(
            f"{n}. Escalar '{top['nombre']}': "
            f"el de mayor retorno en conversaciones por peso "
            f"({efficiency[0][1]:.1f} convs por $1.000 gastados)"
        )
        n += 1

    if not recs:
        recs.append("Sin datos suficientes para recomendaciones esta semana.")

    lines += recs
    lines.append("=" * 40)

    return "\n".join(lines)


# ─── Punto de entrada publico ──────────────────────────────────────────────────

async def fetch_and_analyze(db, start: date, end: date, total_ventas: int) -> str:
    """
    Consulta v_meta_ads_analytics para el periodo y devuelve el bloque de texto
    listo para incluir en el email del reporte semanal.
    Devuelve cadena vacia si la vista no existe o no hay datos.
    """
    try:
        adset_rows = _enrich(await _fetch_adsets(db, start, end))
        ad_rows    = _enrich(await _fetch_ads(db, start, end))
        if not adset_rows and not ad_rows:
            logger.info("meta_ads_analysis: sin datos para %s - %s", start, end)
            return ""
        return _generate_text(adset_rows, ad_rows, total_ventas)
    except Exception as e:
        logger.warning("meta_ads_analysis fallo: %s", e)
        return ""
