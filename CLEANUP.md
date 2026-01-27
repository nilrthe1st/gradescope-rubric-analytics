# Cleanup Summary

## What changed
- Centralized analytics column names, default bins, recommendation defaults, and persistence thresholds in `src/gradescope_analytics/constants.py` and applied them across `metrics.py`, `recommendations.py`, and `concepts.py`.
- Added/standardized type hints on analytics helpers to make call sites clearer and ease refactors.
- Replaced repeated string literals for core columns (student, exam, question, rubric, concept, points) with shared constants; left behavior and outputs unchanged.
- Normalized recommendation defaults (`DEFAULT_TOP_N_RECS`, `PERSISTENCE_ACTION_THRESHOLD`, `UNMAPPED_LABEL`) and reused them when scoring concept recommendations.

## Testing
- Run `pytest` from the repo root to exercise the analytics utilities and UI helper functions.
