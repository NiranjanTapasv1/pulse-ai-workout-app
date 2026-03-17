"""Exercise library and metadata for the workout planner.

This module defines a canonical set of exercises with tags and muscle groups.
"""

from typing import Dict, List, Optional, Any


def _normalize_name(name: str) -> str:
    """Normalize exercise names to reduce duplicates."""
    return name.strip().title()


def _default_meta() -> Dict[str, Any]:
    return {
        "muscle_groups": ["unknown"],
        "categories": ["unknown"],
        "workout_type": "general",
        "equipment": "bodyweight",
        "intensity_level": "medium",
        "is_active": True,
    }


EXERCISE_LIBRARY: Dict[str, Dict[str, Any]] = {
    # Core / bodyweight
    "Rest Day": {"muscle_groups": ["rest"], "categories": ["recovery"]},
    "Cardio": {"muscle_groups": ["cardio"], "categories": ["conditioning"]},
    "Crunches": {"muscle_groups": ["core"], "categories": ["stability"]},
    "Leg Raises": {"muscle_groups": ["core"], "categories": ["stability"]},
    "Obliques": {"muscle_groups": ["core"], "categories": ["stability"]},
    "Oblique Crunches": {"muscle_groups": ["core"], "categories": ["stability"]},

    # Upper body
    "Shoulder Rehab": {"muscle_groups": ["shoulders"], "categories": ["rehab"]},
    "Lateral Raises": {"muscle_groups": ["shoulders"], "categories": ["accessory"]},
    "Rear Delt Fly": {"muscle_groups": ["shoulders"], "categories": ["accessory"]},
    "Shoulder Press": {"muscle_groups": ["shoulders"], "categories": ["push"]},
    "Rows": {"muscle_groups": ["back"], "categories": ["pull"]},
    "Pull Ups": {"muscle_groups": ["back"], "categories": ["pull"]},
    "Scapular Pull Ups": {"muscle_groups": ["back"], "categories": ["pull", "mobility"]},

    # Arms
    "Hammer Curls": {"muscle_groups": ["arms"], "categories": ["pull"]},
    "Bicep Curls": {"muscle_groups": ["arms"], "categories": ["pull"]},
    "Wrist Curls": {"muscle_groups": ["forearms"], "categories": ["pull"]},
    "Wrist Ext": {"muscle_groups": ["forearms"], "categories": ["pull"]},
    "Tricep Ext": {"muscle_groups": ["arms"], "categories": ["push"]},

    # Legs
    "Squats": {"muscle_groups": ["legs"], "categories": ["compound"]},
    "Calf Raises": {"muscle_groups": ["calves"], "categories": ["accessory"]},
    "RDL": {"muscle_groups": ["hamstrings", "glutes"], "categories": ["compound"]},

    # Chest
    "Bench": {"muscle_groups": ["chest"], "categories": ["push"]},
    "Incline Bench": {"muscle_groups": ["upper chest"], "categories": ["push"]},
}


def _normalize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the metadata has all required fields."""
    full = _default_meta()
    full.update(meta or {})
    # Ensure muscle_groups and categories are lists.
    full["muscle_groups"] = list(full.get("muscle_groups") or [])
    full["categories"] = list(full.get("categories") or [])
    return full


def get_library() -> Dict[str, Dict[str, Any]]:
    """Return a copy of the exercise library with structured metadata."""
    return {name: _normalize_meta(meta.copy()) for name, meta in EXERCISE_LIBRARY.items()}


def normalize_exercise_name(exercise: str) -> str:
    """Normalize an exercise name to match the library keys."""
    return _normalize_name(exercise)


def ensure_exercise_in_library(exercise: str) -> str:
    """Ensure a name exists in the library, adding it with generic metadata if missing."""
    key = normalize_exercise_name(exercise)
    if key not in EXERCISE_LIBRARY:
        EXERCISE_LIBRARY[key] = _default_meta()
    return key
