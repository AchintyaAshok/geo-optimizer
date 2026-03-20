from __future__ import annotations

from datetime import UTC, datetime

import httpx
import streamlit as st

from crawllmer.app.web.runtime import client
from crawllmer.core.config import get_settings

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="crawllmer", layout="wide")

STAGES = ["discovery", "extraction", "canonicalization", "scoring", "generation"]
STAGE_LABELS = {
    "discovery": "Discovery",
    "extraction": "Extraction",
    "canonicalization": "Canonicalize",
    "scoring": "Scoring",
    "generation": "Generation",
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
    /* ---- refresh indicator ---- */
    .refresh-bar {
        display: flex; align-items: center; gap: 8px;
        padding: 4px 0; font-size: .75rem; color: #9ca3af;
    }
    .refresh-dot {
        display: inline-block; width: 6px; height: 6px;
        border-radius: 50%; background: #22c55e;
    }
    .refresh-dot-idle { background: #6b7280; }
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
# Session state
# ---------------------------------------------------------------------------

if "selected_run" not in st.session_state:
    st.session_state.selected_run: str | None = None

_settings = get_settings()
RECENT_HOURS = 24


# ---------------------------------------------------------------------------
# Helpers (work with dicts from the API)
# ---------------------------------------------------------------------------


def _elapsed(iso_str: str) -> str:
    start = datetime.fromisoformat(iso_str)
    now = datetime.now(UTC)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    secs = int((now - start).total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s"
    return f"{secs // 3600}h {(secs % 3600) // 60}m"


def _item_duration(item: dict) -> str:
    start = datetime.fromisoformat(item["created_at"])
    end = datetime.fromisoformat(item["updated_at"])
    ms = int((end - start).total_seconds() * 1000)
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _stage_state(stage: str, items: list[dict]) -> str:
    stage_items = [i for i in items if i["stage"] == stage]
    if not stage_items:
        return "pending"
    states = {i["state"] for i in stage_items}
    if "failed" in states:
        return "failed"
    if "processing" in states:
        return "active"
    if "completed" in states:
        return "done"
    return "pending"


def _current_stage_label(items: list[dict]) -> str:
    for stage in reversed(STAGES):
        state = _stage_state(stage, items)
        if state in ("active", "done", "failed"):
            icon = {"active": "\u25b6", "done": "\u2713", "failed": "\u2717"}[state]
            return f"{icon} {STAGE_LABELS[stage]}"
    return "queued"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_stage_bar(items: list[dict]) -> None:
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


def _render_timeline(items: list[dict]) -> None:
    seen: dict[str, dict] = {}
    for item in items:
        existing = seen.get(item["stage"])
        if existing is None or item["state"] != "queued":
            seen[item["stage"]] = item

    icon_map = {
        "completed": "&#10003;",
        "failed": "&#10007;",
        "processing": "&#9654;",
        "queued": "&#9675;",
    }

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

        icon = icon_map.get(item["state"], "&#9675;")
        dur = _item_duration(item)
        err = (
            f'<span class="tl-err">{item["last_error"]}</span>'
            if item.get("last_error")
            else ""
        )
        st.markdown(
            '<div class="tl-row">'
            f'<span class="tl-icon">{icon}</span>'
            f'<span class="tl-stage">{STAGE_LABELS[stage]}</span>'
            f'<span class="tl-dur">{dur}</span>{err}</div>',
            unsafe_allow_html=True,
        )


RECENT_EVENT_COUNT = 8


def _event_row_html(ev: dict) -> str:
    started = ev.get("started_at", "")
    time_str = started[11:19] if len(started) >= 19 else "--"

    dur_str = ""
    dur = ev.get("duration")
    if dur is not None:
        ms = int(dur * 1000)
        dur_str = f"{ms}ms" if ms < 1000 else f"{ms / 1000:.1f}s"

    meta = ev.get("metadata", {})
    meta_parts = []
    for k, v in meta.items():
        val = str(v)
        if len(val) > 60:
            val = val[:57] + "..."
        meta_parts.append(f"{k}={val}")
    meta_str = " ".join(meta_parts)

    return (
        '<div class="ev-row">'
        f'<span class="ev-time">{time_str}</span>'
        f'<span class="ev-name">{ev.get("name", "")}</span>'
        f'<span class="ev-sys">{ev.get("system", "")}</span>'
        f'<span class="ev-dur">{dur_str}</span>'
        f'<span class="ev-meta">{meta_str}</span>'
        "</div>"
    )


def _render_events(events: list[dict], *, is_active: bool) -> None:
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

    recent = list(reversed(events[-RECENT_EVENT_COUNT:]))
    st.markdown(
        "\n".join(_event_row_html(ev) for ev in recent),
        unsafe_allow_html=True,
    )

    if len(events) > RECENT_EVENT_COUNT:
        with st.expander(f"All {len(events)} events"):
            table_rows = []
            for ev in reversed(events):
                started = ev.get("started_at", "")
                dur = ev.get("duration")
                dur_ms = round(dur * 1000) if dur else None
                meta = ev.get("metadata", {})
                meta_str = ", ".join(f"{k}={str(v)[:80]}" for k, v in meta.items())
                table_rows.append(
                    {
                        "Time": started[11:19] if len(started) >= 19 else "",
                        "Event": ev.get("name", ""),
                        "System": ev.get("system", ""),
                        "Duration (ms)": dur_ms,
                        "Details": meta_str,
                    }
                )
            st.dataframe(
                table_rows,
                use_container_width=True,
                hide_index=True,
            )


def _render_llms_txt(artifact_text: str, run_id_str: str) -> None:
    lines = artifact_text.splitlines()
    line_count = len(lines)
    word_count = len(artifact_text.split())

    st.caption(f"{line_count} lines \u00b7 {word_count:,} words")

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
    run = client.get_run(run_id_str)
    if run is None:
        st.warning("Run not found.")
        return

    items = client.get_work_items(run_id_str)
    status = run.get("status", "unknown")
    status_class = f"badge-{status}"

    # Header
    host = run.get("host", run.get("run_id", "?"))
    st.markdown(
        f'<div class="detail-header">{host}</div>',
        unsafe_allow_html=True,
    )
    col_badge, col_time = st.columns([1, 3])
    with col_badge:
        st.markdown(
            f'<span class="badge {status_class}">{status}</span>',
            unsafe_allow_html=True,
        )
    with col_time:
        created = run.get("created_at")
        if created:
            st.caption(f"Started {_elapsed(created)} ago")

    # Stage bar
    _render_stage_bar(items)

    # Score metrics (completed only)
    if status == "completed":
        st.markdown("---")
        mcols = st.columns(4)
        bd = run.get("score_breakdown") or {}
        mcols[0].metric(
            "Overall",
            f"{(run.get('score') or 0):.1%}",
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
    if status == "failed":
        st.error("Crawl failed")

    # llms.txt
    if status == "completed":
        llms_txt = client.get_llms_txt(run_id_str)
        if llms_txt:
            st.markdown("---")
            _render_llms_txt(llms_txt, run_id_str)

    # Timeline
    st.markdown("---")
    st.caption("Pipeline timeline")
    _render_timeline(items)

    # Events
    is_active = status in ("queued", "running")
    events = client.get_events(run_id_str)
    if events or is_active:
        st.markdown("---")
        _render_events(events, is_active=is_active)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _fetch_runs() -> tuple[list[dict], list[dict], list[dict], bool]:
    """Query all runs via API and classify into active / recent / history."""
    try:
        all_runs = client.list_runs(limit=50)
    except httpx.HTTPError:
        st.error("Could not reach API. Is the server running?")
        return [], [], [], False

    active: list[dict] = []
    history: list[dict] = []

    for run in all_runs:
        status = run.get("status", "")
        if status in ("queued", "running"):
            active.append(run)
        else:
            history.append(run)

    return active, [], history, len(active) > 0


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
                result = client.enqueue_crawl(url)
                st.session_state.selected_run = result["run_id"]
                st.rerun()
            except httpx.HTTPStatusError as exc:
                st.error(f"Error: {exc.response.text}")
            except httpx.HTTPError as exc:
                st.error(f"Could not reach API: {exc}")

    # --- Run list helper ---
    def _run_button(
        run: dict, *, key_prefix: str, items: list[dict] | None = None
    ) -> None:
        run_id = run["run_id"]
        is_selected = st.session_state.selected_run == run_id

        score = run.get("score")
        score_str = f"  {score:.0%}" if score is not None else ""
        stage_str = ""
        if items:
            stage_str = f"  {_current_stage_label(items)}"

        status = run.get("status", "")
        status_icons = {
            "completed": "\u2713",
            "failed": "\u2717",
            "running": "\u25b6",
            "queued": "\u25cb",
        }
        icon = status_icons.get(status, "\u25cb")
        host = run.get("host", "?")
        label = f"{icon}  {host}{score_str}{stage_str}"

        if st.button(
            label,
            key=f"{key_prefix}-{run_id}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state.selected_run = run_id
            st.rerun()

    # ---- Auto-refreshing run list fragment ----
    @st.fragment(run_every=_settings.ui_refresh_seconds)
    def _run_list_fragment() -> None:
        active_runs, recent_runs, history_runs, has_active = _fetch_runs()

        # Refresh indicator
        updated_at = datetime.now(UTC).strftime("%H:%M:%S")
        dot_cls = "refresh-dot" if has_active else "refresh-dot refresh-dot-idle"
        label = "Auto-refreshing" if has_active else "Up to date"
        ind_col, ref_btn_col = st.columns([3, 1])
        with ind_col:
            st.markdown(
                f'<div class="refresh-bar">'
                f'<span class="{dot_cls}"></span> {label} \u00b7 {updated_at}'
                f"</div>",
                unsafe_allow_html=True,
            )
        with ref_btn_col:
            if st.button("Refresh", key="refresh-btn", use_container_width=True):
                st.rerun(scope="fragment")

        # Active runs
        if active_runs:
            st.caption("ACTIVE")
            for run in active_runs:
                work_items = client.get_work_items(run["run_id"])
                _run_button(run, key_prefix="active", items=work_items)

        # History (all non-active)
        if history_runs:
            st.caption("HISTORY")
            for run in history_runs:
                _run_button(run, key_prefix="hist")

    _run_list_fragment()

# ---- RIGHT: detail panel ----
with col_detail:

    @st.fragment(run_every=_settings.ui_refresh_seconds)
    def _detail_fragment() -> None:
        if st.session_state.selected_run:
            _render_detail_panel(st.session_state.selected_run)
        else:
            st.markdown(
                "<div style='text-align:center; padding: 80px 20px; "
                "color: #9ca3af;'>"
                "<p style='font-size: 1.2rem;'>"
                "Select a crawl to view details</p></div>",
                unsafe_allow_html=True,
            )

    _detail_fragment()
