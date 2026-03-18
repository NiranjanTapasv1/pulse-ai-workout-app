"""Rule-based recommendation engine for next-day workouts."""

import datetime
from typing import Dict, List, Optional, Tuple

from .db import ensure_db_initialized, fetch_workouts, fetch_exercises


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
    reference_date: Optional[datetime.date] = None,
) -> Dict[str, int]:
    """Compute days since each muscle group was last trained."""
    if reference_date is None:
        reference_date = datetime.date.today()

    muscle_days: Dict[str, str] = {}
    cutoff = reference_date - datetime.timedelta(days=lookback_days)

    for workout in workouts:
        workout_date = _date_from_iso(workout["date"])
        if workout_date < cutoff:
            continue

        exercise = workout["exercise"]
        meta = exercise_meta.get(exercise, {})
        groups = meta.get("muscle_groups", ["unknown"])

        for group in groups:
            if str(group).strip().lower() == "rest":
                continue

            previous = muscle_days.get(group)
            if previous is None or workout_date > _date_from_iso(previous):
                muscle_days[group] = workout["date"]

    return {group: _days_since(date_iso, reference_date) for group, date_iso in muscle_days.items()}


def _pick_exercises_for_groups(
    exercise_meta: Dict[str, Dict],
    target_groups: List[str],
    exclude_groups: Optional[List[str]] = None,
    max_picks: int = 3,
) -> List[str]:
    """Pick exercises that match target muscle groups, avoiding excluded groups."""
    exclude_groups_set = set(exclude_groups or [])
    target_groups_set = set(target_groups)
    picks: List[Tuple[int, str]] = []

    for name, meta in exercise_meta.items():
        groups = set(meta.get("muscle_groups", []))
        if groups & exclude_groups_set:
            continue

        score = len(groups & target_groups_set)
        if score == 0:
            continue

        picks.append((score, name))

    picks.sort(key=lambda item: (-item[0], item[1]))
    return [name for _, name in picks[:max_picks]]


def _format_focus(groups: List[str]) -> str:
    """Create a human-readable focus description from muscle groups."""
    if not groups:
        return "General fitness"

    cleaned = [group.replace("_", " ").title() for group in groups]
    if len(cleaned) == 1:
        return cleaned[0]
    return ", ".join(cleaned[:-1]) + " & " + cleaned[-1]


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
        recommended = ["Cardio", "Bench", "Rows"]
        reason = (
            "You do not have any workout history yet, so this is a simple session to help you get started. "
            "It gives you a balanced mix of cardio, pushing, and pulling."
        )
        return {
            "date": today.isoformat(),
            "workout_focus": "Full Body",
            "recommended_exercises": recommended,
            "estimated_duration_min": 30,
            "workout_type": "strength",
            "reason": reason,
        }

    last_date = _date_from_iso(workouts[0]["date"])
    days_since_last = (today - last_date).days

    last_day_exercises = [w["exercise"] for w in workouts if _date_from_iso(w["date"]) == last_date]
    last_was_rest = all(str(ex).lower().strip() == "rest day" for ex in last_day_exercises)

    muscle_days = _group_muscle_history(
        workouts,
        exercises,
        lookback_days=28,
        reference_date=today,
    )

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

    neglected = []
    for group, threshold in group_thresholds.items():
        days = muscle_days.get(group, 999)
        if days >= threshold:
            neglected.append((days, group))

    neglected.sort(reverse=True)
    neglected_groups = [group for _, group in neglected]

    yesterday_groups: List[str] = []
    if workouts and days_since_last <= 1 and not last_was_rest:
        seen = set()
        for workout in workouts:
            if _date_from_iso(workout["date"]) != last_date:
                break

            for group in exercises.get(workout["exercise"], {}).get("muscle_groups", []):
                if group not in seen:
                    seen.add(group)
                    yesterday_groups.append(group)

    if days_since_last >= 3:
        focus_groups = ["cardio", "core"]
        reason = (
            f"It has been {days_since_last} days since your last workout was logged. "
            "A lighter session is a good way to get moving again without doing too much at once."
        )
        workout_type = "recovery"

    elif last_was_rest:
        focus_groups = neglected_groups[:2] or ["legs", "back"]
        reason = (
            "Your last log was a rest day, so this plan shifts back into training and puts more attention "
            "on areas that have had less work recently."
        )
        workout_type = "strength"

    else:
        if neglected_groups:
            focus_groups = neglected_groups[:2]
            reason = (
                "These areas have not shown up much in your recent workouts, so this session helps bring "
                "your training back into better balance."
            )
        else:
            focus_groups = yesterday_groups[:2] or ["legs", "back"]
            reason = (
                "You have been training consistently, so this plan keeps things moving while avoiding too much repetition."
            )
        workout_type = "strength"

    primary_exercises = _pick_exercises_for_groups(
        exercises,
        target_groups=focus_groups,
        exclude_groups=yesterday_groups,
        max_picks=2,
    )

    support_exercises: List[str] = []
    if "core" not in focus_groups:
        support_exercises.extend(
            _pick_exercises_for_groups(exercises, target_groups=["core"], max_picks=1)
        )

    if "cardio" not in focus_groups:
        support_exercises.extend(
            _pick_exercises_for_groups(exercises, target_groups=["cardio"], max_picks=1)
        )

    recommended: List[str] = []
    for exercise in primary_exercises + support_exercises:
        if exercise not in recommended:
            recommended.append(exercise)

    if len(recommended) < 3:
        filler = _pick_exercises_for_groups(
            exercises,
            target_groups=["legs", "back", "chest"],
            exclude_groups=yesterday_groups,
            max_picks=3,
        )
        for exercise in filler:
            if exercise not in recommended:
                recommended.append(exercise)

    if not recommended:
        recommended = ["Cardio", "Squats", "Rows"]
        reason += " A simple full-body session is a safe fallback here."

    estimated_duration = 10 + 10 * len(recommended)

    return {
        "date": today.isoformat(),
        "workout_focus": _format_focus(focus_groups),
        "recommended_exercises": recommended,
        "estimated_duration_min": estimated_duration,
        "workout_type": workout_type,
        "reason": reason,
    }