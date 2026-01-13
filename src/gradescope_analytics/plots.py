import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def distribution_chart(dist_df: pd.DataFrame) -> go.Figure:
    if dist_df.empty:
        return go.Figure()
    fig = px.bar(dist_df, x="bin", y="count", title="Score distribution", labels={"bin": "Score bin", "count": "Count"})
    fig.update_layout(bargap=0.05)
    return fig


def category_pie(categories_df: pd.DataFrame) -> go.Figure:
    if categories_df.empty:
        return go.Figure()
    fig = px.pie(categories_df, names="category", values="score_sum", title="Category share")
    return fig


def rubric_bar(rubric_df: pd.DataFrame) -> go.Figure:
    if rubric_df.empty:
        return go.Figure()
    fig = px.bar(rubric_df, x="rubric_item", y="avg_score", color="category", title="Average score by rubric item")
    fig.update_layout(xaxis_title="Rubric item", yaxis_title="Average score")
    return fig


def student_bar(students_df: pd.DataFrame) -> go.Figure:
    if students_df.empty:
        return go.Figure()
    fig = px.bar(students_df, x="student_name", y="percent", color="assignment", title="Percent by student")
    fig.update_layout(xaxis_title="Student", yaxis_title="Percent")
    return fig
