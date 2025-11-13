import argparse
import json
from typing import Iterable, Tuple

import psycopg
from psycopg import sql

from app.config import get_settings


def fetch_tables(cursor) -> list[str]:
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
    )
    return [row[0] for row in cursor.fetchall()]


def fetch_columns(cursor, table_name: str) -> Iterable[Tuple[str, str]]:
    cursor.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return cursor.fetchall()


def fetch_sample(cursor, table_name: str, limit: int):
    query = sql.SQL(
        "SELECT * FROM {} ORDER BY created_at DESC LIMIT %s"
    ).format(sql.Identifier(table_name))
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    columns = [desc.name for desc in cursor.description]
    return columns, rows


def main(target_table: str | None = None, sample: int = 0):
    settings = get_settings()

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            tables = fetch_tables(cur)
            print("Public tables:")
            for table in tables:
                marker = "  <-- target" if target_table and table == target_table else ""
                print(f" - {table}{marker}")

            if target_table:
                print(f"\nColumns in '{target_table}':")
                columns = list(fetch_columns(cur, target_table))

                if not columns:
                    print(" (table not found)")
                else:
                    for column_name, data_type in columns:
                        print(f" - {column_name}: {data_type}")

                if sample > 0:
                    print(f"\nSample rows from '{target_table}' (limit {sample}):")
                    columns, rows = fetch_sample(cur, target_table, sample)
                    if not rows:
                        print(" (no data)")
                    else:
                        for row in rows:
                            structured = {
                                column: value
                                for column, value in zip(columns, row)
                            }
                            print(json.dumps(structured, indent=2, default=str, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect public tables and optional column details.")
    parser.add_argument(
        "--table",
        help="Show column information for a specific table.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Show sample rows (JSON) for the selected table.",
    )
    args = parser.parse_args()
    main(target_table=args.table, sample=args.sample)

