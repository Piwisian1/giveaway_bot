"""
SQLite connection management.

Uses WAL journal mode plus a single dedicated writer task: all writes
are serialized through one asyncio.Queue-backed connection to avoid
"database is locked" errors under aiogram's concurrent handler
execution, while reads use their own short-lived connections. See the
architecture doc, section 9 (Deployment Strategy / SQLite concurrency).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import aiosqlite

from bot.config import settings

_PRAGMAS = (
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;",
    "PRAGMA busy_timeout=5000;",
)

# Sentinel put on the write queue to tell the writer loop to stop.
_STOP = object()


class DatabaseConnection:
    """
    Owns the single writer connection/queue and hands out short-lived
    read connections.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or settings.db_path
        self._write_queue: asyncio.Queue[Any] | None = None
        self._writer_task: asyncio.Task | None = None
        self._writer_conn: aiosqlite.Connection | None = None

    async def start(self) -> None:
        """Opens the writer connection, applies PRAGMAs, starts the writer loop."""
        parent_dir = os.path.dirname(self._db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        self._writer_conn = await aiosqlite.connect(self._db_path)
        for pragma in _PRAGMAS:
            await self._writer_conn.execute(pragma)
        await self._writer_conn.commit()

        self._write_queue = asyncio.Queue()
        self._writer_task = asyncio.create_task(self._writer_loop(), name="db-writer")

    async def stop(self) -> None:
        """Drains the write queue and closes the writer connection."""
        if self._write_queue is not None:
            await self._write_queue.put(_STOP)
        if self._writer_task is not None:
            await self._writer_task
        if self._writer_conn is not None:
            await self._writer_conn.close()

    async def _writer_loop(self) -> None:
        assert self._write_queue is not None
        assert self._writer_conn is not None
        while True:
            item = await self._write_queue.get()
            if item is _STOP:
                return
            query, params, future, return_rowcount = item
            try:
                cursor = await self._writer_conn.execute(query, params)
                await self._writer_conn.commit()
                if not future.done():
                    result = cursor.rowcount if return_rowcount else cursor.lastrowid
                    future.set_result(result)
            except Exception as exc:  # noqa: BLE001 - propagated to the caller via the future
                if not future.done():
                    future.set_exception(exc)

    async def execute_write(self, query: str, params: tuple = ()) -> int | None:
        """Enqueues a write statement and waits for the single writer task to execute it.

        Returns the new row's lastrowid (useful for INSERTs); callers that
        don't need it can ignore the return value.
        """
        return await self._enqueue_write(query, params, return_rowcount=False)

    async def execute_write_rowcount(self, query: str, params: tuple = ()) -> int:
        """
        Like execute_write, but returns the number of rows the statement
        actually matched instead of lastrowid — for an UPDATE/DELETE whose
        caller needs to know whether it matched anything, e.g. an atomic
        compare-and-set (see GiveawayRepository.close_if_active).
        """
        return await self._enqueue_write(query, params, return_rowcount=True)

    async def _enqueue_write(self, query: str, params: tuple, *, return_rowcount: bool) -> int:
        if self._write_queue is None:
            raise RuntimeError("DatabaseConnection.start() must be called before use")
        future: asyncio.Future[int] = asyncio.get_running_loop().create_future()
        await self._write_queue.put((query, params, future, return_rowcount))
        return await future

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict]:
        """Runs a read query on a short-lived connection, returns all rows as dicts."""
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def fetch_one(self, query: str, params: tuple = ()) -> dict | None:
        """Runs a read query on a short-lived connection, returns the first row as a dict."""
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row is not None else None


_connection: DatabaseConnection | None = None


def get_connection() -> DatabaseConnection:
    """Returns the process-wide DatabaseConnection singleton."""
    global _connection
    if _connection is None:
        _connection = DatabaseConnection()
    return _connection
