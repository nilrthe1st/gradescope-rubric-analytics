# Changelog

## 2026-01-15
- Added student scope controls (all, single, multi-select) and filtering across analytics views.
- Introduced cohort-aware KPIs (avg and std dev points lost per student) and kept instructor defaults to all students.
- Ensured charts/tables respect student filters and preview reflects the selected cohort.
- Added concept normalization: use provided topics or map rubric items to concepts with persisted JSON storage.
- Introduced concept-level analytics (points lost, students affected) with downloadable rollups and charts.
- Added persistence and trajectory analytics across exams: item-level persistence/drop-off/emergence and conditional mistake transitions with Sankey view.
- Added misconception clustering using rubric item co-occurrence (Jaccard/correlation), with cluster cards and instructor guidance to teach items together.
- Added instructor recommendations: high-impact and high-persistence concepts with ranked actions (“Re-teach” / “Add practice”) and downloadable guidance.
- Added interpretable predictive analytics: logistic-regression-based future mistake probabilities, coefficient display, and per-student risk tables with uncertainty disclaimers.

## 2026-01-12
- Added CI workflow, Docker setup, and Streamlit UI polish for rubric analytics.
- Documented local venv usage, testing, and container instructions.
- Maintained canonical sample dataset with persistence and analytics coverage.
