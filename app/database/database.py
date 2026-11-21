
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine


# Store the SQLite database in the project root
BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_DIR = BASE_DIR / ".rag_cache"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATABASE_DIR / 'rag.db'}"

# SQLite connection configuration
connect_args = {
    "check_same_thread": False
}

# Create database engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)


def create_db_and_tables():
    """Create all registered database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Provide a database session to FastAPI endpoints."""
    with Session(engine) as session:
        yield session
