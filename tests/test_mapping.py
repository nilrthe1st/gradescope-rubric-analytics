from io import StringIO

import pandas as pd

from gradescope_analytics.io import normalize_dataframe
from gradescope_analytics.mapping import MappingConfig, needs_mapping, suggest_mapping


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


def test_suggest_mapping_identifies_columns(sample_df):
    mapping = suggest_mapping(sample_df)
    assert mapping["student_id"] == "student_id"
    assert mapping["points_lost"] == "points_lost"


def test_normalize_dataframe_no_mapping_needed(sample_df):
    normalized, mapping_used, _ = normalize_dataframe(sample_df, infer_mapping=False)
    assert mapping_used is None
    assert list(normalized.columns) == CANONICAL_COLUMNS
    assert len(normalized) == len(sample_df)


def test_normalize_dataframe_with_mapping_and_validation():
    csv = StringIO(
        """sid,exam,question,rubric,loss
u1,ExamA,Q1,Spacing,1
u2,ExamA,Q2,None,0
"""
    )
    df = pd.read_csv(csv, keep_default_na=False)
    assert needs_mapping(df)

    mapping_cfg = MappingConfig.from_dict(
        {
            "student_id": "sid",
            "exam_id": "exam",
            "question_id": "question",
            "rubric_item": "rubric",
            "points_lost": "loss",
            "topic": None,
        }
    )

    normalized, mapping_used, _ = normalize_dataframe(df, mapping=mapping_cfg, infer_mapping=False)
    assert mapping_used is not None
    assert list(normalized.columns) == CANONICAL_COLUMNS
    assert normalized.loc[0, "points_lost"] == 1
    assert normalized.loc[1, "rubric_item"] == "None"


def test_mapping_with_optional_topic():
    csv = StringIO(
        """student,exam_code,qid,item,penalty,tag
a1,Mid1,Q3,Logic gap,2,Logic
"""
    )
    df = pd.read_csv(csv)

    mapping_cfg = MappingConfig.from_dict(
        {
            "student_id": "student",
            "exam_id": "exam_code",
            "question_id": "qid",
            "rubric_item": "item",
            "points_lost": "penalty",
            "topic": "tag",
        }
    )

    normalized, _, _ = normalize_dataframe(df, mapping=mapping_cfg, infer_mapping=False)
    assert normalized.loc[0, "topic"] == "Logic"


def test_normalize_dataframe_rejects_negative_points():
    csv = StringIO(
        """student_id,exam_id,question_id,rubric_item,points_lost
u1,ExamB,Q1,Bad,-1
"""
    )
    df = pd.read_csv(csv)
    assert needs_mapping(df) is False  # headers already canonical
    try:
        normalize_dataframe(df, infer_mapping=False)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "points_lost" in str(exc)
