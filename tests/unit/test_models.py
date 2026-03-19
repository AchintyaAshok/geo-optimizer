from datetime import UTC, datetime, timedelta

from crawllmer.domain.models import (
    CrawlEvent,
    LlmsTxtDocument,
    LlmsTxtEntry,
    WorkItem,
    WorkItemState,
)


def test_work_item_allows_valid_transitions() -> None:
    item = WorkItem()
    item.transition(WorkItemState.processing)
    item.transition(WorkItemState.completed)
    assert item.state == WorkItemState.completed


def test_work_item_rejects_invalid_transition() -> None:
    item = WorkItem()
    try:
        item.transition(WorkItemState.completed)
    except ValueError as exc:
        assert "invalid transition" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_crawl_event_duration_is_derived() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    event = CrawlEvent(
        name="stage.discovery",
        system="discovery",
        started_at=start,
        completed_at=start + timedelta(seconds=2.5),
    )
    assert event.duration == 2.5


def test_crawl_event_duration_is_none_when_not_completed() -> None:
    event = CrawlEvent(name="stage.discovery", system="discovery")
    assert event.duration is None


def test_llms_txt_document_serialization_is_deterministic() -> None:
    document = LlmsTxtDocument(
        source_url="https://example.com",
        title="Example Site",
        site_description="An example website.",
        pages_crawled=2,
        links_discovered=5,
        sections={
            "Pages": [
                LlmsTxtEntry(title="B", url="https://example.com/b"),
                LlmsTxtEntry(title="A", url="https://example.com/a"),
            ],
        },
    )

    text = document.to_text()
    lines = text.splitlines()

    # H1 title
    assert lines[0] == "# Example Site"
    # Blockquote contains metadata
    assert "example.com" in text
    assert "**Pages crawled**: 2" in text
    assert "**Links discovered**: 5" in text
    assert "**Website Description**: An example website." in text
    # H2 section
    assert "## Pages" in text
    # Entries sorted within section
    pages_idx = lines.index("## Pages")
    assert lines[pages_idx + 2].startswith("- [A](https://example.com/a)")
    assert lines[pages_idx + 3].startswith("- [B](https://example.com/b)")
