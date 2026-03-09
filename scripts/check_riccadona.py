import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from app.config import get_settings

conn = psycopg.connect(get_settings().database_url)
cur = conn.cursor()
cur.execute('SELECT raw FROM "Precios Extras" WHERE raw->>\'Extra\' ILIKE \'%riccadon%\'')

print("Todos los precios de Riccadona/Riccadonna en la BD:")
print("="*60)
for r in cur.fetchall():
    print(f"{r[0].get('Extra')}: Precio=${r[0].get('Precio')}, Costo={r[0].get('Costo')}")

conn.close()
