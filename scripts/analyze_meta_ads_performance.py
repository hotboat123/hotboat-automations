"""
Análisis de rendimiento por anuncio desde v_meta_ads_analytics.
Genera CSV + gráficos en outputs/meta_ads_analysis_<timestamp>/
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import psycopg


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL no definida")
        sys.exit(1)

    out_dir = (
        Path(__file__).resolve().parent.parent
        / "outputs"
        / f"meta_ads_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  COALESCE(NULLIF(TRIM("Nombre del anuncio"), ''), '(sin nombre)') AS ad_name,
                  MIN("Día") AS first_day,
                  MAX("Día") AS last_day,
                  COUNT(*)::bigint AS rows_insights,
                  SUM("Importe gastado (CLP)") AS spend,
                  SUM("Impresiones") AS impressions,
                  SUM("Clics en el enlace") AS link_clicks,
                  SUM("Compras") AS purchases,
                  SUM("Conversaciones con mensajes iniciadas") AS msg_conversations,
                  SUM("Alcance") AS reach
                FROM v_meta_ads_analytics
                GROUP BY 1
                """
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    if not rows:
        print("v_meta_ads_analytics: sin filas.")
        sys.exit(0)

    # Métricas derivadas por anuncio
    enriched = []
    for r in rows:
        spend = float(r["spend"] or 0)
        imp = int(r["impressions"] or 0)
        clk = float(r["link_clicks"] or 0)
        pur = float(r["purchases"] or 0)
        msg = float(r["msg_conversations"] or 0)
        ctr = (clk / imp * 100.0) if imp > 0 else 0.0
        cpc = (spend / clk) if clk > 0 else None
        cpm = (spend / imp * 1000.0) if imp > 0 else None
        cost_per_msg = (spend / msg) if msg > 0 else None
        cost_per_purchase = (spend / pur) if pur > 0 else None
        enriched.append(
            {
                **r,
                "ctr_pct": ctr,
                "cpc": cpc,
                "cpm": cpm,
                "cost_per_msg": cost_per_msg,
                "cost_per_purchase": cost_per_purchase,
            }
        )

    enriched.sort(key=lambda x: float(x["spend"] or 0), reverse=True)
    first_day = min(r["first_day"] for r in rows if r["first_day"])
    last_day = max(r["last_day"] for r in rows if r["last_day"])

    csv_path = out_dir / "por_anuncio.csv"
    fieldnames = [
        "ad_name",
        "first_day",
        "last_day",
        "rows_insights",
        "spend",
        "impressions",
        "link_clicks",
        "purchases",
        "msg_conversations",
        "reach",
        "ctr_pct",
        "cpc",
        "cpm",
        "cost_per_msg",
        "cost_per_purchase",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for e in enriched:
            row = {k: e.get(k) for k in fieldnames}
            row["ad_name"] = e["ad_name"]
            w.writerow(row)

    # --- Gráficos (top N por gasto para legibilidad) ---
    top_n = min(15, len(enriched))
    top = enriched[:top_n]
    labels = [str(e["ad_name"])[:42] + ("…" if len(str(e["ad_name"])) > 42 else "") for e in top]
    spends = [float(e["spend"] or 0) for e in top]

    fig, ax = plt.subplots(figsize=(10, max(4, top_n * 0.35)))
    ax.barh(range(len(labels)), spends, color="#2E86AB")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Gasto (CLP)")
    ax.set_title(f"Top {top_n} anuncios por gasto\n{first_day} → {last_day}")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    fig.savefig(out_dir / "01_gasto_por_anuncio.png", dpi=120)
    plt.close()

    # CTR: solo anuncios con impresiones mínimas (evitar ruido)
    min_imp = 500
    ctr_candidates = [e for e in enriched if int(e["impressions"] or 0) >= min_imp]
    ctr_candidates.sort(key=lambda x: x["ctr_pct"], reverse=True)
    ctr_top = ctr_candidates[:top_n]
    if ctr_top:
        labels_c = [
            str(e["ad_name"])[:40] + ("…" if len(str(e["ad_name"])) > 40 else "") for e in ctr_top
        ]
        vals_c = [e["ctr_pct"] for e in ctr_top]
        fig, ax = plt.subplots(figsize=(10, max(4, len(ctr_top) * 0.35)))
        ax.barh(range(len(labels_c)), vals_c, color="#A23B72")
        ax.set_yticks(range(len(labels_c)))
        ax.set_yticklabels(labels_c, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("CTR (clics enlace / impresiones) %")
        ax.set_title(f"Mayor CTR (mín. {min_imp} impresiones)")
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        fig.savefig(out_dir / "02_ctr_por_anuncio.png", dpi=120)
        plt.close()

    # Costo por conversación de mensaje (mejor = más barato), mínimo eventos
    min_msg = 3
    msg_ads = [
        e
        for e in enriched
        if float(e["msg_conversations"] or 0) >= min_msg and e.get("cost_per_msg") is not None
    ]
    msg_ads.sort(key=lambda x: x["cost_per_msg"])
    msg_top = msg_ads[:top_n]
    if msg_top:
        labels_m = [
            str(e["ad_name"])[:38] + ("…" if len(str(e["ad_name"])) > 38 else "") for e in msg_top
        ]
        vals_m = [e["cost_per_msg"] for e in msg_top]
        fig, ax = plt.subplots(figsize=(10, max(4, len(msg_top) * 0.35)))
        ax.barh(range(len(labels_m)), vals_m, color="#F18F01")
        ax.set_yticks(range(len(labels_m)))
        ax.set_yticklabels(labels_m, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("Costo por conversación iniciada (CLP)")
        ax.set_title(f"Menor costo / conversación mensajes (≥{min_msg} eventos)")
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        fig.savefig(out_dir / "03_costo_por_mensaje.png", dpi=120)
        plt.close()

    # Scatter: impresiones vs CTR (tamaño = gasto)
    fig, ax = plt.subplots(figsize=(10, 7))
    xs = [float(e["impressions"] or 0) for e in enriched]
    ys = [e["ctr_pct"] for e in enriched]
    sizes = [max(20, min(800, float(e["spend"] or 0) / 500)) for e in enriched]
    ax.scatter(xs, ys, s=sizes, alpha=0.5, c="#C73E1D")
    ax.set_xlabel("Impresiones (acumulado)")
    ax.set_ylabel("CTR %")
    ax.set_title("Impresiones vs CTR (tamaño ~ gasto)")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(out_dir / "04_scatter_impresiones_ctr.png", dpi=120)
    plt.close()

    # Informe markdown
    total_spend = sum(float(e["spend"] or 0) for e in enriched)
    total_imp = sum(int(e["impressions"] or 0) for e in enriched)
    report_path = out_dir / "informe.md"
    lines = [
        "# Análisis v_meta_ads_analytics",
        "",
        f"- **Periodo en datos:** {first_day} → {last_day}",
        f"- **Anuncios distintos:** {len(enriched)}",
        f"- **Gasto total (suma):** ${total_spend:,.0f} CLP",
        f"- **Impresiones totales:** {total_imp:,}",
        "",
        "## Cómo interpretar",
        "",
        "- **Gasto:** volumen invertido; no implica eficiencia.",
        "- **CTR (clics en enlace / impresiones):** útil para creatividades que generan clic; filtramos anuncios con pocas impresiones para no inflar CTR.",
        "- **Costo por conversación de mensajes:** relevante si buscas leads por inbox; menor = mejor.",
        "- **Compras:** depende de que Meta atribuya `purchase` a tus campañas.",
        "",
        "## Top 10 por gasto",
        "",
        "| Anuncio | Gasto CLP | Impresiones | CTR % | Costo/msg |",
        "|---------|-----------|-------------|-------|-----------|",
    ]
    for e in enriched[:10]:
        cmsg = (
            f"{e['cost_per_msg']:,.0f}"
            if e.get("cost_per_msg") is not None
            else "—"
        )
        lines.append(
            f"| {str(e['ad_name'])[:50]} | {float(e['spend'] or 0):,.0f} | "
            f"{int(e['impressions'] or 0):,} | {e['ctr_pct']:.2f} | {cmsg} |"
        )
    lines.extend(
        [
            "",
            "## Archivos generados",
            "",
            "- `por_anuncio.csv` — métricas por anuncio",
            "- `01_gasto_por_anuncio.png`",
            "- `02_ctr_por_anuncio.png`",
            "- `03_costo_por_mensaje.png`",
            "- `04_scatter_impresiones_ctr.png`",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Listo: {out_dir}")
    print(f"  CSV: {csv_path}")
    print(f"  Informe: {report_path}")


if __name__ == "__main__":
    main()
