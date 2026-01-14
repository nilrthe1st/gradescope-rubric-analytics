from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Iterable, List, Optional

import streamlit as st

PRIMARY = "#2563eb"
SURFACE = "#0b1220"
SURFACE_ALT = "#111827"
BORDER = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#9ca3af"
ACCENT = "#22d3ee"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
ERROR = "#ef4444"

CSS_TEMPLATE = """
<style>
:root {
    --primary: $PRIMARY;
    --surface: $SURFACE;
    --surface-alt: $SURFACE_ALT;
    --border: $BORDER;
    --text: $TEXT;
    --muted: $MUTED;
    --accent: $ACCENT;
    --success: $SUCCESS;
    --warning: $WARNING;
    --error: $ERROR;
    --radius-lg: 18px;
    --radius-md: 12px;
    --shadow-1: 0 12px 40px rgba(0,0,0,0.35);
}

html, body, [class^="css"], .stApp {
    background: radial-gradient(circle at 20% 20%, rgba(34,211,238,0.07), transparent 30%),
                radial-gradient(circle at 80% 10%, rgba(37,99,235,0.07), transparent 30%),
                var(--surface);
    color: var(--text);
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', system-ui, -apple-system, sans-serif;
}

section.main .block-container {
    padding: 1.5rem 2.2rem 2rem 2.2rem;
    max-width: 1400px;
}

.app-card {
    background: linear-gradient(145deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: var(--radius-lg);
    padding: 1.1rem 1.2rem;
    box-shadow: var(--shadow-1);
}

.app-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.05);
    color: var(--text);
}

.app-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.55rem;
    border-radius: 10px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    text-transform: uppercase;
    border: 1px solid rgba(255,255,255,0.08);
}

.app-badge.success { background: rgba(34,197,94,0.18); color: #bbf7d0; border-color: rgba(34,197,94,0.35); }
.app-badge.warning { background: rgba(245,158,11,0.18); color: #fde68a; border-color: rgba(245,158,11,0.35); }
.app-badge.info { background: rgba(37,99,235,0.18); color: #c7d2fe; border-color: rgba(37,99,235,0.35); }

.app-kpi {
    background: linear-gradient(135deg, rgba(37,99,235,0.12), rgba(34,211,238,0.1));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-md);
    padding: 0.9rem 1rem;
}
.app-kpi .label { color: $MUTED; font-size: 0.85rem; margin-bottom: 0.25rem; }
.app-kpi .value { font-size: 1.4rem; font-weight: 700; }

.app-stepper { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.65rem; margin-bottom: 1.1rem; }
.app-step {
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.04);
    border-radius: var(--radius-md);
    padding: 0.8rem 0.9rem;
}
.app-step .title { font-weight: 600; color: var(--text); }
.app-step .status { color: $MUTED; font-size: 0.85rem; }
.app-step.active { border-color: $ACCENT; box-shadow: 0 0 0 1px rgba(34,211,238,0.25); }
.app-step.done { border-color: $SUCCESS; }

.stTabs [data-baseweb="tab-list"] { gap: 0.25rem; }
.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.06);
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.1);
    padding: 0.45rem 0.9rem;
    color: var(--text);
}

/* Tables */
[data-testid="stDataFrame"] .row_heading, [data-testid="stDataFrame"] .blank { display: none; }
[data-testid="stDataFrame"] .row_heading { font-weight: 600; color: var(--text); }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(17,24,39,0.95), rgba(17,24,39,0.8));
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* Buttons */
button[kind="primary"], .stButton>button {
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.1);
    background: linear-gradient(120deg, $PRIMARY, $ACCENT);
    color: white;
    font-weight: 600;
}

.small-muted { color: var(--muted); font-size: 0.9rem; }
.section-header { display: flex; align-items: center; gap: 0.5rem; font-weight: 700; font-size: 1.05rem; margin-bottom: 0.35rem; }
</style>
"""

GLOBAL_CSS = string.Template(CSS_TEMPLATE).safe_substitute(
    {
        "PRIMARY": PRIMARY,
        "SURFACE": SURFACE,
        "SURFACE_ALT": SURFACE_ALT,
        "BORDER": BORDER,
        "TEXT": TEXT,
        "MUTED": MUTED,
        "ACCENT": ACCENT,
        "SUCCESS": SUCCESS,
        "WARNING": WARNING,
        "ERROR": ERROR,
    }
)


@dataclass
class Step:
    title: str
    description: str
    status: str  # waiting | active | done


def muted(text: str):
    st.markdown(f"<div class='small-muted'>{text}</div>", unsafe_allow_html=True)


def pill(label: str, tone: str = "info"):
    colors = {"info": ACCENT, "success": SUCCESS, "warning": WARNING, "danger": ERROR}
    icon = {"info": "●", "success": "●", "warning": "●", "danger": "●"}.get(tone, "●")
    st.markdown(
        f"<span class='app-pill' style='border-color:{colors.get(tone, ACCENT)}; color:{TEXT};'>{icon} {label}</span>",
        unsafe_allow_html=True,
    )


def badge(label: str, tone: str = "info"):
    st.markdown(f"<span class='app-badge {tone}'>{label}</span>", unsafe_allow_html=True)


def card(title: Optional[str] = None, description: Optional[str] = None):
    class _Card:
        def __enter__(self):
            st.markdown("<div class='app-card'>", unsafe_allow_html=True)
            if title:
                st.markdown(f"<div class='section-header'>{title}</div>", unsafe_allow_html=True)
            if description:
                muted(description)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
            return False

    return _Card()


def kpi_row(items: Iterable[dict]):
    items = list(items)
    cols = st.columns(len(items)) if items else []
    for col, item in zip(cols, items):
        with col:
            st.markdown(
                f"""
                <div class='app-kpi'>
                    <div class='label'>{item.get('label','')}</div>
                    <div class='value'>{item.get('value','-')}</div>
                    <div class='small-muted'>{item.get('hint','')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def stepper(steps: List[Step]):
    st.markdown("<div class='app-stepper'>", unsafe_allow_html=True)
    for step in steps:
        classes = "app-step " + step.status
        indicator = "•" if step.status == "waiting" else ("✔" if step.status == "done" else "➜")
        st.markdown(
            f"""
            <div class='{classes}'>
                <div class='title'>{indicator} {step.title}</div>
                <div class='status'>{step.description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def section_header(title: str, description: Optional[str] = None):
    st.markdown(f"<div class='section-header'>{title}</div>", unsafe_allow_html=True)
    if description:
        muted(description)


class AppShell:
    def __init__(self, title: str, subtitle: Optional[str] = None):
        self.title = title
        self.subtitle = subtitle
        self._inject_css()

    @staticmethod
    def _inject_css():
        st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    def header(self, right: Optional[str] = None):
        left, right_col = st.columns([0.8, 0.2])
        with left:
            st.title(self.title)
            if self.subtitle:
                muted(self.subtitle)
        if right:
            with right_col:
                st.markdown("<div style='display:flex; justify-content:flex-end'>", unsafe_allow_html=True)
                pill(right)
                st.markdown("</div>", unsafe_allow_html=True)

    def layout(self):
        st.markdown("<div style='margin-top:0.2rem'></div>", unsafe_allow_html=True)
