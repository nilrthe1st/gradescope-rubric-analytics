# Technical Summary

## Scope
Implemented a validated concept layer for rubric analytics: persistent rubric→concept mappings, Unmapped handling, UI bulk editing, and concept-first recommendations.

## Key changes
- Added `gradescope_analytics.concepts` for loading/saving concept mappings (rejects placeholders like "yes"/"true"/"none"/empty) and for applying concept columns with `topic` priority, rubric fallback, and `Unmapped` default.
- Streamlit UI now provides searchable bulk concept editing, persists mappings to `data/concept_mappings.json`, surfaces Unmapped counts, and offers an opt-in toggle to include Unmapped in recommendations.
- Recommendations run strictly at the concept level, defaulting to mapped concepts only; analytics pipelines label Unmapped rows and warn when coverage is incomplete.

## Testing
- `/Users/nilroy/Documents/gradescope-rubric-analytics/.venv/bin/python -m pytest -q` → 27 passed.
