import pandas as pd
import pytest

from app.analytics import category_breakdown, rubric_item_stats, score_distribution, student_summary
from app.ingest import sanitize_rows
from app.mapping import apply_mapping
from app.models import MappingConfig


def _normalized(sample_df: pd.DataFrame) -> pd.DataFrame:
    mapping = MappingConfig.from_dict(
        {
            "student_id": "Student ID",
            "student_name": "Student Name",
            "assignment": "Assignment",
            "rubric_item": "Rubric Item",
            "category": "Category",
            "score": "Score",
            "max_score": "Max Score",
            "comment": "Comment",
        }
    )
    return sanitize_rows(apply_mapping(sample_df, mapping))


def test_rubric_item_stats(sample_df):
    normalized = _normalized(sample_df)
    stats = rubric_item_stats(normalized)

    correctness = stats[stats["rubric_item"] == "Correctness"].iloc[0]
    style = stats[stats["rubric_item"] == "Style"].iloc[0]

    assert correctness["count"] == 3
    assert pytest.approx(correctness["avg_score"], rel=1e-3) == 8.0
    assert pytest.approx(style["avg_score"], rel=1e-3) == 4.0


def test_category_breakdown(sample_df):
    normalized = _normalized(sample_df)
    categories = category_breakdown(normalized)
    row = categories.iloc[0]

    assert row["category"] == "Technical"
    assert row["items"] == 2
    assert row["submissions"] == 3
    assert pytest.approx(row["score_sum"], rel=1e-3) == 36.0
    assert pytest.approx(row["pct_of_total"], rel=1e-3) == 80.0


def test_student_summary(sample_df):
    normalized = _normalized(sample_df)
    students = student_summary(normalized)

    top = students.iloc[0]
    assert top["student_name"] == "Riley Chen"
    assert pytest.approx(top["percent"], rel=1e-3) == 100.0

    alex = students[students["student_name"] == "Alex Kim"].iloc[0]
    assert pytest.approx(alex["score_sum"], rel=1e-3) == 11.0
    assert pytest.approx(alex["percent"], rel=1e-3) == 73.3333333


def test_score_distribution(sample_df):
    normalized = _normalized(sample_df)
    dist = score_distribution(normalized, bins=5)
    assert not dist.empty
    assert set(dist.columns) == {"bin", "count"}
