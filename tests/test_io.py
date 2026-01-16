from gradescope_analytics.io import load_and_normalize
from io import StringIO


def test_load_and_normalize_from_path(sample_truth_path):
    normalized, mapping_used, suggested = load_and_normalize(sample_truth_path, infer_mapping=False)
    assert mapping_used is None
    assert suggested is None
    assert not normalized.empty


def test_load_canonical_with_optionals_preserves_columns():
    csv = StringIO(
        """student_id,exam_id,question_id,rubric_item,points_lost,topic,section_id,ta_id
u1,Exam1,Q1,A,1,Mech,S1,TA1
u2,Exam1,Q2,B,2,Mech,S2,TA2
"""
    )
    normalized, _, _ = load_and_normalize(csv, infer_mapping=False)
    assert "section_id" in normalized.columns
    assert "ta_id" in normalized.columns
    assert normalized.loc[0, "section_id"] == "S1"
    assert normalized.loc[1, "ta_id"] == "TA2"


def test_load_canonical_without_optionals_still_valid(sample_df):
    normalized, _, _ = load_and_normalize(StringIO(sample_df.to_csv(index=False)), infer_mapping=False)
    assert "section_id" in normalized.columns
    assert "ta_id" in normalized.columns
    # optional columns should default to empty strings
    assert normalized["section_id"].fillna("").eq("").all()
    assert normalized["ta_id"].fillna("").eq("").all()
