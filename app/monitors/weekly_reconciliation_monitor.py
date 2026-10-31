"""
Monitor de Cuadratura Semanal: abonos del banco (flujo_caja_actual) vs pagos de la app (all_appointments.pagos).

Se envía los miércoles (el flujo de caja se actualiza a mano los martes). Empareja CADA abono del banco con
uno o más pagos de la app (mismo método, fecha cercana, monto neto de comisión) en vez de comparar totales,
porque los totales esconden los desfases (ej. Transbank del fin de semana llega el lunes).
"""
from datetime import date, datetime, time as dt_time, timedelta
from itertools import combinations
from typing import Any, Dict, List, Optional

import pytz

from app.logger import logger
from app.monitors.base_monitor import BaseMonitor

# categor_a_2 del banco -> método de la app. GetYourGuide/Viator no se emparejan (no hay pago en la app).
BANK_METHOD = {
    "ingreso mercadopago": "mercadopago",
    "ingreso transferencia": "transferencia",
    "transbank": "transbank",
}
# Razón banco/app aceptada por método (neto de comisión). Transferencia llega íntegra.
RATIO = {
    "transferencia": (0.999, 1.001),
    "mercadopago": (0.93, 1.002),
    "transbank": (0.90, 1.002),
}
METHOD_LABEL = {"mercadopago": "MercadoPago", "transferencia": "Transferencia", "transbank": "Transbank"}
MAX_SUBSET = 5
LAG_BEFORE = 10  # el pago en la app puede estar hasta N días antes del abono
LAG_AFTER = 3
LOOKBACK = 28  # se empareja desde N días antes de la semana para no reutilizar un pago en dos semanas


def _to_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _clp(n: float) -> str:
    return "$" + f"{round(n):,}".replace(",", ".")


def reconcile(bank_rows: List[Dict], app_rows: List[Dict], start: date, end: date) -> Dict[str, Any]:
    """bank_rows: fecha, abonos, descripci_n, categor_a_2. app_rows: booking_id, nombre_cliente, paseo, method, amount, pdate."""
    bank = []
    for r in bank_rows:
        method = BANK_METHOD.get((r["categor_a_2"] or "").lower())
        bank.append({**r, "fecha": _to_date(r["fecha"]), "abonos": float(r["abonos"]), "method": method})
    app = [{**r, "pdate": _to_date(r["pdate"]), "amount": float(r["amount"]), "method": (r["method"] or "").lower(), "used": False}
           for r in app_rows]
    in_week = lambda d: start <= d <= end  # noqa: E731

    matches, unmatched_bank = [], []
    for b in sorted((x for x in bank if x["method"]), key=lambda x: (x["fecha"], x["abonos"])):
        lo, hi = RATIO[b["method"]]
        pool = sorted(
            (p for p in app if not p["used"] and p["method"] == b["method"]
             and -LAG_AFTER <= (b["fecha"] - p["pdate"]).days <= LAG_BEFORE),
            key=lambda p: abs((b["fecha"] - p["pdate"]).days))[:12]
        best = None
        for size in range(1, MAX_SUBSET + 1):
            for s in combinations(pool, size):
                gross = sum(p["amount"] for p in s)
                if gross <= 0 or not lo <= b["abonos"] / gross <= hi:
                    continue
                score = size * 1000 + sum(abs((b["fecha"] - p["pdate"]).days) for p in s)
                if best is None or score < best[0]:
                    best = (score, s, gross)
        if best:
            for p in best[1]:
                p["used"] = True
            matches.append({"bank": b, "payments": list(best[1]), "gross": best[2], "ratio": b["abonos"] / best[2]})
        else:
            unmatched_bank.append(b)

    w_matches = [m for m in matches if in_week(m["bank"]["fecha"])]
    w_unmatched_bank = [b for b in unmatched_bank if in_week(b["fecha"])]
    unmatched_app = [p for p in app if not p["used"] and in_week(p["pdate"]) and p["method"] in METHOD_LABEL]
    by_method = {}
    for m in METHOD_LABEL:
        by_method[m] = {
            "bank": sum(b["abonos"] for b in bank if b["method"] == m and in_week(b["fecha"])),
            "app": sum(p["amount"] for p in app if p["method"] == m and in_week(p["pdate"])),
            "unmatched_bank": sum(b["abonos"] for b in w_unmatched_bank if b["method"] == m),
            "unmatched_app": sum(p["amount"] for p in unmatched_app if p["method"] == m),
        }
    return {
        "start": start, "end": end, "by_method": by_method, "matches": w_matches,
        "unmatched_bank": w_unmatched_bank, "unmatched_app": unmatched_app,
        "other_bank": [b for b in bank if not b["method"] and in_week(b["fecha"])],
    }


def render_html(r: Dict[str, Any]) -> str:
    # Sin saltos de línea: EmailNotifier._format_html convierte "\n" en <br>.
    td = "padding:6px 10px;border-bottom:1px solid #eee;"
    th = "padding:6px 10px;text-align:left;background:#f4f6f8;"
    ok = not r["unmatched_bank"] and not r["unmatched_app"]
    head = (f"<h2>Cuadratura semanal {r['start']:%d-%m} al {r['end']:%d-%m-%Y}</h2>"
            + ("<p style='color:#198754'><b>Todo calza.</b></p>" if ok else
               f"<p style='color:#dc3545'><b>{len(r['unmatched_bank'])} abono(s) del banco sin pago en la app y "
               f"{len(r['unmatched_app'])} pago(s) de la app sin abono.</b></p>"))
    rows = "".join(
        f"<tr><td style='{td}'>{METHOD_LABEL[m]}</td><td style='{td}'>{_clp(v['bank'])}</td><td style='{td}'>{_clp(v['app'])}</td>"
        f"<td style='{td}color:#dc3545'>{_clp(v['unmatched_bank'])}</td><td style='{td}color:#dc3545'>{_clp(v['unmatched_app'])}</td></tr>"
        for m, v in r["by_method"].items())
    summary = (f"<table style='border-collapse:collapse;font-size:14px'><tr><th style='{th}'>Método</th><th style='{th}'>Banco</th>"
               f"<th style='{th}'>App (bruto)</th><th style='{th}'>Banco sin app</th><th style='{th}'>App sin banco</th></tr>{rows}</table>")
    ub = "".join(f"<li>{b['fecha']:%d-%m} · {METHOD_LABEL[b['method']]} · <b>{_clp(b['abonos'])}</b> · «{b['descripci_n']}»</li>"
                 for b in r["unmatched_bank"]) or "<li>Ninguno</li>"
    ua = "".join(f"<li>{p['pdate']:%d-%m} · {METHOD_LABEL[p['method']]} · <b>{_clp(p['amount'])}</b> · {p['nombre_cliente']} "
                 f"(paseo {_to_date(p['paseo']):%d-%m}, reserva {p['booking_id']})</li>" for p in r["unmatched_app"]) or "<li>Ninguno</li>"
    mt = "".join(f"<li>{m['bank']['fecha']:%d-%m} · {METHOD_LABEL[m['bank']['method']]} {_clp(m['bank']['abonos'])} ← "
                 + " + ".join(f"{p['nombre_cliente']} {_clp(p['amount'])}" for p in m["payments"]) + "</li>" for m in r["matches"]) or "<li>Ninguno</li>"
    other = "".join(f"<li>{b['fecha']:%d-%m} · {b['categor_a_2']} · {_clp(b['abonos'])}</li>" for b in r["other_bank"])
    return (head + summary
            + "<h3>Abonos en el banco sin pago en la app</h3><p style='font-size:13px;color:#666'>Registra el pago en la app o corrige el método/fecha.</p><ul>" + ub + "</ul>"
            + "<h3>Pagos de la app sin abono en el banco</h3><p style='font-size:13px;color:#666'>Puede llegar la próxima semana (Transbank) o estar mal anotado.</p><ul>" + ua + "</ul>"
            + "<h3>Emparejados</h3><ul style='font-size:13px'>" + mt + "</ul>"
            + (f"<h3>Otros abonos (no se cuadran)</h3><ul>{other}</ul>" if other else ""))


class WeeklyReconciliationMonitor(BaseMonitor):
    """Envía la cuadratura de la semana anterior los miércoles a la hora configurada."""

    def __init__(self, settings, config, notification_manager):
        super().__init__(settings, config, notification_manager)
        self.check_interval = config.get("check_interval", 1800)
        hour, minute = map(int, config.get("report_time", "08:00").split(":"))
        self.report_time = dt_time(hour, minute)
        self.weekday = int(config.get("weekday", 2))  # 0=lunes ... 2=miércoles
        self.last_sent_date: Optional[date] = None
        self.timezone = pytz.timezone(config.get("timezone", "America/Santiago"))

    async def check(self) -> List[Dict[str, Any]]:
        now = datetime.now(pytz.UTC).astimezone(self.timezone)
        if now.weekday() != self.weekday or now.time() < self.report_time or self.last_sent_date == now.date():
            return []
        return [{"date": now.date()}]

    async def detect_changes(self, current_state: List[Dict[str, Any]]) -> None:
        for req in current_state:
            today = req["date"]
            monday = today - timedelta(days=today.weekday() + 7)
            await self.send_report(monday)
            self.last_sent_date = today

    async def build_report(self, monday: date) -> Dict[str, Any]:
        sunday = monday + timedelta(days=6)
        bank = await self.db.execute_query(
            """SELECT fecha, descripci_n, abonos, categor_a_2 FROM flujo_caja_actual
               WHERE fecha BETWEEN %s AND %s AND abonos > 0 AND categor_a_1 = 'Ingreso Operativo'""",
            (monday - timedelta(days=LOOKBACK), sunday + timedelta(days=LAG_AFTER)))
        app = await self.db.execute_query(
            """SELECT a.id AS booking_id, a.nombre_cliente, a.fecha AS paseo, lower(x.value->>'method') AS method,
                      (x.value->>'amount')::numeric AS amount, (x.value->>'date')::date AS pdate
               FROM all_appointments a, jsonb_array_elements(coalesce(a.pagos, '[]'::jsonb)) x
               WHERE (x.value->>'date')::date BETWEEN %s AND %s
                 AND coalesce(a.status, '') NOT ILIKE '%%cancel%%' AND (x.value->>'amount')::numeric > 0""",
            (monday - timedelta(days=LOOKBACK + LAG_BEFORE), sunday + timedelta(days=LAG_AFTER)))
        return reconcile(bank, app, monday, sunday)

    async def send_report(self, monday: date) -> None:
        logger.info(f"🏦 Generando cuadratura semanal desde {monday}")
        report = await self.build_report(monday)
        await self.send_notification(message=render_html(report), priority="high", channel="email")
