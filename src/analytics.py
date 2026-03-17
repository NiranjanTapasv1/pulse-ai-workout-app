"""Analytics helpers for workout history and balance reporting."""

import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

import pandas as pd


def _normalize_group(name: str) -> str:
    return name.strip().lower()


def muscle_group_counts(
    workouts_df: pd.DataFrame,
    exercise_meta: Dict[str, Dict[str, List[str]]],
    since: Optional[datetime.date] = None,
) -> Dict[str, int]:
    """Count how many times each muscle group was trained in the given window."""
    if since is not None:
        workouts_df = workouts_df[workouts_df["date"] >= since]

    counts: Counter[str] = Counter()
    for _, row in workouts_df.iterrows():
        exercise = row.get("exercise")
        if not exercise:
            continue
        if str(exercise).strip().lower() == "rest day":
            continue
        groups = exercise_meta.get(exercise, {}).get("muscle_groups", [])
        for g in groups:
            counts[_normalize_group(g)] += 1
    return dict(counts)


def workout_frequency_over_time(
    workouts_df: pd.DataFrame,
    days: int = 30,
    today: Optional[datetime.date] = None,
) -> pd.DataFrame:
    """Return daily workout counts over the last N days."""
    if today is None:
        today = datetime.date.today()

    start = today - datetime.timedelta(days=days - 1)
    date_range = pd.date_range(start=start, end=today, freq='D')
    df_dates = pd.DataFrame({'date': date_range.date})

    # Count workouts per day
    daily_counts = workouts_df.groupby('date').size().reset_index(name='workouts')

    # Merge with full date range
    merged = df_dates.merge(daily_counts, on='date', how='left').fillna(0)
    merged['workouts'] = merged['workouts'].astype(int)
    return merged


def muscle_group_trends(
    workouts_df: pd.DataFrame,
    exercise_meta: Dict[str, Dict[str, List[str]]],
    weeks: int = 4,
    today: Optional[datetime.date] = None,
) -> pd.DataFrame:
    """Return weekly muscle group coverage over the last N weeks."""
    if today is None:
        today = datetime.date.today()

    trends = []
    for i in range(weeks):
        week_end = today - datetime.timedelta(days=i * 7)
        week_start = week_end - datetime.timedelta(days=6)
        week_data = workouts_df[(workouts_df['date'] >= week_start) & (workouts_df['date'] <= week_end)]
        counts = muscle_group_counts(week_data, exercise_meta)
        counts['week'] = f"Week {weeks - i}"
        trends.append(counts)

    df = pd.DataFrame(trends).fillna(0)
    return df


def generate_conclusions(
    workouts_df: pd.DataFrame,
    exercise_meta: Dict[str, Dict[str, List[str]]],
    today: Optional[datetime.date] = None,
) -> List[str]:
    """Generate human-readable insights from workout data."""
    if today is None:
        today = datetime.date.today()

    conclusions = []

    # Overall activity
    total_workouts = len(workouts_df)
    if total_workouts == 0:
        return ["No workout data available yet."]

    # Recent activity (last 7 days)
    week_ago = today - datetime.timedelta(days=7)
    recent = workouts_df[workouts_df['date'] >= week_ago]
    recent_days = recent['date'].nunique()
    recent_workouts = len(recent)

    if recent_days == 0:
        conclusions.append("You haven't logged any workouts in the last week. Consider getting back on track!")
    elif recent_days >= 5:
        conclusions.append(f"Great consistency! You've worked out {recent_days} days this week.")
    elif recent_days >= 3:
        conclusions.append(f"Good effort with {recent_days} workout days this week.")
    else:
        conclusions.append(f"You've had {recent_days} workout days this week. Aim for more consistency.")

    # Rest days
    total_days = 7
    rest_days = total_days - recent_days
    if rest_days > 3:
        conclusions.append(f"You've had {rest_days} rest days this week. Recovery is important, but don't over-rest.")
    elif rest_days == 0:
        conclusions.append("No rest days this week. Make sure to include recovery to avoid burnout.")

    # Balance
    balance = weekly_balance(workouts_df, exercise_meta, today)
    score = balance.get('balance_score', 0)
    if score >= 80:
        conclusions.append("Excellent muscle group balance! Keep up the well-rounded training.")
    elif score >= 60:
        conclusions.append("Good balance overall, but some muscle groups could use more attention.")
    else:
        conclusions.append("Your training is imbalanced. Focus on neglected muscle groups for better results.")

    # Neglected groups
    neglected = balance.get('missing_groups', [])
    if neglected:
        neglected_str = ", ".join([g.title() for g in neglected[:3]])
        conclusions.append(f"Consider adding exercises for: {neglected_str}")

    return conclusions


def weekly_balance(
    workouts_df: pd.DataFrame,
    exercise_meta: Dict[str, Dict[str, List[str]]],
    today: Optional[datetime.date] = None,
) -> Dict[str, object]:
    """Compute a simple weekly balance summary for the dashboard."""
    if today is None:
        today = datetime.date.today()

    week_start = today - datetime.timedelta(days=6)
    week = workouts_df[workouts_df["date"] >= week_start]

    # Days with any entry
    logged_days = sorted(week["date"].unique())
    total_logged = len(logged_days)

    # Rest days count
    rest_days = week[week["exercise"].str.lower().str.strip() == "rest day"]["date"].nunique()

    muscle_counts = muscle_group_counts(week, exercise_meta)

    # Determine which groups are missing entirely this week.
    all_groups = sorted({
        g
        for meta in exercise_meta.values()
        for g in meta.get("muscle_groups", [])
        if g and g.lower() not in {"rest"}
    })
    missing_groups = [g for g in all_groups if muscle_counts.get(_normalize_group(g), 0) == 0]

    # Simple balance score: 100 - normalized variance of counts.
    if muscle_counts:
        vals = list(muscle_counts.values())
        avg = sum(vals) / len(vals)
        variance = sum((v - avg) ** 2 for v in vals) / len(vals)
        # Normalize by avg (avoid division by zero)
        balance_score = max(0, 100 - int((variance / (avg + 1)) * 10))
    else:
        balance_score = 0

    return {
        "total_logged_days": total_logged,
        "rest_days": rest_days,
        "muscle_group_counts": muscle_counts,
        "missing_groups": missing_groups,
        "balance_score": balance_score,
    }
