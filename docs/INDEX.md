# Documentación - Hot Boat Automations

Índice de toda la documentación disponible.

## 📚 Documentación Principal

### [README.md](../README.md)
Guía principal del proyecto con características, instalación y configuración básica.

### [QUICKSTART.md](../QUICKSTART.md)
Guía rápida para empezar a usar el sistema en minutos.

### [CONFIGURATION.md](../CONFIGURATION.md)
Configuración detallada de monitores, notificaciones y personalización.

### [EXAMPLES.md](../EXAMPLES.md)
Ejemplos de uso y casos prácticos.

### [CHANGELOG.md](../CHANGELOG.md)
Historial de cambios y versiones.

## 📊 Análisis y Reportes

### [EXPORT_RESERVATIONS.md](EXPORT_RESERVATIONS.md)
**Guía completa** para exportar información consolidada de reservas a CSV.
- Uso del script `export_reservations_full.py`
- Columnas del CSV generado
- Ejemplos de uso
- Solución de problemas

### [CRUCE_TABLAS.md](CRUCE_TABLAS.md)
**Explicación técnica** de cómo se hace el cruce de tablas.
- Estructura de las 3 tablas (appointments, payments, Informacion Reservas)
- Lógica del JOIN (fecha + hora + ROW_NUMBER)
- Query SQL completa
- Procesamiento de extras
- Cálculos de costos y utilidades

### [EJEMPLO_CRUCE_TABLAS.md](EJEMPLO_CRUCE_TABLAS.md)
**Ejemplo visual paso a paso** con datos reales.
- Datos de entrada de las 3 tablas
- Proceso de normalización
- Cruce paso a paso
- Cálculos de ingresos y costos
- Resultado final en CSV

### [RESUMEN_CRUCE_TABLAS.md](RESUMEN_CRUCE_TABLAS.md)
**Resumen ejecutivo** de la implementación del sistema de cruce.
- ¿Qué se implementó?
- ¿Cómo funciona?
- Uso rápido
- Archivos creados
- Próximos pasos

### [MARKETING_COSTS.md](MARKETING_COSTS.md)
Gestión de costos de marketing.
- Importación de costos desde CSV
- Cálculo de CAC (Customer Acquisition Cost)
- Scripts de actualización y consulta

### [SISTEMA_EMAILS.md](SISTEMA_EMAILS.md)
**Sistema de Emails Automáticos** - Guía completa del funcionamiento.
- Qué código se ejecuta para enviar emails
- Cómo funciona el despliegue automático en Railway
- Cada cuánto se envían los correos
- Tipos de emails (stock bajo, crítico, agotado, resúmenes)
- Configuración de Resend y variables de entorno
- Logs y troubleshooting

### [RESUMEN_DIARIO.md](RESUMEN_DIARIO.md)
**Monitor de Resumen Diario** - Explicación detallada del reporte automático diario.
- Qué contiene el email (ingresos, costos, utilidades, faltantes)
- Cómo se calculan ingresos de reservas y extras
- Sistema de aliases para matching de extras
- Cruce de reservas (fecha/hora y por nombre)
- Configuraciones personalizables
- Solución de problemas comunes

### [TABLA_MATERIALIZADA.md](TABLA_MATERIALIZADA.md)
**Nueva Arquitectura: Tabla `reservas_con_extras`** - Sistema de datos pre-procesados.
- Concepto de tabla materializada
- Ventajas: simplicidad, performance, consistencia
- Scripts de sincronización automática
- Monitor que mantiene la tabla actualizada
- Queries de ejemplo para análisis
- Migración de monitores existentes

## 🔍 Scripts de Análisis

| Script | Descripción | Documentación |
|--------|-------------|---------------|
| `export_reservations_full.py` | Exporta CSV consolidado con toda la información de cada reserva | [EXPORT_RESERVATIONS.md](EXPORT_RESERVATIONS.md) |
| `export_daily_analysis.py` | Genera 3 CSVs: reservas detalladas, resumen diario, resumen extras | [EXAMPLES.md](../EXAMPLES.md) |
| `calculate_month_revenue_optimized.py` | Calcula ingresos del mes hasta hoy | [EXAMPLES.md](../EXAMPLES.md) |
| `calculate_daily_revenue.py` | Calcula ingresos de un día específico | [EXAMPLES.md](../EXAMPLES.md) |

## 📖 Guías por Tema

### Análisis de Reservas
1. [EXPORT_RESERVATIONS.md](EXPORT_RESERVATIONS.md) - Exportar información completa
2. [CRUCE_TABLAS.md](CRUCE_TABLAS.md) - Entender el cruce de tablas
3. [EJEMPLO_CRUCE_TABLAS.md](EJEMPLO_CRUCE_TABLAS.md) - Ver ejemplo práctico

### Costos y Rentabilidad
1. [MARKETING_COSTS.md](MARKETING_COSTS.md) - Gestión de costos de marketing
2. [EXPORT_RESERVATIONS.md](EXPORT_RESERVATIONS.md) - Análisis de utilidades

### Configuración
1. [CONFIGURATION.md](../CONFIGURATION.md) - Configuración general
2. [QUICKSTART.md](../QUICKSTART.md) - Configuración rápida

### Sistema de Notificaciones
1. [SISTEMA_EMAILS.md](SISTEMA_EMAILS.md) - Emails automáticos
2. [CONFIGURATION.md](../CONFIGURATION.md) - Configurar monitores y prioridades

## 🚀 Empezar Rápido

### Para Analistas
1. Lee [EXPORT_RESERVATIONS.md](EXPORT_RESERVATIONS.md)
2. Ejecuta: `export_reservations.bat 2026-01-01 2026-01-31`
3. Abre el CSV en Excel

### Para Desarrolladores
1. Lee [CRUCE_TABLAS.md](CRUCE_TABLAS.md)
2. Revisa [EJEMPLO_CRUCE_TABLAS.md](EJEMPLO_CRUCE_TABLAS.md)
3. Estudia el código en `scripts/export_reservations_full.py`

### Para Gerentes
1. Lee [RESUMEN_CRUCE_TABLAS.md](RESUMEN_CRUCE_TABLAS.md)
2. Revisa los reportes en `outputs/`
3. Consulta [EXAMPLES.md](../EXAMPLES.md) para más casos de uso

## 📝 Notas

- Todos los scripts de Windows tienen extensión `.bat`
- Todos los scripts de Linux/Mac tienen extensión `.sh`
- Los CSVs generados se guardan en `outputs/`
- La documentación técnica está en la carpeta `docs/`

## 🤝 Contribuir

Para agregar documentación:
1. Crea un archivo `.md` en `docs/`
2. Agrega una entrada en este `INDEX.md`
3. Referencia desde el README principal si es relevante

## 📧 Soporte

Para preguntas o problemas:
- Consulta primero la documentación relevante
- Revisa [EXAMPLES.md](../EXAMPLES.md) para casos de uso
- Abre un issue en GitHub si no encuentras la respuesta
