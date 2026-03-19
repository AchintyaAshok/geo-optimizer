"""Typed exception hierarchy for crawllmer.

Every module should raise one of these instead of generic ``Exception`` or
``ValueError``.  The sole approved exception is ``retry.py``, which must
catch bare ``Exception`` by design.
"""

from __future__ import annotations

from uuid import UUID


class CrawllmerError(Exception):
    """Base exception for all crawllmer errors.

    All project-specific exceptions inherit from this class so callers
    can catch broadly when they don't need to distinguish failure modes.
    """


class MissingConfigError(CrawllmerError):
    """A required configuration value is absent or empty.

    Raised when a module attempts to use a Settings field that has no
    usable value — either because the environment variable was never set
    and there is no default, or because the value is present but invalid
    for the module's needs (e.g. an empty string where a URL is required).
    """

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(f"missing or invalid config: {field_name}")


class InvalidInputError(CrawllmerError):
    """User-supplied input fails validation.

    Raised at the API / pipeline boundary when input data cannot be
    processed — for example, a malformed URL passed to enqueue_run().
    Replaces the generic ValueError currently used for input validation.
    """

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"invalid {field}: {reason}")


class RunNotFoundError(CrawllmerError):
    """A requested crawl run does not exist in the repository.

    Raised when a run_id is passed to process_run(), get_run(), or any
    operation that requires an existing run, but no matching record is
    found.  Distinct from InvalidInputError because the input format is
    valid — the resource simply doesn't exist.
    """

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        super().__init__(f"run not found: {run_id}")


class PipelineProcessingError(CrawllmerError):
    """A named pipeline stage failed during execution.

    Raised by the orchestrator when a stage (discovery, extraction,
    canonicalization, scoring, or generation) encounters an unrecoverable
    error after retries are exhausted.  Wraps the original exception as
    ``__cause__`` so the full error chain is preserved for debugging.
    """

    def __init__(self, stage: str, run_id: UUID, cause: Exception) -> None:
        self.stage = stage
        self.run_id = run_id
        super().__init__(f"stage '{stage}' failed for run {run_id}: {cause}")
        self.__cause__ = cause


class CrawlFetchError(CrawllmerError):
    """An HTTP request to a target website failed.

    Raised during the discovery or extraction stages when an HTTP request
    returns an unexpected status code, times out, or encounters a
    connection error.  Carries the URL and status code (if available) so
    callers can decide whether to retry, skip, or abort.
    """

    def __init__(
        self, url: str, status_code: int | None = None, reason: str = ""
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.reason = reason
        detail = f"status {status_code}" if status_code else reason
        super().__init__(f"fetch failed for {url}: {detail}")


class ContentExtractionError(CrawllmerError):
    """HTML or metadata parsing failed for a fetched page.

    Raised when a page was successfully fetched (HTTP 200) but the
    content could not be parsed — for example, malformed HTML that
    crashes BeautifulSoup, or a page that returns non-HTML content
    (PDF, image) despite a text/html Content-Type header.
    """

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"extraction failed for {url}: {reason}")


class GenerationError(CrawllmerError):
    """llms.txt assembly failed after extraction completed.

    Raised during the generation stage when the extracted pages cannot
    be assembled into a valid llms.txt document — for example, if zero
    pages survived canonicalization, or if the document builder
    encounters an internal inconsistency.
    """

    def __init__(self, run_id: UUID, reason: str) -> None:
        self.run_id = run_id
        self.reason = reason
        super().__init__(f"generation failed for run {run_id}: {reason}")
