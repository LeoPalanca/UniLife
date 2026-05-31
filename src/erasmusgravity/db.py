"""SQLite data layer for ErasmusGravity.

Single self-contained `data/erasmusgravity.db` holds every analysis table. CSVs in
data/processed are the producers' exports; `scripts/build_db.py` ingests them here,
and analysis/dashboard code reads from the DB.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path("data/erasmusgravity.db")


def get_conn(path: str | Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(str(path))


def write_table(df: pd.DataFrame, name: str, conn: sqlite3.Connection, if_exists: str = "replace") -> None:
    df.to_sql(name, conn, if_exists=if_exists, index=False)


def read_table(name: str, conn: sqlite3.Connection | None = None) -> pd.DataFrame:
    own = conn is None
    conn = conn or get_conn()
    try:
        return pd.read_sql_query(f'SELECT * FROM "{name}"', conn)
    finally:
        if own:
            conn.close()


def read_sql(query: str, conn: sqlite3.Connection | None = None, params=None) -> pd.DataFrame:
    own = conn is None
    conn = conn or get_conn()
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        if own:
            conn.close()


def table_names(conn: sqlite3.Connection | None = None) -> list[str]:
    own = conn is None
    conn = conn or get_conn()
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return [r[0] for r in rows]
    finally:
        if own:
            conn.close()
