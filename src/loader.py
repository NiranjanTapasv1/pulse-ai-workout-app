"""Helpers to load and clean workout history from CSV into the database."""

import datetime
from dateutil import parser
import pandas as pd
from typing import Dict, Optional

from .db import connect_db, insert_workout, init_db, upsert_exercises
from .exercises import ensure_exercise_in_library, get_library, normalize_exercise_name


def normalize_workout_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize CSV column names to standard lowercase format.

    Handles variations like 'Date'/'date', 'Exercise'/'exercise', trims whitespace.
    Raises ValueError if required columns are missing.
    """
    if df.empty:
        raise ValueError("CSV is empty or has no data rows.")

    # Strip whitespace and lowercase all column names
    df = df.rename(columns=lambda c: str(c).strip().lower())

    # Map any remaining variations if needed (e.g., 'workout_date' -> 'date')
    column_mapping = {
        'workout_date': 'date',
        'activity': 'exercise',
        # Add more mappings as needed
    }
    df = df.rename(columns=column_mapping)

    required = ['date', 'exercise']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}. Found columns: {list(df.columns)}")

    return df


def _parse_date(date_str: str) -> str:
    """Parse dates like '16th Feb' and return ISO date string.

    If the year is missing, it uses the current year.
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Invalid date")

    today = datetime.date.today()
    default = datetime.datetime(year=today.year, month=1, day=1)
    dt = parser.parse(date_str, default=default, dayfirst=True, fuzzy=True)

    # If parsed date is in the future (e.g. Feb while today is Dec), assume last year
    if dt.date() > today:
        dt = dt.replace(year=today.year - 1)

    return dt.date().isoformat()


def load_history_from_csv(
    csv_path: str,
    db_path: Optional[str] = None,
    overwrite: bool = False,
) -> None:
    """Load a workout history CSV into the SQLite database.

    The CSV is expected to have columns: date, exercise (case-insensitive).
    """
    conn = connect_db(db_path)
    init_db(conn=conn)

    # Ensure the exercise library exists in the DB.
    library = get_library()
    upsert_exercises(conn, library)

    df = pd.read_csv(csv_path)
    df = normalize_workout_columns(df)

    # Clean up common formatting issues.
    df = df.dropna(subset=["date", "exercise"]).copy()
    df["exercise"] = df["exercise"].astype(str).map(normalize_exercise_name)
    df["DateISO"] = df["date"].astype(str).map(_parse_date)

    # Insert into DB; if overwrite is True, remove existing rows with the same date+exercise.
    if overwrite:
        with conn:
            conn.execute("DELETE FROM workouts")

    exercises_in_csv = set()
    for _, row in df.iterrows():
        exercises_in_csv.add(ensure_exercise_in_library(row["exercise"]))

    # Persist any newly discovered exercises so foreign keys are satisfied.
    # Use the same metadata definitions from the static library.
    library = get_library()
    to_upsert = {name: library.get(name, {"muscle_groups": ["unknown"], "categories": ["unknown"]}) for name in exercises_in_csv}
    upsert_exercises(conn, to_upsert)

    for _, row in df.iterrows():
        insert_workout(conn, row["DateISO"], row["exercise"])

    conn.close()


def load_history_dataframe(csv_path: str) -> pd.DataFrame:
    """Return a cleaned pandas DataFrame for quick analysis."""
    df = pd.read_csv(csv_path)
    df = normalize_workout_columns(df)
    df = df.dropna(subset=["date", "exercise"]).copy()
    df["exercise"] = df["exercise"].astype(str).map(normalize_exercise_name)
    df["DateISO"] = df["date"].astype(str).map(_parse_date)
    df = df.sort_values("DateISO")
    return df


def merge_history_from_dataframe(
    df: pd.DataFrame,
    db_path: Optional[str] = None,
    assume_columns: bool = False,
) -> Dict[str, int]:
    """Merge a cleaned workout DataFrame into the database.

    Returns a dict with counts: inserted and skipped.
    """
    conn = connect_db(db_path)
    init_db(conn=conn)

    # Ensure library exists.
    library = get_library()
    upsert_exercises(conn, library)

    # Normalize columns.
    df = normalize_workout_columns(df)
    df = df.dropna(subset=["date", "exercise"]).copy()
    df["exercise"] = df["exercise"].astype(str).map(normalize_exercise_name)
    df["DateISO"] = df["date"].astype(str).map(_parse_date)

    existing = set((r["date"], r["exercise"]) for r in conn.execute("SELECT date, exercise FROM workouts"))
    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        key = (row["DateISO"], row["exercise"])
        if key in existing:
            skipped += 1
            continue
        exercise = ensure_exercise_in_library(row["exercise"])
        insert_workout(conn, row["DateISO"], exercise)
        existing.add(key)
        inserted += 1

    conn.close()
    return {"inserted": inserted, "skipped": skipped}
