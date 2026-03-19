---
parent_prd: ../prd-007-fallback-link-following-crawler/prd.md
prd_name: "PRD 007: Fallback Link-Following Crawler"
prd_id: 007
task_id: 004
created: 2026-03-19
state: pending
---

# Task 004: Implement BFS spider scan

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

Create `app/indexer/spider.py` implementing Phase 1 of the two-phase spider: a BFS scan that builds a link graph, counts in-links, tracks depth, and returns a priority-ordered list of URLs ranked by importance (in-link count descending, depth ascending).

## Inputs

- `app/indexer/link_filter.py` from Task 003 (extract_same_domain_links)
- Spider config settings from Task 002 (spider_max_depth, spider_max_scan_pages, spider_timeout_per_page)
- HTTP fetching capability (httpx, already a project dependency)

## Outputs

- `src/crawllmer/app/indexer/spider.py` with `spider_scan(seed_url, max_depth, max_scan_pages, timeout_per_page, include_extensions)` function
- Returns a priority-ordered list of `(url, inlink_score, depth)` tuples
- Unit tests in `tests/unit/test_spider.py`

## Steps

1. Create `src/crawllmer/app/indexer/spider.py`
2. Implement `spider_scan(seed_url, max_depth, max_scan_pages, timeout_per_page, include_extensions)`:
   - Initialise `visited: set`, `queue: deque[(url, depth)]`, `inlink_count: Counter`, `depth_map: dict`
   - BFS loop: pop from queue, skip if visited or depth > max_depth, mark visited, fetch HTML via httpx
   - Call `extract_same_domain_links` to get outbound links
   - For each unvisited link: increment its in-link count, append to queue with depth+1
   - Stop when queue is empty or `len(visited) >= max_scan_pages`
   - Handle fetch errors gracefully (log and skip, don't crash the scan)
   - Rank visited URLs: sort by `-inlink_count[url]` then by `depth_map[url]` ascending
   - Return the ranked list
3. Write unit tests with mocked HTTP responses (use `respx` or `unittest.mock.patch`):
   - Basic 3-page site: seed links to A and B, verify both discovered
   - In-link ranking: page linked from 3 pages ranks higher than page linked from 1
   - Depth limit: pages beyond max_depth are not visited
   - Page limit: scanning stops at max_scan_pages
   - Fetch failure: one page returns 500, scan continues with remaining URLs
   - Seed URL with no links returns only the seed
4. Run `make check`

## Done Criteria

- [ ] `spider.py` exists at `src/crawllmer/app/indexer/spider.py`
- [ ] BFS traversal respects `max_depth` and `max_scan_pages` limits
- [ ] URLs are ranked by in-link count (descending), with depth as tiebreaker (ascending)
- [ ] Fetch errors are handled gracefully without crashing the scan
- [ ] `extract_same_domain_links` from `link_filter.py` is used for href extraction
- [ ] Unit tests pass with mocked HTTP responses
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
