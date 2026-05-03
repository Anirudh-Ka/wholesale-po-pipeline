"""SQLite connection helpers and database initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_SEED_PATH = _PROJECT_ROOT / "data" / "inventory_seed.sql"
DEFAULT_DB_PATH = _PROJECT_ROOT / "inventory.db"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to Row."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    """Create tables and seed inventory if empty."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = get_connection(path)
    try:
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()

        row = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()
        if row[0] == 0 and _SEED_PATH.exists():
            seed_sql = _SEED_PATH.read_text(encoding="utf-8")
            conn.executescript(seed_sql)
            conn.commit()
            print(f"Seeded inventory from {_SEED_PATH}")
        print(f"Database initialised at {path}")
    finally:
        conn.close()


def get_inventory_item(sku: str, db_path: Path | str | None = None) -> sqlite3.Row | None:
    """Return a single inventory row for *sku*, or None if not found."""
    conn = get_connection(db_path)
    try:
        return conn.execute(
            "SELECT * FROM inventory WHERE sku = ?", (sku,)
        ).fetchone()
    finally:
        conn.close()


def save_processed_po(
    po_number: str,
    retailer: str,
    submitted_date: str,
    processed_at: str,
    status: str,
    validation_json: str | None,
    exception_json: str | None,
    db_path: Path | str | None = None,
) -> None:
    """Insert or replace a processed PO record."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO processed_pos
            (po_number, retailer, submitted_date, processed_at, status, validation_json, exception_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (po_number, retailer, submitted_date, processed_at, status, validation_json, exception_json),
        )
        conn.commit()
    finally:
        conn.close()


def get_processed_po(po_number: str, db_path: Path | str | None = None) -> sqlite3.Row | None:
    """Return a processed_pos row by PO number, or None if not found."""
    conn = get_connection(db_path)
    try:
        return conn.execute(
            "SELECT * FROM processed_pos WHERE po_number = ?", (po_number,)
        ).fetchone()
    finally:
        conn.close()
