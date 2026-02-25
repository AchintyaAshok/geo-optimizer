from __future__ import annotations

import streamlit as st

from crawllmer.web.runtime import repo, run_crawl

st.set_page_config(page_title="crawllmer", layout="wide")
st.title("crawllmer")
st.caption("Discover or generate llms.txt from a target website")

with st.form("crawl-form"):
    url = st.text_input("Website URL", placeholder="https://example.com")
    submitted = st.form_submit_button("Crawl")

if submitted:
    if not url:
        st.error("Please provide a URL.")
    else:
        with st.spinner("Running crawl strategies..."):
            run, result = run_crawl(url)
        st.success(f"Run complete: {run.status}")
        st.subheader("Run details")
        st.json(
            {
                "run_id": str(run.id),
                "status": run.status,
                "strategy_attempts": run.strategy_attempts,
                "diagnostics": run.diagnostics,
            }
        )
        if result and result.document:
            llms_txt = result.document.to_text()
            st.subheader("Generated llms.txt")
            st.code(llms_txt, language="text")
            st.download_button(
                "Download llms.txt",
                data=llms_txt,
                file_name="llms.txt",
                mime="text/plain",
            )

st.divider()
st.subheader("Recent crawl history")
history = repo.latest_runs(limit=20)
if not history:
    st.info("No prior crawls yet.")
else:
    rows = [
        {
            "run_id": str(run.id),
            "host": run.target.hostname,
            "status": run.status,
            "attempts": ", ".join(run.strategy_attempts),
        }
        for run in history
    ]
    st.dataframe(rows, use_container_width=True)
