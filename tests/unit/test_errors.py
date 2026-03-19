from __future__ import annotations

from uuid import UUID

from crawllmer.core import (
    ContentExtractionError,
    CrawlFetchError,
    CrawllmerError,
    GenerationError,
    InvalidInputError,
    MissingConfigError,
    PipelineProcessingError,
    RunNotFoundError,
)


class TestCrawllmerErrorHierarchy:
    """All custom errors inherit from CrawllmerError."""

    def test_all_errors_inherit_from_base(self) -> None:
        assert issubclass(MissingConfigError, CrawllmerError)
        assert issubclass(InvalidInputError, CrawllmerError)
        assert issubclass(RunNotFoundError, CrawllmerError)
        assert issubclass(PipelineProcessingError, CrawllmerError)
        assert issubclass(CrawlFetchError, CrawllmerError)
        assert issubclass(ContentExtractionError, CrawllmerError)
        assert issubclass(GenerationError, CrawllmerError)

    def test_broad_catch_works(self) -> None:
        for exc in [
            MissingConfigError("x"),
            InvalidInputError("url", "bad"),
            RunNotFoundError(UUID(int=0)),
            CrawlFetchError("http://x", 404),
            ContentExtractionError("http://x", "oops"),
            GenerationError(UUID(int=0), "oops"),
        ]:
            try:
                raise exc
            except CrawllmerError:
                pass  # expected


class TestMissingConfigError:
    def test_stores_field_name(self) -> None:
        exc = MissingConfigError("db_url")
        assert exc.field_name == "db_url"

    def test_message(self) -> None:
        exc = MissingConfigError("db_url")
        assert str(exc) == "missing or invalid config: db_url"


class TestInvalidInputError:
    def test_stores_attributes(self) -> None:
        exc = InvalidInputError("url", "no scheme")
        assert exc.field == "url"
        assert exc.reason == "no scheme"

    def test_message(self) -> None:
        exc = InvalidInputError("url", "no scheme")
        assert str(exc) == "invalid url: no scheme"


class TestRunNotFoundError:
    def test_stores_run_id(self) -> None:
        rid = UUID(int=42)
        exc = RunNotFoundError(rid)
        assert exc.run_id == rid

    def test_message(self) -> None:
        rid = UUID(int=42)
        assert "run not found" in str(RunNotFoundError(rid))


class TestPipelineProcessingError:
    def test_stores_attributes(self) -> None:
        cause = RuntimeError("boom")
        rid = UUID(int=1)
        exc = PipelineProcessingError("discovery", rid, cause)
        assert exc.stage == "discovery"
        assert exc.run_id == rid
        assert exc.__cause__ is cause

    def test_message(self) -> None:
        exc = PipelineProcessingError("extraction", UUID(int=1), ValueError("x"))
        assert "extraction" in str(exc)
        assert "x" in str(exc)


class TestCrawlFetchError:
    def test_with_status_code(self) -> None:
        exc = CrawlFetchError("http://x.com", status_code=503)
        assert exc.url == "http://x.com"
        assert exc.status_code == 503
        assert "503" in str(exc)

    def test_with_reason(self) -> None:
        exc = CrawlFetchError("http://x.com", reason="timeout")
        assert exc.status_code is None
        assert "timeout" in str(exc)


class TestContentExtractionError:
    def test_stores_attributes(self) -> None:
        exc = ContentExtractionError("http://x.com/page", "malformed html")
        assert exc.url == "http://x.com/page"
        assert exc.reason == "malformed html"
        assert "malformed html" in str(exc)


class TestGenerationError:
    def test_stores_attributes(self) -> None:
        rid = UUID(int=5)
        exc = GenerationError(rid, "zero pages")
        assert exc.run_id == rid
        assert exc.reason == "zero pages"
        assert "zero pages" in str(exc)
