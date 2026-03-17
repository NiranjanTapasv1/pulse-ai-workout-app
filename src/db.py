"""Database helpers for the workout tracker.

This module uses SQLite for storage so the app can run without external services.
"""

import datetime
import json
import os
import sqlite3
from pathlib import Path

from typing import Any, Dict, List, Optional


def get_db_path() -> str:
    """Return the path where the SQLite database is stored."""
    root = Path(__file__).resolve().parent.parent
    return str(root / "workouts.db")


def connect_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a sqlite3 connection with useful defaults."""
    if db_path is None:
        db_path = get_db_path()

    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_def: str) -> None:
    """Add a column to a table if it doesn't already exist."""
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")


def init_db(conn: Optional[sqlite3.Connection] = None, db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create the tables if they do not exist."""
    close_after = False
    if conn is None:
        conn = connect_db(db_path)
        close_after = True

    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                name TEXT PRIMARY KEY,
                meta_json TEXT NOT NULL
            )
            """
        )

        # Add structured fields for exercise library metadata.
        _ensure_column(
            conn,
            "exercises",
            "muscle_groups",
            "muscle_groups TEXT DEFAULT '[]'",
        )
        _ensure_column(
            conn,
            "exercises",
            "workout_type",
            "workout_type TEXT DEFAULT ''",
        )
        _ensure_column(
            conn,
            "exercises",
            "equipment",
            "equipment TEXT DEFAULT ''",
        )
        _ensure_column(
            conn,
            "exercises",
            "intensity_level",
            "intensity_level TEXT DEFAULT ''",
        )
        _ensure_column(
            conn,
            "exercises",
            "is_active",
            "is_active INTEGER DEFAULT 1",
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                exercise TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (exercise) REFERENCES exercises(name)
            )
            """
        )

    if close_after:
        conn.close()
    return conn


def upsert_exercises(conn: sqlite3.Connection, exercises: Dict[str, Dict[str, Any]]) -> None:
    """Insert or update exercises metadata into the database.

    This maintains backward compatibility via `meta_json` while also
    storing structured fields for the exercise library.
    """
    with conn:
        for name, meta in exercises.items():
            muscle_groups = json.dumps(meta.get("muscle_groups", []), sort_keys=True)
            workout_type = meta.get("workout_type", "")
            equipment = meta.get("equipment", "")
            intensity_level = meta.get("intensity_level", "")
            is_active = 1 if meta.get("is_active", True) else 0

            conn.execute(
                "INSERT INTO exercises "
                "(name, meta_json, muscle_groups, workout_type, equipment, intensity_level, is_active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET "
                "meta_json = excluded.meta_json, "
                "muscle_groups = excluded.muscle_groups, "
                "workout_type = excluded.workout_type, "
                "equipment = excluded.equipment, "
                "intensity_level = excluded.intensity_level, "
                "is_active = excluded.is_active",
                (
                    name,
                    json.dumps(meta, sort_keys=True),
                    muscle_groups,
                    workout_type,
                    equipment,
                    intensity_level,
                    is_active,
                ),
            )


def insert_workout(conn: sqlite3.Connection, date_iso: str, exercise_name: str) -> None:
    """Insert a single workout record."""
    with conn:
        conn.execute(
            "INSERT INTO workouts (date, exercise) VALUES (?, ?)",
            (date_iso, exercise_name),
        )


def fetch_workouts(conn: sqlite3.Connection, limit: Optional[int] = None) -> List[sqlite3.Row]:
    """Fetch workouts ordered by date descending."""
    query = "SELECT * FROM workouts ORDER BY date DESC, id DESC"
    if limit is not None:
        query += " LIMIT ?"
        return list(conn.execute(query, (limit,)))
    return list(conn.execute(query))


def fetch_exercises(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """Return the exercise library from the DB."""
    rows = conn.execute(
        "SELECT name, meta_json, muscle_groups, workout_type, equipment, intensity_level, is_active FROM exercises"
    ).fetchall()

    result: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        meta = json.loads(r["meta_json"])
        # Prefer structured columns if available.
        try:
            meta["muscle_groups"] = json.loads(r["muscle_groups"] or "[]")
        except Exception:
            meta["muscle_groups"] = meta.get("muscle_groups", [])

        meta["workout_type"] = r["workout_type"] or meta.get("workout_type", "")
        meta["equipment"] = r["equipment"] or meta.get("equipment", "")
        meta["intensity_level"] = r["intensity_level"] or meta.get("intensity_level", "")
        meta["is_active"] = bool(r["is_active"])

        result[r["name"]] = meta
    return result


def ensure_db_initialized(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Make sure the database exists and has the required schema."""
    conn = connect_db(db_path)
    init_db(conn=conn)
    return conn
