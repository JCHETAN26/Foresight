"""Async Postgres access via a psycopg connection pool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings

_SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


class Database:
    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or settings.database_url
        self.pool: AsyncConnectionPool | None = None

    async def connect(self) -> None:
        self.pool = AsyncConnectionPool(self._dsn, min_size=1, max_size=10, open=False)
        await self.pool.open()
        await self.init_schema()

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()

    async def init_schema(self) -> None:
        assert self.pool is not None
        async with self.pool.connection() as conn:
            await conn.execute(_SCHEMA)

    async def fetch(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        assert self.pool is not None
        async with self.pool.connection() as conn:
            cur = conn.cursor(row_factory=dict_row)
            await cur.execute(query, params)
            return await cur.fetchall()


db = Database()
