import json
from pathlib import Path

import pandas as pd
import pytest

from gradescope_analytics.concepts import apply_concept_column, load_concept_mapping, save_concept_mapping
from gradescope_analytics.recommendations import compute_recommendations


def test_save_concept_mapping_rejects_placeholders(tmp_path: Path):
    path = tmp_path / "concept_mappings.json"
    mapping = {"Item A": "yes", "Item B": "Valid"}

    with pytest.raises(ValueError):
        save_concept_mapping(mapping, path)

    assert not path.exists()


def test_load_concept_mapping_drops_placeholders(tmp_path: Path):
    path = tmp_path / "concept_mappings.json"
    raw = {"Item A": "Valid", "Item B": "none"}
    path.write_text(json.dumps(raw), encoding="utf-8")

    result = load_concept_mapping(path)
    assert result == {"Item A": "Valid"}


def test_apply_concept_column_prioritizes_topic_and_mapping():
    df = pd.DataFrame(
        [
            {"student_id": "s1", "exam_id": "Exam1", "question_id": "Q1", "rubric_item": "Item A", "topic": "Topic A", "points_lost": 1},
            {"student_id": "s2", "exam_id": "Exam1", "question_id": "Q2", "rubric_item": "Item B", "topic": "", "points_lost": 2},
            {"student_id": "s3", "exam_id": "Exam1", "question_id": "Q3", "rubric_item": "Item C", "points_lost": 3},
        ]
    )

    mapping = {"Item B": "Concept B"}
    result = apply_concept_column(df, mapping)

    assert list(result["concept"]) == ["Topic A", "Concept B", "Unmapped"]


def test_compute_recommendations_excludes_unmapped_by_default():
    df = pd.DataFrame(
        [
            {"student_id": "s1", "exam_id": "Exam1", "question_id": "Q1", "rubric_item": "R1", "concept": "Mapped", "points_lost": 2},
            {"student_id": "s1", "exam_id": "Exam2", "question_id": "Q1", "rubric_item": "R1", "concept": "Mapped", "points_lost": 1},
            {"student_id": "s2", "exam_id": "Exam1", "question_id": "Q2", "rubric_item": "R2", "concept": "Unmapped", "points_lost": 5},
        ]
    )

    recs = compute_recommendations(df, exam_order=["Exam1", "Exam2"], top_n=5)
    assert not recs.empty
    assert set(recs["concept"]) == {"Mapped"}

    recs_with_unmapped = compute_recommendations(
        df,
        exam_order=["Exam1", "Exam2"],
        top_n=5,
        include_unmapped=True,
        allowed_concepts=["Mapped", "Unmapped"],
    )
    assert set(recs_with_unmapped["concept"]) == {"Mapped", "Unmapped"}
