"""
Databaza SQLite - ruan historikun e plotë të çdo coin të analizuar.
Përdoret për: shmangie ri-analize, tracking të momentum-it, verifikim
performance të sistemit me kohë.
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

import config

log = logging.getLogger("scanner.database")


@contextmanager
def get_connection():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database():
    """Krijon tabelat nëse s'ekzistojnë ende."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coin_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                token_symbol TEXT,
                token_name TEXT,
                chain TEXT,
                scanned_at TEXT NOT NULL,
                price_usd REAL,
                liquidity_usd REAL,
                volume_24h REAL,
                holders_count INTEGER,
                final_score REAL,
                category TEXT,
                component_scores TEXT,
                risk_flags TEXT,
                notified INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_address
            ON coin_scans (token_address)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scanned_at
            ON coin_scans (scanned_at)
        """)
    log.info("Databaza u inicializua.")


def save_scan_result(result_dict):
    """Ruan një rezultat skanimi të vetëm."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO coin_scans (
                token_address, token_symbol, token_name, chain, scanned_at,
                price_usd, liquidity_usd, volume_24h, holders_count,
                final_score, category, component_scores, risk_flags, notified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_dict.get("token_address"),
            result_dict.get("token_symbol"),
            result_dict.get("token_name"),
            result_dict.get("chain"),
            datetime.now(timezone.utc).isoformat(),
            result_dict.get("price_usd", 0),
            result_dict.get("liquidity_usd", 0),
            result_dict.get("volume_24h", 0),
            result_dict.get("holders_count"),
            result_dict.get("final_score", 0),
            result_dict.get("category", ""),
            json.dumps(result_dict.get("component_scores", {})),
            json.dumps(result_dict.get("risk_flags", [])),
            0,
        ))


def was_recently_scanned(token_address, within_hours=1):
    """Kontrollon nëse ky token u skanua tashmë brenda X orësh (shmang punë të dyfishtë)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=within_hours)).isoformat()
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id FROM coin_scans
            WHERE token_address = ? AND scanned_at > ?
            ORDER BY scanned_at DESC LIMIT 1
        """, (token_address, cutoff)).fetchone()
        return row is not None


def get_previous_scan(token_address):
    """Merr skanimin e fundit të mëparshëm për një token (për llogaritje momentum)."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM coin_scans
            WHERE token_address = ?
            ORDER BY scanned_at DESC LIMIT 1
        """, (token_address,)).fetchone()
        return dict(row) if row else None


def mark_as_notified(token_address, scanned_at):
    """Shënon një rezultat si tashmë të njoftuar (shmang njoftime të dyfishta)."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE coin_scans SET notified = 1
            WHERE token_address = ? AND scanned_at = ?
        """, (token_address, scanned_at))


def was_notified_recently(token_address, within_hours=24):
    """Kontrollon nëse tashmë u dërgua njoftim për këtë coin kohët e fundit."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=within_hours)).isoformat()
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id FROM coin_scans
            WHERE token_address = ? AND scanned_at > ? AND notified = 1
            LIMIT 1
        """, (token_address, cutoff)).fetchone()
        return row is not None


def get_top_results(limit=20, min_score=0):
    """Merr rezultatet më të fundit, renditur sipas piketës (për dashboard)."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM coin_scans
            WHERE final_score >= ?
            AND scanned_at > ?
            ORDER BY final_score DESC
            LIMIT ?
        """, (
            min_score,
            (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(),
            limit,
        )).fetchall()
        return [dict(r) for r in rows]


def get_scan_history_for_token(token_address):
    """Merr të gjithë historikun e një token-i specifik (për grafik trend nëse duhet)."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM coin_scans
            WHERE token_address = ?
            ORDER BY scanned_at ASC
        """, (token_address,)).fetchall()
        return [dict(r) for r in rows]
