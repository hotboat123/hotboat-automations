"""
Monitor de Cuadratura Semanal: abonos del banco (flujo_caja_actual) vs pagos de la app (all_appointments.pagos).

Se envía los miércoles (el flujo de caja se actualiza a mano los martes). Empareja CADA abono del banco con
uno o más pagos de la app (mismo método, fecha cercana, monto neto de comisión) en vez de comparar totales,
porque los totales esconden los desfases (ej. Transbank del fin de semana llega el lunes).
"""
from datetime import date, datetime, time as dt_time, timedelta
from itertools import combinations
from typing import Any, Dict, List, Optional

import unicodedata

import pytz

from app.logger import logger
from app.monitors.base_monitor import BaseMonitor

# categor_a_2 del banco -> método de la app. GetYourGuide/Viator no se emparejan (no hay pago en la app).
BANK_METHOD = {
    "ingreso mercadopago": "mercadopago",
    "ingreso transferencia": "transferencia",
    "transbank": "transbank",
}
# Razón banco/app aceptada por método (neto de comisión). Medido en octubre 2026 contra el portal de Transbank:
# Transbank 98,4%-99,3% (crédito/débito), MercadoPago 94,4%-96,5%, transferencia 100%. Las bandas no se tocan
# para que un abono de Transbank no se confunda con uno de MercadoPago.
RATIO = {
    "transferencia": (0.999, 1.001),
    "mercadopago": (0.93, 0.972),
    "transbank": (0.975, 0.995),
}
# Comisión + IVA que descuenta Transbank, medida contra el portal (oct-2026): crédito $1.219 sobre $76.990;
# débito/prepago $858 sobre $131.067. Con el medio de pago de cada venta, el abono se explica al peso.
TBK_RATE = {"credito": 0.015834, "debito": 0.007378, "prepago": 0.007378}
TBK_NET_TOL = 3  # pesos
TBK_SALE_WINDOW_BEFORE = 12  # días entre la venta Transbank y su abono (no hay abonos fin de semana)
TBK_BOOKING_BEFORE = timedelta(minutes=45)  # la reserva web se crea justo antes de pagar
TBK_BOOKING_AFTER = timedelta(minutes=5)
TBK_AMOUNT_TOL_DAYS = 3
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
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



def _norm_name(v: Any) -> str:
    t = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def _same_person(a: Any, b: Any) -> bool:
    ta, tb = set(_norm_name(a).split()), set(_norm_name(b).split())
    return bool(ta and tb) and len(ta & tb) >= min(2, len(ta), len(tb))


def _tbk_net(sale: Dict) -> Optional[float]:
    medio = unicodedata.normalize("NFKD", str(sale.get("medio") or "")).encode("ascii", "ignore").decode().lower()
    rate = TBK_RATE.get(medio)
    return sale["amount"] * (1 - rate) if rate is not None else None


def _tbk_pass(bank: List[Dict], app: List[Dict], sales: List[Dict], bookings: List[Dict]) -> List[Dict]:
    """Cruce Transbank con el portal: abono -> ventas (monto bruto exacto) -> pago/reserva de la app.

    Cada venta se resuelve por, en orden: (1) código de autorización guardado en la app, (2) monto exacto de un pago
    Transbank de la app con fecha cercana, (3) la reserva creada a la hora de la venta (la reserva web se crea justo antes de
    pagar) y su pago de ese monto registrado con otro método o en otra reserva, (4) reserva sin pago registrado.
    """
    lo, hi = RATIO["transbank"]
    for sale in sales:
        sale["used"] = False
    links = []
    for b in sorted((x for x in bank if x["method"] in ("transbank", "transferencia", "mercadopago")), key=lambda x: (x["fecha"], x["abonos"])):
        other_cat = b["method"] != "transbank"
        pool = [x for x in sales if not x["used"] and 1 <= (b["fecha"] - x["dt"].date()).days <= TBK_SALE_WINDOW_BEFORE]
        pool.sort(key=lambda x: (b["fecha"] - x["dt"].date()).days)
        best = None
        for size in range(1, 5):
            for sub in combinations(pool[:10], size):
                nets = [_tbk_net(x) for x in sub]
                if all(n is not None for n in nets):
                    # exacto: suma de netos por medio de pago == abono (±$3)
                    if abs(sum(nets) - b["abonos"]) <= TBK_NET_TOL:
                        score = size * 1000 + sum((b["fecha"] - x["dt"].date()).days for x in sub)
                        if best is None or score < best[0]:
                            best = (score, sub)
        if not best and not other_cat:  # sin medio de pago: banda de razón
            for size in range(1, 5):
                for sub in combinations(pool[:10], size):
                    gross = sum(x["amount"] for x in sub)
                    if lo <= b["abonos"] / gross <= hi:
                        score = size * 1000 + sum((b["fecha"] - x["dt"].date()).days for x in sub)
                        if best is None or score < best[0]:
                            best = (score, sub)
        if not best:
            if not other_cat:
                links.append({"bank": b, "sales": []})
            continue
        for x in best[1]:
            x["used"] = True
        links.append({"bank": b, "cat_wrong": other_cat, "sales": [_resolve_sale(x, app, bookings) for x in best[1]]})
    return links


def _resolve_sale(sale: Dict, app: List[Dict], bookings: List[Dict]) -> Dict:
    day = sale["dt"].date()
    res = {"sale": sale, "status": "sin_reserva", "payment": None, "booking": None}
    free = [p for p in app if not p["used"]]
    hit = next((p for p in free if p.get("auth") and p["auth"] == sale["code"]), None)         or next((p for p in free if p["method"] == "transbank" and p["amount"] == sale["amount"]
                 and abs((p["pdate"] - day).days) <= TBK_AMOUNT_TOL_DAYS and not p["final"]), None)
    if hit:
        hit["used"] = True
        res.update(status="ok", payment=hit)
        return res
    near = [b for b in bookings if -TBK_BOOKING_AFTER <= (sale["dt"] - b["created"]) <= TBK_BOOKING_BEFORE]
    near.sort(key=lambda b: sale["dt"] - b["created"])
    res["booking"] = near[0] if near else None
    for p in free:
        if p["amount"] != sale["amount"] or abs((p["pdate"] - day).days) > 30 or p["final"]:
            continue
        # pago del mismo monto en otro método: la misma persona de la reserva creada a esa hora, o la misma reserva
        if near and (p["booking_id"] in {b["id"] for b in near} or _same_person(p["nombre_cliente"], near[0]["nombre_cliente"])):
            p["used"] = True
            res.update(status="metodo", payment=p)
            return res
    if near:
        res["status"] = "sin_pago"
    return res


def reconcile(bank_rows: List[Dict], app_rows: List[Dict], start: date, end: date,
              tbk_sales: Optional[List[Dict]] = None, bookings: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """bank_rows: fecha, abonos, descripci_n, categor_a_2. app_rows: booking_id, nombre_cliente, paseo, method, amount, pdate."""
    bank = []
    for r in bank_rows:
        method = BANK_METHOD.get((r["categor_a_2"] or "").lower())
        bank.append({**r, "fecha": _to_date(r["fecha"]), "abonos": float(r["abonos"]), "method": method})
    app = [{**r, "pdate": _to_date(r["pdate"]), "amount": float(r["amount"]), "method": (r["method"] or "").lower(), "used": False, "auth": (r.get("auth") or "").strip(),
            # Segundo pago hecho el día del paseo (se paga al volver, con la máquina presencial): nunca es Transbank.
            "final": int(r.get("idx") or 1) >= 2 and _to_date(r["pdate"]) == _to_date(r["paseo"])}
           for r in app_rows]
    in_week = lambda d: start <= d <= end  # noqa: E731

    tbk_links = _tbk_pass(bank, app, tbk_sales, bookings or []) if tbk_sales else []
    tbk_done = {id(l["bank"]) for l in tbk_links if l["sales"]}

    matches, unmatched_bank = [], []
    for b in sorted((x for x in bank if x["method"] and id(x) not in tbk_done), key=lambda x: (x["fecha"], x["abonos"])):
        lo, hi = RATIO[b["method"]]
        pool = sorted(
            (p for p in app if not p["used"] and p["method"] == b["method"]
             and not (p["final"] and b["method"] == "transbank")
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

    # Método distinto: abono sin pago del mismo método, pero que calza con un pago de la app anotado con OTRO método.
    # Se prueba contra la banda del método del banco (la app tiene mal el método) y contra la banda del método de
    # la app (el banco tiene mal la categoría). Si hay más de una opción se listan todas como alternativas.
    mismatches, still_unmatched = [], []
    for b in unmatched_bank:
        lo, hi = RATIO[b["method"]]
        near = [p for p in app if not p["used"] and p["method"] != b["method"]
                and not (p["final"] and b["method"] == "transbank")
                and -LAG_AFTER <= (b["fecha"] - p["pdate"]).days <= LAG_BEFORE]
        cands = []
        for p in near:
            ratio = b["abonos"] / p["amount"] if p["amount"] > 0 else 0
            if lo <= ratio <= hi:
                wrong = "app"  # el banco está bien, la app tiene mal el método
            elif p["method"] in RATIO and not (p["final"] and p["method"] == "transbank")                     and RATIO[p["method"]][0] <= ratio <= RATIO[p["method"]][1]:
                wrong = "banco"  # la app está bien, el banco tiene mal la categoría
            else:
                continue
            cands.append({"payments": [p], "gross": p["amount"], "ratio": ratio, "wrong": wrong,
                          "score": abs((b["fecha"] - p["pdate"]).days)})
        if not cands:
            pool = sorted((p for p in near if p["amount"] <= b["abonos"] / lo),
                          key=lambda p: abs((b["fecha"] - p["pdate"]).days))[:12]
            for size in (2, 3):
                for sub in combinations(pool, size):
                    gross = sum(p["amount"] for p in sub)
                    if lo <= b["abonos"] / gross <= hi:
                        cands.append({"payments": list(sub), "gross": gross, "ratio": b["abonos"] / gross, "wrong": "app",
                                      "score": 1000 * size + sum(abs((b["fecha"] - p["pdate"]).days) for p in sub)})
        if cands:
            cands.sort(key=lambda c: c["score"])
            best = cands[0]
            for p in best["payments"]:
                p["used"] = True
            mismatches.append({"bank": b, "payments": best["payments"], "gross": best["gross"], "ratio": best["ratio"],
                               "wrong": best["wrong"], "alternatives": cands[1:4]})
        else:
            still_unmatched.append(b)
    unmatched_bank = still_unmatched

    w_tbk = [l for l in tbk_links if l["sales"] and in_week(l["bank"]["fecha"])]
    w_matches = [m for m in matches if in_week(m["bank"]["fecha"])]
    w_mismatches = [m for m in mismatches if in_week(m["bank"]["fecha"])]
    w_unmatched_bank = [b for b in unmatched_bank if in_week(b["fecha"])]
    unmatched_app = [p for p in app if not p["used"] and in_week(p["pdate"]) and p["method"] in METHOD_LABEL]
    by_method = {}
    for m in METHOD_LABEL:
        by_method[m] = {
            "bank": sum(b["abonos"] for b in bank if b["method"] == m and in_week(b["fecha"])),
            "app": sum(p["amount"] for p in app if p["method"] == m and in_week(p["pdate"])),
            "unmatched_bank": sum(b["abonos"] for b in w_unmatched_bank if b["method"] == m)
            + (sum(l["bank"]["abonos"] for l in w_tbk if m == "transbank" and any(x["status"] != "ok" for x in l["sales"])) if tbk_sales else 0),
            "unmatched_app": sum(p["amount"] for p in unmatched_app if p["method"] == m),
        }

    # Detalle día a día: cada movimiento del banco y de la app con su estado.
    status_bank = {id(m["bank"]): "ok" for m in matches}
    status_bank.update({id(m["bank"]): "metodo" for m in mismatches})
    for l in tbk_links:
        sts = {x["status"] for x in l["sales"]}
        if sts:
            status_bank[id(l["bank"])] = "metodo" if l.get("cat_wrong") else "ok" if sts == {"ok"} else "metodo" if "metodo" in sts and sts <= {"ok", "metodo"} else "falta_app"
    tbk_ok_ids = {id(x["payment"]) for l in tbk_links for x in l["sales"] if x["status"] == "ok"}
    tbk_mm_ids = {id(x["payment"]) for l in tbk_links for x in l["sales"] if x["status"] == "metodo"}
    days: Dict[date, Dict[str, list]] = {}
    for b in bank:
        if in_week(b["fecha"]):
            st = "otro" if not b["method"] else status_bank.get(id(b), "falta_app")
            days.setdefault(b["fecha"], {"bank": [], "app": []})["bank"].append({**b, "status": st})
    mismatch_ids = {id(p) for m in mismatches for p in m["payments"]}
    matched_ids = {id(p) for m in matches for p in m["payments"]} | tbk_ok_ids
    mismatch_ids |= tbk_mm_ids
    for p in app:
        if in_week(p["pdate"]):
            st = "ok" if id(p) in matched_ids else "metodo" if id(p) in mismatch_ids else "falta_banco"
            if p["method"] not in METHOD_LABEL and st == "falta_banco":
                st = "efectivo"
            days.setdefault(p["pdate"], {"bank": [], "app": []})["app"].append({**p, "status": st})
    final_tbk = [p for p in app if p["final"] and p["method"] == "transbank" and in_week(p["pdate"])]
    return {
        "final_tbk": final_tbk, "tbk": w_tbk,
        "start": start, "end": end, "by_method": by_method, "matches": w_matches, "mismatches": w_mismatches, "days": dict(sorted(days.items())),
        "unmatched_bank": w_unmatched_bank, "unmatched_app": unmatched_app,
        "other_bank": [b for b in bank if not b["method"] and in_week(b["fecha"])],
    }


def render_html(r: Dict[str, Any]) -> str:
    # Sin saltos de línea: EmailNotifier._format_html convierte "\n" en <br>.
    td = "padding:6px 10px;border-bottom:1px solid #eee;"
    th = "padding:6px 10px;text-align:left;background:#f4f6f8;"
    ok = not r["unmatched_bank"] and not r["unmatched_app"] and not r["mismatches"] and not r["final_tbk"] and all(x["status"] == "ok" for l in r.get("tbk", []) for x in l["sales"])
    head = (f"<h2>Cuadratura semanal {r['start']:%d-%m} al {r['end']:%d-%m-%Y}</h2>"
            + ("<p style='color:#198754'><b>Todo calza.</b></p>" if ok else
               f"<p style='color:#dc3545'><b>{len(r['unmatched_bank'])} abono(s) del banco sin pago en la app y "
               f"{len(r['unmatched_app'])} pago(s) de la app sin abono"
               + (f", y {len(r['mismatches'])} con método distinto" if r["mismatches"] else "") + ".</b></p>"))
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
    def _mm(m):
        who = "la app tiene mal el método" if m["wrong"] == "app" else "la categoría del banco está mal"
        txt = (f"<li>{m['bank']['fecha']:%d-%m} · el banco recibió <b>{_clp(m['bank']['abonos'])}</b> como <b>{METHOD_LABEL[m['bank']['method']]}</b>; "
               "en la app calza con " + " + ".join(f"{p['method']} {_clp(p['amount'])} ({p['nombre_cliente']}, reserva {p['booking_id']}, {p['pdate']:%d-%m})" for p in m["payments"])
               + f" (banco/app {m['ratio'] * 100:.1f}%) → probable: {who}."
               + (" Es el pago del día del paseo: no puede ser Transbank, probablemente MercadoPago (máquina presencial)."
                  if any(p["final"] and p["method"] == "transbank" for p in m["payments"]) else ""))
        if m["alternatives"]:
            alts = "; ".join(" + ".join(f"{p['method']} {_clp(p['amount'])} ({p['nombre_cliente']})" for p in a["payments"])
                             + f" ({a['ratio'] * 100:.1f}%)" for a in m["alternatives"])
            txt += f" <i>Ambiguo, también podría ser: {alts}.</i>"
        return txt + "</li>"
    mm = "".join(_mm(m) for m in r["mismatches"])
    icon = {"ok": "✅", "metodo": "🔁", "falta_app": "❌", "falta_banco": "⏳", "otro": "➖", "efectivo": "💵"}
    day_html = ""
    for d, ev in r["days"].items():
        items = "".join(f"<li>{icon[x['status']]} Banco · {x['categor_a_2']} · {_clp(x['abonos'])} · {x['descripci_n']}</li>" for x in ev["bank"])             + "".join(f"<li>{icon[x['status']]} App · {x['method']} · {_clp(x['amount'])} · {x['nombre_cliente']}</li>" for x in ev["app"])
        day_html += f"<p style='margin:10px 0 2px'><b>{DIAS[d.weekday()]} {d:%d-%m}</b></p><ul style='margin:0;font-size:13px'>{items}</ul>"
    ft = "".join(f"<li>{p['pdate']:%d-%m} · <b>{_clp(p['amount'])}</b> · {p['nombre_cliente']} (reserva {p['booking_id']}) · el segundo pago del día del paseo "
                 "no puede ser Transbank: cambiar a MercadoPago (máquina) o transferencia</li>" for p in r["final_tbk"])
    tb = ""
    for l in r.get("tbk", []):
        b = l["bank"]
        parts = []
        for x in l["sales"]:
            sl, pay, bk = x["sale"], x["payment"], x["booking"]
            when = f"venta {sl['dt']:%d-%m %H:%M} {_clp(sl['amount'])}"
            if x["status"] == "ok":
                parts.append(f"✅ {when} ← {pay['nombre_cliente']} (reserva {pay['booking_id']})")
            elif x["status"] == "metodo":
                parts.append(f"🔁 {when}: la reserva creada a esa hora es <b>{bk['nombre_cliente']}</b> (reserva {bk['id']}, {bk['status']}, creada {bk['created']:%H:%M}). "
                             f"Su pago está en la reserva {pay['booking_id']} como <b>{pay['method']}</b> ({pay['pdate']:%d-%m}) → <b>cambiar el método a Transbank</b>")
            elif x["status"] == "sin_pago":
                parts.append(f"❌ {when}: la reserva creada a esa hora es <b>{bk['nombre_cliente']}</b> (reserva {bk['id']}, {bk['status']}) pero <b>no tiene este pago registrado</b> → registrarlo como Transbank")
            else:
                parts.append(f"❌ {when} (código {sl['code']}): <b>no hay reserva ni pago en la app</b> → buscar al cliente en el portal y registrarlo")
        cw = (f" · <b>el banco lo tiene como {METHOD_LABEL[b['method']]}: es Transbank, cambiar la categoría</b>" if l.get("cat_wrong") else "")
        tb += f"<li>Abono {b['fecha']:%d-%m} · <b>{_clp(b['abonos'])}</b>{cw}<ul>" + "".join(f"<li>{x}</li>" for x in parts) + "</ul></li>"
    legend = "<p style='font-size:12px;color:#666'>✅ calza · 🔁 método distinto · ❌ banco sin app · ⏳ app sin banco (aún) · 💵 efectivo/otro · ➖ no se cuadra (ej. GetYourGuide)</p>"
    return (head + summary
            + (f"<h3>Posible método equivocado en la app</h3><ul>{mm}</ul>" if mm else "")
            + (f"<h3>Transbank: cruce con el portal (hora de la venta ↔ hora de creación de la reserva)</h3><ul style='font-size:13px'>{tb}</ul>" if tb else "")
            + (f"<h3>Segundo pago anotado como Transbank</h3><ul>{ft}</ul>" if ft else "")
            + "<h3>Abonos en el banco sin pago en la app</h3><p style='font-size:13px;color:#666'>Registra el pago en la app o corrige el método/fecha.</p><ul>" + ub + "</ul>"
            + "<h3>Pagos de la app sin abono en el banco</h3><p style='font-size:13px;color:#666'>Puede llegar la próxima semana (Transbank) o estar mal anotado.</p><ul>" + ua + "</ul>"
            + "<h3>Emparejados</h3><ul style='font-size:13px'>" + mt + "</ul>"
            + (f"<h3>Otros abonos (no se cuadran)</h3><ul>{other}</ul>" if other else "")
            + "<h3>Detalle día a día</h3>" + legend + day_html)


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
                      (x.value->>'amount')::numeric AS amount, (x.value->>'date')::date AS pdate, x.idx AS idx, x.value->>'authorization_code' AS auth
               FROM all_appointments a, jsonb_array_elements(coalesce(a.pagos, '[]'::jsonb)) WITH ORDINALITY x(value, idx)
               WHERE (x.value->>'date')::date BETWEEN %s AND %s
                 AND coalesce(a.status, '') NOT ILIKE '%%cancel%%' AND (x.value->>'amount')::numeric > 0""",
            (monday - timedelta(days=LOOKBACK + LAG_BEFORE), sunday + timedelta(days=LAG_AFTER)))
        sales = await self._load_tbk_sales(monday - timedelta(days=LOOKBACK), sunday + timedelta(days=LAG_AFTER))
        bookings = []
        if sales:
            first = min(x["dt"] for x in sales) - TBK_BOOKING_BEFORE
            last = max(x["dt"] for x in sales) + TBK_BOOKING_AFTER
            rows = await self.db.execute_query(
                """SELECT id, nombre_cliente, status, payment_status, fecha, created_at FROM all_appointments
                   WHERE created_at BETWEEN %s AND %s""",
                (self.timezone.localize(first).astimezone(pytz.UTC), self.timezone.localize(last).astimezone(pytz.UTC)))
            bookings = [{**r, "created": r["created_at"].astimezone(self.timezone).replace(tzinfo=None)} for r in rows]
        return reconcile(bank, app, monday, sunday, tbk_sales=sales, bookings=bookings)

    async def _load_tbk_sales(self, d_from: date, d_to: date) -> List[Dict[str, Any]]:
        """Ventas del portal Transbank (fecha_hora en hora de Chile, monto bruto, código de autorización).
        Se leen de la tabla `transbank_ventas` si existe; si no, el cruce usa solo montos aproximados."""
        try:
            rows = await self.db.execute_query(
                """SELECT fecha_hora, monto, codigo, medio FROM transbank_ventas
                   WHERE fecha_hora::date BETWEEN %s AND %s AND coalesce(tipo, 'venta') = 'venta'""", (d_from, d_to))
        except Exception:
            return []
        return [{"dt": r["fecha_hora"], "amount": float(r["monto"]), "code": str(r["codigo"] or "").strip(), "medio": r.get("medio")} for r in rows]

    async def send_report(self, monday: date) -> None:
        logger.info(f"🏦 Generando cuadratura semanal desde {monday}")
        report = await self.build_report(monday)
        await self.send_notification(message=render_html(report), priority="high", channel="email")
