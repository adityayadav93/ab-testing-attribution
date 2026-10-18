"""Build the local warehouse (DuckDB) and run the SQL layer.

Creates data/warehouse.duckdb from sql/schema_setup.sql, loads data/raw/*.csv, then runs
every `-- name: <id>` query in sql/experiment_queries.sql and sql/attribution_queries.sql,
writing data/processed/<id>.csv. The SQL is PostgreSQL-compatible.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, DB = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "data" / "warehouse.duckdb"
TABLES = {"experiment_users": "experiment_users.csv", "journeys": "journeys.csv",
          "touchpoints": "touchpoints.csv", "channel_spend": "channel_spend.csv"}   # load order respects FKs
QUERY_FILES = ["experiment_queries.sql", "attribution_queries.sql"]


def split_queries(text: str) -> dict[str, str]:
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    con.execute((ROOT / "sql" / "schema_setup.sql").read_text())
    order = ["experiment_users", "journeys", "touchpoints", "channel_spend"]
    for t in order:
        con.execute(f"INSERT INTO {t} SELECT * FROM read_csv_auto('{RAW / TABLES[t]}', header=true)")
        print(f"loaded {t:<18} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>8,} rows")
    for f in QUERY_FILES:
        for name, sql in split_queries((ROOT / "sql" / f).read_text()).items():
            df = con.execute(sql).fetchdf()
            df.to_csv(OUT / f"{name}.csv", index=False)
            print(f"query  {name:<24} -> {len(df):>7,} rows")
    con.close()


if __name__ == "__main__":
    main()
