# Gradescope Rubric Analytics

A self-contained web app (Streamlit) for exploring Gradescope-style rubric exports. Upload CSVs, map columns to standard fields, and view rubric, category, and student-level analytics—no Gradescope login or scraping.

## Features
- Upload instructor or student-provided CSV exports (Gradescope rubric detail works best)
- Mapping wizard to normalize arbitrary column names to a common schema
- Core analytics: rubric item stats, category breakdowns, score distributions, per-student summaries
- Interactive visuals (Plotly) and downloadable normalized data
- Sample dataset bundled for quick demos

## Quickstart
1. **Install dependencies** (preferably in a virtualenv):
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the app**:
   ```bash
   streamlit run streamlit_app.py
   ```
3. Open the provided local URL in your browser and either upload a CSV or load the sample data.

## Data expectations
The mapping wizard can align most CSVs to this schema:
- `student_id`, `student_name`, `assignment`, `rubric_item`, `category`, `score`, `max_score`, `comment`

## Tests
Run unit tests with pytest:
```bash
pytest
```

## Repository layout
- `app/` core logic (ingestion, mapping, analytics, sample data)
- `streamlit_app.py` Streamlit UI
- `tests/` unit tests and fixtures

## Notes
- All processing stays local; no external APIs are called.
- If your export lacks some fields (e.g., category), leave them unmapped; the app handles missing optional fields gracefully.
