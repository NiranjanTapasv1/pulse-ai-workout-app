"""Streamlit app for the workout tracker.

Run locally with:
    streamlit run app.py

The app stores data in a local SQLite file (`workouts.db`), so no external services are required.
"""

import calendar
import datetime

import pandas as pd
import streamlit as st

from src.db import (
    ensure_db_initialized,
    fetch_workouts,
    insert_workout,
    upsert_exercises,
)
from src.exercises import get_library, normalize_exercise_name, ensure_exercise_in_library
from src.analytics import (
    weekly_balance,
    workout_frequency_over_time,
    muscle_group_trends,
    generate_conclusions,
)
from src.loader import load_history_from_csv, merge_history_from_dataframe
from src.recommend import recommend_next_workout


def apply_custom_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #07111f;
            --bg-soft: #0d1a2b;
            --panel: rgba(12, 24, 42, 0.88);
            --panel-2: rgba(17, 31, 54, 0.92);
            --border: rgba(160, 185, 220, 0.18);
            --text: #f4f7fb;
            --muted: #b4c0d1;
            --accent: #86b7ff;
            --accent-2: #5a8dee;
            --shadow: 0 14px 40px rgba(0, 0, 0, 0.28);
        }

        html, body, [class*="css"] {
            font-size: 17px;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(55, 82, 147, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(55, 82, 147, 0.12), transparent 24%),
                linear-gradient(180deg, #08111f 0%, #07111f 45%, #050b14 100%);
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(8,18,33,0.98), rgba(6,13,24,0.98));
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * {
            color: var(--text) !important;
        }

        .block-container {
            padding-top: 1.7rem;
            padding-bottom: 3rem;
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 1480px;
        }

        h1, h2, h3 {
            color: var(--text) !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }

        p, li, div, span, label {
            color: var(--text);
            font-size: 1rem;
        }

        .hero-title {
            font-size: 4rem;
            line-height: 1.0;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 0.9rem;
        }

        .hero-subtitle {
            font-size: 1.08rem;
            color: var(--muted) !important;
            max-width: 780px;
            line-height: 1.7;
            margin-bottom: 1.2rem;
        }

        .section-title {
            font-size: 2.1rem;
            line-height: 1.12;
            font-weight: 780;
            margin-bottom: 0.35rem;
            letter-spacing: -0.02em;
        }

        .section-copy {
            color: var(--muted) !important;
            font-size: 1.02rem;
            line-height: 1.7;
            margin-bottom: 1rem;
        }

        .panel {
            background: linear-gradient(180deg, rgba(15, 27, 47, 0.92), rgba(10, 19, 34, 0.95));
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.35rem 1.35rem;
            box-shadow: var(--shadow);
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        }

        .panel:hover {
            transform: translateY(-2px);
            border-color: rgba(134, 183, 255, 0.26);
            box-shadow: 0 16px 42px rgba(0, 0, 0, 0.32);
        }

        .hero-panel {
            background: linear-gradient(135deg, rgba(14, 26, 46, 0.96), rgba(7, 16, 30, 0.96));
            border: 1px solid var(--border);
            border-radius: 28px;
            padding: 1.6rem 1.6rem;
            box-shadow: var(--shadow);
        }

        .soft-label {
            color: #dce7f7 !important;
            font-size: 0.86rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.78;
            margin-bottom: 0.55rem;
        }

        .stat-card {
            background: linear-gradient(180deg, rgba(14, 27, 47, 0.96), rgba(9, 19, 34, 0.96));
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.1rem 1rem 1rem 1rem;
            min-height: 145px;
            box-shadow: var(--shadow);
        }

        .stat-title {
            color: var(--muted) !important;
            font-size: 1rem;
            margin-bottom: 0.55rem;
        }

        .stat-value {
            font-size: 2.2rem;
            line-height: 1.05;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.45rem;
        }

        .stat-note {
            color: var(--muted) !important;
            font-size: 0.95rem;
            line-height: 1.45;
        }

        .mini-card {
            background: linear-gradient(180deg, rgba(16, 30, 53, 0.96), rgba(9, 18, 33, 0.96));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1.1rem 1rem;
            box-shadow: var(--shadow);
            min-height: 128px;
        }

        .list-card {
            background: linear-gradient(180deg, rgba(14, 27, 47, 0.96), rgba(9, 19, 34, 0.96));
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.25rem 1.25rem;
            box-shadow: var(--shadow);
        }

        .divider {
            height: 1px;
            background: linear-gradient(90deg, rgba(255,255,255,0.0), rgba(165,185,220,0.22), rgba(255,255,255,0.0));
            margin: 1.6rem 0 1.8rem 0;
        }

        .stButton > button,
        .stFormSubmitButton > button,
        .stDownloadButton > button {
            width: 100% !important;
            min-height: 56px !important;
            background: linear-gradient(180deg, #8ab8ff 0%, #6ea4f7 100%) !important;
            color: #07111f !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.95rem 1rem !important;
            font-size: 1rem !important;
            font-weight: 750 !important;
            box-shadow: 0 10px 28px rgba(90, 141, 238, 0.26) !important;
            transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease !important;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 30px rgba(90, 141, 238, 0.35) !important;
            filter: brightness(1.04);
        }

        .back-button-wrap {
            max-width: 230px;
            margin-bottom: 1rem;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(14, 27, 47, 0.94), rgba(9, 19, 34, 0.94));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.95rem 1rem;
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted) !important;
            font-size: 1rem !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--text) !important;
            font-weight: 800;
            font-size: 2rem !important;
        }

        .stDateInput input,
        .stMultiSelect div[data-baseweb="select"],
        .stFileUploader,
        .stTextInput input,
        .stSelectbox div[data-baseweb="select"],
        .stNumberInput input {
            background: rgba(7, 16, 30, 0.88) !important;
            font-size: 1rem !important;
        }

        .stDateInput label,
        .stMultiSelect label,
        .stFileUploader label,
        .stTextInput label,
        .stSelectbox label,
        .stNumberInput label {
            font-size: 1rem !important;
            font-weight: 600 !important;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--border) !important;
            border-radius: 18px !important;
            background: linear-gradient(180deg, rgba(14, 27, 47, 0.94), rgba(9, 19, 34, 0.94)) !important;
        }

        .footer-note {
            color: rgba(200, 212, 228, 0.72) !important;
            font-size: 0.95rem;
            text-align: center;
            margin-top: 2.2rem;
            padding-bottom: 1rem;
            line-height: 1.7;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _load_initial_data(csv_path: str = "workouts.csv") -> None:
    conn = ensure_db_initialized()
    existing = fetch_workouts(conn, limit=1)
    conn.close()
    if not existing:
        load_history_from_csv(csv_path)


@st.cache_data(show_spinner=False)
def get_all_workouts() -> pd.DataFrame:
    conn = ensure_db_initialized()
    rows = fetch_workouts(conn)
    conn.close()

    if not rows:
        return pd.DataFrame(columns=["date", "exercise"])

    df = pd.DataFrame.from_records([dict(r) for r in rows])
    df = df.rename(columns=lambda c: str(c).strip().lower())

    required = ["date", "exercise"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(
            f"Workout data is missing these columns: {missing}. Please re-import your CSV."
        )
        return pd.DataFrame(columns=["date", "exercise"])

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])

    return df


def add_workout(date: datetime.date, exercise: str) -> None:
    conn = ensure_db_initialized()
    name = normalize_exercise_name(exercise)
    name = ensure_exercise_in_library(name)

    library = get_library()
    meta = library.get(name, {"muscle_groups": ["unknown"], "categories": ["unknown"]})
    upsert_exercises(conn, {name: meta})

    insert_workout(conn, date.isoformat(), name)
    conn.close()


def set_page(page_name: str) -> None:
    st.session_state["page"] = page_name


def render_section_header(title: str, copy: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-copy">{copy}</div>', unsafe_allow_html=True)


def render_back_home_button() -> None:
    st.markdown('<div class="back-button-wrap">', unsafe_allow_html=True)
    if st.button("Back to home", key=f"back_home_{st.session_state['page']}"):
        set_page("Home")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_stat_card(title: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-title">{title}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_small_info_card(title: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="mini-card">
            <div class="soft-label">{title}</div>
            <div style="font-size:1.55rem;font-weight:780;line-height:1.2;margin-bottom:0.35rem;word-break:break-word;">{value}</div>
            <div style="color:#b4c0d1;font-size:0.95rem;line-height:1.45;">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_readiness_summary(sleep: int, energy: int, soreness: int, stress: int) -> tuple[int, str, str]:
    score = int(round((sleep + energy + (6 - soreness) + (6 - stress)) / 4 * 20))
    if score >= 80:
        return score, "Ready to train", "You look in good shape for a normal workout today."
    if score >= 60:
        return score, "Train light", "A shorter or lighter session may feel better today."
    return score, "Recovery day suggested", "Your body may need an easier day, walking, or mobility work."


def render_recommendation_card(rec: dict, readiness_text: str = "Ready to train") -> None:
    exercises = rec.get("recommended_exercises", rec.get("recommendations", []))
    short_list = exercises[:3]

    st.markdown('<div class="list-card">', unsafe_allow_html=True)
    st.caption("Tomorrow's plan")
    st.markdown(f"## {rec.get('date', '')}")
    st.markdown(f"### {rec.get('workout_focus', 'Workout focus')}")

    meta_cols = st.columns(3)
    meta_cols[0].caption(f"{rec.get('estimated_duration_min', 0)} min")
    meta_cols[1].caption(str(rec.get("workout_type", "general")).title())
    meta_cols[2].caption(readiness_text)

    st.markdown("#### Recommended exercises")
    if exercises:
        for ex in exercises:
            st.write(f"• {ex}")
    else:
        st.write("No exercises available.")

    if short_list:
        st.markdown("#### Short version")
        st.write(", ".join(short_list))

    st.markdown("#### Why this plan")
    st.write(rec.get("reason", ""))

    st.markdown("</div>", unsafe_allow_html=True)


def get_recent_activity(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "entries"])
    recent = (
        df.groupby("date")["exercise"]
        .count()
        .reset_index()
        .rename(columns={"exercise": "entries"})
        .sort_values("date", ascending=False)
        .head(5)
    )
    return recent


def build_dashboard_stats(df: pd.DataFrame, library: dict) -> dict:
    today = datetime.date.today()
    last_7 = today - datetime.timedelta(days=6)
    last_28 = today - datetime.timedelta(days=27)

    week_df = df[df["date"] >= last_7].copy() if not df.empty else df.copy()
    month_df = df[df["date"] >= last_28].copy() if not df.empty else df.copy()

    workouts_this_week = int(len(week_df))
    active_days_7 = int(week_df["date"].nunique()) if not week_df.empty else 0
    total_entries = int(len(df))
    avg_per_week = round(len(month_df) / 4, 1) if not month_df.empty else 0.0

    muscle_counts = {}
    if not df.empty:
        for exercise in df["exercise"]:
            meta = library.get(exercise, {})
            groups = meta.get("muscle_groups", ["unknown"])
            for group in groups:
                muscle_counts[group] = muscle_counts.get(group, 0) + 1

    top_group = "No data"
    if muscle_counts:
        top_group = max(muscle_counts, key=muscle_counts.get).replace("_", " ").title()

    streak = 0
    if not df.empty:
        unique_days = sorted(set(df["date"]))
        check_day = today
        while check_day in unique_days:
            streak += 1
            check_day -= datetime.timedelta(days=1)

    return {
        "workouts_this_week": workouts_this_week,
        "active_days_7": active_days_7,
        "total_entries": total_entries,
        "avg_per_week": avg_per_week,
        "top_group": top_group,
        "streak": streak,
        "week_df": week_df,
        "month_df": month_df,
        "muscle_counts": muscle_counts,
    }


def build_weekday_activity(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["day", "entries"])

    order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    temp = df.copy()
    temp["weekday"] = pd.to_datetime(temp["date"]).dt.day_name().str[:3]
    out = (
        temp.groupby("weekday")["exercise"]
        .count()
        .reset_index()
        .rename(columns={"weekday": "day", "exercise": "entries"})
    )
    out["day"] = pd.Categorical(out["day"], categories=order, ordered=True)
    out = out.sort_values("day")
    return out


def build_recent_volume(df: pd.DataFrame, days: int = 14) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "entries"])
    since = datetime.date.today() - datetime.timedelta(days=days - 1)
    temp = df[df["date"] >= since].copy()
    if temp.empty:
        return pd.DataFrame(columns=["date", "entries"])
    out = (
        temp.groupby("date")["exercise"]
        .count()
        .reset_index()
        .rename(columns={"exercise": "entries"})
        .sort_values("date")
    )
    return out


def filter_df_by_window(df: pd.DataFrame, window_label: str) -> pd.DataFrame:
    if df.empty or window_label == "All time":
        return df.copy()

    today = datetime.date.today()
    mapping = {
        "Last 7 days": 7,
        "Last 30 days": 30,
        "Last 90 days": 90,
    }
    days = mapping.get(window_label)
    if days is None:
        return df.copy()

    since = today - datetime.timedelta(days=days - 1)
    return df[df["date"] >= since].copy()


def render_goal_tracker(df: pd.DataFrame) -> None:
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=6)
    week_entries = int(len(df[df["date"] >= week_start])) if not df.empty else 0

    if "weekly_goal" not in st.session_state:
        st.session_state["weekly_goal"] = 4

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="card-heading">Weekly goal</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtext">Set a simple goal for how many workout entries you want to log this week.</div>',
        unsafe_allow_html=True,
    )

    st.session_state["weekly_goal"] = st.number_input(
        "Entries this week",
        min_value=1,
        max_value=10,
        value=st.session_state["weekly_goal"],
        step=1,
        key="weekly_goal_input",
    )

    goal = st.session_state["weekly_goal"]
    progress = min(week_entries / goal, 1.0) if goal > 0 else 0.0

    st.progress(progress)
    st.write(f"You have logged **{week_entries}** of **{goal}** entries this week.")

    if week_entries >= goal:
        st.success("Nice work. You have already reached your weekly goal.")
    elif week_entries >= max(goal - 1, 1):
        st.info("You are very close to your goal.")
    else:
        st.info("Keep going. A few more workouts will move you closer to your goal.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_monthly_calendar(df: pd.DataFrame) -> None:
    today = datetime.date.today()
    year = today.year
    month = today.month
    month_matrix = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    counts = {}
    if not df.empty:
        month_df = df[
            (pd.to_datetime(df["date"]).dt.year == year)
            & (pd.to_datetime(df["date"]).dt.month == month)
        ].copy()
        if not month_df.empty:
            counts = month_df.groupby("date")["exercise"].count().to_dict()

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-heading">{month_name} consistency calendar</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtext">Each box shows how many workout entries were logged on that day.</div>',
        unsafe_allow_html=True,
    )

    header_cols = st.columns(7)
    for idx, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        header_cols[idx].markdown(f"**{day_name}**")

    max_count = max(counts.values()) if counts else 1

    for week in month_matrix:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            with cols[idx]:
                if day == 0:
                    st.write("")
                else:
                    current_date = datetime.date(year, month, day)
                    count = int(counts.get(current_date, 0))
                    if count == 0:
                        st.markdown(
                            f"""
                            <div style="border:1px solid rgba(160,185,220,0.16);border-radius:14px;padding:0.8rem;min-height:88px;background:rgba(11,22,39,0.55);">
                                <div style="font-weight:700;margin-bottom:0.35rem;">{day}</div>
                                <div style="font-size:1.2rem;font-weight:800;">0</div>
                                <div style="color:#b4c0d1;font-size:0.82rem;">entries</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        opacity = min(0.25 + count / max_count * 0.55, 0.9)
                        st.markdown(
                            f"""
                            <div style="border:1px solid rgba(160,185,220,0.16);border-radius:14px;padding:0.8rem;min-height:88px;background:rgba(110,164,247,{opacity});">
                                <div style="font-weight:700;margin-bottom:0.35rem;">{day}</div>
                                <div style="font-size:1.2rem;font-weight:800;">{count}</div>
                                <div style="color:#dce7f7;font-size:0.82rem;">entries</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    st.markdown("</div>", unsafe_allow_html=True)


def build_milestones(df: pd.DataFrame, library: dict) -> dict:
    if df.empty:
        return {
            "longest_streak": 0,
            "best_day_entries": 0,
            "best_week_entries": 0,
            "top_exercise": "No data",
            "top_muscle_group": "No data",
        }

    daily_counts = (
        df.groupby("date")["exercise"]
        .count()
        .reset_index()
        .rename(columns={"exercise": "entries"})
        .sort_values("date")
    )

    best_day_entries = int(daily_counts["entries"].max()) if not daily_counts.empty else 0

    temp = daily_counts.copy()
    temp["date"] = pd.to_datetime(temp["date"])
    temp["week"] = temp["date"].dt.to_period("W").astype(str)
    weekly = temp.groupby("week")["entries"].sum().reset_index()
    best_week_entries = int(weekly["entries"].max()) if not weekly.empty else 0

    exercise_counts = df["exercise"].value_counts()
    top_exercise = str(exercise_counts.index[0]) if not exercise_counts.empty else "No data"

    muscle_counts = {}
    for exercise in df["exercise"]:
        meta = library.get(exercise, {})
        for group in meta.get("muscle_groups", []):
            muscle_counts[group] = muscle_counts.get(group, 0) + 1
    top_group = max(muscle_counts, key=muscle_counts.get).replace("_", " ").title() if muscle_counts else "No data"

    unique_days = sorted(set(df["date"]))
    longest_streak = 0
    current = 0
    prev = None
    for day in unique_days:
        if prev is None or day == prev + datetime.timedelta(days=1):
            current += 1
        else:
            current = 1
        longest_streak = max(longest_streak, current)
        prev = day

    return {
        "longest_streak": longest_streak,
        "best_day_entries": best_day_entries,
        "best_week_entries": best_week_entries,
        "top_exercise": top_exercise,
        "top_muscle_group": top_group,
    }


def render_milestones(df: pd.DataFrame, library: dict) -> None:
    stats = build_milestones(df, library)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="card-heading">Milestones and bests</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtext">A few simple highlights from your training history.</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(5)
    cols[0].metric("Longest streak", stats["longest_streak"])
    cols[1].metric("Best day", stats["best_day_entries"])
    cols[2].metric("Best week", stats["best_week_entries"])
    cols[3].metric("Top exercise", stats["top_exercise"])
    cols[4].metric("Top area", stats["top_muscle_group"])

    st.markdown("</div>", unsafe_allow_html=True)


def render_home(df: pd.DataFrame, library: dict) -> None:
    rec = recommend_next_workout(today=datetime.date.today() + datetime.timedelta(days=1))
    stats = build_dashboard_stats(df, library)
    recent = get_recent_activity(df)
    readiness_status = "Ready to train"

    st.markdown(
        """
        <div class="hero-panel">
            <div class="hero-title">Pulse</div>
            <div class="hero-subtitle">
                Track your workouts, stay consistent, and see what to train next.
                Keep today’s log close and use the dashboard when you want a deeper view.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    cta1, cta2, _ = st.columns([1, 1, 4])
    with cta1:
        if st.button("Log today's workout", use_container_width=True):
            set_page("Log Workout")
            st.rerun()
    with cta2:
        if st.button("View dashboard", use_container_width=True):
            set_page("Dashboard")
            st.rerun()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    top_left, top_right = st.columns([1.2, 1], gap="large")
    with top_left:
        render_goal_tracker(df)
    with top_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Today at a glance</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">A quick view of your current position.</div>',
            unsafe_allow_html=True,
        )
        info_cols = st.columns(3)
        info_cols[0].metric("This week", stats["workouts_this_week"])
        info_cols[1].metric("Streak", stats["streak"])
        with info_cols[2]:
            render_small_info_card("Status", readiness_status, "")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    left, right = st.columns([1.45, 1], gap="large")

    with left:
        render_section_header(
            "Start with what matters",
            "Log today’s session, keep recent activity visible, and use the dashboard when you want a deeper view.",
        )

        row1 = st.columns(3, gap="medium")
        with row1[0]:
            render_small_info_card(
                "Workouts this week",
                str(stats["workouts_this_week"]),
                "Total entries over the last 7 days.",
            )
        with row1[1]:
            render_small_info_card(
                "Active days",
                str(stats["active_days_7"]),
                "Days you trained this week.",
            )
        with row1[2]:
            render_small_info_card(
                "Most trained area",
                stats["top_group"],
                "The area that shows up most.",
            )

        st.write("")
        st.markdown(
            """
            <div class="panel">
                <div class="card-heading">Recent activity</div>
                <div class="card-subtext">
                    A quick look at the last few days you logged.
                </div>
            """,
            unsafe_allow_html=True,
        )
        if recent.empty:
            st.info("No workouts logged yet. Add your first session to get started.")
        else:
            st.dataframe(recent, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        render_section_header(
            "Tomorrow's workout",
            "A simple next session based on your recent activity.",
        )
        render_recommendation_card(rec, readiness_status)


def render_log_workout(df: pd.DataFrame) -> None:
    render_back_home_button()

    library = get_library()
    exercise_options = sorted(library.keys())

    render_section_header(
        "Log your workout",
        "Add what you trained today and keep your progress up to date.",
    )

    left, right = st.columns([1.4, 1], gap="large")

    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Workout entry</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">Pick a date, choose what you trained, and save it.</div>',
            unsafe_allow_html=True,
        )

        with st.form("log_workout_form", clear_on_submit=True):
            workout_date = st.date_input("Workout date", value=datetime.date.today())
            selected = st.multiselect("What did you train?", exercise_options, default=[])
            submitted = st.form_submit_button("Save workout", use_container_width=True)

        if submitted:
            if not selected:
                st.warning("Please select at least one exercise.")
            else:
                for ex in selected:
                    add_workout(workout_date, ex)
                st.success(f"Saved {len(selected)} item(s) for {workout_date.isoformat()}.")
                get_all_workouts.clear()
                _load_initial_data.clear()
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Recent log summary</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">This helps you see whether your recent logging is staying consistent.</div>',
            unsafe_allow_html=True,
        )

        if df.empty:
            st.info("No workout history found yet.")
        else:
            recent = get_recent_activity(df)
            active_days = int(df["date"].nunique())
            last_logged = df["date"].max()

            metric_cols = st.columns(2)
            metric_cols[0].metric("Total entries", len(df))
            metric_cols[1].metric("Active days", active_days)

            st.write(f"Last logged date: {last_logged}")
            st.dataframe(recent, use_container_width=True, hide_index=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    render_section_header(
        "Import or export your data",
        "Bring in an older workout file or download your current history at any time.",
    )

    manage1, manage2 = st.columns(2, gap="large")

    with manage1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        with st.expander("Import workout history", expanded=False):
            uploaded = st.file_uploader("Upload a CSV file", type=["csv"])
            if uploaded is not None:
                try:
                    df_upload = pd.read_csv(uploaded)
                    result = merge_history_from_dataframe(df_upload)
                    st.success(
                        f"Imported {result['inserted']} new rows and skipped {result['skipped']} duplicates."
                    )
                    get_all_workouts.clear()
                    _load_initial_data.clear()
                    st.rerun()
                except ValueError as e:
                    st.error(f"CSV import failed: {e}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with manage2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        with st.expander("Export workout history", expanded=False):
            export_df = get_all_workouts()
            csv = export_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                data=csv,
                file_name="workouts_export.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard(df: pd.DataFrame, library: dict) -> None:
    render_back_home_button()

    render_section_header(
        "Dashboard",
        "See your training at a glance, then scroll for the full picture.",
    )

    if df.empty:
        st.info("No workout data is available yet. Log a workout first to unlock the dashboard.")
        return

    filter_col1, filter_col2 = st.columns([1.2, 4])
    with filter_col1:
        view_window = st.selectbox(
            "Time range",
            ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
            index=1,
        )

    filtered_df = filter_df_by_window(df, view_window)
    stats = build_dashboard_stats(filtered_df, library)

    row = st.columns(5, gap="medium")
    with row[0]:
        render_stat_card(
            "Entries",
            str(stats["total_entries"]),
            f"Shown for {view_window.lower()}.",
        )
    with row[1]:
        render_stat_card(
            "Active days",
            str(filtered_df["date"].nunique() if not filtered_df.empty else 0),
            "Days with at least one workout.",
        )
    with row[2]:
        render_stat_card(
            "Current streak",
            str(build_dashboard_stats(df, library)["streak"]),
            "Based on your full history.",
        )
    with row[3]:
        render_stat_card(
            "Average per week",
            str(stats["avg_per_week"]),
            "Rolling average from recent data.",
        )
    with row[4]:
        render_stat_card(
            "Most trained area",
            stats["top_group"],
            "Most common muscle group.",
        )

    st.write("")
    render_milestones(df, library)

    st.write("")
    top_left, top_right = st.columns(2, gap="large")

    freq_df = workout_frequency_over_time(filtered_df, days=30 if view_window != "Last 7 days" else 7)
    weekday_df = build_weekday_activity(filtered_df)

    with top_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Workout frequency</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">A day by day view of how often you have been logging workouts.</div>',
            unsafe_allow_html=True,
        )
        if not freq_df.empty:
            freq_plot = freq_df.copy()
            freq_plot["date"] = pd.to_datetime(freq_plot["date"])
            st.line_chart(freq_plot.set_index("date")["workouts"], use_container_width=True)
        else:
            st.info("No recent frequency data available.")
        st.markdown("</div>", unsafe_allow_html=True)

    with top_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Activity by day of week</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">This helps you spot which days you usually train.</div>',
            unsafe_allow_html=True,
        )
        if not weekday_df.empty:
            st.bar_chart(weekday_df.set_index("day")["entries"], use_container_width=True)
        else:
            st.info("No weekday activity data available.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    full_width = build_recent_volume(filtered_df, days=14 if view_window != "Last 7 days" else 7)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="card-heading">Recent training volume</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtext">A closer look at how many items you logged across the recent period.</div>',
        unsafe_allow_html=True,
    )
    if not full_width.empty:
        temp = full_width.copy()
        temp["date"] = pd.to_datetime(temp["date"])
        st.area_chart(temp.set_index("date")["entries"], use_container_width=True)
    else:
        st.info("No recent training volume data available.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    render_monthly_calendar(df)

    st.write("")
    lower_left, lower_right = st.columns(2, gap="large")

    with lower_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Muscle group trends</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">See how your training has been spread across muscle groups.</div>',
            unsafe_allow_html=True,
        )
        trends_df = muscle_group_trends(filtered_df, library, weeks=4)
        if not trends_df.empty:
            melted = trends_df.melt(id_vars="week", var_name="muscle_group", value_name="count")
            pivoted = melted.pivot(index="week", columns="muscle_group", values="count").fillna(0)
            st.bar_chart(pivoted, use_container_width=True)
        else:
            st.info("No trend data available.")
        st.markdown("</div>", unsafe_allow_html=True)

    with lower_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Weekly balance</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">A simple summary of your recent training balance.</div>',
            unsafe_allow_html=True,
        )
        balance = weekly_balance(df, library) if not df.empty else {
            "total_logged_days": 0,
            "rest_days": 7,
            "balance_score": 0,
            "muscle_group_counts": {},
            "missing_groups": [],
        }

        metric_cols = st.columns(3)
        metric_cols[0].metric("Logged days", balance["total_logged_days"])
        metric_cols[1].metric("Rest days", balance["rest_days"])
        metric_cols[2].metric("Balance score", f"{balance['balance_score']}/100")

        muscle_counts = balance.get("muscle_group_counts", {})
        if muscle_counts:
            muscle_df = pd.Series(muscle_counts).sort_values(ascending=False)
            st.bar_chart(muscle_df, use_container_width=True)
        else:
            st.info("No muscle group coverage found for the last 7 days.")

        missing = balance.get("missing_groups", [])
        if missing:
            display_missing = ", ".join([m.replace("_", " ").title() for m in missing[:8]])
            st.caption(f"Less attention recently: {display_missing}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    insight_left, insight_right = st.columns([1.1, 0.9], gap="large")

    with insight_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Recent summary table</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">Your latest logged days and how many items were added on each date.</div>',
            unsafe_allow_html=True,
        )
        recent_summary = (
            filtered_df.groupby("date")["exercise"]
            .count()
            .reset_index()
            .rename(columns={"exercise": "entries"})
            .sort_values("date", ascending=False)
            .head(14)
        )
        st.dataframe(recent_summary, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with insight_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">What stands out</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtext">Simple notes based on your workout history.</div>',
            unsafe_allow_html=True,
        )
        conclusions = generate_conclusions(filtered_df, library)
        if conclusions:
            for conclusion in conclusions:
                st.write(f"- {conclusion}")
        else:
            st.write("No clear patterns yet. Keep logging workouts and this section will become more useful.")
        st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Pulse",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_custom_css()
    _load_initial_data()

    if "page" not in st.session_state:
        st.session_state["page"] = "Home"

    df = get_all_workouts()
    library = get_library()

    with st.sidebar:
        st.markdown(
            """
            <div style="padding:0.55rem 0 0.85rem 0;">
                <div style="font-size:1.75rem;font-weight:800;letter-spacing:-0.03em;">Pulse</div>
                <div style="color:#b4c0d1;font-size:1rem;line-height:1.6;margin-top:0.35rem;">
                    Workout tracking and planning made simple.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_page = st.radio(
            "Go to",
            ["Home", "Log Workout", "Dashboard"],
            index=["Home", "Log Workout", "Dashboard"].index(st.session_state["page"]),
            label_visibility="collapsed",
        )
        st.session_state["page"] = selected_page

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        side_stats = build_dashboard_stats(df, library)
        st.markdown(
            """
            <div style="font-size:0.95rem;color:#b4c0d1;margin-bottom:0.6rem;">
                Quick overview
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.metric("Total entries", side_stats["total_entries"])
        st.metric("Active days this week", side_stats["active_days_7"])
        st.metric("Current streak", side_stats["streak"])

    if st.session_state["page"] == "Home":
        render_home(df, library)
    elif st.session_state["page"] == "Log Workout":
        render_log_workout(df)
    elif st.session_state["page"] == "Dashboard":
        render_dashboard(df, library)

    st.markdown(
        """
        <div class="footer-note">
            © 2026 Niranjan Tapasvi. All rights reserved.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()