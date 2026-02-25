from crawllmer.application.workers import _extract_description, _extract_title


def test_extracts_title_and_description_from_head_meta() -> None:
    html = (
        "<html><head><title>Title A</title>"
        '<meta name="description" content="Desc A" /></head><body>'
        '<title>Wrong Body Title</title><meta name="description" content="Nope" />'
        "</body></html>"
    )

    title, title_source, title_conf = _extract_title(html)
    desc, desc_source, desc_conf = _extract_description(html)

    assert title == "Title A"
    assert title_source == "title"
    assert title_conf == 1.0
    assert desc == "Desc A"
    assert desc_source == "meta:description"
    assert desc_conf == 1.0


def test_extracts_fallbacks_from_head_only() -> None:
    html = (
        "<html><head>"
        '<meta property="twitter:title" content="Tw Title" />'
        '<meta property="twitter:description" content="Tw Desc" />'
        "</head><body></body></html>"
    )

    title, title_source, _ = _extract_title(html)
    desc, desc_source, _ = _extract_description(html)

    assert title == "Tw Title"
    assert title_source == "twitter:title"
    assert desc == "Tw Desc"
    assert desc_source == "twitter:description"


def test_extracts_jsonld_from_head() -> None:
    html = (
        "<html><head>"
        '<script type="application/ld+json">'
        '{"headline": "Head JsonLD", "description": "Head JsonLD Desc"}'
        "</script></head><body></body></html>"
    )

    title, title_source, _ = _extract_title(html)
    desc, desc_source, _ = _extract_description(html)

    assert title == "Head JsonLD"
    assert title_source == "jsonld:headline"
    assert desc == "Head JsonLD Desc"
    assert desc_source == "jsonld:description"
