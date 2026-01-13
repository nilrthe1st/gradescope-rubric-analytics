import pandas as pd


SAMPLE_ROWS = [
    {
        "Student Name": "Alex Kim",
        "Student ID": "s101",
        "Assignment": "Project 1",
        "Rubric Item": "Correctness",
        "Category": "Technical",
        "Score": 8,
        "Max Score": 10,
        "Comment": "Missed edge case",
    },
    {
        "Student Name": "Alex Kim",
        "Student ID": "s101",
        "Assignment": "Project 1",
        "Rubric Item": "Style",
        "Category": "Technical",
        "Score": 3,
        "Max Score": 5,
        "Comment": "Variable naming",
    },
    {
        "Student Name": "Riley Chen",
        "Student ID": "s102",
        "Assignment": "Project 1",
        "Rubric Item": "Correctness",
        "Category": "Technical",
        "Score": 10,
        "Max Score": 10,
        "Comment": "Great work",
    },
    {
        "Student Name": "Riley Chen",
        "Student ID": "s102",
        "Assignment": "Project 1",
        "Rubric Item": "Style",
        "Category": "Technical",
        "Score": 5,
        "Max Score": 5,
        "Comment": "Clean code",
    },
    {
        "Student Name": "Jordan Patel",
        "Student ID": "s103",
        "Assignment": "Project 1",
        "Rubric Item": "Correctness",
        "Category": "Technical",
        "Score": 6,
        "Max Score": 10,
        "Comment": "Two failing tests",
    },
    {
        "Student Name": "Jordan Patel",
        "Student ID": "s103",
        "Assignment": "Project 1",
        "Rubric Item": "Style",
        "Category": "Technical",
        "Score": 4,
        "Max Score": 5,
        "Comment": "Spacing issues",
    },
]


def load_sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(SAMPLE_ROWS)
