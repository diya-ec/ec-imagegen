from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False for use across FastAPI's threadpool +
# the separate RQ worker process reading the same file during local dev.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist. Fine for local dev; use Alembic migrations in prod."""
    from app.db import models  # noqa: F401 (ensures models are registered on Base)
    Base.metadata.create_all(bind=engine)