"""
Script para generar análisis automático a partir del CSV de reservas completas
Genera un reporte ejecutivo en formato Markdown
"""
import sys
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List

def load_csv(filepath: str) -> List[Dict]:
    """Carga el CSV de reservas"""
    reservas = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convertir números
            for key in ['Ingreso Reserva', 'Ingreso Extras', 'Ingreso Total', 
                       'Costo Op Fijo', 'Costo Op Variable', 'Costo Op Total',
                       'Costo Marketing', 'Costo Total', 'Utilidad Bruta', 'Utilidad Neta',
                       'Margen Bruto %', 'Margen Neto %', 'Num Personas', 'Descuento %']:
                try:
                    row[key] = float(row[key]) if row[key] else 0
                except (ValueError, KeyError):
                    row[key] = 0
            reservas.append(row)
    return reservas

def analizar_resumen_ejecutivo(reservas: List[Dict]) -> Dict:
    """Genera métricas del resumen ejecutivo"""
    total_reservas = len(reservas)
    total_ingreso = sum(r['Ingreso Total'] for r in reservas)
    total_costo = sum(r['Costo Total'] for r in reservas)
    total_utilidad = sum(r['Utilidad Neta'] for r in reservas)
    
    margen_neto = (total_utilidad / total_ingreso * 100) if total_ingreso > 0 else 0
    
    return {
        'total_reservas': total_reservas,
        'total_ingreso': total_ingreso,
        'total_costo': total_costo,
        'total_utilidad': total_utilidad,
        'margen_neto': margen_neto
    }

def analizar_financiero(reservas: List[Dict]) -> Dict:
    """Analiza ingresos y costos"""
    ingreso_reservas = sum(r['Ingreso Reserva'] for r in reservas)
    ingreso_extras = sum(r['Ingreso Extras'] for r in reservas)
    
    costo_fijo = sum(r['Costo Op Fijo'] for r in reservas)
    costo_variable = sum(r['Costo Op Variable'] for r in reservas)
    costo_marketing = sum(r['Costo Marketing'] for r in reservas)
    costo_total = sum(r['Costo Total'] for r in reservas)
    
    rentables = [r for r in reservas if r['Utilidad Neta'] > 0]
    no_rentables = [r for r in reservas if r['Utilidad Neta'] <= 0]
    
    return {
        'ingreso_reservas': ingreso_reservas,
        'ingreso_extras': ingreso_extras,
        'costo_fijo': costo_fijo,
        'costo_variable': costo_variable,
        'costo_marketing': costo_marketing,
        'costo_total': costo_total,
        'rentables': len(rentables),
        'no_rentables': len(no_rentables),
        'utilidad_rentables': sum(r['Utilidad Neta'] for r in rentables),
        'perdida_no_rentables': sum(r['Utilidad Neta'] for r in no_rentables)
    }

def analizar_top_clientes(reservas: List[Dict], top_n: int = 10) -> List[Dict]:
    """Identifica los top clientes"""
    clientes = defaultdict(lambda: {'reservas': 0, 'ingreso': 0})
    
    for r in reservas:
        nombre = r.get('Nombre Cliente', 'Sin nombre')
        if nombre and nombre != 'Sin nombre':
            clientes[nombre]['reservas'] += 1
            clientes[nombre]['ingreso'] += r['Ingreso Total']
    
    # Ordenar por ingreso
    top = sorted(clientes.items(), key=lambda x: x[1]['ingreso'], reverse=True)[:top_n]
    
    return [
        {
            'cliente': nombre,
            'reservas': data['reservas'],
            'ingreso': data['ingreso'],
            'promedio': data['ingreso'] / data['reservas']
        }
        for nombre, data in top
    ]

def analizar_extras(reservas: List[Dict]) -> Dict:
    """Analiza los extras vendidos"""
    con_extras = [r for r in reservas if r['Ingreso Extras'] > 0]
    sin_extras = [r for r in reservas if r['Ingreso Extras'] == 0]
    
    # Contar menciones de extras populares
    extras_count = Counter()
    for r in con_extras:
        extras_str = r.get('Extras', '')
        if extras_str and extras_str != 'Sin extras':
            # Contar cada extra mencionado
            if 'cerveza_artesanal_negra' in extras_str.lower():
                extras_count['Cerveza Artesanal Negra'] += 1
            if 'tabla_2_personas' in extras_str.lower() or 'tabla 2' in extras_str.lower():
                extras_count['Tabla 2 Personas'] += 1
            if 'foto' in extras_str.lower() and 'marco' in extras_str.lower():
                extras_count['Foto con Marco'] += 1
            if 'video' in extras_str.lower() and '15' in extras_str:
                extras_count['Video 15 Segundos'] += 1
            if 'champaña' in extras_str.lower() or 'champana' in extras_str.lower():
                extras_count['Champaña'] += 1
    
    return {
        'con_extras': len(con_extras),
        'sin_extras': len(sin_extras),
        'tasa_conversion': len(con_extras) / len(reservas) * 100 if reservas else 0,
        'ingreso_con_extras': sum(r['Ingreso Total'] for r in con_extras),
        'ingreso_sin_extras': sum(r['Ingreso Total'] for r in sin_extras),
        'top_extras': extras_count.most_common(5)
    }

def analizar_horarios(reservas: List[Dict]) -> Dict:
    """Analiza distribución por horarios"""
    franjas = {
        '10:00-12:00': [],
        '12:00-15:00': [],
        '15:00-18:00': [],
        '18:00-21:00': [],
        '21:00-23:00': []
    }
    
    for r in reservas:
        hora_str = r.get('Hora', '')
        if not hora_str:
            continue
        
        try:
            hora = int(hora_str.split(':')[0])
            if 10 <= hora < 12:
                franjas['10:00-12:00'].append(r)
            elif 12 <= hora < 15:
                franjas['12:00-15:00'].append(r)
            elif 15 <= hora < 18:
                franjas['15:00-18:00'].append(r)
            elif 18 <= hora < 21:
                franjas['18:00-21:00'].append(r)
            elif 21 <= hora < 24:
                franjas['21:00-23:00'].append(r)
        except (ValueError, IndexError):
            continue
    
    result = {}
    for franja, reservas_franja in franjas.items():
        if reservas_franja:
            result[franja] = {
                'cantidad': len(reservas_franja),
                'ingreso_promedio': sum(r['Ingreso Total'] for r in reservas_franja) / len(reservas_franja)
            }
        else:
            result[franja] = {'cantidad': 0, 'ingreso_promedio': 0}
    
    return result

def generar_reporte(reservas: List[Dict], output_path: str):
    """Genera el reporte en Markdown"""
    
    # Análisis
    resumen = analizar_resumen_ejecutivo(reservas)
    financiero = analizar_financiero(reservas)
    top_clientes = analizar_top_clientes(reservas)
    extras = analizar_extras(reservas)
    horarios = analizar_horarios(reservas)
    
    # Top reservas
    top_rentables = sorted(reservas, key=lambda x: x['Utilidad Neta'], reverse=True)[:5]
    
    # Generar markdown
    md = []
    md.append("# Análisis de Reservas - Hot Boat")
    md.append("")
    md.append(f"**Fecha de análisis:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    md.append("")
    
    # Resumen Ejecutivo
    md.append("## 📊 RESUMEN EJECUTIVO")
    md.append("")
    md.append(f"- **Total Reservas:** {resumen['total_reservas']}")
    md.append(f"- **Ingreso Total:** ${resumen['total_ingreso']:,.0f}")
    md.append(f"- **Costo Total:** ${resumen['total_costo']:,.0f}")
    md.append(f"- **Utilidad Neta:** ${resumen['total_utilidad']:,.0f}")
    md.append(f"- **Margen Neto:** {resumen['margen_neto']:.1f}%")
    md.append("")
    
    # Problemas Críticos
    md.append("## 🚨 PROBLEMAS IDENTIFICADOS")
    md.append("")
    if financiero['ingreso_reservas'] == 0:
        md.append("### ⚠️ CRÍTICO: Ingreso por Reserva = $0")
        md.append("- TODAS las reservas tienen 'Ingreso Reserva' en $0")
        md.append("- Solo se capturan ingresos por extras")
        md.append("- **Acción requerida:** Revisar integración con sistema de pagos")
        md.append("")
    
    if financiero['costo_marketing'] / resumen['total_reservas'] > 15000:
        md.append("### ⚠️ Costos de Marketing Elevados")
        md.append(f"- Promedio: ${financiero['costo_marketing'] / resumen['total_reservas']:,.0f} por reserva")
        md.append("- **Acción sugerida:** Revisar ROI del marketing")
        md.append("")
    
    # Análisis Financiero
    md.append("## 💰 ANÁLISIS FINANCIERO")
    md.append("")
    md.append("### Ingresos")
    md.append("")
    md.append(f"- Reservas Base: ${financiero['ingreso_reservas']:,.0f}")
    md.append(f"- Extras: ${financiero['ingreso_extras']:,.0f}")
    md.append(f"- **Total:** ${financiero['ingreso_reservas'] + financiero['ingreso_extras']:,.0f}")
    md.append("")
    
    md.append("### Costos")
    md.append("")
    md.append(f"- Operativos Fijos: ${financiero['costo_fijo']:,.0f} ({financiero['costo_fijo']/financiero['costo_total']*100:.1f}%)")
    md.append(f"- Operativos Variables: ${financiero['costo_variable']:,.0f} ({financiero['costo_variable']/financiero['costo_total']*100:.1f}%)")
    md.append(f"- Marketing: ${financiero['costo_marketing']:,.0f} ({financiero['costo_marketing']/financiero['costo_total']*100:.1f}%)")
    md.append(f"- **Total:** ${financiero['costo_total']:,.0f}")
    md.append("")
    
    md.append("### Rentabilidad")
    md.append("")
    md.append(f"- Reservas Rentables: {financiero['rentables']} ({financiero['rentables']/resumen['total_reservas']*100:.1f}%)")
    md.append(f"- Utilidad de rentables: ${financiero['utilidad_rentables']:,.0f}")
    md.append(f"- Reservas en Pérdida: {financiero['no_rentables']} ({financiero['no_rentables']/resumen['total_reservas']*100:.1f}%)")
    md.append(f"- Pérdida de no rentables: ${financiero['perdida_no_rentables']:,.0f}")
    md.append("")
    
    # Top Clientes
    md.append("## 👥 TOP 10 CLIENTES")
    md.append("")
    md.append("| Cliente | Reservas | Ingreso Total | Promedio |")
    md.append("|---------|----------|---------------|----------|")
    for c in top_clientes:
        md.append(f"| {c['cliente'][:30]} | {c['reservas']} | ${c['ingreso']:,.0f} | ${c['promedio']:,.0f} |")
    md.append("")
    
    # Análisis de Extras
    md.append("## 🎯 ANÁLISIS DE EXTRAS")
    md.append("")
    md.append(f"- **Reservas con extras:** {extras['con_extras']} ({extras['tasa_conversion']:.1f}%)")
    md.append(f"- **Reservas sin extras:** {extras['sin_extras']} ({100-extras['tasa_conversion']:.1f}%)")
    md.append(f"- **Ingreso de extras:** ${extras['ingreso_con_extras']:,.0f}")
    md.append("")
    
    md.append("### Top 5 Extras Más Mencionados")
    md.append("")
    for extra, count in extras['top_extras']:
        md.append(f"- **{extra}:** {count} veces")
    md.append("")
    
    # Horarios
    md.append("## 🕐 ANÁLISIS DE HORARIOS")
    md.append("")
    md.append("| Franja | Reservas | Ingreso Promedio |")
    md.append("|--------|----------|------------------|")
    for franja, data in horarios.items():
        md.append(f"| {franja} | {data['cantidad']} | ${data['ingreso_promedio']:,.0f} |")
    md.append("")
    
    # Top Reservas Rentables
    md.append("## 🏆 TOP 5 RESERVAS MÁS RENTABLES")
    md.append("")
    for idx, r in enumerate(top_rentables, 1):
        md.append(f"### {idx}. {r['Nombre Cliente']} ({r['Fecha']})")
        md.append(f"- **Ingreso:** ${r['Ingreso Total']:,.0f}")
        md.append(f"- **Costo:** ${r['Costo Total']:,.0f}")
        md.append(f"- **Utilidad:** ${r['Utilidad Neta']:,.0f}")
        md.append(f"- **Margen:** {r['Margen Neto %']:.1f}%")
        md.append(f"- **Extras:** {r['Extras']}")
        md.append("")
    
    # Recomendaciones
    md.append("## 💡 RECOMENDACIONES")
    md.append("")
    
    if financiero['ingreso_reservas'] == 0:
        md.append("### URGENTE")
        md.append("1. **Corregir captura de ingresos base** - Prioridad máxima")
        md.append("2. Investigar por qué los payments están en $0")
        md.append("")
    
    if extras['tasa_conversion'] < 50:
        md.append("### Marketing de Extras")
        md.append(f"1. Aumentar tasa de conversión de extras (actual: {extras['tasa_conversion']:.1f}%, objetivo: 60%)")
        md.append("2. Crear paquetes predefinidos de extras")
        md.append("3. Ofrecer combos con descuento")
        md.append("")
    
    if financiero['costo_marketing'] / resumen['total_reservas'] > 15000:
        md.append("### Optimización de Costos")
        md.append("1. Revisar estrategia de marketing")
        md.append("2. Analizar ROI por canal")
        md.append("3. Reducir CAC (Customer Acquisition Cost)")
        md.append("")
    
    # Guardar
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    
    print(f"\n[OK] Reporte generado: {output_path}")

def main():
    if len(sys.argv) < 2:
        print("\nUso: python scripts/analizar_reservas.py <archivo_csv>")
        print("\nEjemplo:")
        print("  python scripts/analizar_reservas.py outputs/reservas_completas_20260101_20260131.csv")
        return
    
    csv_path = sys.argv[1]
    
    if not Path(csv_path).exists():
        print(f"Error: Archivo no encontrado: {csv_path}")
        return
    
    print(f"\nAnalizando: {csv_path}")
    
    # Cargar datos
    reservas = load_csv(csv_path)
    print(f"Reservas cargadas: {len(reservas)}")
    
    # Generar nombre de output
    csv_name = Path(csv_path).stem
    output_path = Path(csv_path).parent / f"analisis_{csv_name}.md"
    
    # Generar reporte
    generar_reporte(reservas, str(output_path))
    
    print(f"\n{'='*60}")
    print("ANALISIS COMPLETADO")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
