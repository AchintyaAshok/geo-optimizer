# llms.txt Generation

This guide explains how crawllmer generates spec-compliant [llms.txt](https://llmstxt.org/) files, including the output structure, section grouping logic, and known caveats.

## Output Structure

The generated file follows the llmstxt.org specification:

```markdown
# Site Title

> Navigational prompt for LLMs explaining the file structure,
> listing all available sections, and providing generation metadata.
>
> - **Generated**: 2026-03-19 12:23 UTC
> - **Pages crawled**: 1095
> - **Links discovered**: 1097
>
> **Website Description**: Description from the homepage meta tag.

## Docs

- [Getting Started](https://example.com/docs/getting-started): How to install and configure the project.
- [API Reference](https://example.com/docs/api): Complete API documentation.

## Blog

- [Announcing v2](https://example.com/blog/v2): Major release announcement.
```

### H1 — Site Title

Extracted from the homepage's `<title>` tag. Falls back to the hostname if no title is found (common for SPAs or sites that return raw markdown).

### Blockquote — Summary

The blockquote serves as a navigational prompt for LLMs. It contains:

1. **Prose description**: A human-readable paragraph explaining what the file is, that it groups pages by topic, and listing all section names so the LLM can jump to the right section.
2. **Generation metadata**: Date, number of pages crawled, number of links discovered.
3. **Website description** (if available): Pulled from the homepage's `meta[name=description]` or `og:description` tag.

### H2 Sections — Grouped by Top-Level Path

Pages are grouped into sections based on their **first URL path segment**:

| URL | First Segment | Section Name |
|-----|--------------|--------------|
| `https://example.com/docs/intro` | `docs` | Docs |
| `https://example.com/blog/post-1` | `blog` | Blog |
| `https://example.com/api/v1/users` | `api` | Api |
| `https://example.com/guide/setup` | `guide` | Guide |
| `https://example.com/` | (root) | Home |
| `https://other-domain.com/page` | (external) | External |

Section names are derived by title-casing the first path segment. Hyphens and underscores become spaces (e.g., `getting-started` → `Getting Started`).

### Link Format

Each entry uses standard markdown link syntax with an optional description:

```markdown
- [Page Title](https://url): Description from meta tags.
```

- **Title**: From `<title>`, `og:title`, `twitter:title`, or `jsonld:headline` (in priority order).
- **Description**: From `meta[name=description]`, `og:description`, `twitter:description`, or `jsonld:description`.
- If no title is found, the raw URL is used as the link text.

### Excluded Paths

The following first-segment prefixes are excluded from the output entirely, as they typically serve duplicate or non-content resources:

- `raw` — Raw markdown mirrors of rendered pages
- `assets`, `static` — Static files (images, CSS, JS)
- `_next`, `_nuxt`, `__` — Framework build artifacts

## Caveats and Known Limitations

### 1. Flat Section Grouping

The current implementation groups by the **first path segment only**. This means deeply nested URL structures get rolled up into a single large section.

**Example — nuxt.com**:

All of these URLs produce a single `## Docs` section:

```
https://nuxt.com/docs/3.x/getting-started/introduction
https://nuxt.com/docs/3.x/api/composables/use-fetch
https://nuxt.com/docs/4.x/getting-started/installation
https://nuxt.com/docs/4.x/api/components/nuxt-link
```

This results in a `## Docs` section with hundreds of entries and no sub-grouping by version or topic. For a site like nuxt.com (1095 pages, most under `/docs/`), the Docs section alone can have 900+ entries.

**Potential extension**: Generate hierarchical sub-headings based on the URL structure. For nuxt.com this would produce:

```markdown
## Docs

### 3.x

#### Getting Started
- [Introduction](https://nuxt.com/docs/3.x/getting-started/introduction): ...

#### Api
- [useFetch](https://nuxt.com/docs/3.x/api/composables/use-fetch): ...

### 4.x

#### Getting Started
- [Installation](https://nuxt.com/docs/4.x/getting-started/installation): ...
```

This would require a configurable depth parameter (e.g., group by first 2 or 3 path segments) and logic to avoid creating sections with only 1-2 entries.

### 2. Markdown Content Extraction

Many llms.txt files link to `.md` URLs (e.g., `https://vite.dev/guide/api-plugin.md`). Our extractor treats all responses as HTML and looks for `<head>` metadata tags. When a server returns raw markdown, the HTML parser finds no `<title>` or `<meta>` tags, resulting in:

- No title (falls back to the raw URL as link text)
- No description
- 0.0 confidence score

This is why vite.dev scores only 4.5% coverage — its llms.txt links to `.md` files that return raw markdown, not rendered HTML.

**Potential extension**: Detect `Content-Type: text/markdown` or `.md` file extensions and parse the first `# Heading` as the title and the first paragraph as the description.

### 3. Homepage Metadata Dependency

The site title and description in the blockquote come from the homepage's HTML metadata. This fails when:

- The homepage is an SPA that renders client-side (no server-rendered `<title>`)
- The site returns a redirect (e.g., `example.com` → `example.com/en/`)
- The homepage isn't included in the discovered URLs

In these cases, the title falls back to the hostname and the description is omitted.

### 4. No Semantic Grouping

Sections are derived purely from URL structure, not from content semantics. A site that puts tutorials at `/tutorials/` and guides at `/guides/` gets two separate sections even though they're conceptually similar. Conversely, a site that puts everything under `/pages/` gets one massive section.

**Potential extension**: Use page titles or descriptions to cluster pages by topic rather than URL path.

### 5. External Links

Links to other domains (e.g., MDN documentation referenced in vite.dev's llms.txt) are grouped into an `## External` section. These are included because they were discovered through the site's own llms.txt or sitemap, but they may not be relevant to the site itself.

## Implementation Reference

- **Model**: `LlmsTxtDocument` in `src/crawllmer/domain/models.py`
- **Generation**: `generate_llms_txt()` in `src/crawllmer/application/workers.py`
- **Section logic**: `_section_name_from_url()` in the same file
- **Orchestrator call**: `run_generation()` in `src/crawllmer/application/orchestrator.py`
