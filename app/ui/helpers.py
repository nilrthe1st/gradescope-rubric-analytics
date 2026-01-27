from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Dict, Optional
import zipfile

import streamlit as st

from gradescope_analytics.security import build_export_path, sanitize_filename


def _key(prefix: str, name: str) -> str:
    safe = sanitize_filename(name).replace("/", "_")
    return f"{prefix}:{safe}"


def download_df(label: str, df, filename: str, mime: str = "text/csv", safe_mode: bool = False) -> None:
    """Render a download button with deterministic key; no-op in safe mode."""
    if safe_mode:
        st.caption("Downloads disabled in safe mode.")
        return

    SAFE_EXPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "exports"
    SAFE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(filename)
    path = build_export_path(SAFE_EXPORT_DIR, safe_name)
    path.write_bytes(df.to_csv(index=False).encode("utf-8"))

    st.download_button(
        label=label,
        data=path.read_bytes(),
        file_name=safe_name,
        mime=mime,
        key=_key("dl", safe_name),
        use_container_width=False,
    )


def download_packet(artifact_map: Dict[str, object], fig_map: Optional[Dict[str, object]] = None, label: str = "Download instructor packet", safe_mode: bool = False) -> None:
    """Zip artifacts/figs for export; suppressed in safe mode."""
    if safe_mode:
        st.caption("Packet export disabled in safe mode.")
        return
    if not artifact_map:
        st.caption("No artifacts available to export.")
        return

    SAFE_EXPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "exports"
    SAFE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename("instructor_packet.zip")
    packet_path = build_export_path(SAFE_EXPORT_DIR, safe_name)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, df in artifact_map.items():
            if df is None or getattr(df, "empty", False):
                continue
            safe = sanitize_filename(f"{name}.csv")
            zf.writestr(safe, df.to_csv(index=False))

        if fig_map:
            for name, fig in fig_map.items():
                if fig is None:
                    continue
                try:
                    png = fig.to_image(format="png")
                    zf.writestr(sanitize_filename(f"{name}.png"), png)
                except Exception:
                    continue

    packet_path.write_bytes(buffer.getvalue())

    st.download_button(
        label,
        data=packet_path.read_bytes(),
        file_name=safe_name,
        mime="application/zip",
        use_container_width=False,
        key=_key("packet", label),
    )


def download_fig(label: str, fig, filename: str, safe_mode: bool = False) -> None:
    """Export a Plotly fig as PNG; suppressed in safe mode."""
    if safe_mode:
        st.caption("Chart export disabled in safe mode.")
        return
    if fig is None or not getattr(fig, "data", None):
        st.caption("No chart to export")
        return
    try:
        SAFE_EXPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "exports"
        SAFE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = sanitize_filename(filename)
        payload = fig.to_image(format="png")
        path = build_export_path(SAFE_EXPORT_DIR, safe_name)
        path.write_bytes(payload)
        st.download_button(label, path.read_bytes(), file_name=safe_name, mime="image/png", key=_key("dl-png", safe_name))
    except Exception as exc:  # pragma: no cover - GUI only
        st.warning(f"Unable to export chart: {exc}")


def style_fig(fig, title: Optional[str] = None):
    fig.update_layout(
        title=title or fig.layout.title.text,
        margin=dict(t=60, r=24, b=40, l=24),
        template="plotly_dark",
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220",
        font=dict(family="Inter, sans-serif", color="#e5e7eb", size=12),
        hoverlabel=dict(bgcolor="#111827", font_size=12),
    )
    return fig

```