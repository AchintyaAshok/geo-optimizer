from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

import streamlit as st

from crawllmer.app.web.runtime import pipeline, repo
from crawllmer.core import InvalidInputError
from crawllmer.core.config import get_settings
from crawllmer.domain.models import (
    CrawlEvent,
    CrawlRun,
    RunStatus,
    WorkItem,
    WorkItemState,
    WorkStage,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="crawllmer", layout="wide")

STAGES = list(WorkStage)
STAGE_LABELS = {
    WorkStage.discovery: "Discovery",
    WorkStage.extraction: "Extraction",
    WorkStage.canonicalization: "Canonicalize",
    WorkStage.scoring: "Scoring",
    WorkStage.generation: "Generation",
}

MAX_PREVIEW_LINES = 1000

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    /* ---- hide default streamlit header/footer ---- */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* ---- navbar ---- */
    .navbar {
        display: flex; align-items: center;
        padding: 10px 24px;
        border-bottom: 1px solid rgba(128,128,128,.2);
        margin: -1rem -1rem 1rem -1rem;
        gap: 16px;
    }
    .navbar-brand {
        font-size: 1.35rem; font-weight: 800;
        letter-spacing: -0.5px;
    }
    .navbar-tagline {
        font-size: .85rem; color: #9ca3af;
        flex: 1;
    }
    .navbar-menu-btn {
        background: none; border: 1px solid rgba(128,128,128,.3);
        border-radius: 6px; padding: 6px 10px; cursor: pointer;
        font-size: 1.1rem; color: inherit; line-height: 1;
    }
    .navbar-menu-btn:hover { background: rgba(128,128,128,.1); }
    /* hamburger dropdown */
    .menu-dropdown {
        position: relative; display: inline-block;
    }
    .menu-items {
        display: none; position: absolute; right: 0; top: 100%;
        background: var(--background-color, #fff);
        border: 1px solid rgba(128,128,128,.2);
        border-radius: 8px; min-width: 180px;
        box-shadow: 0 4px 12px rgba(0,0,0,.12);
        z-index: 999; padding: 4px 0;
    }
    .menu-dropdown:hover .menu-items,
    .menu-dropdown:focus-within .menu-items { display: block; }
    .menu-item {
        display: block; padding: 8px 16px; font-size: .85rem;
        color: #9ca3af; cursor: not-allowed; text-decoration: none;
        border: none; background: none; width: 100%; text-align: left;
    }
    .menu-item-label { margin-left: 8px; }
    .menu-item-badge {
        font-size: .65rem; background: rgba(128,128,128,.15);
        padding: 1px 6px; border-radius: 8px; margin-left: 6px;
    }

    /* ---- stage pills ---- */
    .stage-pill {
        display: inline-block; padding: 2px 10px;
        border-radius: 12px; font-size: .78rem;
        font-weight: 600; margin-right: 4px;
    }
    .stage-done  { background: #166534; color: #bbf7d0; }
    .stage-active{ background: #1e40af; color: #bfdbfe; }
    .stage-pend  { background: #374151; color: #9ca3af; }
    .stage-fail  { background: #991b1b; color: #fecaca; }

    /* ---- badges ---- */
    .badge {
        display: inline-block; padding: 2px 8px;
        border-radius: 10px; font-size: .75rem; font-weight: 600;
    }
    .badge-completed { background: #166534; color: #bbf7d0; }
    .badge-failed    { background: #991b1b; color: #fecaca; }
    .badge-running   { background: #1e40af; color: #bfdbfe; }
    .badge-queued    { background: #374151; color: #9ca3af; }

    /* ---- timeline ---- */
    .tl-row {
        display: flex; align-items: center; gap: 10px;
        padding: 4px 0; font-size: .85rem;
        border-bottom: 1px solid rgba(128,128,128,.15);
    }
    .tl-icon { font-size: 1.1rem; width: 22px; text-align: center; }
    .tl-stage { font-weight: 600; min-width: 110px; }
    .tl-dur { color: #9ca3af; min-width: 70px; }
    .tl-err { color: #f87171; font-size: .8rem; }

    /* ---- detail panel ---- */
    .detail-header {
        font-size: 1.4rem; font-weight: 700; margin-bottom: 4px;
    }
    /* ---- live events ---- */
    .ev-row {
        display: flex; align-items: baseline; gap: 8px;
        padding: 3px 0; font-size: .8rem;
        border-bottom: 1px solid rgba(128,128,128,.08);
        font-family: 'SF Mono', 'Fira Code', monospace;
    }
    .ev-time { color: #6b7280; min-width: 55px; }
    .ev-name { font-weight: 600; }
    .ev-sys  { color: #9ca3af; font-size: .75rem; }
    .ev-dur  { color: #6b7280; min-width: 50px; text-align: right; }
    .ev-meta { color: #9ca3af; font-size: .75rem; }
    .ev-live-dot {
        display: inline-block; width: 6px; height: 6px;
        border-radius: 50%; background: #3b82f6;
        animation: pulse 1.5s infinite;
        margin-right: 4px; vertical-align: middle;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Navbar
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="navbar">
        <span class="navbar-brand">crawllmer</span>
        <span class="navbar-tagline">
            Generate spec-compliant llms.txt for any website
        </span>
        <div class="menu-dropdown">
            <button class="navbar-menu-btn" aria-label="Menu">
                &#9776;
            </button>
            <div class="menu-items">
                <div class="menu-item">
                    &#9881;<span class="menu-item-label">Settings</span>
                    <span class="menu-item-badge">soon</span>
                </div>
                <div class="menu-item">
                    &#128100;<span class="menu-item-label">Account</span>
                    <span class="menu-item-badge">soon</span>
                </div>
                <div class="menu-item">
                    &#128179;<span class="menu-item-label">Billing</span>
                    <span class="menu-item-badge">soon</span>
                </div>
                <div class="menu-item">
                    &#128218;<span class="menu-item-label">API Docs</span>
                    <span class="menu-item-badge">soon</span>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state — only UI selection, no run tracking
# ---------------------------------------------------------------------------

if "selected_run" not in st.session_state:
    st.session_state.selected_run: str | None = None

_settings = get_settings()
RECENT_HOURS = 24


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _elapsed(start: datetime) -> str:
    now = datetime.now(UTC)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    secs = int((now - start).total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s"
    return f"{secs // 3600}h {(secs % 3600) // 60}m"


def _duration(item: WorkItem) -> str:
    ms = int((item.updated_at - item.created_at).total_seconds() * 1000)
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _stage_state(stage: WorkStage, items: list[WorkItem]) -> str:
    stage_items = [i for i in items if i.stage == stage]
    if not stage_items:
        return "pending"
    states = {i.state for i in stage_items}
    if WorkItemState.failed in states:
        return "failed"
    if WorkItemState.processing in states:
        return "active"
    if WorkItemState.completed in states:
        return "done"
    return "pending"


def _current_stage_label(items: list[WorkItem]) -> str:
    """Short label for the current/latest stage."""
    for stage in reversed(STAGES):
        state = _stage_state(stage, items)
        if state in ("active", "done", "failed"):
            icon = {"active": "▶", "done": "✓", "failed": "✗"}[state]
            return f"{icon} {STAGE_LABELS[stage]}"
    return "queued"


# ---------------------------------------------------------------------------
# Rendering: stage bar, timeline, detail panel
# ---------------------------------------------------------------------------


def _render_stage_bar(items: list[WorkItem]) -> None:
    pills: list[str] = []
    for stage in STAGES:
        state = _stage_state(stage, items)
        css = {
            "done": "stage-done",
            "active": "stage-active",
            "pending": "stage-pend",
            "failed": "stage-fail",
        }[state]
        icon = {
            "done": "&#10003;",
            "active": "&#9654;",
            "pending": "&#8226;",
            "failed": "&#10007;",
        }[state]
        pills.append(
            f'<span class="stage-pill {css}">{icon} {STAGE_LABELS[stage]}</span>'
        )
    st.markdown(" ".join(pills), unsafe_allow_html=True)


def _render_timeline(items: list[WorkItem]) -> None:
    seen: dict[WorkStage, WorkItem] = {}
    for item in items:
        existing = seen.get(item.stage)
        if existing is None or item.state != WorkItemState.queued:
            seen[item.stage] = item

    for stage in STAGES:
        item = seen.get(stage)
        if item is None:
            st.markdown(
                '<div class="tl-row">'
                '<span class="tl-icon">&#9675;</span>'
                f'<span class="tl-stage">{STAGE_LABELS[stage]}</span>'
                '<span class="tl-dur">--</span></div>',
                unsafe_allow_html=True,
            )
            continue

        icon_map = {
            WorkItemState.completed: "&#10003;",
            WorkItemState.failed: "&#10007;",
            WorkItemState.processing: "&#9654;",
            WorkItemState.queued: "&#9675;",
        }
        icon = icon_map.get(item.state, "&#9675;")
        dur = _duration(item)
        err = (
            f'<span class="tl-err">{item.last_error}</span>' if item.last_error else ""
        )
        st.markdown(
            '<div class="tl-row">'
            f'<span class="tl-icon">{icon}</span>'
            f'<span class="tl-stage">{STAGE_LABELS[stage]}</span>'
            f'<span class="tl-dur">{dur}</span>{err}</div>',
            unsafe_allow_html=True,
        )


RECENT_EVENT_COUNT = 8


def _event_row_html(ev: CrawlEvent) -> str:
    """Build one HTML row for a crawl event."""
    ts = ev.started_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    time_str = ts.strftime("%H:%M:%S")

    dur_str = ""
    if ev.duration is not None:
        ms = int(ev.duration * 1000)
        dur_str = f"{ms}ms" if ms < 1000 else f"{ms / 1000:.1f}s"

    meta_parts: list[str] = []
    for k, v in ev.metadata.items():
        val = str(v)
        if len(val) > 60:
            val = val[:57] + "..."
        meta_parts.append(f"{k}={val}")
    meta_str = " ".join(meta_parts)

    return (
        '<div class="ev-row">'
        f'<span class="ev-time">{time_str}</span>'
        f'<span class="ev-name">{ev.name}</span>'
        f'<span class="ev-sys">{ev.system}</span>'
        f'<span class="ev-dur">{dur_str}</span>'
        f'<span class="ev-meta">{meta_str}</span>'
        "</div>"
    )


def _render_events(events: list[CrawlEvent], *, is_active: bool) -> None:
    """Render recent events as styled log + full list in a dataframe."""
    if not events:
        if is_active:
            st.caption("Waiting for events...")
        return

    header = "Live events" if is_active else "Events"
    dot = '<span class="ev-live-dot"></span>' if is_active else ""
    st.markdown(
        f"<p style='font-size:.85rem; color:#9ca3af;'>"
        f"{dot}{header} ({len(events)})</p>",
        unsafe_allow_html=True,
    )

    # Recent events as styled monospace log (most recent first)
    recent = list(reversed(events[-RECENT_EVENT_COUNT:]))
    st.markdown(
        "\n".join(_event_row_html(ev) for ev in recent),
        unsafe_allow_html=True,
    )

    # Full event table in a collapsed expander (if more than shown)
    if len(events) > RECENT_EVENT_COUNT:
        with st.expander(f"All {len(events)} events"):
            table_rows = []
            for ev in reversed(events):
                ts = ev.started_at
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                dur = None
                if ev.duration is not None:
                    dur = round(ev.duration * 1000)

                meta_str = ", ".join(
                    f"{k}={str(v)[:80]}" for k, v in ev.metadata.items()
                )
                table_rows.append(
                    {
                        "Time": ts.strftime("%H:%M:%S"),
                        "Event": ev.name,
                        "System": ev.system,
                        "Duration (ms)": dur,
                        "Details": meta_str,
                    }
                )
            st.dataframe(
                table_rows,
                use_container_width=True,
                hide_index=True,
            )


def _render_llms_txt(artifact_text: str, run_id_str: str) -> None:
    """Render llms.txt with stats, truncation for large files."""
    lines = artifact_text.splitlines()
    line_count = len(lines)
    word_count = len(artifact_text.split())

    st.caption(f"{line_count} lines · {word_count:,} words")

    truncated = line_count > MAX_PREVIEW_LINES
    preview = "\n".join(lines[:MAX_PREVIEW_LINES]) if truncated else artifact_text

    with st.expander(
        "View llms.txt" if not truncated else "View llms.txt (truncated)",
        expanded=False,
    ):
        st.code(preview, language="text")
        if truncated:
            st.info(
                f"Showing first {MAX_PREVIEW_LINES} of {line_count} "
                "lines. Download the file to see the full output."
            )

    st.download_button(
        "Download llms.txt",
        data=artifact_text,
        file_name="llms.txt",
        mime="text/plain",
        key=f"dl-{run_id_str}",
    )


def _render_detail_panel(run_id_str: str) -> None:
    """Render the full detail view for a selected run."""
    run = repo.get_run(UUID(run_id_str))
    if run is None:
        st.warning("Run not found.")
        return

    items = repo.list_work_items(UUID(run_id_str))
    status_class = f"badge-{run.status.value}"

    # Header
    st.markdown(
        f'<div class="detail-header">{run.hostname}</div>',
        unsafe_allow_html=True,
    )
    col_badge, col_time = st.columns([1, 3])
    with col_badge:
        st.markdown(
            f'<span class="badge {status_class}">{run.status.value}</span>',
            unsafe_allow_html=True,
        )
    with col_time:
        st.caption(f"Started {_elapsed(run.created_at)} ago")

    # Stage bar
    _render_stage_bar(items)

    # Score metrics (completed only)
    if run.status == RunStatus.completed:
        st.markdown("---")
        mcols = st.columns(4)
        bd = run.score_breakdown or {}
        mcols[0].metric(
            "Overall",
            f"{(run.score or 0):.1%}",
            help="Weighted: 40% coverage + 40% confidence + 20% redundancy",
        )
        mcols[1].metric(
            "Coverage",
            f"{bd.get('coverage', 0):.1%}",
            help=(
                "Fraction of pages with title and description. "
                "Average of (titled/total) and (described/total)."
            ),
        )
        mcols[2].metric(
            "Confidence",
            f"{bd.get('confidence', 0):.1%}",
            help=(
                "Average extraction confidence across pages. "
                "Higher when metadata comes from structured "
                "sources (meta tags, JSON-LD) vs fallbacks."
            ),
        )
        mcols[3].metric(
            "Redundancy",
            f"{bd.get('redundancy', 0):.1%}",
            help=(
                "Ratio of unique URLs to total pages. "
                "100% means no duplicates were found."
            ),
        )

    # Error (failed only)
    if run.status == RunStatus.failed:
        st.error("Crawl failed: " + run.notes.get("processing_error", "unknown error"))

    # llms.txt
    if run.status == RunStatus.completed:
        artifact = repo.get_artifact(UUID(run_id_str))
        if artifact:
            st.markdown("---")
            _render_llms_txt(artifact.llms_txt, run_id_str)

    # Timeline
    st.markdown("---")
    st.caption("Pipeline timeline")
    _render_timeline(items)

    # Events
    is_active = run.status in (RunStatus.queued, RunStatus.running)
    events = repo.list_events(UUID(run_id_str))
    if events or is_active:
        st.markdown("---")
        _render_events(events, is_active=is_active)


# ---------------------------------------------------------------------------
# Classify runs from the database (no session-state tracking)
# ---------------------------------------------------------------------------

all_runs = repo.list_runs(limit=50)
now = datetime.now(UTC)
recent_cutoff = now - timedelta(hours=RECENT_HOURS)

active_runs: list[CrawlRun] = []
recent_runs: list[CrawlRun] = []
history_runs: list[CrawlRun] = []

for run in all_runs:
    if run.status in (RunStatus.queued, RunStatus.running):
        active_runs.append(run)
    else:
        created = run.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if created >= recent_cutoff:
            recent_runs.append(run)
        else:
            history_runs.append(run)

has_active = len(active_runs) > 0

# ---------------------------------------------------------------------------
# Two-column layout
# ---------------------------------------------------------------------------

col_list, col_detail = st.columns([2, 3], gap="large")

# ---- LEFT: master list ----
with col_list:
    # URL input
    url_col, btn_col = st.columns([4, 1])
    with url_col:
        url = st.text_input(
            "Website URL",
            placeholder="https://example.com",
            label_visibility="collapsed",
        )
    with btn_col:
        submitted = st.button("Crawl", use_container_width=True, type="primary")

    if submitted:
        if not url:
            st.error("Please provide a URL.")
        else:
            try:
                new_run = pipeline.enqueue_run(url)
                st.session_state.selected_run = str(new_run.id)
                st.rerun()
            except InvalidInputError as exc:
                st.error(f"Invalid URL: {exc}")

    # --- Run list helper ---
    def _run_button(
        run: CrawlRun, *, key_prefix: str, items: list[WorkItem] | None = None
    ) -> None:
        """Render a compact selectable row for a run."""
        is_selected = st.session_state.selected_run == str(run.id)

        # Build label
        score_str = ""
        if run.score is not None:
            score_str = f"  {run.score:.0%}"
        stage_str = ""
        if items:
            stage_str = f"  {_current_stage_label(items)}"

        status_icons = {
            "completed": "✓",
            "failed": "✗",
            "running": "▶",
            "queued": "○",
        }
        icon = status_icons.get(run.status.value, "○")
        label = f"{icon}  {run.hostname}{score_str}{stage_str}"
        elapsed = _elapsed(run.created_at)

        if st.button(
            label,
            key=f"{key_prefix}-{run.id}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
            help=f"{elapsed} ago",
        ):
            st.session_state.selected_run = str(run.id)
            st.rerun()

    # Active runs
    if active_runs:
        st.caption("ACTIVE")
        for run in active_runs:
            items = repo.list_work_items(run.id)
            _run_button(run, key_prefix="active", items=items)

    # Recent completed/failed
    if recent_runs:
        st.caption("RECENT")
        for run in recent_runs:
            _run_button(run, key_prefix="recent")

    # Older history
    if history_runs:
        st.caption("HISTORY")
        for run in history_runs:
            _run_button(run, key_prefix="hist")

# ---- RIGHT: detail panel ----
with col_detail:
    if st.session_state.selected_run:
        _render_detail_panel(st.session_state.selected_run)
    else:
        st.markdown(
            "<div style='text-align:center; padding: 80px 20px; "
            "color: #9ca3af;'>"
            "<p style='font-size: 1.2rem;'>Select a crawl to view details"
            "</p></div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Auto-refresh while crawls are active
# ---------------------------------------------------------------------------

if has_active:
    time.sleep(_settings.ui_refresh_seconds)
    st.rerun()
