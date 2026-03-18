"""Analytics helpers for workout history and balance reporting."""

import datetime
from collections import Counter
from typing import Dict, List, Optional

import pandas as pd


def _normalize_group(name: str) -> str:
    return str(name).strip().lower()


def muscle_group_counts(
    workouts_df: pd.DataFrame,
    exercise_meta: Dict[str, Dict[str, List[str]]],
    since: Optional[datetime.date] = None,
) -> Dict[str, int]:
    """Count how many times each muscle group was trained in the given window."""
    if workouts_df.empty:
        return {}

    df = workouts_df.copy()
    if since is not None:
        df = df[df["date"] >= since]

    counts: Counter[str] = Counter()

    for _, row in df.iterrows():
        exercise = row.get("exercise")
        if not exercise:
            continue

        exercise_name = str(exercise).strip()
        if exercise_name.lower() == "rest day":
            continue

        groups = exercise_meta.get(exercise_name, {}).get("muscle_groups", [])
        for group in groups:
            norm = _normalize_group(group)
            if norm and norm != "rest":
                counts[norm] += 1

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
    date_range = pd.date_range(start=start, end=today, freq="D")
    df_dates = pd.DataFrame({"date": date_range.date})

    if workouts_df.empty:
        df_dates["workouts"] = 0
        return df_dates

    daily_counts = workouts_df.groupby("date").size().reset_index(name="workouts")
    merged = df_dates.merge(daily_counts, on="date", how="left").fillna(0)
    merged["workouts"] = merged["workouts"].astype(int)
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

    if workouts_df.empty:
        return pd.DataFrame(columns=["week"])

    trends = []
    for i in range(weeks):
        week_end = today - datetime.timedelta(days=i * 7)
        week_start = week_end - datetime.timedelta(days=6)

        week_data = workouts_df[
            (workouts_df["date"] >= week_start) & (workouts_df["date"] <= week_end)
        ]

        counts = muscle_group_counts(week_data, exercise_meta)
        counts["week"] = f"Week {weeks - i}"
        trends.append(counts)

    return pd.DataFrame(trends).fillna(0)


def activity_by_weekday(workouts_df: pd.DataFrame) -> pd.DataFrame:
    """Return workout counts by weekday."""
    order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    if workouts_df.empty:
        return pd.DataFrame({"day": order, "entries": [0] * 7})

    df = workouts_df.copy()
    df["day"] = pd.to_datetime(df["date"]).dt.day_name().str[:3]

    out = (
        df.groupby("day")
        .size()
        .reset_index(name="entries")
    )

    out["day"] = pd.Categorical(out["day"], categories=order, ordered=True)
    out = out.sort_values("day")

    full = pd.DataFrame({"day": order})
    full = full.merge(out, on="day", how="left").fillna(0)
    full["entries"] = full["entries"].astype(int)
    return full


def recent_training_volume(
    workouts_df: pd.DataFrame,
    days: int = 14,
    today: Optional[datetime.date] = None,
) -> pd.DataFrame:
    """Return entry counts across the last N days."""
    if today is None:
        today = datetime.date.today()

    start = today - datetime.timedelta(days=days - 1)
    date_range = pd.date_range(start=start, end=today, freq="D")
    df_dates = pd.DataFrame({"date": date_range.date})

    if workouts_df.empty:
        df_dates["entries"] = 0
        return df_dates

    temp = workouts_df[workouts_df["date"] >= start].copy()
    counts = temp.groupby("date").size().reset_index(name="entries")

    merged = df_dates.merge(counts, on="date", how="left").fillna(0)
    merged["entries"] = merged["entries"].astype(int)
    return merged


def summary_stats(
    workouts_df: pd.DataFrame,
    exercise_meta: Dict[str, Dict[str, List[str]]],
    today: Optional[datetime.date] = None,
) -> Dict[str, object]:
    """Build top-level dashboard stats."""
    if today is None:
        today = datetime.date.today()

    if workouts_df.empty:
        return {
            "total_entries": 0,
            "active_days": 0,
            "workouts_this_week": 0,
            "active_days_this_week": 0,
            "current_streak": 0,
            "average_per_week": 0.0,
            "top_muscle_group": "No data",
        }

    df = workouts_df.copy()
    total_entries = int(len(df))
    active_days = int(df["date"].nunique())

    week_start = today - datetime.timedelta(days=6)
    week_df = df[df["date"] >= week_start]
    workouts_this_week = int(len(week_df))
    active_days_this_week = int(week_df["date"].nunique())

    month_start = today - datetime.timedelta(days=27)
    month_df = df[df["date"] >= month_start]
    average_per_week = round(len(month_df) / 4, 1) if not month_df.empty else 0.0

    group_counts = muscle_group_counts(df, exercise_meta)
    if group_counts:
        top_muscle_group = max(group_counts, key=group_counts.get).replace("_", " ").title()
    else:
        top_muscle_group = "No data"

    current_streak = 0
    logged_days = set(df["date"].tolist())
    day_cursor = today
    while day_cursor in logged_days:
        current_streak += 1
        day_cursor -= datetime.timedelta(days=1)

    return {
        "total_entries": total_entries,
        "active_days": active_days,
        "workouts_this_week": workouts_this_week,
        "active_days_this_week": active_days_this_week,
        "current_streak": current_streak,
        "average_per_week": average_per_week,
        "top_muscle_group": top_muscle_group,
    }


def generate_conclusions(
    workouts_df: pd.DataFrame,
    exercise_meta: Dict[str, Dict[str, List[str]]],
    today: Optional[datetime.date] = None,
) -> List[str]:
    """Generate simple, human-readable insights from workout data."""
    if today is None:
        today = datetime.date.today()

    if workouts_df.empty:
        return ["No workout history yet. Add a few workouts and this section will start to fill in."]

    conclusions: List[str] = []

    week_ago = today - datetime.timedelta(days=6)
    recent = workouts_df[workouts_df["date"] >= week_ago]
    recent_days = int(recent["date"].nunique())
    recent_entries = int(len(recent))

    if recent_days >= 5:
        conclusions.append(f"You have been very consistent this week with workouts logged on {recent_days} days.")
    elif recent_days >= 3:
        conclusions.append(f"You logged workouts on {recent_days} days this week, which is a solid routine.")
    elif recent_days >= 1:
        conclusions.append(f"You logged {recent_entries} workout entries across {recent_days} day(s) this week.")
    else:
        conclusions.append("You have not logged a workout in the last 7 days.")

    balance = weekly_balance(workouts_df, exercise_meta, today)
    score = balance.get("balance_score", 0)

    if score >= 80:
        conclusions.append("Your training looks well spread across muscle groups.")
    elif score >= 60:
        conclusions.append("Your training looks fairly balanced, but a few areas could use more attention.")
    else:
        conclusions.append("Your recent training is a bit uneven, so it may help to rotate focus more deliberately.")

    missing = balance.get("missing_groups", [])
    if missing:
        missing_text = ", ".join([g.replace("_", " ").title() for g in missing[:3]])
        conclusions.append(f"Areas with little or no work recently: {missing_text}.")

    group_counts = muscle_group_counts(workouts_df, exercise_meta)
    if group_counts:
        top_group = max(group_counts, key=group_counts.get).replace("_", " ").title()
        conclusions.append(f"The area showing up most in your log is {top_group}.")

    return conclusions


def weekly_balance(
    workouts_df: pd.DataFrame,
    exercise_meta: Dict[str, Dict[str, List[str]]],
    today: Optional[datetime.date] = None,
) -> Dict[str, object]:
    """Compute a weekly balance summary for the dashboard."""
    if today is None:
        today = datetime.date.today()

    if workouts_df.empty:
        return {
            "total_logged_days": 0,
            "rest_days": 7,
            "muscle_group_counts": {},
            "missing_groups": [],
            "balance_score": 0,
        }

    week_start = today - datetime.timedelta(days=6)
    week = workouts_df[workouts_df["date"] >= week_start].copy()

    logged_days = sorted(week["date"].unique()) if not week.empty else []
    total_logged = len(logged_days)

    if week.empty:
        rest_days = 7
    else:
        rest_days = int(
            week[week["exercise"].astype(str).str.lower().str.strip() == "rest day"]["date"].nunique()
        )

    muscle_counts = muscle_group_counts(week, exercise_meta)

    all_groups = sorted(
        {
            _normalize_group(group)
            for meta in exercise_meta.values()
            for group in meta.get("muscle_groups", [])
            if group and _normalize_group(group) != "rest"
        }
    )

    missing_groups = [g for g in all_groups if muscle_counts.get(g, 0) == 0]

    if muscle_counts:
        vals = list(muscle_counts.values())
        avg = sum(vals) / len(vals)
        variance = sum((v - avg) ** 2 for v in vals) / len(vals)
        balance_score = max(0, min(100, 100 - int((variance / (avg + 1)) * 10)))
    else:
        balance_score = 0

    return {
        "total_logged_days": total_logged,
        "rest_days": rest_days,
        "muscle_group_counts": muscle_counts,
        "missing_groups": missing_groups,
        "balance_score": balance_score,
    }