#!/usr/bin/env python3
"""Initialize the database and run all migrations."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.db import get_connection, apply_migrations


def main() -> int:
    print("Initializing IntelForce database...")
    conn = get_connection()
    apply_migrations(conn)

    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    print(f"✅ Database ready: {len(tables)} tables")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"   {t}: {count} rows")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
