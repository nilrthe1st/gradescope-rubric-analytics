from typing import Dict, List

import pandas as pd

REQUIRED_COLUMNS = [
    "student_id",
    "exam_id",
    "question_id",
    "rubric_item",
    "points_lost",
    "topic",
]


def check_required_columns(df: pd.DataFrame) -> Dict[str, bool]:
    return {col: col in df.columns for col in REQUIRED_COLUMNS}


def check_missing_identifiers(df: pd.DataFrame) -> int:
    missing_any = (
        df["student_id"].astype(str).str.strip() == ""
    ) | (
        df["exam_id"].astype(str).str.strip() == ""
    ) | (
        df["question_id"].astype(str).str.strip() == ""
    ) | (
        df["rubric_item"].astype(str).str.strip() == ""
    )
    return int(missing_any.sum())


def check_numeric_points(df: pd.DataFrame) -> int:
    numeric_points = pd.to_numeric(df["points_lost"], errors="coerce")
    return int(numeric_points.isna().sum())


def check_points_non_negative(df: pd.DataFrame) -> int:
    numeric_points = pd.to_numeric(df["points_lost"], errors="coerce")
    return int((numeric_points < 0).sum())


def run_invariants(df: pd.DataFrame) -> List[Dict[str, object]]:
    results = []

    required = check_required_columns(df)
    missing_required = [col for col, present in required.items() if not present]
    results.append(
        {
            "name": "required_columns",
            "ok": len(missing_required) == 0,
            "detail": ", ".join(missing_required) if missing_required else "all present",
        }
    )

    missing_ids = check_missing_identifiers(df)
    results.append({"name": "missing_identifiers", "ok": missing_ids == 0, "detail": missing_ids})

    non_numeric = check_numeric_points(df)
    results.append({"name": "non_numeric_points_lost", "ok": non_numeric == 0, "detail": non_numeric})

    negatives = check_points_non_negative(df)
    results.append({"name": "negative_points_lost", "ok": negatives == 0, "detail": negatives})

    return results
