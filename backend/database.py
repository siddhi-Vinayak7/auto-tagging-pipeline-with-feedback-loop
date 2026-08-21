"""
database.py
-----------
SQLAlchemy engine and session factory.

The DATABASE_URL is read exclusively from the environment (loaded via
python-dotenv from backend/.env).  No credentials are ever hardcoded here.

Engine creation is deferred to `get_engine()` so that importing this module
(e.g. from Alembic migrations) does not immediately attempt a DB connection
with a placeholder URL.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load variables from .env (only if not already set in the environment)
load_dotenv()

Base = declarative_base()

# ---------------------------------------------------------------------------
# Lazy engine — created on first call, not at module import time.
# This lets Alembic import Base (and the models) without needing a real URL.
# ---------------------------------------------------------------------------
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url or "HOST" in database_url or "PASSWORD" in database_url:
            database_url = "sqlite:///./dev.db"
        
        connect_args = {}
        if database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        _engine = create_engine(
            database_url,
            pool_pre_ping=True if not database_url.startswith("sqlite") else False,
            connect_args=connect_args,
            echo=False,
        )
        if database_url.startswith("sqlite"):
            Base.metadata.create_all(bind=_engine)
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


# Convenience alias — use get_session_local()() to obtain a session
SessionLocal = get_session_local
