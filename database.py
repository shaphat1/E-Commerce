"""
Database engine and session configuration.

Defaults to SQLite for zero-setup local development. Set DATABASE_URL to
a Postgres URL (e.g. postgresql://user:pass@host:5432/dbname) to run
against Postgres instead. Every query goes through SQLAlchemy's ORM; the
only dialect branches are the full-text search in routers/listings.py and
the advisory lock in init_db() below.

Schema management: init_db() calls create_all(), which creates missing
tables but never alters existing ones. That is fine for a first deployment;
introduce Alembic before the first schema change to a database holding real
data (see DEPLOYMENT.md).
"""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./maumart.db")

if DATABASE_URL.startswith("sqlite"):
    # 30s busy timeout: concurrent writers wait for the lock instead of failing immediately.
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
else:
    # pre_ping drops connections the server/proxy closed while idle; recycle bounds connection age.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_INIT_LOCK_ID = 727274  # arbitrary app-wide advisory lock key


def init_db():
    """
    Create any missing tables. On Postgres this takes an advisory lock so that
    several workers/containers booting at once don't race each other in
    create_all() (which otherwise intermittently fails on first boot).
    """
    import models  # noqa: F401 -- registers all tables on Base.metadata

    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _INIT_LOCK_ID})
            Base.metadata.create_all(bind=conn)
    else:
        Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
