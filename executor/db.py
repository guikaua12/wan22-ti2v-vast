import json
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class ClaimedJob:
    job_id: str
    job_type: str
    request_payload: dict[str, Any]
    attempt: int
    max_attempts: int


class QueueDb:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def claim(self, conn, executor_id: str, capabilities: dict[str, Any]) -> ClaimedJob | None:
        row = conn.execute(
            "SELECT * FROM gpu_claim_generation_job(%s, %s::jsonb)",
            (executor_id, json.dumps(capabilities)),
        ).fetchone()
        conn.commit()
        if row is None:
            return None
        return ClaimedJob(
            job_id=str(row["job_id"]),
            job_type=row["job_type"],
            request_payload=row["request_payload"],
            attempt=row["attempt"],
            max_attempts=row["max_attempts"],
        )

    def heartbeat(self, conn, job_id: str, executor_id: str, status: str, progress: int, note: str, metadata: dict[str, Any] | None = None) -> bool:
        row = conn.execute(
            "SELECT gpu_heartbeat_generation_job(%s, %s, %s, %s, %s, %s::jsonb) AS ok",
            (job_id, executor_id, status, progress, note, json.dumps(metadata or {})),
        ).fetchone()
        conn.commit()
        return bool(row and row["ok"])

    def complete(self, conn, job_id: str, executor_id: str, result: dict[str, Any]) -> bool:
        row = conn.execute(
            "SELECT gpu_complete_generation_job(%s, %s, %s::jsonb) AS ok",
            (job_id, executor_id, json.dumps(result)),
        ).fetchone()
        conn.commit()
        return bool(row and row["ok"])

    def fail(self, conn, job_id: str, executor_id: str, error_code: str, error_message: str, retriable: bool, stage: str) -> str | None:
        row = conn.execute(
            "SELECT gpu_fail_generation_job(%s, %s, %s, %s, %s, %s) AS status",
            (job_id, executor_id, error_code, error_message, retriable, stage),
        ).fetchone()
        conn.commit()
        return row["status"] if row else None
