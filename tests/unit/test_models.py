from crawllmer.domain.models import LlmsTxtDocument, LlmsTxtEntry


def test_llms_txt_is_deterministic() -> None:
    doc = LlmsTxtDocument(
        source_url="https://example.com",
        entries=[
            LlmsTxtEntry(title="B", url="https://example.com/b"),
            LlmsTxtEntry(title="A", url="https://example.com/a"),
        ],
    )

    output = doc.to_text()

    assert output.splitlines()[2].startswith("- [A](https://example.com/a)")
    assert output.splitlines()[3].startswith("- [B](https://example.com/b)")
