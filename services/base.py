from __future__ import annotations

from pathlib import Path

from domain.repositories.sqlite import SqliteRepository


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "runtime" / "traffic_factory.sqlite3"


class BaseService:
    def __init__(self, repository: SqliteRepository | None = None, *, db_path: str | Path | None = None):
        target_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self.repository = repository or SqliteRepository(target_path)
