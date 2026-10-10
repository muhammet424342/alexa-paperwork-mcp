import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any


def get_db_path():
    return os.environ.get("PAPERWORK_DB", "./paperwork.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                vendor TEXT,
                amount REAL,
                currency TEXT,
                due_date TEXT,
                paid INTEGER DEFAULT 0,
                raw_text TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def add_document(
    kind: str,
    vendor: Optional[str],
    amount: Optional[float],
    currency: Optional[str],
    due_date: Optional[str],
    raw_text: str
) -> Dict[str, Any]:
    created_at = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO documents (kind, vendor, amount, currency, due_date, paid, raw_text, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (kind, vendor, amount, currency, due_date, raw_text, created_at)
        )
        conn.commit()
        doc_id = cur.lastrowid
    return get_document_by_id(doc_id)


def get_document_by_id(doc_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


def list_due(days: int = 7) -> List[Dict[str, Any]]:
    from datetime import date, timedelta
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM documents
            WHERE paid = 0 AND due_date IS NOT NULL AND due_date <= ?
            ORDER BY due_date ASC
            """,
            (cutoff,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_document(vendor: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM documents
            WHERE vendor LIKE ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (f"%{vendor}%",)
        ).fetchone()
    return dict(row) if row else None


def mark_paid(document_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE documents SET paid = 1 WHERE id = ?",
            (document_id,)
        )
        conn.commit()
    return cur.rowcount > 0


def monthly_total(month: str = "") -> Dict[str, float]:
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT currency, SUM(amount) as total
            FROM documents
            WHERE strftime('%Y-%m', created_at) = ? AND amount IS NOT NULL
            GROUP BY currency
            """,
            (month,)
        ).fetchall()
    return {row["currency"]: row["total"] for row in rows if row["currency"]}