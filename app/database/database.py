
import os
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine


# Use Supabase PostgreSQL when DATABASE_URL is configured.
# Otherwise, use SQLite for local development and testing.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Use the psycopg 3 driver with SQLAlchemy.
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

else:
    BASE_DIR = Path(__file__).resolve().parents[2]
    DATABASE_DIR = BASE_DIR / ".rag_cache"
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    SQLITE_URL = f"sqlite:///{DATABASE_DIR / 'rag.db'}"

    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )


def create_db_and_tables():
    """Create all registered database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Provide a database session to FastAPI endpoints."""
    with Session(engine) as session:
        yield session
