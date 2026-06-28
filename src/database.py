from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from src.config import DATA_DIR, settings

engine = create_engine(settings.database_url, echo=False)

_SCHEMA_PATCHES = [
    "ALTER TABLE twin ADD COLUMN stopped_reason VARCHAR",
    "ALTER TABLE experimentrun ADD COLUMN replication_index INTEGER DEFAULT 1",
    "ALTER TABLE conversation ADD COLUMN constraints VARCHAR DEFAULT ''",
    "ALTER TABLE conversation ADD COLUMN difficulty VARCHAR DEFAULT 'simple'",
]


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _apply_schema_patches()


def _apply_schema_patches() -> None:
    with engine.connect() as conn:
        for stmt in _SCHEMA_PATCHES:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()


def get_session() -> Session:
    return Session(engine)
