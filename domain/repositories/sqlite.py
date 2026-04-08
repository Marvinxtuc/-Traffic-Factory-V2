from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, TypeVar

from domain.models.base import DomainRecord


ModelT = TypeVar("ModelT", bound=DomainRecord)


class SqliteRepository:
    """Minimal SQLite repository used by service skeletons.

    This is intentionally thin: enough to load, insert, update and query
    phase-one domain records without expanding into a full persistence layer.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _managed_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def add(self, entity: ModelT) -> ModelT:
        payload = entity.to_record()
        columns = ", ".join(payload.keys())
        placeholders = ", ".join("?" for _ in payload)
        sql = f"INSERT INTO {entity.TABLE_NAME} ({columns}) VALUES ({placeholders})"
        with self._managed_connection() as connection:
            connection.execute(sql, tuple(payload.values()))
            connection.commit()
        return entity

    def update(self, entity: ModelT) -> ModelT:
        payload = entity.to_record()
        entity_id = payload.pop("id")
        assignments = ", ".join(f"{column} = ?" for column in payload)
        sql = f"UPDATE {entity.TABLE_NAME} SET {assignments} WHERE id = ?"
        with self._managed_connection() as connection:
            connection.execute(sql, (*payload.values(), entity_id))
            connection.commit()
        return entity

    def get(self, model_cls: type[ModelT], entity_id: str) -> ModelT | None:
        sql = f"SELECT * FROM {model_cls.TABLE_NAME} WHERE id = ?"
        with self._managed_connection() as connection:
            row = connection.execute(sql, (entity_id,)).fetchone()
        if row is None:
            return None
        return model_cls.from_record(row)

    def exists(self, model_cls: type[ModelT], entity_id: str) -> bool:
        sql = f"SELECT 1 FROM {model_cls.TABLE_NAME} WHERE id = ? LIMIT 1"
        with self._managed_connection() as connection:
            row = connection.execute(sql, (entity_id,)).fetchone()
        return row is not None

    def list(
        self,
        model_cls: type[ModelT],
        *,
        where: dict[str, Any] | None = None,
        order_by: str | None = None,
    ) -> list[ModelT]:
        where = where or {}
        sql = f"SELECT * FROM {model_cls.TABLE_NAME}"
        params: list[Any] = []
        if where:
            clauses = [f"{column} = ?" for column in where]
            sql += " WHERE " + " AND ".join(clauses)
            params.extend(where.values())
        if order_by:
            sql += f" ORDER BY {order_by}"
        with self._managed_connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [model_cls.from_record(row) for row in rows]

    def scalar(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> Any:
        with self._managed_connection() as connection:
            row = connection.execute(sql, tuple(params or ())).fetchone()
        if row is None:
            return None
        return row[0]

    def execute(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> int:
        with self._managed_connection() as connection:
            cursor = connection.execute(sql, tuple(params or ()))
            connection.commit()
        return cursor.rowcount
