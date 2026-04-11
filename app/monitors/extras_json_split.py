"""
Desglose ingresos/costos desde extras_json (claves aloj* = alojamiento).

Ingresos: qty × unit_price por línea (columnas ingreso_* en all_appointments).

Costos variables: **tabla "Precios Extras"** (costo unitario por nombre de extra) × cantidad
en cada línea del JSON. Si no hay match en la tabla, se intenta reparto desde
costo_operativo_variable (columna all_appointments) proporcional a ingresos.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.utils.extras_pricing import find_cost_for_extra


def _to_float(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def line_amount(item: Any) -> float:
    """Monto de una línea: qty * unit_price si es dict; si no, amount/total o número plano."""
    if isinstance(item, dict):
        if item.get("unit_price") is not None:
            q = item.get("qty")
            if q is None:
                q = item.get("quantity")
            return _to_float(q) * _to_float(item.get("unit_price"))
        return _to_float(item.get("amount") or item.get("total"))
    return _to_float(item)


def parse_qty(val: Any) -> float:
    """Cantidad para costo/ingreso por línea."""
    if isinstance(val, dict):
        q = val.get("qty")
        if q is None:
            q = val.get("quantity")
        if q is None:
            if val.get("unit_price") is not None or val.get("name") is not None:
                return 1.0
            return 0.0
        return max(0.0, _to_float(q))
    try:
        return max(0.0, _to_float(val))
    except (TypeError, ValueError):
        return 0.0


def line_cost_from_precios_extras(
    key: str,
    val: Any,
    costs_dict: Dict[str, float],
) -> float:
    """
    Costo total de línea = costo unitario (tabla Precios Extras) × qty.
    Si no hay match en tabla, opcional unit_cost en el JSON.
    """
    qty = parse_qty(val)
    if qty <= 0:
        return 0.0
    uc = find_cost_for_extra(str(key), costs_dict)
    if uc > 0:
        return uc * qty
    if isinstance(val, dict) and val.get("unit_cost") is not None:
        return qty * _to_float(val.get("unit_cost"))
    return 0.0


def split_extras_json_keys(extras: Any) -> Tuple[float, float]:
    """
    Suma qty*unit_price por clave: claves que empiezan con 'aloj' -> alojamiento, resto extras.
    """
    if not extras or not isinstance(extras, dict):
        return 0.0, 0.0
    extras_only = 0.0
    aloj = 0.0
    for key, val in extras.items():
        amt = line_amount(val)
        k = str(key).lower()
        if k.startswith("aloj"):
            aloj += amt
        else:
            extras_only += amt
    return extras_only, aloj


def split_extras_json_costs_from_precios(
    extras: Any,
    costs_dict: Dict[str, float],
) -> Tuple[float, float]:
    """Suma costos por línea usando Precios Extras; mismas claves aloj* que ingresos."""
    if not extras or not isinstance(extras, dict) or not costs_dict:
        return 0.0, 0.0
    extras_only = 0.0
    aloj = 0.0
    for key, val in extras.items():
        c = line_cost_from_precios_extras(key, val, costs_dict)
        k = str(key).lower()
        if k.startswith("aloj"):
            aloj += c
        else:
            extras_only += c
    return extras_only, aloj


def _is_aloj_key(key: Any) -> bool:
    return str(key).lower().startswith("aloj")


def split_row_extras_income(extras_json: Any, ingreso_extras: float) -> Tuple[float, float]:
    """
    Ingreso extras vs aloj según JSON. Si la suma de montos por línea cubre ingreso_extras,
    se usa tal cual. Si no (p. ej. valores solo cantidad como {"aloj__x": 1}), el saldo no
    va siempre a extras: si todas las claves son aloj*, el saldo va a alojamiento; si todas
    son no-aloj, a extras; si hay mezcla, proporcional por montos parseados o por cantidades.
    """
    e, a = split_extras_json_keys(extras_json)
    inc = _to_float(ingreso_extras)
    parsed = e + a
    if parsed >= inc - 0.005:
        return e, a
    rem = inc - parsed
    if not extras_json or not isinstance(extras_json, dict):
        e += rem
        return e, a
    aloj_keys = [k for k in extras_json if _is_aloj_key(k)]
    other_keys = [k for k in extras_json if not _is_aloj_key(k)]
    if aloj_keys and not other_keys:
        a += rem
        return e, a
    if other_keys and not aloj_keys:
        e += rem
        return e, a
    if parsed > 0.005:
        a += rem * (a / parsed)
        e += rem * (e / parsed)
        return e, a
    wa = sum(parse_qty(extras_json[k]) for k in aloj_keys)
    we = sum(parse_qty(extras_json[k]) for k in other_keys)
    wtot = wa + we
    if wtot > 0.005:
        a += rem * (wa / wtot)
        e += rem * (we / wtot)
    else:
        e += rem
    return e, a


def split_row_variable_cost_fallback(
    extras_json: Any,
    ingreso_extras_only: float,
    ingreso_aloj: float,
    costo_variable: float,
) -> Tuple[float, float]:
    """Reparte costo_operativo_variable cuando no hay costos desde Precios Extras."""
    cv = _to_float(costo_variable)
    if cv <= 0:
        return 0.0, 0.0
    e = _to_float(ingreso_extras_only)
    a = _to_float(ingreso_aloj)
    t_inc = e + a
    if t_inc > 0.005:
        return cv * (e / t_inc), cv * (a / t_inc)
    return cv, 0.0


def compute_row_variable_costs(
    extras_json: Any,
    e_inc: float,
    a_inc: float,
    costo_variable: float,
    costs_dict: Optional[Dict[str, float]],
) -> Tuple[float, float]:
    """
    Costos variables extras vs aloj: primero suma desde Precios Extras × qty.
    Si eso da 0 pero hay costo_operativo_variable en la fila, reparto proporcional a ingresos.
    """
    ce, ca = 0.0, 0.0
    if costs_dict:
        ce, ca = split_extras_json_costs_from_precios(extras_json, costs_dict)
    if ce + ca > 0.005:
        return ce, ca
    return split_row_variable_cost_fallback(extras_json, e_inc, a_inc, costo_variable)


def aggregate_financial_rows(
    rows: List[Dict[str, Any]],
    costs_dict: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Suma ingresos y costos variables por fila (all_appointments).

    total_ingresos = reservas + extras + aloj (no usa la columna ingreso_total) para que
    coincida con el desglose; si ingreso_total difiere de ingreso_reserva + ingreso_extras
    en la BD, el informe sigue siendo aritméticamente coherente.
    """
    n = len(rows)
    if n == 0:
        return {
            "total_reservas_count": 0,
            "total_ingreso_reservas": 0.0,
            "total_ingreso_extras": 0.0,
            "total_ingreso_aloj": 0.0,
            "total_ingresos": 0.0,
            "total_costo_variable_extras": 0.0,
            "total_costo_variable_aloj": 0.0,
            "promedio_por_reserva": 0.0,
            "dias_con_reservas": 0,
        }
    total_ingreso_reservas = 0.0
    total_ingreso_extras = 0.0
    total_ingreso_aloj = 0.0
    total_cv_e = 0.0
    total_cv_a = 0.0
    fechas = set()
    for r in rows:
        if r.get("fecha") is not None:
            fechas.add(r["fecha"])
        ir = _to_float(r.get("ingreso_reserva"))
        ie = _to_float(r.get("ingreso_extras"))
        ej = r.get("extras_json")
        cv = _to_float(r.get("costo_operativo_variable"))
        total_ingreso_reservas += ir
        e_inc, a_inc = split_row_extras_income(ej, ie)
        total_ingreso_extras += e_inc
        total_ingreso_aloj += a_inc
        ve, va = compute_row_variable_costs(ej, e_inc, a_inc, cv, costs_dict)
        total_cv_e += ve
        total_cv_a += va
    total_ingresos = (
        total_ingreso_reservas + total_ingreso_extras + total_ingreso_aloj
    )
    return {
        "total_reservas_count": n,
        "total_ingreso_reservas": total_ingreso_reservas,
        "total_ingreso_extras": total_ingreso_extras,
        "total_ingreso_aloj": total_ingreso_aloj,
        "total_ingresos": total_ingresos,
        "total_costo_variable_extras": total_cv_e,
        "total_costo_variable_aloj": total_cv_a,
        "promedio_por_reserva": (total_ingresos / n) if n else 0.0,
        "dias_con_reservas": len(fechas),
    }
