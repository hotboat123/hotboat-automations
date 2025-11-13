import json
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings


def collect_raw_keys(cur) -> None:
    cur.execute("SELECT raw FROM booknetic_appointments")
    keys = set()
    for (raw_data,) in cur.fetchall():
        keys.update(raw_data.keys())

    print("\nClaves detectadas en raw:")
    print(", ".join(sorted(keys)))


def print_latest_raw(cur) -> None:
    cur.execute(
        """
        SELECT id, raw
        FROM booknetic_appointments
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row:
        print("\nNo hay registros en booknetic_appointments")
        return

    appointment_id, raw_data = row
    print(f"\nÚltima reserva ID: {appointment_id}")
    print("Raw:")
    print(json.dumps(raw_data, indent=2, ensure_ascii=False))


def main() -> None:
    settings = get_settings()
    query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'booknetic_appointments'
        ORDER BY ordinal_position
    """

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            for name, data_type in cur.fetchall():
                print(f"{name:30s} {data_type}")

            print_latest_raw(cur)
            collect_raw_keys(cur)

            cur.execute(
                """
                SELECT raw
                FROM booknetic_appointments
                WHERE raw ? 'extras'
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if row:
                print("\nEjemplo Extras:")
                print(json.dumps(row[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

