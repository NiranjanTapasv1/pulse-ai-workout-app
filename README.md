# AI Pulse Workout App

AI Pulse is a simple workout tracking app that helps you log your exercises, view your recent workout history, and get a smart suggestion for what to train next.

The app is made for people who want an easy way to stay consistent with their fitness routine without using complicated tools. You can record your daily workouts, keep everything organized in one place, and see helpful summaries of your progress over time.

It also looks at your recent workout activity and gives you a practical recommendation for your next workout, so you do not have to guess what to do each day.

# Workout Planner (MVP)

A lightweight workout tracking and recommendation app that runs entirely locally with no paid APIs.

## Features
- Workout history storage (SQLite)
- Exercise library with muscle group metadata
- Daily workout logging (Streamlit UI)
- Rule-based next-day workout recommendation
- Weekly summary dashboard

## Getting started

### 1) Create a Python environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the app

```bash
streamlit run app.py
```

## Project structure

- `app.py` - Streamlit frontend
- `src/db.py` - SQLite helpers and schema
- `src/exercises.py` - Exercise library metadata
- `src/loader.py` - CSV loader and data cleaner
- `src/recommend.py` - Recommendation engine
- `workouts.csv` - Initial workout history import

## Notes

- All data is stored locally in `workouts.db` for portability.
- The recommendation engine is deterministic and rule-based, designed to avoid paid/third-party APIs.
