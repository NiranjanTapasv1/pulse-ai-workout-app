"""Streamlit app for the workout tracker.

Run locally with:
    streamlit run app.py

The app stores data in a local SQLite file (`workouts.db`), so no external services are required.
"""

import datetime

import pandas as pd
import streamlit as st

from src.db import ensure_db_initialized, connect_db, fetch_workouts, fetch_exercises, insert_workout, upsert_exercises
from src.exercises import get_library, normalize_exercise_name, ensure_exercise_in_library
from src.analytics import weekly_balance, workout_frequency_over_time, muscle_group_trends, generate_conclusions
from src.loader import load_history_from_csv, merge_history_from_dataframe
from src.recommend import recommend_next_workout


# Custom CSS for elegant, premium look
def apply_custom_css():
    st.markdown("""
    <style>
    /* Dark gradient background, fading from top to bottom */
    .stApp {
        background: linear-gradient(180deg, #100934 0%, #050618 70%, #000000 100%);
        color: #ffffff;
    }

    /* Headings */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700;
    }

    /* Button styling */
    .stButton>button, .stFormSubmitButton>button {
        background: linear-gradient(90deg, #2b2d48 0%, #1c2337 80%, #0c0f21 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: #ffffff !important;
        border-radius: 18px !important;
        padding: 12px 22px !important;
        font-weight: 700 !important;
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.35) !important;
    }

    .stButton>button:hover, .stFormSubmitButton>button:hover {
        background: linear-gradient(90deg, #3a3d5f 0%, #23314d 80%, #151c30 100%) !important;
        transform: translateY(-1px) !important;
    }

    /* Inputs and select boxes */
    .stTextInput>div>div>input,
    .stSelectbox>div>div>select,
    .stDateInput>div>input,
    .stMultiSelect>div>div>div>div>div {
        background: rgba(0, 0, 0, 0.75) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 10px !important;
    }

    /* Slider and other controls */
    .stSlider>div>div>div>div {
        background: rgba(255, 255, 255, 0.15) !important;
    }

    /* Containers */
    .css-18e3th9 {
        background: rgba(0, 0, 0, 0.35) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 18px !important;
        padding: 20px !important;
    }

    /* Dataframes */
    .dataframe {
        background: rgba(0, 0, 0, 0.45) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
    }

    /* Charts */
    .stPlotlyChart, .stBarChart, .stLineChart {
        background: rgba(0, 0, 0, 0.45) !important;
        border-radius: 14px !important;
        padding: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
    }

    /* Make all text readable on dark background */
    .stMarkdown, .stText, p, span, div {
        color: #ffffff !important;
    }

    /* Footer */
    .footer {
        text-align: center !important;
        color: rgba(255, 255, 255, 0.65) !important;
        font-size: 0.85em !important;
        margin-top: 40px !important;
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _load_initial_data(csv_path: str = "workouts.csv") -> None:
    """Load initial CSV history into the database if it isn't already populated."""
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
        st.error(f"Workout data missing required columns: {missing}. Please re-import your CSV to fix the database.")
        return pd.DataFrame(columns=["date", "exercise"])

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])

    return df


def add_workout(date: datetime.date, exercise: str) -> None:
    conn = ensure_db_initialized()
    name = normalize_exercise_name(exercise)
    name = ensure_exercise_in_library(name)

    # Ensure the exercise is present in the DB so the foreign key constraint passes
    library = get_library()
    meta = library.get(name, {"muscle_groups": ["unknown"], "categories": ["unknown"]})
    upsert_exercises(conn, {name: meta})

    insert_workout(conn, date.isoformat(), name)
    conn.close()


def main() -> None:
    st.set_page_config(
        page_title="Pulse",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    apply_custom_css()
    _load_initial_data()

    st.title("Pulse")
    st.markdown("*Precision training intelligence built for elite performance*")
    st.write(
        "A refined workout tracking and recommendation platform designed for serious athletes. "
        "Track progress, stay consistent, and level up your training with meaningful insights."
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.container():
            st.header("Log Today's Workout")
            st.markdown("Record your training session with precision.")

            library = get_library()
            exercise_options = sorted(library.keys())

            with st.form("log_workout_form", clear_on_submit=True):
                workout_date = st.date_input("Select Date", value=datetime.date.today())
                selected = st.multiselect("Select Exercises or Habits", exercise_options, default=[])
                submitted = st.form_submit_button("💾 Log Workout", use_container_width=True)

            if submitted:
                if not selected:
                    st.warning("⚠️ Please select at least one exercise.")
                else:
                    for ex in selected:
                        add_workout(workout_date, ex)
                    st.success(f"✅ Successfully logged {len(selected)} item(s) for {workout_date.isoformat()}")
                    get_all_workouts.clear()
                    _load_initial_data.clear()
                    st.rerun()

        st.markdown("---")

        with st.container():
            st.header("Weekly Performance Summary")
            st.markdown("Analyze your training balance over the past 7 days.")

            df = get_all_workouts()
            if df.empty:
                st.info("📭 No workouts logged yet. Start your journey!")
            else:
                since = datetime.date.today() - datetime.timedelta(days=7)
                week = df[df["date"] >= since]
                if week.empty:
                    st.info("📭 No workouts in the last 7 days.")
                else:
                    summary = week.groupby("date")["exercise"].count().reset_index()
                    summary = summary.rename(columns={"exercise": "entries"})
                    st.dataframe(summary.sort_values("date", ascending=False), use_container_width=True)

                    balance = weekly_balance(week, get_library())
                    cols = st.columns(3)
                    cols[0].metric("🏋️ Active Days", balance["total_logged_days"])
                    cols[1].metric("😴 Rest Days", balance["rest_days"])
                    cols[2].metric("⚖️ Balance Score", f"{balance['balance_score']}/100")

                    st.subheader("🎯 Muscle Group Coverage")
                    if balance["muscle_group_counts"]:
                        st.bar_chart(
                            pd.Series(balance["muscle_group_counts"]).sort_values(ascending=False)
                        )
                    else:
                        st.write("No muscle group activity detected.")

                    missing = balance.get("missing_groups", [])
                    if missing:
                        st.warning(
                            f"⚠️ **Neglected Groups:** {', '.join([m.title() for m in missing[:10]])}"
                        )

        st.markdown("---")

        with st.container():
            st.header("Detailed Analytics Dashboard")
            st.markdown("Deep insights into your training patterns and progress.")

            df = get_all_workouts()
            if df.empty:
                st.info("📭 No data available for analysis.")
            else:
                st.subheader("📅 Workout Frequency (Last 30 Days)")
                freq_df = workout_frequency_over_time(df, days=30)
                st.line_chart(freq_df.set_index("date")["workouts"])

                st.subheader("💪 Muscle Group Trends (Last 4 Weeks)")
                trends_df = muscle_group_trends(df, get_library(), weeks=4)
                if not trends_df.empty:
                    melted = trends_df.melt(id_vars="week", var_name="muscle_group", value_name="count")
                    st.bar_chart(melted.pivot(index="week", columns="muscle_group", values="count").fillna(0))
                else:
                    st.write("No trend data available.")

                st.subheader("🔍 AI-Powered Insights & Recommendations")
                conclusions = generate_conclusions(df, get_library())
                for conclusion in conclusions:
                    st.write(f"• {conclusion}")

        st.markdown("---")

        with st.container():
            st.header("Data Management")
            st.markdown("Import historical data or export your progress.")

            with st.expander("📤 Import Workout History CSV"):
                uploaded = st.file_uploader("Upload CSV File", type=["csv"])
                if uploaded is not None:
                    try:
                        df_upload = pd.read_csv(uploaded)
                        result = merge_history_from_dataframe(df_upload)
                        st.success(
                            f"✅ Imported {result['inserted']} new rows (skipped {result['skipped']} duplicates)."
                        )
                        get_all_workouts.clear()
                        _load_initial_data.clear()
                        st.rerun()
                    except ValueError as e:
                        st.error(f"❌ CSV import failed: {e}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {e}")

            with st.expander("📥 Export Workout History"):
                export_df = get_all_workouts()
                csv = export_df.to_csv(index=False)
                st.download_button(
                    "⬇️ Download CSV",
                    data=csv,
                    file_name="workouts_export.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    with col2:
        with st.container():
            st.header("Tomorrow's Recommendation")
            st.markdown("A data-driven suggestion based on your recent workouts.")

            target = datetime.date.today() + datetime.timedelta(days=1)
            rec = recommend_next_workout(today=target)

            st.metric("Target Date", rec["date"])
            st.subheader(f"{rec.get('workout_focus', 'Workout Focus')}")
            st.metric("Estimated Duration", f"{rec.get('estimated_duration_min', 0)} min")
            st.write(f"**Type:** {rec.get('workout_type', 'General').title()}")

            st.subheader("Recommended Exercises")
            for ex in rec.get("recommended_exercises", rec.get("recommendations", [])):
                st.write(f"• {ex}")

            st.subheader("Why This Plan?")
            st.write(rec.get("reason", ""))

            st.markdown("---")
            st.caption("_💡 Pro tip: Use this as a guide and adjust based on your energy levels._")

    st.markdown('<div class="footer">© 2026 Elite Workout Planner | Precision Training Intelligence</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()