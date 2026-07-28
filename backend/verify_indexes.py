"""
verify_indexes.py
-----------------
Post-migration check: confirms that the unique constraint and indexes
added in migration fbdce510ef7e are live in the Supabase database.

Usage (from backend/):
    python verify_indexes.py
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv()

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

EXPECTED_INDEXES = {
    "model_suggestions": [
        {"name": "ix_model_suggestions_post_id", "columns": ["post_id"], "unique": False},
    ],
    "human_corrections": [
        {"name": "ix_human_corrections_post_id", "columns": ["post_id"], "unique": False},
    ],
}

EXPECTED_UNIQUE_CONSTRAINTS = {
    "human_corrections": [
        {"name": "uq_human_corrections_suggestion_id", "columns": ["suggestion_id"]},
    ],
}

all_ok = True

with engine.connect() as conn:
    inspector = inspect(conn)

    print("\n=== Indexes ===")
    for table, expected_list in EXPECTED_INDEXES.items():
        actual = {ix["name"]: ix for ix in inspector.get_indexes(table, schema="public")}
        print(f"\n  {table}:")
        for exp in expected_list:
            if exp["name"] in actual:
                ix = actual[exp["name"]]
                print(f"    [OK]  {ix['name']}  columns={ix['column_names']}  unique={ix['unique']}")
            else:
                print(f"    [MISSING]  {exp['name']}")
                all_ok = False

    print("\n=== Unique Constraints ===")
    for table, expected_list in EXPECTED_UNIQUE_CONSTRAINTS.items():
        actual = {uc["name"]: uc for uc in inspector.get_unique_constraints(table, schema="public")}
        print(f"\n  {table}:")
        for exp in expected_list:
            if exp["name"] in actual:
                uc = actual[exp["name"]]
                print(f"    [OK]  {uc['name']}  columns={uc['column_names']}")
            else:
                print(f"    [MISSING]  {exp['name']}")
                all_ok = False

    print()
    if all_ok:
        print("[OK] All expected indexes and constraints are present.\n")
    else:
        print("[FAIL] One or more indexes/constraints are missing.\n")
