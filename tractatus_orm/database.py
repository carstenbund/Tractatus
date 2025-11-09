from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///tractatus.db"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db() -> None:
    # Import inside function to avoid circular dependencies during module import.
    from .models import Proposition, Translation  # noqa: F401

    Base.metadata.create_all(bind=engine)
