from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class MappingConfig:
    """Defines how input CSV columns map to normalized field names."""

    student_id: str
    student_name: str
    assignment: Optional[str]
    rubric_item: str
    category: Optional[str]
    score: str
    max_score: Optional[str]
    comment: Optional[str]

    @classmethod
    def from_dict(cls, mapping: Dict[str, Optional[str]]) -> "MappingConfig":
        required = ["student_id", "student_name", "rubric_item", "score"]
        for field in required:
            if not mapping.get(field):
                raise ValueError(f"Missing required mapping for {field}")
        return cls(
            student_id=mapping.get("student_id", ""),
            student_name=mapping.get("student_name", ""),
            assignment=mapping.get("assignment"),
            rubric_item=mapping.get("rubric_item", ""),
            category=mapping.get("category"),
            score=mapping.get("score", ""),
            max_score=mapping.get("max_score"),
            comment=mapping.get("comment"),
        )

    def as_dict(self) -> Dict[str, Optional[str]]:
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


NORMALIZED_COLUMNS = [
    "student_id",
    "student_name",
    "assignment",
    "rubric_item",
    "category",
    "score",
    "max_score",
    "comment",
]
