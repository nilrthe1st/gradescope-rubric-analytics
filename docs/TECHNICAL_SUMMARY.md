# Technical Summary

## New analytics added
- Concept-level rollups (points lost, students affected) with bar visualizations and downloads.
- Concept mapping layer with validated rubric→concept store persisted to JSON; unmapped items are surfaced and warned in UI.
- Persistence and trajectory analytics across exams: item persistence, drop-off/emergence, conditional mistake transitions (Sankey), and trajectory stats.
- Misconception clustering via rubric-item co-occurrence (Jaccard/correlation) with cluster cards and pair tables.
- Instructor recommendations prioritizing concepts by impact (points lost × students affected) and persistence, with action guidance and downloads.
- Predictive analytics using logistic regression (prior rubric occurrences and concept points) producing per-student risk tables, confidence buckets, and interpretable coefficients.
- Course-structure analytics comparing section vs section and TA vs TA disparities (avg points lost per student), with CSV exports and charts.
- Export suite: CSV downloads for top issues, persistence, recommendations; PNG chart exports; one-click PDF instructor report (top issues, persistence, recommendations).

## New data requirements
- Canonical schema now includes optional `topic`, `section_id`, and `ta_id` columns; required: `student_id`, `exam_id`, `question_id`, `rubric_item`, `points_lost`.
- Concept mapping can be defined via `topic` or rubric→concept mapping UI; invalid placeholders (yes/true/none/empty) are rejected. Unmapped rows are labeled `Unmapped` and excluded from recommendations by default.
- For predictive analytics, at least two exams per student are needed to train and score future mistake probabilities.
- Concept mappings can be supplied via `topic` column or interactive rubric→concept mapping persisted to JSON.

## Modeling assumptions
- Points lost are non-negative and numeric; rows with blank identifiers are invalid during normalization.
- Logistic regression features: binary prior_seen of rubric item and cumulative prior_concept_points; predictions interpret coefficients directly.
- Persistence defines cohort on first exam in order; repeated if appearing in later exams; exam ordering may be user-specified.
- Misconception clustering uses rubric-item co-occurrence with Jaccard/correlation thresholds; clusters formed via union-find on edges above thresholds.
- Course-structure disparities treat blank section/TA values as “Unassigned” and compute average points lost per student; no risk adjustment for sample size.
- Anonymization replaces student_id (and student_name when present) with deterministic aliases for all visuals/exports.

## Limitations
- Predictive model is simple logistic regression without temporal decay, calibration, or cross-validation; sensitive to sparse history and class imbalance.
- Recommendations heuristic (impact × persistence) is not personalized and ignores instructional sequencing.
- Misconception clustering thresholds are static; may under/over-cluster depending on dataset size and noise.
- Course-structure comparisons do not include statistical significance or confidence intervals; small-section volatility not flagged automatically.
- PDF generation depends on optional `reportlab`; if missing, only CSV/PNG exports function.
- Concept mapping completeness drives many analytics; unmapped rubric items reduce usefulness of concept-level views.
	- Recommendations skip `Unmapped` unless the user opts in; UI warns when Unmapped rows exist.

## Suggested next research directions
- Add calibration and uncertainty estimates for the predictive model (Platt scaling/temperature scaling, bootstrapped confidence).
- Incorporate temporal decay and recency-weighted features, plus per-student baselines, for future mistake prediction.
- Add significance testing or Bayesian shrinkage for section/TA disparities to mitigate small-sample noise.
- Extend recommendations with mastery models (e.g., BKT/IRT) and concept prerequisite graphs to rank interventions.
- Auto-tune misconception clustering thresholds and visualize cluster stability; add semantic similarity using rubric text.
- Introduce cohort/segment filters (majors, enrollment status) and fairness checks across demographics where appropriate.
- Package PDF report generation behind a service abstraction to support branding and richer layouts (charts + tables inline).
