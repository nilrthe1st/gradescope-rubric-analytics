from typing import Dict, Optional

import pandas as pd

from .models import MappingConfig, NORMALIZED_COLUMNS


def suggest_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Heuristically suggest a column mapping based on header keywords."""

    def find_column(keywords):
        for col in df.columns:
            header = col.lower()
            if any(keyword in header for keyword in keywords):
                return col
        return None

    return {
        "student_id": find_column(["student id", "id", "sid"]),
        "student_name": find_column(["name", "student"]),
        "assignment": find_column(["assignment", "homework", "exam", "assessment"]),
        "rubric_item": find_column(["rubric", "question", "item", "criterion", "prompt"]),
        "category": find_column(["category", "section", "group"]),
        "score": find_column(["score", "points awarded", "points"]),
        "max_score": find_column(["max", "total", "possible", "out of"]),
        "comment": find_column(["comment", "feedback", "remark", "note"]),
    }


def apply_mapping(df: pd.DataFrame, mapping: MappingConfig) -> pd.DataFrame:
    """Return a normalized dataframe matching NORMALIZED_COLUMNS."""

    normalized = pd.DataFrame()
    normalized["student_id"] = df[mapping.student_id].astype(str).str.strip()
    normalized["student_name"] = df[mapping.student_name].astype(str).str.strip()

    if mapping.assignment and mapping.assignment in df.columns:
        normalized["assignment"] = df[mapping.assignment].astype(str).str.strip()
    else:
        normalized["assignment"] = "Assignment"

    normalized["rubric_item"] = df[mapping.rubric_item].astype(str).str.strip()

    if mapping.category and mapping.category in df.columns:
        normalized["category"] = df[mapping.category].fillna("Uncategorized").astype(str)
    else:
        normalized["category"] = "Uncategorized"

    normalized["score"] = pd.to_numeric(df[mapping.score], errors="coerce")

    if mapping.max_score and mapping.max_score in df.columns:
        normalized["max_score"] = pd.to_numeric(df[mapping.max_score], errors="coerce")
    else:
        normalized["max_score"] = pd.NA

    if mapping.comment and mapping.comment in df.columns:
        normalized["comment"] = df[mapping.comment].fillna("").astype(str)
    else:
        normalized["comment"] = ""

    for col in NORMALIZED_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = pd.NA

    normalized = normalized[NORMALIZED_COLUMNS]
    return normalized
