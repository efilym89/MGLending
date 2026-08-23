from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SubmissionRecord:
    submission_id: str
    state: str
    encrypted_payload: bytes | None
    attempts: int
    updated_at: int
    kommo_uid: str | None
    lead_id: int | None
    contact_id: int | None
    error_code: str | None


@dataclass(slots=True)
class JobRecord:
    id: int
    submission_id: str
    kind: str
    encrypted_payload: bytes
    attempts: int


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS submissions (
                    submission_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    encrypted_payload BLOB,
                    phone_hash TEXT NOT NULL,
                    ip_hash TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    kommo_uid TEXT,
                    lead_id INTEGER,
                    contact_id INTEGER,
                    error_code TEXT
                );
                CREATE INDEX IF NOT EXISTS submissions_phone_time
                    ON submissions(phone_hash, created_at);
                CREATE INDEX IF NOT EXISTS submissions_ip_time
                    ON submissions(ip_hash, created_at);
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    encrypted_payload BLOB NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at INTEGER NOT NULL,
                    last_error TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    UNIQUE(submission_id, kind),
                    FOREIGN KEY(submission_id) REFERENCES submissions(submission_id)
                );
                CREATE INDEX IF NOT EXISTS jobs_due ON jobs(state, next_attempt_at);
                """
            )
            connection.execute("UPDATE jobs SET state = 'pending' WHERE state = 'processing'")

    def get_submission(self, submission_id: str) -> SubmissionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM submissions WHERE submission_id = ?", (submission_id,)
            ).fetchone()
        return self._submission_from_row(row) if row else None

    def create_submission(
        self,
        submission_id: str,
        encrypted_payload: bytes,
        phone_hash: str,
        ip_hash: str,
    ) -> bool:
        now = int(time.time())
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO submissions(
                        submission_id, state, encrypted_payload, phone_hash, ip_hash,
                        created_at, updated_at
                    ) VALUES (?, 'received', ?, ?, ?, ?, ?)
                    """,
                    (submission_id, encrypted_payload, phone_hash, ip_hash, now, now),
                )
                connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def claim_submission(self, submission_id: str, stale_after_seconds: int = 60) -> bool:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE submissions
                   SET state = 'processing', attempts = attempts + 1,
                       updated_at = ?, error_code = NULL
                 WHERE submission_id = ?
                   AND (state IN ('received', 'retryable')
                        OR (state = 'processing' AND updated_at < ?))
                """,
                (now, submission_id, now - stale_after_seconds),
            )
            connection.commit()
            return cursor.rowcount == 1

    def mark_retryable(self, submission_id: str, error_code: str) -> None:
        self._update_state(submission_id, "retryable", error_code)

    def mark_failed(self, submission_id: str, error_code: str) -> None:
        self._update_state(submission_id, "failed", error_code)

    def save_kommo_and_jobs(
        self,
        submission_id: str,
        *,
        kommo_uid: str,
        lead_id: int,
        contact_id: int | None,
        jobs: list[tuple[str, bytes]],
    ) -> None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE submissions
                   SET state = 'kommo_saved', kommo_uid = ?, lead_id = ?, contact_id = ?,
                       updated_at = ?, error_code = NULL, encrypted_payload = NULL
                 WHERE submission_id = ?
                """,
                (kommo_uid, lead_id, contact_id, now, submission_id),
            )
            for kind, payload in jobs:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO jobs(
                        submission_id, kind, encrypted_payload, next_attempt_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (submission_id, kind, payload, now, now, now),
                )
            connection.commit()

    def enqueue_job(self, submission_id: str, kind: str, encrypted_payload: bytes) -> bool:
        now = int(time.time())
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO jobs(
                    submission_id, kind, encrypted_payload, next_attempt_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (submission_id, kind, encrypted_payload, now, now, now),
            )
        return cursor.rowcount == 1

    def count_recent(self, column: str, value: str, since: int) -> int:
        if column not in {"phone_hash", "ip_hash"}:
            raise ValueError("Unsupported rate-limit column")
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS total FROM submissions WHERE {column} = ? AND created_at >= ?",
                (value, since),
            ).fetchone()
        return int(row["total"])

    def claim_due_jobs(self, limit: int = 20) -> list[JobRecord]:
        now = int(time.time())
        claimed: list[JobRecord] = []
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT * FROM jobs
                 WHERE state = 'pending' AND next_attempt_at <= ?
                 ORDER BY id
                 LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            for row in rows:
                cursor = connection.execute(
                    """
                    UPDATE jobs
                       SET state = 'processing', attempts = attempts + 1, updated_at = ?
                     WHERE id = ? AND state = 'pending'
                    """,
                    (now, row["id"]),
                )
                if cursor.rowcount:
                    claimed.append(
                        JobRecord(
                            id=int(row["id"]),
                            submission_id=str(row["submission_id"]),
                            kind=str(row["kind"]),
                            encrypted_payload=bytes(row["encrypted_payload"]),
                            attempts=int(row["attempts"]) + 1,
                        )
                    )
            connection.commit()
        return claimed

    def finish_job(self, job_id: int) -> None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET state = 'done', updated_at = ?, last_error = NULL WHERE id = ?",
                (now, job_id),
            )

    def retry_job(self, job_id: int, attempts: int, error_code: str) -> None:
        now = int(time.time())
        if attempts >= 10:
            state = "dead"
            next_attempt_at = now
        else:
            state = "pending"
            next_attempt_at = now + min(3600, 2 ** min(attempts, 10) * 5)
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                   SET state = ?, next_attempt_at = ?, updated_at = ?, last_error = ?
                 WHERE id = ?
                """,
                (state, next_attempt_at, now, error_code[:100], job_id),
            )

    def health(self) -> dict[str, int]:
        with self._connect() as connection:
            submissions = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
            pending = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE state IN ('pending', 'processing')"
            ).fetchone()[0]
            dead = connection.execute("SELECT COUNT(*) FROM jobs WHERE state = 'dead'").fetchone()[
                0
            ]
        return {
            "submissions": int(submissions),
            "pending_jobs": int(pending),
            "dead_jobs": int(dead),
        }

    def _update_state(self, submission_id: str, state: str, error_code: str) -> None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE submissions
                   SET state = ?, error_code = ?, updated_at = ?
                 WHERE submission_id = ?
                """,
                (state, error_code[:100], now, submission_id),
            )

    @staticmethod
    def _submission_from_row(row: sqlite3.Row) -> SubmissionRecord:
        return SubmissionRecord(
            submission_id=str(row["submission_id"]),
            state=str(row["state"]),
            encrypted_payload=(
                bytes(row["encrypted_payload"]) if row["encrypted_payload"] else None
            ),
            attempts=int(row["attempts"]),
            updated_at=int(row["updated_at"]),
            kommo_uid=str(row["kommo_uid"]) if row["kommo_uid"] else None,
            lead_id=int(row["lead_id"]) if row["lead_id"] else None,
            contact_id=int(row["contact_id"]) if row["contact_id"] else None,
            error_code=str(row["error_code"]) if row["error_code"] else None,
        )
