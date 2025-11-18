import os
from sqlmodel import SQLModel, create_engine, Session


DB_PATH = os.getenv("DROP2PRINT_DB_PATH", "app/db/drop2print.sqlite3")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create database tables if they do not exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        yield session
