import pandas as pd
import plotly.express as px
import streamlit as st

from app.analytics import category_breakdown, rubric_item_stats, score_distribution, student_summary
from app.ingest import load_csv, sanitize_rows, validate_normalized
from app.mapping import apply_mapping, suggest_mapping
from app.models import MappingConfig, NORMALIZED_COLUMNS
from app.sample_data import load_sample_dataframe


st.set_page_config(
    page_title="Gradescope Rubric Analytics",
    layout="wide",
    page_icon="📊",
)


def _render_header():
    st.title("Gradescope Rubric Analytics")
    st.caption("Upload rubric exports, map columns, and explore analytics in one place.")


def _get_raw_dataframe() -> pd.DataFrame | None:
    st.sidebar.subheader("1) Upload CSV")
    uploaded = st.sidebar.file_uploader("Upload a rubric CSV", type=["csv"])

    if st.sidebar.button("Load sample data"):
        return load_sample_dataframe()

    if uploaded:
        return load_csv(uploaded)
    return None


def _mapping_form(df: pd.DataFrame):
    st.subheader("Mapping wizard")
    suggested = suggest_mapping(df)
    cols = [None] + list(df.columns)

    with st.form("mapping_form"):
        left, right = st.columns(2)
        with left:
            student_id = st.selectbox("Student ID", options=cols, index=cols.index(suggested.get("student_id")) if suggested.get("student_id") in cols else 0)
            student_name = st.selectbox("Student name", options=cols, index=cols.index(suggested.get("student_name")) if suggested.get("student_name") in cols else 0)
            assignment = st.selectbox("Assignment (optional)", options=cols, index=cols.index(suggested.get("assignment")) if suggested.get("assignment") in cols else 0)
            rubric_item = st.selectbox("Rubric item", options=cols, index=cols.index(suggested.get("rubric_item")) if suggested.get("rubric_item") in cols else 0)
        with right:
            category = st.selectbox("Category (optional)", options=cols, index=cols.index(suggested.get("category")) if suggested.get("category") in cols else 0)
            score = st.selectbox("Score / points awarded", options=cols, index=cols.index(suggested.get("score")) if suggested.get("score") in cols else 0)
            max_score = st.selectbox("Max points (optional)", options=cols, index=cols.index(suggested.get("max_score")) if suggested.get("max_score") in cols else 0)
            comment = st.selectbox("Comment (optional)", options=cols, index=cols.index(suggested.get("comment")) if suggested.get("comment") in cols else 0)

        submitted = st.form_submit_button("Apply mapping")

    if not submitted:
        return None

    mapping_dict = {
        "student_id": student_id,
        "student_name": student_name,
        "assignment": assignment,
        "rubric_item": rubric_item,
        "category": category,
        "score": score,
        "max_score": max_score,
        "comment": comment,
    }

    try:
        mapping = MappingConfig.from_dict(mapping_dict)
        return apply_mapping(df, mapping)
    except ValueError as exc:
        st.error(str(exc))
        return None


def _show_metrics(df: pd.DataFrame):
    unique_students = df["student_id"].nunique()
    assignments = df["assignment"].nunique()
    total_rows = len(df)
    avg_score = pd.to_numeric(df["score"], errors="coerce").mean()
    max_score = pd.to_numeric(df["max_score"], errors="coerce").dropna()
    avg_pct = (avg_score / max_score.mean() * 100) if not max_score.empty else float("nan")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Students", unique_students)
    m2.metric("Assignments", assignments)
    m3.metric("Rows", total_rows)
    m4.metric("Average score", f"{avg_score:.2f}" if pd.notna(avg_score) else "-")
    if pd.notna(avg_pct):
        st.caption(f"Average percent of max: {avg_pct:.1f}%")


def _plot_distribution(dist_df: pd.DataFrame):
    if dist_df.empty:
        st.info("No scores to plot yet.")
        return
    fig = px.bar(dist_df, x="bin", y="count", title="Score distribution")
    fig.update_layout(xaxis_title="Score bin", yaxis_title="Count", bargap=0.1)
    st.plotly_chart(fig, use_container_width=True)


def _render_tables(rubric_df: pd.DataFrame, category_df: pd.DataFrame, student_df: pd.DataFrame):
    st.subheader("Rubric items")
    st.dataframe(rubric_df, use_container_width=True, height=320)

    st.subheader("Categories")
    st.dataframe(category_df, use_container_width=True, height=240)

    st.subheader("Students")
    st.dataframe(student_df, use_container_width=True, height=320)


def _download_buttons(df: pd.DataFrame):
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download normalized CSV", data=csv_bytes, file_name="normalized_rubric.csv", mime="text/csv")


def main():
    _render_header()
    raw_df = _get_raw_dataframe()

    if raw_df is None:
        st.info("Upload a CSV or use the sample data to get started.")
        return

    st.write("### Data preview")
    st.dataframe(raw_df.head(20), use_container_width=True)

    normalized_df = _mapping_form(raw_df)
    if normalized_df is None:
        st.warning("Apply a mapping to continue.")
        return

    normalized_df = sanitize_rows(normalized_df)
    errors = validate_normalized(normalized_df)
    if errors:
        st.error("; ".join(errors))
        return

    st.success("Mapping applied. Analytics below.")
    _download_buttons(normalized_df)

    _show_metrics(normalized_df)

    rubrics = rubric_item_stats(normalized_df)
    categories = category_breakdown(normalized_df)
    students = student_summary(normalized_df)
    distribution = score_distribution(normalized_df)

    left, right = st.columns([2, 1])
    with left:
        _plot_distribution(distribution)
    with right:
        st.write("### Category share")
        if not categories.empty:
            fig = px.pie(categories, names="category", values="score_sum")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No categories to show yet.")

    _render_tables(rubrics, categories, students)

    st.write("### Normalized data")
    st.dataframe(normalized_df[NORMALIZED_COLUMNS], use_container_width=True, height=300)


if __name__ == "__main__":
    main()
