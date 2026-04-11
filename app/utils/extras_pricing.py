"""
Costos y precios unitarios desde la tabla "Precios Extras" (columna raw).
Misma lógica que scripts/sync_reservas_con_extras.py para consistencia.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().strip()
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = "".join(c if c.isalnum() or c.isspace() else "_" for c in text)
    text = "_".join(text.split())
    return text


def _parse_money(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(".", "").replace(",", "").strip() or 0)
    except (ValueError, AttributeError):
        return 0.0


def build_costs_dict_from_precios_extras_rows(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """Arma diccionario nombre normalizado -> costo unitario desde filas SELECT ... FROM \"Precios Extras\"."""
    costs: Dict[str, float] = {}
    for row in rows:
        raw = row.get("raw")
        if not raw:
            continue
        extra_name = raw.get("Extra", "")
        if not extra_name:
            continue
        costo = _parse_money(raw.get("costo", "0"))
        normalized = normalize_text(extra_name)
        if normalized in costs:
            costs[normalized] = max(costs[normalized], costo)
        else:
            costs[normalized] = costo
    return costs


def find_cost_for_extra(extra_name: str, costs_dict: Dict[str, float]) -> float:
    """Costo unitario de un extra; prueba variantes de clave (incl. aloj__)."""
    if not extra_name:
        return 0.0
    extra_normalized = normalize_text(extra_name)
    if extra_normalized in costs_dict:
        return costs_dict[extra_normalized]

    # Variantes para claves tipo aloj__slug-o-slug
    variants = [extra_name]
    low = str(extra_name).lower()
    if low.startswith("aloj__"):
        variants.append(extra_name[6:])
        variants.append(extra_name.split("__", 1)[-1])
    for v in variants:
        n = normalize_text(v)
        if n in costs_dict:
            return costs_dict[n]

    mappings = {
        "tabla_2_personas": "tabla_2",
        "tabla_4_personas": "tabla_1",
        "tabla_1_persona": "tabla_1",
        "video_15_segundos": "video_15_seg",
        "video_60_segundos": "video_1_min",
        "champana_riccadonna_ruby": "champana_riccadona",
        "champana_riccadonna_asti": "champana_riccadona",
        "champana_riccadonna_moscato_rose": "champana_riccadona",
        "champana_riccadonna": "champana_riccadona",
        "hora_extra": "hora_extra",
        "hora_adicional": "hora_extra",
        "hora_extra_de_navegacion": "hora_extra",
    }
    if extra_normalized in mappings:
        mapped_name = mappings[extra_normalized]
        if mapped_name in costs_dict:
            return costs_dict[mapped_name]

    words = [w for w in extra_normalized.split("_") if len(w) > 2]
    best_match = 0.0
    best_score = 0
    for bd_name, bd_cost in costs_dict.items():
        if bd_cost == 0:
            continue
        score = sum(1 for word in words if word in bd_name)
        if score > best_score:
            best_score = score
            best_match = bd_cost
    if best_score >= 1:
        return best_match
    return 0.0


async def fetch_precios_extras_costs_dict(db) -> Dict[str, float]:
    """Carga costos unitarios desde la tabla \"Precios Extras\" (async)."""
    rows = await db.execute_query('SELECT raw FROM "Precios Extras"')
    return build_costs_dict_from_precios_extras_rows(rows or [])
