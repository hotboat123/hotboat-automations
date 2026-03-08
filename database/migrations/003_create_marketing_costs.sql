-- Tabla para almacenar costos de marketing de Facebook Ads
-- Esta tabla se sincroniza desde Looker Studio / CSV exportado

CREATE TABLE IF NOT EXISTS marketing_costs (
    id TEXT PRIMARY KEY,  -- SHA-1 hash de (dia + nombre_anuncio)
    dia DATE NOT NULL,
    nombre_anuncio TEXT,
    nombre_campana TEXT,
    nombre_conjunto_anuncios TEXT,
    
    -- Métricas de alcance
    alcance INTEGER,
    impresiones INTEGER,
    frecuencia DECIMAL(10, 2),
    
    -- Costo (la métrica más importante)
    divisa TEXT DEFAULT 'CLP',
    importe_gastado DECIMAL(15, 2) NOT NULL,
    
    -- Conversiones
    compras INTEGER DEFAULT 0,
    costo_por_compra DECIMAL(15, 2),
    
    -- Engagement
    clics_enlace INTEGER,
    ctr_todos DECIMAL(10, 4),
    cpc_todos DECIMAL(15, 2),
    cpm DECIMAL(15, 2),
    
    -- Carrito
    items_agregados_carrito INTEGER,
    costo_por_item_carrito DECIMAL(15, 2),
    
    -- Videos
    reproducciones_3s INTEGER,
    reproducciones_25 INTEGER,
    reproducciones_50 INTEGER,
    reproducciones_75 INTEGER,
    reproducciones_95 INTEGER,
    reproducciones_100 INTEGER,
    
    -- Proceso de compra
    agrego_carrito_tom INTEGER,
    costo_por_agrego_carrito_tom DECIMAL(15, 2),
    hizo_pago INTEGER,
    costo_por_hizo_pago DECIMAL(15, 2),
    
    -- Otros
    interaccion_pagina INTEGER,
    intento_pagar INTEGER,
    conversaciones_iniciadas INTEGER,
    costo_por_conversacion DECIMAL(15, 2),
    
    -- Metadata
    inicio_informe DATE,
    fin_informe DATE,
    raw JSONB,  -- Guardar todos los datos raw del CSV
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices para búsquedas rápidas
    CONSTRAINT unique_marketing_entry UNIQUE (dia, nombre_anuncio, nombre_campana)
);

-- Índice para búsquedas por fecha (el más común)
CREATE INDEX IF NOT EXISTS idx_marketing_costs_dia ON marketing_costs(dia);

-- Índice para búsquedas por campaña
CREATE INDEX IF NOT EXISTS idx_marketing_costs_campana ON marketing_costs(nombre_campana);

-- Índice para búsquedas por rango de fechas
CREATE INDEX IF NOT EXISTS idx_marketing_costs_date_range ON marketing_costs(dia, importe_gastado);

-- Vista para resumen diario de costos
CREATE OR REPLACE VIEW daily_marketing_summary AS
SELECT 
    dia,
    COUNT(*) as num_anuncios,
    SUM(importe_gastado) as costo_total,
    SUM(compras) as total_compras,
    SUM(clics_enlace) as total_clics,
    SUM(impresiones) as total_impresiones,
    CASE 
        WHEN SUM(compras) > 0 THEN SUM(importe_gastado) / SUM(compras)
        ELSE 0
    END as costo_por_compra_promedio,
    STRING_AGG(DISTINCT nombre_campana, ', ') as campanas
FROM marketing_costs
GROUP BY dia
ORDER BY dia DESC;

-- Comentarios
COMMENT ON TABLE marketing_costs IS 'Costos de marketing de Facebook Ads importados desde Looker Studio';
COMMENT ON COLUMN marketing_costs.importe_gastado IS 'Costo en CLP del anuncio para ese día';
COMMENT ON COLUMN marketing_costs.compras IS 'Número de conversiones (compras) atribuidas';
