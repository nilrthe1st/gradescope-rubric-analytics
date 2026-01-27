# Gradescope Rubric Analytics — Instructor Brief

## 1) Technical Audit (concise)
- **Architecture overview**: Streamlit UI in `app/app.py`; analytics library in `src/gradescope_analytics` (ingestion, mapping, invariants, metrics, recommendations, plots); UI shell/helpers in `app/ui`; sample data in `data/sample_truth.csv`; configuration/theme in `.streamlit/config.toml`. Entry point: `python -m app` (runs `streamlit run app/app.py`).
- **Data flow**: Upload CSV or use Demo/Synthetic toggle → optional mapping wizard aligns columns → invariants run during validation → concept mapping applied (optional) → anonymization applied by default → filtered student scope → tabs render metrics (overview KPIs, persistence, instructor summary, data quality). Downloads/exports use helper functions with deterministic keys and respect Safe Mode.
- **Security posture**: Runs client-side in Streamlit session; no authentication or multi-user separation. Student IDs are anonymized by default; instructor toggle can reveal IDs. Safe Mode hides downloads/instructor analytics/predictive exports. Exports are written to `data/exports/` on the host; no external services. No persistence beyond session except optional export files. No network calls besides Streamlit static assets.
- **Known limitations**: Personal mode hides instructor analytics when <5 students. Safe Mode disables downloads and instructor/predictive views. Predictive tab requires `scikit-learn`; PNG exports need `kaleido`. Persistence/trajectory views need at least two exams. Large uploads are limited by Streamlit session memory (no chunked ingest). No RBAC, auditing, or datastore; single-user session model. Concept mappings must be provided by instructors; unmapped topics reduce recommendation fidelity.

## 2) Instructor-Facing Summary (non-technical)
- **What insights it provides**: Overall class KPIs (rows, students, exams), points lost per student and per rubric item, top deductions, recurring rubric items across exams, concept-level rollups, instructor summary of high-impact and persistent concepts, exam-over-exam changes, and data quality checks.
- **Questions it answers**: Which rubric items cost students the most points? Which mistakes repeat across exams? Which concepts drive the largest impact? How did performance shift between exams? For whom are mistakes recurring (in aggregate, not individually when anonymized)?
- **What it does NOT claim**: It does not grade papers, change Gradescope scores, or predict individual future grades with guarantees. Predictive risks are heuristic and optional. It does not provide per-student interventions when personal mode/safe mode hide identifiers. It is not a secure, multi-user LMS; use locally or in trusted Streamlit Cloud workspaces.

## 3) Five-Minute Demo Script (using built-in synthetic data)
- **Setup (0:30)**: Run `python -m app`. Mention Python 3.12 and that no secrets are needed.
- **Load data (0:30)**: In sidebar, toggle **Synthetic demo dataset**. The app auto-loads a generated class (80 students, multiple exams).
- **Validate (0:30)**: Show the stepper hitting "Validate" and the Data Quality tab listing schema and invariants.
- **Overview KPIs (1:00)**: On Overview, point out KPIs (students, exams, avg points lost), the top rubric items table, and downloads disabled if Safe Mode is on.
- **Concepts (0:45)**: Scroll to Concepts bar chart; note how topics aggregate deductions and how unmapped concepts are handled.
- **Course Structure & Misconceptions (0:45)**: Show transitions/sankey and the misconceptions list; explain these are cohort-level signals.
- **Instructor Summary (0:45)**: If Safe/Personal mode permits, open Instructor Summary to highlight top/persistent concepts and exam-over-exam changes; note Safe Mode hides exports.
- **Close (0:15)**: Remind that predictive tab appears only with `scikit-learn`; Safe Mode/Personal Mode reduce visibility to protect privacy.
