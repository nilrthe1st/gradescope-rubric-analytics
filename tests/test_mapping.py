from app.ingest import sanitize_rows, validate_normalized
from app.mapping import apply_mapping, suggest_mapping
from app.models import MappingConfig, NORMALIZED_COLUMNS


def test_suggest_mapping(sample_df):
    mapping = suggest_mapping(sample_df)
    assert mapping["student_id"] is not None
    assert mapping["student_name"] is not None
    assert mapping["rubric_item"] is not None
    assert mapping["score"] is not None


def test_apply_mapping(sample_df):
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

    normalized = apply_mapping(sample_df, mapping)
    normalized = sanitize_rows(normalized)

    assert list(normalized.columns) == NORMALIZED_COLUMNS
    assert len(normalized) == len(sample_df)
    assert validate_normalized(normalized) == []
