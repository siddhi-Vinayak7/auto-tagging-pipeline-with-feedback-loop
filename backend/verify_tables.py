"""
verify_tables.py
----------------
Run after migration to confirm the three expected tables exist in the database.

Usage (from backend/):
    python verify_tables.py
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

with engine.connect() as conn:
    inspector = inspect(conn)
    tables = inspector.get_table_names(schema="public")
    print("\n=== Tables in 'public' schema ===")
    for t in sorted(tables):
        print(f"  {t}")
    print()

    expected = {"posts", "model_suggestions", "human_corrections"}
    missing = expected - set(tables)
    if missing:
        print(f"[FAIL] Missing tables: {missing}")
    else:
        print("[OK] All three expected tables are present.")
        # Show column names for each
        for table_name in sorted(expected):
            cols = [c["name"] for c in inspector.get_columns(table_name, schema="public")]
            print(f"  {table_name}: {cols}")
    print()
