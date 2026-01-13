import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def distribution_chart(dist_df: pd.DataFrame) -> go.Figure:
    if dist_df.empty:
        return go.Figure()
    fig = px.bar(dist_df, x="bin", y="count", title="Points lost distribution", labels={"bin": "Points bin", "count": "Count"})
    fig.update_layout(bargap=0.05)
    return fig


def exam_pie(exams_df: pd.DataFrame) -> go.Figure:
    if exams_df.empty:
        return go.Figure()
    fig = px.pie(exams_df, names="exam_id", values="total_points_lost", title="Points lost by exam")
    return fig


def rubric_bar(rubric_df: pd.DataFrame) -> go.Figure:
    if rubric_df.empty:
        return go.Figure()
    fig = px.bar(rubric_df, x="rubric_item", y="avg_points_lost", color="topic", title="Average points lost by rubric item")
    fig.update_layout(xaxis_title="Rubric item", yaxis_title="Avg points lost")
    return fig


def student_bar(students_df: pd.DataFrame) -> go.Figure:
    if students_df.empty:
        return go.Figure()
    fig = px.bar(students_df, x="student_id", y="total_points_lost", color="exam_id", title="Points lost by student")
    fig.update_layout(xaxis_title="Student", yaxis_title="Total points lost")
    return fig
