"""Rule-based recommendation engine for next-day workouts."""

import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .db import ensure_db_initialized, connect_db, fetch_workouts, fetch_exercises


def _date_from_iso(date_iso: str) -> datetime.date:
    return datetime.date.fromisoformat(date_iso)


def _days_since(date_iso: str, reference: Optional[datetime.date] = None) -> int:
    if reference is None:
        reference = datetime.date.today()
    return (reference - _date_from_iso(date_iso)).days


def _group_muscle_history(
    workouts: List[Dict],
    exercise_meta: Dict[str, Dict],
    lookback_days: int = 14,
) -> Dict[str, int]:
    """Compute days since each muscle group was last trained."""
    today = datetime.date.today()
    muscle_days: Dict[str, int] = {}
    cutoff = today - datetime.timedelta(days=lookback_days)

    for w in workouts:
        date = _date_from_iso(w["date"])
        if date < cutoff:
            continue
        ex = w["exercise"]
        meta = exercise_meta.get(ex, {})
        groups = meta.get("muscle_groups", ["unknown"])
        for group in groups:
            if group == "rest":
                continue
            prev = muscle_days.get(group)
            # store the most recent date (smallest days since)
            if prev is None or date > _date_from_iso(prev):
                muscle_days[group] = w["date"]

    # Convert to days since
    return {g: _days_since(d, today) for g, d in muscle_days.items()}


def _pick_exercises_for_groups(
    exercise_meta: Dict[str, Dict],
    target_groups: List[str],
    exclude_groups: Optional[List[str]] = None,
    max_picks: int = 3,
) -> List[str]:
    """Pick exercises that match target muscle groups, avoiding excluded groups."""
    exclude_groups = set(exclude_groups or [])
    picks: List[Tuple[int, str]] = []

    for name, meta in exercise_meta.items():
        groups = set(meta.get("muscle_groups", []))
        if groups & exclude_groups:
            continue
        score = len(groups & set(target_groups))
        if score == 0:
            continue
        picks.append((score, name))

    picks.sort(key=lambda tup: (-tup[0], tup[1]))
    return [name for _, name in picks[:max_picks]]


def _format_focus(groups: List[str]) -> str:
    """Create a human-readable focus description from muscle groups."""
    if not groups:
        return "General fitness"
    # Prefer more descriptive naming for common groups.
    groups = [g.replace("_", " ").title() for g in groups]
    if len(groups) == 1:
        return groups[0]
    return ", ".join(groups[:-1]) + " & " + groups[-1]


def recommend_next_workout(
    db_path: Optional[str] = None,
    today: Optional[datetime.date] = None,
) -> Dict[str, object]:
    """Return a recommendation for the next workout and a short explanation."""
    if today is None:
        today = datetime.date.today()

    conn = ensure_db_initialized(db_path)
    exercises = fetch_exercises(conn)
    workouts = fetch_workouts(conn)
    conn.close()

    if not workouts:
        # First-time user recommendation
        recs = ["Cardio", "Bench", "Rows"]
        reason = (
            "No workout history found yet. Start with a balanced session including cardio, a push, "
            "and a pull movement."
        )
        return {
            "date": today.isoformat(),
            "workout_focus": "Full body",
            "recommended_exercises": recs,
            "estimated_duration_min": 30,
            "workout_type": "strength",
            "reason": reason,
        }

    # Determine when the last workout happened (most recent day).
    last_date = _date_from_iso(workouts[0]["date"])
    days_since_last = (today - last_date).days

    # Detect whether the last logged session was a rest day.
    last_day_exercises = [w["exercise"] for w in workouts if _date_from_iso(w["date"]) == last_date]
    last_was_rest = all(ex.lower().strip() == "rest day" for ex in last_day_exercises)

    # Figure out which muscle groups are least recently trained.
    muscle_days = _group_muscle_history(workouts, exercises, lookback_days=28)

    # Define desired maximum days between hits for each group.
    group_thresholds = {
        "legs": 3,
        "back": 4,
        "chest": 4,
        "shoulders": 4,
        "arms": 4,
        "core": 3,
        "calves": 5,
        "hamstrings": 5,
        "glutes": 5,
        "cardio": 2,
    }

    # Determine neglected groups.
    neglected = []
    for group, thresh in group_thresholds.items():
        days = muscle_days.get(group, 999)
        if days >= thresh:
            neglected.append((days, group))

    neglected.sort(reverse=True)
    neglected_groups = [g for _, g in neglected]

    # Track which muscle groups were worked yesterday to avoid repeating them.
    yesterday_groups = []
    if workouts and days_since_last <= 1 and not last_was_rest:
        seen = set()
        for w in workouts:
            if _date_from_iso(w["date"]) != last_date:
                break
            for g in exercises.get(w["exercise"], {}).get("muscle_groups", []):
                if g not in seen:
                    seen.add(g)
                    yesterday_groups.append(g)

    # Decide workout structure based on recent activity.
    if days_since_last >= 3:
        # If the user has missed multiple days, suggest a light re-entry.
        focus_groups = ["cardio", "core"]
        reason = (
            f"It has been {days_since_last} days since your last log. "
            "A gentle, balanced session is a good way to re-engage safely."
        )
        workout_type = "recovery"
    elif last_was_rest:
        focus_groups = neglected_groups[:2] or ["legs", "back"]
        reason = (
            "You logged a rest day last time. Today's session can focus on undertrained areas "
            "while keeping things balanced."
        )
        workout_type = "strength"
    else:
        if neglected_groups:
            focus_groups = neglected_groups[:2]
            reason = (
                "These muscle groups haven’t been trained recently, so today’s session "
                "prioritizes them to keep your training balanced."
            )
        else:
            # If nothing is neglected, rotate focus based on the most recent session.
            focus_groups = yesterday_groups[:2] or ["legs", "back"]
            reason = (
                "You’ve been consistent recently. This session keeps the momentum by "
                "staying balanced and avoiding repeating the same muscle groups."
            )
        workout_type = "strength"

    # Build a workout around the selected focus groups.
    primary_exercises = _pick_exercises_for_groups(
        exercises,
        target_groups=focus_groups,
        exclude_groups=yesterday_groups,
        max_picks=2,
    )

    # Add a core or cardio exercise if not present.
    support_exercises = []
    if "core" not in focus_groups:
        support_exercises.extend(
            _pick_exercises_for_groups(exercises, target_groups=["core"], max_picks=1)
        )
    if "cardio" not in focus_groups:
        support_exercises.extend(
            _pick_exercises_for_groups(exercises, target_groups=["cardio"], max_picks=1)
        )

    # Deduplicate and keep order.
    recommended = []
    for ex in primary_exercises + support_exercises:
        if ex not in recommended:
            recommended.append(ex)

    # If we still have too few exercises, fill in with a general movement.
    if len(recommended) < 3:
        filler = _pick_exercises_for_groups(
            exercises,
            target_groups=["legs", "back", "chest"],
            exclude_groups=yesterday_groups,
            max_picks=3,
        )
        for ex in filler:
            if ex not in recommended:
                recommended.append(ex)

    # If all else fails, provide a basic fallback.
    if not recommended:
        recommended = ["Cardio", "Squats", "Rows"]
        reason += "\nFallback to a simple full-body session."

    # Estimate duration (minutes) based on number of exercises.
    estimated_duration = 10 + 10 * len(recommended)

    return {
        "date": today.isoformat(),
        "workout_focus": _format_focus(focus_groups),
        "recommended_exercises": recommended,
        "estimated_duration_min": estimated_duration,
        "workout_type": workout_type,
        "reason": reason,
    }
