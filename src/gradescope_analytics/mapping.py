from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

CANONICAL_COLUMNS = [
    "student_id",
    "student_name",
    "assignment",
    "rubric_item",
    "category",
    "score",
    "max_score",
    "comment",
]

REQUIRED_CANONICAL = ["student_id", "student_name", "rubric_item", "score"]


@dataclass
class MappingConfig:
    student_id: str
    student_name: str
    rubric_item: str
    score: str
    assignment: Optional[str] = None
    category: Optional[str] = None
    max_score: Optional[str] = None
    comment: Optional[str] = None

    @classmethod
    def from_dict(cls, mapping: Dict[str, Optional[str]]) -> "MappingConfig":
        for key in REQUIRED_CANONICAL:
            if not mapping.get(key):
                raise ValueError(f"Missing required mapping for '{key}'")
        return cls(
            student_id=mapping.get("student_id", ""),
            student_name=mapping.get("student_name", ""),
            rubric_item=mapping.get("rubric_item", ""),
            score=mapping.get("score", ""),
            assignment=mapping.get("assignment"),
            category=mapping.get("category"),
            max_score=mapping.get("max_score"),
            comment=mapping.get("comment"),
        )

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "student_id": self.student_id,
            "student_name": self.student_name,
            "assignment": self.assignment,
            "rubric_item": self.rubric_item,
            "category": self.category,
            "score": self.score,
            "max_score": self.max_score,
            "comment": self.comment,
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
        "student_name": find_column(["name", "student", "full name"]),
        "assignment": find_column(["assignment", "exam", "homework", "project", "assessment"]),
        "rubric_item": find_column(["rubric", "question", "item", "criterion", "prompt"]),
        "category": find_column(["category", "section", "group", "domain"]),
        "score": find_column(["score", "points", "awarded", "grade"]),
        "max_score": find_column(["max", "total", "possible", "out of"]),
        "comment": find_column(["comment", "feedback", "remark", "note"]),
    }


def apply_mapping(df: pd.DataFrame, mapping: MappingConfig) -> pd.DataFrame:
    missing = [source for source in mapping.to_dict().values() if source and source not in df.columns]
    if missing:
        raise ValueError(f"Source columns not found: {missing}")

    normalized = pd.DataFrame()
    normalized["student_id"] = df[mapping.student_id].astype(str).str.strip()
    normalized["student_name"] = df[mapping.student_name].astype(str).str.strip()

    if mapping.assignment and mapping.assignment in df.columns:
        normalized["assignment"] = df[mapping.assignment].astype(str).str.strip()
    else:
        normalized["assignment"] = "Assessment"

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

    for col in CANONICAL_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = pd.NA

    return normalized[CANONICAL_COLUMNS]


def ensure_canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in CANONICAL_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dataframe missing canonical columns: {missing}")
    return df[CANONICAL_COLUMNS].copy()
