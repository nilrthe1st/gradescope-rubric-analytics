from gradescope_analytics.io import normalize_dataframe
from gradescope_analytics.mapping import MappingConfig, needs_mapping, suggest_mapping


def test_suggest_mapping_identifies_columns(sample_df):
    mapping = suggest_mapping(sample_df)
    assert mapping["student_id"] == "student_id"
    assert mapping["score"] == "score"


def test_normalize_dataframe_no_mapping_needed(sample_df):
    normalized, mapping_used, _ = normalize_dataframe(sample_df, infer_mapping=False)
    assert mapping_used is None
    assert list(normalized.columns) == [
        "student_id",
        "student_name",
        "assignment",
        "rubric_item",
        "category",
        "score",
        "max_score",
        "comment",
    ]
    assert len(normalized) == len(sample_df)


def test_normalize_dataframe_with_mapping(sample_df):
    # Rename columns to force mapping usage
    renamed = sample_df.rename(columns={"student_id": "SID", "score": "Points"})
    assert needs_mapping(renamed)

    mapping_cfg = MappingConfig.from_dict(
        {
            "student_id": "SID",
            "student_name": "student_name",
            "assignment": "assignment",
            "rubric_item": "rubric_item",
            "category": "category",
            "score": "Points",
            "max_score": "max_score",
            "comment": "comment",
        }
    )

    normalized, mapping_used, _ = normalize_dataframe(renamed, mapping=mapping_cfg, infer_mapping=False)
    assert mapping_used is not None
    assert normalized["student_id"].iloc[0] == sample_df["student_id"].iloc[0]
    assert normalized["score"].sum() == sample_df["score"].sum()
