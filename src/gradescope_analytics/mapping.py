from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

CANONICAL_COLUMNS = [
    "student_id",
    "exam_id",
    "question_id",
    "rubric_item",
    "points_lost",
    "topic",
    "section_id",
    "ta_id",
]

REQUIRED_CANONICAL = ["student_id", "exam_id", "question_id", "rubric_item", "points_lost"]


@dataclass
class MappingConfig:
    student_id: str
    exam_id: str
    question_id: str
    rubric_item: str
    points_lost: str
    topic: Optional[str] = None
    section_id: Optional[str] = None
    ta_id: Optional[str] = None

    @classmethod
    def from_dict(cls, mapping: Dict[str, Optional[str]]) -> "MappingConfig":
        for key in REQUIRED_CANONICAL:
            if not mapping.get(key):
                raise ValueError(f"Missing required mapping for '{key}'")
        return cls(
            student_id=mapping.get("student_id", ""),
            exam_id=mapping.get("exam_id", ""),
            question_id=mapping.get("question_id", ""),
            rubric_item=mapping.get("rubric_item", ""),
            points_lost=mapping.get("points_lost", ""),
            topic=mapping.get("topic"),
            section_id=mapping.get("section_id"),
            ta_id=mapping.get("ta_id"),
        )

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "student_id": self.student_id,
            "exam_id": self.exam_id,
            "question_id": self.question_id,
            "rubric_item": self.rubric_item,
            "points_lost": self.points_lost,
            "topic": self.topic,
            "section_id": self.section_id,
            "ta_id": self.ta_id,
        }


def needs_mapping(df: pd.DataFrame) -> bool:
    return not all(col in df.columns for col in REQUIRED_CANONICAL)


def suggest_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    def find_column(keywords):
        for col in df.columns:
            header = col.lower()
            if any(keyword in header for keyword in keywords):
                return col
        return None

    return {
        "student_id": find_column(["student id", "id", "sid", "uid"]),
        "exam_id": find_column(["exam", "assessment", "assignment", "test"]),
        "question_id": find_column(["question", "item", "q", "problem"]),
        "rubric_item": find_column(["rubric", "criterion", "prompt", "issue", "deduction"]),
        "points_lost": find_column(["points_lost", "points lost", "deduction", "penalty", "loss", "points"]),
        "topic": find_column(["topic", "tag", "category"]),
        "section_id": find_column(["section", "discussion", "lecture"]),
        "ta_id": find_column(["ta", "grader", "assistant", "gsi"]),
    }


def apply_mapping(df: pd.DataFrame, mapping: MappingConfig) -> pd.DataFrame:
    missing = [source for source in mapping.to_dict().values() if source and source not in df.columns]
    if missing:
        raise ValueError(f"Source columns not found: {missing}")

    normalized = pd.DataFrame()
    normalized["student_id"] = df[mapping.student_id].astype(str).str.strip()
    normalized["exam_id"] = df[mapping.exam_id].astype(str).str.strip()
    normalized["question_id"] = df[mapping.question_id].astype(str).str.strip()

    rubric_series = df[mapping.rubric_item].astype(str).str.strip()
    normalized["rubric_item"] = rubric_series.str.replace(r"\s+", " ", regex=True)

    points = pd.to_numeric(df[mapping.points_lost], errors="coerce")
    if points.isna().any():
        raise ValueError("points_lost column contains non-numeric values")
    if (points < 0).any():
        raise ValueError("points_lost must be non-negative")
    normalized["points_lost"] = points

    if mapping.topic and mapping.topic in df.columns:
        normalized["topic"] = df[mapping.topic].astype(str).str.strip()
    else:
        normalized["topic"] = ""

    if mapping.section_id and mapping.section_id in df.columns:
        normalized["section_id"] = df[mapping.section_id].astype(str).str.strip()
    else:
        normalized["section_id"] = ""

    if mapping.ta_id and mapping.ta_id in df.columns:
        normalized["ta_id"] = df[mapping.ta_id].astype(str).str.strip()
    else:
        normalized["ta_id"] = ""

    for col in REQUIRED_CANONICAL:
        if normalized[col].isna().any() or (normalized[col].astype(str).str.strip() == "").any():
            raise ValueError(f"Missing required values in '{col}'")

    return ensure_canonical_columns(normalized)


def ensure_canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    df_copy = df.copy()
    if "topic" not in df_copy.columns:
        df_copy["topic"] = ""

    missing_required = [col for col in REQUIRED_CANONICAL if col not in df_copy.columns]
    if missing_required:
        raise ValueError(f"Dataframe missing required columns: {missing_required}")

    for col in ["student_id", "exam_id", "question_id", "rubric_item"]:
        df_copy.loc[:, col] = df_copy[col].astype(str).str.strip()
        if (df_copy[col] == "").any():
            raise ValueError(f"Missing required values in '{col}'")

    for optional_col in ["topic", "section_id", "ta_id"]:
        if optional_col not in df_copy.columns:
            df_copy[optional_col] = ""
        df_copy.loc[:, optional_col] = df_copy[optional_col].fillna("").astype(str).str.strip()

    points = pd.to_numeric(df_copy["points_lost"], errors="coerce")
    if points.isna().any():
        raise ValueError("points_lost column contains non-numeric values")
    if (points < 0).any():
        raise ValueError("points_lost must be non-negative")
    df_copy.loc[:, "points_lost"] = points

    return df_copy[CANONICAL_COLUMNS].copy()
