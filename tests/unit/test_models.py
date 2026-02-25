from crawllmer.domain.models import WorkItem, WorkItemState


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
