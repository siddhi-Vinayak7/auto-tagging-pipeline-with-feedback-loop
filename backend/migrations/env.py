"""
migrations/env.py
-----------------
Alembic environment configuration.

Key behaviours:
  - DATABASE_URL is loaded exclusively from backend/.env via python-dotenv.
    It is injected at runtime into the Alembic config so no credentials ever
    appear in alembic.ini or in version control.
  - target_metadata points to our SQLAlchemy Base so `alembic revision --autogenerate`
    can diff the models against the live schema.
  - For online migrations, get_engine() from database.py is used directly
    (lazy — only called when a live connection is actually needed).
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy import text

from alembic import context

# ---------------------------------------------------------------------------
# Make sure `backend/` is on sys.path so imports of database and models work.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env from the backend directory (one level above migrations/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject DATABASE_URL into Alembic config from environment.
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# ---------------------------------------------------------------------------
# Import models — this registers all ORM classes on Base.metadata.
# database.py uses a lazy engine so importing it here is safe even when
# DATABASE_URL contains a placeholder value (autogenerate only needs metadata).
# ---------------------------------------------------------------------------
from database import Base  # noqa: E402
import models  # noqa: E402, F401

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL without a live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (apply directly to the database)."""
    # Validate URL is real before attempting connection
    url = config.get_main_option("sqlalchemy.url")
    if not url or "HOST" in url or "PASSWORD" in url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Fill in backend/.env with your real Supabase connection string."
        )

    from database import get_engine
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
