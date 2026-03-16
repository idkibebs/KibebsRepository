"""
Database connection, schema initialisation, and low-level helpers.
"""
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

from config.settings import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # better concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_conn():
    """Context manager: auto-commit on success, rollback on error."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables from schema.sql if they don't exist."""
    schema = SCHEMA_PATH.read_text()
    with db_conn() as conn:
        conn.executescript(schema)
    logger.info("Database initialised at %s", DB_PATH)


# ── Pipeline run helpers ──────────────────────────────────────────────────────

def start_pipeline_run(run_type: str) -> int:
    """Insert a new pipeline_run row and return its id."""
    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO pipeline_runs (run_type, status, started_at) VALUES (?,?,?)",
            (run_type, "running", _now()),
        )
        return cur.lastrowid


def finish_pipeline_run(run_id: int, status: str, records: int = 0, notes: str = ""):
    """Update a pipeline_run row on completion."""
    with db_conn() as conn:
        conn.execute(
            """UPDATE pipeline_runs
               SET status=?, records_synced=?, finished_at=?, notes=?
               WHERE id=?""",
            (status, records, _now(), notes, run_id),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
