"""Legacy strategy module kept for compatibility.

The queue-driven pipeline now lives under ``crawllmer.application.workers``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StrategyNote:
    name: str
    description: str


SUPPORTED_STRATEGIES = [
    StrategyNote(
        name="direct_llms", description="Read /llms.txt directly when present."
    ),
    StrategyNote(
        name="robots_hints",
        description="Use robots.txt hints for llms/sitemap discovery.",
    ),
    StrategyNote(
        name="sitemap", description="Traverse sitemap and sitemap index resources."
    ),
    StrategyNote(
        name="fallback", description="Bounded fallback to the root target URL."
    ),
]
