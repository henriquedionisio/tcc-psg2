from __future__ import annotations

from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from src.config import DATA_DIR, settings

engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
