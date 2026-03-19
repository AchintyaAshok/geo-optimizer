---
parent_prd: ../prd-007-fallback-link-following-crawler/prd.md
prd_name: "PRD 007: Fallback Link-Following Crawler"
prd_id: 007
task_id: 003
created: 2026-03-19
state: pending
---

# Task 003: Implement link filter

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 007: Fallback Link-Following Crawler](../prd.md) |
| Created | 2026-03-19 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |

## Objective

Create `app/indexer/link_filter.py` implementing a BeautifulSoup-based same-domain link extractor with extension allowlist filtering and non-content path rejection, suitable for use by the BFS spider.

## Inputs

- Spider config settings from Task 002 (`spider_include_extensions`)
- PRD link extraction pseudocode and `NON_CONTENT_PATHS` list
- BeautifulSoup (already a project dependency)

## Outputs

- `src/crawllmer/app/indexer/link_filter.py` with `extract_same_domain_links(html, base_url, hostname, include_extensions)` function
- `NON_CONTENT_PATHS` constant: `login`, `signup`, `cart`, `admin`, `wp-admin`, `wp-login`, `logout`, `register`
- Unit tests in `tests/unit/test_link_filter.py`

## Steps

1. Create `src/crawllmer/app/indexer/link_filter.py`
2. Define `NON_CONTENT_PATHS` frozenset with the eight non-content path segments
3. Implement `extract_same_domain_links(html, base_url, hostname, include_extensions)`:
   - Parse HTML with `BeautifulSoup(html, "html.parser")`
   - Find all `<a href=...>` tags
   - Resolve relative URLs with `urljoin(base_url, href)`
   - Reject cross-domain links (parsed netloc != hostname)
   - Strip URL fragments
   - Filter by extension allowlist (skip URLs whose extension is not in the list; empty extension matches extensionless paths)
   - Filter out URLs containing non-content path segments
   - Deduplicate and return the list
4. Write unit tests covering:
   - Same-domain links are extracted; cross-domain links are rejected
   - Fragment stripping works (`/page#section` becomes `/page`)
   - Extension filtering: `.html` passes, `.css`/`.js`/`.png` are rejected, extensionless paths pass
   - Non-content paths (`/login`, `/admin`, `/wp-admin`) are rejected
   - Relative URLs are resolved correctly
   - Malformed hrefs (empty, javascript:, mailto:) are handled gracefully
5. Run `make check`

## Done Criteria

- [ ] `link_filter.py` exists at `src/crawllmer/app/indexer/link_filter.py`
- [ ] `extract_same_domain_links` correctly extracts and filters links per the PRD rules
- [ ] Non-content path segments are rejected
- [ ] Extension allowlist filtering works, including extensionless path support
- [ ] Unit tests pass for all filtering scenarios
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
