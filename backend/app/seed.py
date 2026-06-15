from app.config import settings
from app.database import SCHEMA, seed_demo_data

import sqlite3
from pathlib import Path


def main() -> None:
    db_path = settings.database_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        results = seed_demo_data(conn)
        conn.commit()

    print(f"Seed complete for {db_path}")
    for table_name, inserted in results.items():
        status = "inserted demo data" if inserted else "skipped existing data"
        print(f"- {table_name}: {status}")


if __name__ == "__main__":
    main()
