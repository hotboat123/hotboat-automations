# Análisis v_meta_ads_analytics

- **Periodo en datos:** 2026-03-11 → 2026-04-10
- **Anuncios distintos:** 10
- **Gasto total (suma):** $587,660 CLP
- **Impresiones totales:** 486,175

## Cómo interpretar

- **Gasto:** volumen invertido; no implica eficiencia.
- **CTR (clics en enlace / impresiones):** útil para creatividades que generan clic; filtramos anuncios con pocas impresiones para no inflar CTR.
- **Costo por conversación de mensajes:** relevante si buscas leads por inbox; menor = mejor.
- **Compras:** depende de que Meta atribuya `purchase` a tus campañas.

## Top 10 por gasto

| Anuncio | Gasto CLP | Impresiones | CTR % | Costo/msg |
|---------|-----------|-------------|-------|-----------|
| Stefideviaje | 162,147 | 146,539 | 0.77 | 281 |
| Paro Lluvia | 104,404 | 72,944 | 1.48 | 14,915 |
| Video explicando servicio corto | 91,846 | 81,750 | 0.89 | 442 |
| 20 diciembre | 91,444 | 75,059 | 1.61 | 6,532 |
| Ad lluvia septiembre - Copia | 80,098 | 65,209 | 0.46 | 621 |
| Nocturno romantico | 34,173 | 25,648 | 1.17 | 17,086 |
| 6 horas | 11,443 | 8,889 | 5.77 | 3,814 |
| Ad lluvia septiembre | 8,544 | 7,203 | 0.47 | 712 |
| Viral navegantes | 2,950 | 2,541 | 0.24 | 983 |
| Fran Sin concurso | 611 | 393 | 0.00 | — |

## Archivos generados

- `por_anuncio.csv` — métricas por anuncio
- `01_gasto_por_anuncio.png`
- `02_ctr_por_anuncio.png`
- `03_costo_por_mensaje.png`
- `04_scatter_impresiones_ctr.png`