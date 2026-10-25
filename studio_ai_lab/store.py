from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_STATES = ("waiting", "running")
TERMINAL_STATES = ("succeeded", "failed", "cancelled")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self.database = database
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    asset_paths_json TEXT NOT NULL,
                    output_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS jobs_owner_created "
                "ON jobs(owner_id, created_at DESC)"
            )
        if os.name == "posix":
            os.chmod(self.database, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        result = dict(row)
        result["config"] = json.loads(result.pop("config_json"))
        result["asset_paths"] = json.loads(result.pop("asset_paths_json"))
        return result

    def create(
        self,
        job_id: str,
        owner_id: str,
        config: dict[str, Any],
        asset_paths: list[str],
        max_active_jobs: int,
    ) -> bool:
        now = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE owner_id = ? "
                "AND status IN ('waiting', 'running')",
                (owner_id,),
            ).fetchone()[0]
            if active >= max_active_jobs:
                return False
            connection.execute(
                """
                INSERT INTO jobs
                    (id, owner_id, status, config_json, asset_paths_json,
                     created_at, updated_at)
                VALUES (?, ?, 'waiting', ?, ?, ?, ?)
                """,
                (
                    job_id,
                    owner_id,
                    json.dumps(config, ensure_ascii=False),
                    json.dumps(asset_paths),
                    now,
                    now,
                ),
            )
        return True

    def get(self, job_id: str, owner_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ? AND owner_id = ?",
                (job_id, owner_id),
            ).fetchone()
        return self._decode(row)

    def list(self, owner_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE owner_id = ? "
                "ORDER BY created_at DESC LIMIT 100",
                (owner_id,),
            ).fetchall()
        return [self._decode(row) for row in rows if row is not None]

    def start(self, job_id: str, owner_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = 'running', updated_at = ? "
                "WHERE id = ? AND owner_id = ? AND status = 'waiting'",
                (utc_now(), job_id, owner_id),
            )
            if cursor.rowcount != 1:
                return None
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ? AND owner_id = ?",
                (job_id, owner_id),
            ).fetchone()
        return self._decode(row)

    def fail(self, job_id: str, owner_id: str, error: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = 'failed', error = ?, updated_at = ? "
                "WHERE id = ? AND owner_id = ? AND status = 'running'",
                (error[:500], utc_now(), job_id, owner_id),
            )

    def complete(self, job_id: str, owner_id: str, output_path: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = 'succeeded', output_path = ?, "
                "updated_at = ? WHERE id = ? AND owner_id = ? AND status = 'running'",
                (output_path, utc_now(), job_id, owner_id),
            )
        return cursor.rowcount == 1

    def cancel(self, job_id: str, owner_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = 'cancelled', updated_at = ? "
                "WHERE id = ? AND owner_id = ? AND status IN ('waiting', 'running')",
                (utc_now(), job_id, owner_id),
            )
        return cursor.rowcount == 1
