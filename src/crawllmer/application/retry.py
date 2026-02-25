from __future__ import annotations

from dataclasses import dataclass
from time import sleep


@dataclass(slots=True)
class RetryPolicy:
    retries: int = 2
    base_delay_seconds: float = 0.05
    backoff_multiplier: float = 2.0

    def run(self, fn):
        delay = self.base_delay_seconds
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == self.retries:
                    break
                sleep(delay)
                delay *= self.backoff_multiplier
        if last_error:
            raise last_error
        raise RuntimeError("retry policy exhausted without executing function")
