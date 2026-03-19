from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic, sleep


@dataclass(slots=True)
class HostRateLimiter:
    """Simple host-aware pacing controller.

    `wait()` enforces a minimum delay between consecutive requests to the same host.
    `penalize()` pushes the next allowed time forward after host-side throttling.
    """

    per_host_delay_seconds: float = 0.01
    adaptive_penalty_seconds: float = 0.05
    _last_seen: dict[str, float] = field(default_factory=dict)

    def wait(self, host: str) -> None:
        """Block until per-host minimum delay has elapsed."""
        now = monotonic()
        last = self._last_seen.get(host)
        if last is not None:
            wait_for = self.per_host_delay_seconds - (now - last)
            if wait_for > 0:
                sleep(wait_for)
        self._last_seen[host] = monotonic()

    def penalize(self, host: str) -> None:
        """Apply adaptive slowdown for a host after transient throttling."""
        self._last_seen[host] = monotonic() + self.adaptive_penalty_seconds
