"""
Reporte semanal Meta Ads: análisis por público y por anuncio.
Evolución: gasto diario Meta vs ventas reales (all_appointments.fecha, confirmed).

Uso:
  python scripts/weekly_meta_report.py
  python scripts/weekly_meta_report.py --start 2026-04-04 --end 2026-04-10
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import psycopg

# ─── Paleta ───────────────────────────────────────────────────────────────────
BLUE   = "#2E86AB"
ORANGE = "#F18F01"
GREEN  = "#27AE60"
RED    = "#C73E1D"
PURPLE = "#8E44AD"
GREY   = "#BDC3C7"


# ─── CLI ──────────────────────────────────────────────────────────────────────
def parse_args():
    today = date.today()
    # Default: esta semana lunes → ayer (o lunes → domingo si es lunes)
    weekday = today.weekday()  # 0=lunes … 6=domingo
    this_monday = today - timedelta(days=weekday)
    default_end = today - timedelta(days=1) if weekday > 0 else today - timedelta(days=1)
    default_start = this_monday

    p = argparse.ArgumentParser(description="Reporte semanal Meta Ads")
    p.add_argument("--start", default=str(default_start),
                   help="Inicio YYYY-MM-DD (def: lunes de esta semana)")
    p.add_argument("--end", default=str(default_end),
                   help="Fin YYYY-MM-DD (def: ayer)")
    return p.parse_args()


# ─── Queries ──────────────────────────────────────────────────────────────────
def query_all(conn, start: str, end: str):
    with conn.cursor() as cur:

        # Por conjunto de anuncios (público)
        cur.execute("""
            SELECT
              COALESCE(NULLIF(TRIM("Nombre del conjunto de anuncios"),''),'(sin conjunto)') AS nombre,
              SUM("Importe gastado (CLP)")                          AS spend,
              SUM("Impresiones")                                    AS impressions,
              SUM("Clics en el enlace")                             AS link_clicks,
              SUM("Conversaciones con mensajes iniciadas")          AS conversations,
              SUM("Artículos agregados al carrito")                 AS add_to_cart,
              SUM("Alcance")                                        AS reach
            FROM v_meta_ads_analytics
            WHERE "Día" BETWEEN %s AND %s
            GROUP BY 1
            ORDER BY 2 DESC
        """, (start, end))
        cols = [d[0] for d in cur.description]
        adset_rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        # Por anuncio
        cur.execute("""
            SELECT
              COALESCE(NULLIF(TRIM("Nombre del anuncio"),''),'(sin nombre)') AS nombre,
              SUM("Importe gastado (CLP)")                          AS spend,
              SUM("Impresiones")                                    AS impressions,
              SUM("Clics en el enlace")                             AS link_clicks,
              SUM("Conversaciones con mensajes iniciadas")          AS conversations,
              SUM("Artículos agregados al carrito")                 AS add_to_cart,
              SUM("Alcance")                                        AS reach
            FROM v_meta_ads_analytics
            WHERE "Día" BETWEEN %s AND %s
            GROUP BY 1
            ORDER BY 2 DESC
        """, (start, end))
        cols = [d[0] for d in cur.description]
        ad_rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        # Gasto diario total Meta
        cur.execute("""
            SELECT
              "Día"                                        AS dia,
              SUM("Importe gastado (CLP)")                 AS spend,
              SUM("Conversaciones con mensajes iniciadas") AS conversations
            FROM v_meta_ads_analytics
            WHERE "Día" BETWEEN %s AND %s
            GROUP BY 1
            ORDER BY 1
        """, (start, end))
        cols = [d[0] for d in cur.description]
        daily_meta = [dict(zip(cols, r)) for r in cur.fetchall()]

        # Reservas confirmadas por día
        cur.execute("""
            SELECT fecha, COUNT(*) AS ventas
            FROM all_appointments
            WHERE fecha BETWEEN %s AND %s AND status = 'confirmed'
            GROUP BY 1
            ORDER BY 1
        """, (start, end))
        cols = [d[0] for d in cur.description]
        daily_appts = [dict(zip(cols, r)) for r in cur.fetchall()]

    return adset_rows, ad_rows, daily_meta, daily_appts


def enrich(rows):
    for r in rows:
        sp  = float(r.get("spend") or 0)
        imp = float(r.get("impressions") or 0)
        clk = float(r.get("link_clicks") or 0)
        cv  = float(r.get("conversations") or 0)
        r["ctr"]          = (clk / imp * 100) if imp > 0 else 0.0
        r["cpc"]          = (sp / clk)         if clk > 0 else 0.0
        r["cpm"]          = (sp / imp * 1000)  if imp > 0 else 0.0
        r["cost_per_msg"] = (sp / cv)           if cv  > 0 else None
    return rows


# ─── Helpers ──────────────────────────────────────────────────────────────────
def shorten(s: str, n: int = 30) -> str:
    s = str(s)
    return (s[:n] + "…") if len(s) > n else s


def fmt_k(x, _=None):
    return f"{x/1000:.1f}k" if x >= 1000 else f"{x:.0f}"


def dual_hbar(ax, labels, vals, color, xlabel, show_labels=True):
    """Barras horizontales simples con etiquetas de valor."""
    ax.barh(range(len(labels)), vals, color=color, alpha=0.82)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=8)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_k))
    ax.grid(axis="x", alpha=0.2)
    if show_labels:
        for i, v in enumerate(vals):
            if v > 0:
                ax.text(v * 1.01, i, fmt_k(v), va="center", fontsize=7)


def grouped_dual_bar(ax1, ax2, labels, vals1, vals2,
                     label1, label2, c1=BLUE, c2=ORANGE):
    """Barras agrupadas con doble eje Y, replicando el estilo del dashboard Meta."""
    x = np.arange(len(labels))
    w = 0.38
    ax1.bar(x - w/2, vals1, w, color=c1, alpha=0.85, label=label1)
    ax2.bar(x + w/2, vals2, w, color=c2, alpha=0.75, label=label2)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=38, ha="right", fontsize=8)
    ax1.set_ylabel(label1, color=c1, fontsize=8)
    ax2.set_ylabel(label2, color=c2, fontsize=8)
    ax1.tick_params(axis="y", labelcolor=c1, labelsize=7)
    ax2.tick_params(axis="y", labelcolor=c2, labelsize=7)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_k))
    ax1.grid(axis="y", alpha=0.2)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper right")


# ─── Figura: sección (público o anuncio) ──────────────────────────────────────
def make_section_figure(rows, title: str, out_path: Path, start: str, end: str):
    if not rows:
        print(f"  [AVISO] Sin datos para: {title}")
        return

    labels  = [shorten(r["nombre"], 30) for r in rows]
    spends  = [float(r["spend"] or 0) for r in rows]
    ctrs    = [r["ctr"] for r in rows]
    cpcs    = [r["cpc"] for r in rows]
    cpms    = [r["cpm"] for r in rows]
    convs   = [float(r["conversations"] or 0) for r in rows]
    carts   = [float(r.get("add_to_cart") or 0) for r in rows]
    cost_msg = [r["cost_per_msg"] if r["cost_per_msg"] is not None else 0 for r in rows]

    fig = plt.figure(figsize=(17, 13))
    fig.patch.set_facecolor("#F8F9FA")
    fig.suptitle(f"{title}\n{start} → {end}",
                 fontsize=14, fontweight="bold", y=0.99)

    gs = fig.add_gridspec(2, 2, hspace=0.55, wspace=0.42,
                          left=0.08, right=0.95, top=0.92, bottom=0.05)

    # Panel 1 (arriba izq): Gasto vs CPC — doble eje, barras agrupadas
    ax1  = fig.add_subplot(gs[0, 0])
    ax1b = ax1.twinx()
    ax1.set_title("Importe gastado (CLP)  vs  CPC", fontsize=10, pad=6)
    grouped_dual_bar(ax1, ax1b, labels, spends, cpcs,
                     "Gasto (CLP)", "CPC (CLP)", BLUE, ORANGE)

    # Panel 2 (arriba der): CTR vs CPM — doble eje
    ax2  = fig.add_subplot(gs[0, 1])
    ax2b = ax2.twinx()
    ax2.set_title("CTR %  vs  CPM (CLP / 1000 imp)", fontsize=10, pad=6)
    grouped_dual_bar(ax2, ax2b, labels, ctrs, cpms,
                     "CTR %", "CPM", PURPLE, ORANGE)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.2f}"))

    # Panel 3 (abajo izq): Conversaciones en mensajes + artículos al carrito
    ax3  = fig.add_subplot(gs[1, 0])
    ax3b = ax3.twinx()
    ax3.set_title("Conversaciones de mensajes  vs  Artículos al carrito", fontsize=10, pad=6)
    grouped_dual_bar(ax3, ax3b, labels, convs, carts,
                     "Conversaciones", "Al carrito", GREEN, ORANGE)
    ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    ax3b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))

    # Panel 4 (abajo der): Costo por conversación (horizontal, verde→rojo según eficiencia)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_title("Costo por conversación iniciada (menor = mejor)", fontsize=10, pad=6)
    percentiles = sorted([v for v in cost_msg if v > 0])
    p33 = percentiles[len(percentiles) // 3] if percentiles else 1
    p66 = percentiles[2 * len(percentiles) // 3] if percentiles else 1
    bar_colors = []
    for v in cost_msg:
        if v == 0:
            bar_colors.append(GREY)
        elif v <= p33:
            bar_colors.append(GREEN)
        elif v <= p66:
            bar_colors.append(ORANGE)
        else:
            bar_colors.append(RED)
    ax4.barh(range(len(labels)), cost_msg, color=bar_colors, alpha=0.85)
    ax4.set_yticks(range(len(labels)))
    ax4.set_yticklabels(labels, fontsize=8)
    ax4.invert_yaxis()
    ax4.set_xlabel("CLP / conversación", fontsize=8)
    ax4.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_k))
    ax4.grid(axis="x", alpha=0.2)
    for i, v in enumerate(cost_msg):
        if v > 0:
            ax4.text(v * 1.01, i, fmt_k(v), va="center", fontsize=7)
    from matplotlib.patches import Patch
    legend_items = [
        Patch(color=GREEN,  label="Mejor tercio"),
        Patch(color=ORANGE, label="Tercio medio"),
        Patch(color=RED,    label="Peor tercio"),
        Patch(color=GREY,   label="Sin convs."),
    ]
    ax4.legend(handles=legend_items, fontsize=7, loc="lower right")

    plt.savefig(out_path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  {out_path.name}")


# ─── Figura: evolución gasto vs reservas ──────────────────────────────────────
def make_evolution_figure(daily_meta, daily_appts, out_path: Path,
                          start: str, end: str):
    from datetime import datetime as dt
    start_d = dt.strptime(start, "%Y-%m-%d").date()
    end_d   = dt.strptime(end,   "%Y-%m-%d").date()

    all_dates: list[date] = []
    d = start_d
    while d <= end_d:
        all_dates.append(d)
        d += timedelta(days=1)

    meta_by_d  = {r["dia"]:   float(r["spend"] or 0) for r in daily_meta}
    appts_by_d = {r["fecha"]: int(r["ventas"]   or 0) for r in daily_appts}

    spends = [meta_by_d.get(d, 0)  for d in all_dates]
    ventas = [appts_by_d.get(d, 0) for d in all_dates]
    xlbls  = [d.strftime("%d/%m") for d in all_dates]
    xs     = range(len(all_dates))

    fig, ax1 = plt.subplots(figsize=(15, 5))
    fig.patch.set_facecolor("#F8F9FA")
    ax2 = ax1.twinx()

    # Gasto Meta (área + línea)
    ax1.fill_between(xs, spends, alpha=0.15, color=BLUE)
    ax1.plot(xs, spends, color=BLUE, linewidth=2.2, marker="o",
             markersize=5, label="Gasto Meta (CLP)")
    for i, (x, v) in enumerate(zip(xs, spends)):
        if v > 0:
            ax1.annotate(fmt_k(v), (x, v), textcoords="offset points",
                         xytext=(0, 7), ha="center", fontsize=7, color=BLUE)

    # Reservas confirmadas (barras + línea)
    ax2.bar(xs, ventas, color=GREEN, alpha=0.40, width=0.55, label="Reservas")
    ax2.plot(xs, ventas, color=GREEN, linewidth=1.8, marker="s",
             markersize=6, linestyle="--", label="Reservas (línea)")
    for i, (x, v) in enumerate(zip(xs, ventas)):
        if v > 0:
            ax2.annotate(str(v), (x, v), textcoords="offset points",
                         xytext=(0, 6), ha="center", fontsize=8,
                         fontweight="bold", color=GREEN)

    ax1.set_xticks(list(xs))
    ax1.set_xticklabels(xlbls, rotation=45, ha="right", fontsize=8)
    ax1.set_ylabel("Gasto Meta (CLP)", color=BLUE, fontsize=9)
    ax2.set_ylabel("Reservas confirmadas", color=GREEN, fontsize=9)
    ax1.tick_params(axis="y", labelcolor=BLUE, labelsize=8)
    ax2.tick_params(axis="y", labelcolor=GREEN, labelsize=8)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_k))
    ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax1.grid(axis="y", alpha=0.2)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=9, loc="upper left")

    total_spend = sum(spends)
    total_ventas = sum(ventas)
    ax1.set_title(
        f"Evolución: Gasto Meta vs Reservas confirmadas  ·  {start} → {end}\n"
        f"Gasto total: ${total_spend:,.0f} CLP   |   Reservas periodo: {total_ventas}",
        fontsize=11, fontweight="bold"
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close()
    print(f"  {out_path.name}")


# ─── CSV ──────────────────────────────────────────────────────────────────────
def save_csv(rows, path: Path):
    if not rows:
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ─── Informe Markdown ─────────────────────────────────────────────────────────
def save_report(adset_rows, ad_rows, daily_meta, daily_appts,
                out_path: Path, start: str, end: str):

    total_spend  = sum(float(r["spend"] or 0) for r in adset_rows)
    total_convs  = sum(float(r["conversations"] or 0) for r in adset_rows)
    total_ventas = sum(int(r["ventas"] or 0) for r in daily_appts)

    def section(title, rows):
        lines = [f"## {title}", ""]
        if not rows:
            lines += ["Sin datos.", ""]
            return lines
        lines += [
            "| # | Nombre | Gasto CLP | Impresiones | CTR % | Msgs | Costo/msg |",
            "|---|--------|-----------|-------------|-------|------|-----------|",
        ]
        for i, r in enumerate(rows, 1):
            cm = f"${r['cost_per_msg']:,.0f}" if r.get("cost_per_msg") else "—"
            lines.append(
                f"| {i} | {str(r['nombre'])[:50]} "
                f"| ${float(r['spend'] or 0):,.0f} "
                f"| {int(r['impressions'] or 0):,} "
                f"| {r['ctr']:.2f} "
                f"| {float(r['conversations'] or 0):.0f} "
                f"| {cm} |"
            )
        lines.append("")
        return lines

    lines = [
        "# Reporte Semanal Meta Ads",
        "",
        f"**Periodo:** {start} → {end}",
        f"**Gasto Meta total:** ${total_spend:,.0f} CLP",
        f"**Conversaciones (mensajes) totales:** {total_convs:.0f}",
        f"**Reservas confirmadas en el periodo:** {total_ventas}",
        "",
    ]
    lines += section("Análisis por Público (Conjunto de anuncios)", adset_rows)
    lines += section("Análisis por Anuncio", ad_rows)
    lines += [
        "## Archivos generados",
        "",
        "- `00_evolucion.png` — Gasto Meta vs reservas reales por día",
        "- `01_publico.png`   — Análisis por conjunto de anuncios (público)",
        "- `02_anuncio.png`   — Análisis por anuncio",
        "- `datos_publico.csv`, `datos_anuncio.csv` — datos en tabla",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  {out_path.name}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    args  = parse_args()
    start = args.start
    end   = args.end

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL no definida")
        sys.exit(1)

    out_dir = (
        Path(__file__).resolve().parent.parent
        / "outputs"
        / f"reporte_semanal_meta_{start}_{end}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Consultando {start} a {end} ...")
    with psycopg.connect(url) as conn:
        adset_rows, ad_rows, daily_meta, daily_appts = query_all(conn, start, end)

    adset_rows = enrich(adset_rows)
    ad_rows    = enrich(ad_rows)

    print(f"  Públicos (adsets): {len(adset_rows)}")
    print(f"  Anuncios:          {len(ad_rows)}")
    print(f"  Días Meta:         {len(daily_meta)}")
    print(f"  Días c/reservas:   {len(daily_appts)}")

    print("\nGenerando graficos ...")
    make_evolution_figure(daily_meta, daily_appts,
                          out_dir / "00_evolucion.png", start, end)
    make_section_figure(adset_rows, "Análisis por Público (Conjunto de anuncios)",
                        out_dir / "01_publico.png", start, end)
    make_section_figure(ad_rows, "Análisis por Anuncio",
                        out_dir / "02_anuncio.png", start, end)

    save_csv(adset_rows, out_dir / "datos_publico.csv")
    save_csv(ad_rows,    out_dir / "datos_anuncio.csv")
    save_report(adset_rows, ad_rows, daily_meta, daily_appts,
                out_dir / "informe.md", start, end)

    print(f"\nListo: {out_dir}")


if __name__ == "__main__":
    main()
