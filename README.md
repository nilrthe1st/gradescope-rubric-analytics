# Gradescope Rubric Analytics

Option A architecture (Streamlit-only) with all analytics in a reusable Python package.

## Features
- Guided ingestion stepper (Upload/Demo → Map → Validate → Explore) with empty-state welcome screen.
- Canonical schema: `student_id, exam_id, question_id, rubric_item, points_lost` (+ optional `topic`) with a mapping wizard when headers differ.
- Overview with KPI cards, instructor summary, drilldowns, and exportable charts/tables.
- Persistence tab with cohort-based repeat rate and a heatmap of rubric occurrences by exam.
- Data Quality tab for invariants, schema view, and a clear cleaning summary.
- Export helpers for CSV/PNG across tables and charts; demo mode loads `data/sample_truth.csv` instantly.

## UI Tour
- **Shell & theme**: Dark SaaS-inspired shell defined in `.streamlit/config.toml` and `app/ui/shell.py`.
- **Ingestion stepper**: Sidebar hosts demo toggle and upload; stepper tracks progress.
- **Overview**: KPI cards, top rubric items table, instructor summary, drilldown buttons, and bar charts with downloads.
- **Persistence**: Persistence table with export + heatmap of rubric items by exam.
- **Data Quality**: Invariant results and schema table for quick validation.
- See `docs/UI_GUIDE.md` for screenshot checklist and screen-by-screen guidance.

## Local development (venv)
> Recommended Python: **3.12** (matches CI). If using pyenv, set the version via `.python-version` or `pyenv local 3.12.0`.

1. Create and activate a virtualenv
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit app (single supported entrypoint)
   ```bash
   PYTHONPATH=src streamlit run app/app.py
   ```
4. In the sidebar, upload a CSV or toggle **Demo mode** to explore the bundled `sample_truth.csv`.

## Testing
Run the library tests locally:
```bash
PYTHONPATH=src python -m pytest -q
```

## Docker
Build and run the Streamlit app in a container:
```bash
docker build -t gradescope-rubric-analytics .
docker run -p 8501:8501 gradescope-rubric-analytics
```

Or use Compose (rebuilds when code changes thanks to the bind mount):
```bash
docker compose up --build
```

## CI
GitHub Actions (`.github/workflows/ci.yml`) runs `pytest` on each push and pull request using Python 3.12.

## Project layout
- `src/gradescope_analytics/` – library code (io, mapping, invariants, metrics, plots)
- `app/app.py` – Streamlit UI that consumes the library
- `data/sample_truth.csv` – canonical sample dataset
- `tests/` – pytest suite for the library

## Notes
- All analytics live in the library; the UI orchestrates only.
- Persistence tab writes normalized CSVs under `data/` by default.
