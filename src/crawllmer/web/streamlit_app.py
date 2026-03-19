from __future__ import annotations

import time
from datetime import UTC, datetime

import streamlit as st

from crawllmer.domain.models import RunStatus, WorkItem, WorkItemState, WorkStage
from crawllmer.web.runtime import pipeline, repo

# ---------------------------------------------------------------------------
# Page config & custom CSS
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

st.markdown(
    """
    <style>
    /* ---- card container ---- */
    div[data-testid="stExpander"] {
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 8px;
    }
    /* ---- stage pill ---- */
    .stage-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: .78rem;
        font-weight: 600;
        margin-right: 4px;
    }
    .stage-done  { background: #166534; color: #bbf7d0; }
    .stage-active{ background: #1e40af; color: #bfdbfe; }
    .stage-pend  { background: #374151; color: #9ca3af; }
    .stage-fail  { background: #991b1b; color: #fecaca; }
    /* ---- status badge ---- */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: .75rem;
        font-weight: 600;
    }
    .badge-completed { background: #166534; color: #bbf7d0; }
    .badge-failed    { background: #991b1b; color: #fecaca; }
    .badge-running   { background: #1e40af; color: #bfdbfe; }
    .badge-queued    { background: #374151; color: #9ca3af; }
    /* ---- timeline row ---- */
    .tl-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 4px 0;
        font-size: .85rem;
        border-bottom: 1px solid rgba(128,128,128,.15);
    }
    .tl-icon { font-size: 1.1rem; width: 22px; text-align: center; }
    .tl-stage { font-weight: 600; min-width: 110px; }
    .tl-dur { color: #9ca3af; min-width: 70px; }
    .tl-err { color: #f87171; font-size: .8rem; }
    /* ---- header area ---- */
    .app-subtitle {
        font-size: 1.05rem;
        color: #9ca3af;
        margin-top: -12px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("crawllmer")
st.markdown(
    '<p class="app-subtitle">Generate spec-compliant llms.txt for any website</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "active_runs" not in st.session_state:
    st.session_state.active_runs: list[str] = []
if "completed_runs" not in st.session_state:
    st.session_state.completed_runs: list[str] = []

# ---------------------------------------------------------------------------
# URL input
# ---------------------------------------------------------------------------

col_input, col_btn = st.columns([5, 1])
with col_input:
    url = st.text_input(
        "Website URL",
        placeholder="https://example.com",
        label_visibility="collapsed",
    )
with col_btn:
    submitted = st.button("Crawl", use_container_width=True, type="primary")

if submitted:
    if not url:
        st.error("Please provide a URL.")
    else:
        try:
            run = pipeline.enqueue_run(url)
            st.session_state.active_runs.append(str(run.id))
        except ValueError as exc:
            st.error(f"Invalid URL: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _elapsed(start: datetime) -> str:
    """Human-readable elapsed time."""
    now = datetime.now(UTC)
    # SQLite may return naive datetimes — treat them as UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    delta = now - start
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s"
    return f"{secs // 3600}h {(secs % 3600) // 60}m"


def _duration(item: WorkItem) -> str:
    """Duration of a work item."""
    delta = item.updated_at - item.created_at
    ms = int(delta.total_seconds() * 1000)
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _stage_index(items: list[WorkItem]) -> int:
    """Return the index of the furthest completed stage, or current active."""
    completed_stages: set[WorkStage] = set()
    for item in items:
        if item.state == WorkItemState.completed:
            completed_stages.add(item.stage)
    for i, stage in enumerate(STAGES):
        if stage not in completed_stages:
            return i
    return len(STAGES)


def _stage_state(stage: WorkStage, items: list[WorkItem]) -> str:
    """Determine the visual state of a pipeline stage from work items."""
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


def _render_stage_bar(items: list[WorkItem]) -> None:
    """Render a 5-stage progress bar as colored pills."""
    pills: list[str] = []
    for stage in STAGES:
        state = _stage_state(stage, items)
        label = STAGE_LABELS[stage]
        css_class = {
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
        pills.append(f'<span class="stage-pill {css_class}">{icon} {label}</span>')
    st.markdown(" ".join(pills), unsafe_allow_html=True)


def _render_timeline(items: list[WorkItem]) -> None:
    """Render an event timeline for a crawl run."""
    # Deduplicate: keep one item per stage (prefer non-queued/initial)
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
                '<span class="tl-dur">--</span>'
                "</div>",
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
        err_html = ""
        if item.last_error:
            err_html = f'<span class="tl-err">{item.last_error}</span>'

        st.markdown(
            '<div class="tl-row">'
            f'<span class="tl-icon">{icon}</span>'
            f'<span class="tl-stage">{STAGE_LABELS[stage]}</span>'
            f'<span class="tl-dur">{dur}</span>'
            f"{err_html}"
            "</div>",
            unsafe_allow_html=True,
        )


def _render_run_card(run_id_str: str, *, is_active: bool) -> bool:
    """Render a crawl card. Returns True if the run is still active."""
    from uuid import UUID

    run_id = UUID(run_id_str)
    run = repo.get_run(run_id)
    if run is None:
        return False

    items = repo.list_work_items(run_id)
    terminal = run.status in (RunStatus.completed, RunStatus.failed)
    status_class = f"badge-{run.status.value}"

    header = f"**{run.hostname}**"
    if terminal:
        header += f" &mdash; {_elapsed(run.created_at)} ago"
    else:
        header += f" &mdash; started {_elapsed(run.created_at)} ago"

    with st.expander(header, expanded=is_active or terminal):
        # Status + stage bar
        col_status, col_elapsed = st.columns([4, 1])
        with col_status:
            _render_stage_bar(items)
        with col_elapsed:
            st.markdown(
                f'<span class="badge {status_class}">{run.status.value}</span>',
                unsafe_allow_html=True,
            )

        if terminal:
            if run.status == RunStatus.completed:
                # Score metrics
                mcols = st.columns(4)
                breakdown = run.score_breakdown or {}
                mcols[0].metric(
                    "Overall",
                    f"{(run.score or 0):.1%}",
                    help=(
                        "Weighted composite: "
                        "40% coverage + 40% confidence + 20% redundancy"
                    ),
                )
                mcols[1].metric(
                    "Coverage",
                    f"{breakdown.get('coverage', 0):.1%}",
                    help=(
                        "Fraction of pages with title and description. "
                        "Average of (titled/total) and (described/total)."
                    ),
                )
                mcols[2].metric(
                    "Confidence",
                    f"{breakdown.get('confidence', 0):.1%}",
                    help=(
                        "Average extraction confidence across pages. "
                        "Higher when metadata comes from structured "
                        "sources (meta tags, JSON-LD) vs fallbacks."
                    ),
                )
                mcols[3].metric(
                    "Redundancy",
                    f"{breakdown.get('redundancy', 0):.1%}",
                    help=(
                        "Ratio of unique URLs to total pages. "
                        "100% means no duplicates were found."
                    ),
                )

                # llms.txt preview
                artifact = repo.get_artifact(run_id)
                if artifact:
                    st.code(artifact.llms_txt, language="text")
                    st.download_button(
                        "Download llms.txt",
                        data=artifact.llms_txt,
                        file_name="llms.txt",
                        mime="text/plain",
                        key=f"dl-{run_id_str}",
                    )

            elif run.status == RunStatus.failed:
                st.error(
                    "Crawl failed: "
                    f"{run.notes.get('processing_error', 'unknown error')}"
                )

        # Timeline
        with st.container():
            st.caption("Pipeline timeline")
            _render_timeline(items)

    return not terminal


# ---------------------------------------------------------------------------
# Active crawls
# ---------------------------------------------------------------------------

has_active = False

if st.session_state.active_runs:
    # Classify runs before rendering to avoid showing completed in active section
    still_active: list[str] = []
    newly_completed: list[str] = []
    for rid in st.session_state.active_runs:
        run = repo.get_run(__import__("uuid").UUID(rid))
        if run and run.status in (RunStatus.completed, RunStatus.failed):
            newly_completed.append(rid)
        else:
            still_active.append(rid)

    if still_active:
        st.subheader("Active crawls")
        for rid in still_active:
            _render_run_card(rid, is_active=True)
        has_active = True

    for rid in newly_completed:
        if rid not in st.session_state.completed_runs:
            st.session_state.completed_runs.insert(0, rid)

    st.session_state.active_runs = still_active

# ---------------------------------------------------------------------------
# Completed crawls from this session
# ---------------------------------------------------------------------------

if st.session_state.completed_runs:
    st.subheader("Completed this session")
    for rid in st.session_state.completed_runs:
        _render_run_card(rid, is_active=False)

# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Recent crawl history")
history = repo.list_runs(limit=20)
if not history:
    st.info("No prior crawls yet.")
else:
    rows = []
    for r in history:
        status_html = (
            f'<span class="badge badge-{r.status.value}">{r.status.value}</span>'
        )
        rows.append(
            {
                "Host": r.hostname,
                "Status": r.status.value,
                "Score": f"{r.score:.1%}" if r.score is not None else "--",
                "Created": r.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )
    st.dataframe(rows, use_container_width=True)

# ---------------------------------------------------------------------------
# Auto-refresh while crawls are active
# ---------------------------------------------------------------------------

if has_active:
    time.sleep(1)
    st.rerun()
