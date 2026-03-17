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
