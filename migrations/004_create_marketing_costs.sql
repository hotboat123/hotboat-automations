-- Tabla para almacenar costos de marketing diarios
-- Esta tabla acumula los gastos por día para calcular la utilidad operativa

CREATE TABLE IF NOT EXISTS marketing_costs (
    id SERIAL PRIMARY KEY,
    cost_date DATE NOT NULL,
    ad_name TEXT,
    campaign_name TEXT,
    adset_name TEXT,
    amount_spent NUMERIC(10, 2) NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'CLP',
    reach INTEGER,
    impressions INTEGER,
    clicks INTEGER,
    purchases INTEGER,
    raw JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice para consultas rápidas por fecha
CREATE INDEX IF NOT EXISTS idx_marketing_costs_date ON marketing_costs(cost_date);

-- Índice para consultas por campaña
CREATE INDEX IF NOT EXISTS idx_marketing_costs_campaign ON marketing_costs(campaign_name);

-- Vista agregada por día para facilitar consultas
CREATE OR REPLACE VIEW marketing_costs_daily AS
SELECT 
    cost_date,
    COUNT(*) as num_ads,
    SUM(amount_spent) as total_spent,
    SUM(reach) as total_reach,
    SUM(impressions) as total_impressions,
    SUM(clicks) as total_clicks,
    SUM(purchases) as total_purchases,
    CASE 
        WHEN SUM(clicks) > 0 THEN ROUND(SUM(amount_spent) / SUM(clicks), 2)
        ELSE 0 
    END as avg_cpc,
    CASE 
        WHEN SUM(purchases) > 0 THEN ROUND(SUM(amount_spent) / SUM(purchases), 2)
        ELSE 0 
    END as avg_cost_per_purchase
FROM marketing_costs
GROUP BY cost_date
ORDER BY cost_date DESC;

COMMENT ON TABLE marketing_costs IS 'Costos diarios de marketing para calcular utilidad operativa';
COMMENT ON COLUMN marketing_costs.cost_date IS 'Fecha del gasto de marketing';
COMMENT ON COLUMN marketing_costs.amount_spent IS 'Monto gastado en CLP';
COMMENT ON COLUMN marketing_costs.raw IS 'Datos completos del CSV en formato JSON';
