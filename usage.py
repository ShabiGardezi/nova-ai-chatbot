"""Token usage tracking and cost estimation.

Provider agnostic: token counts come straight from the API response's
``usage`` field (when the provider returns one), and cost is derived from
per-1k prices supplied by the caller. Providers that omit usage simply
yield ``None`` and providers with no pricing report a $0 estimate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token counts for a single request."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @classmethod
    def from_response(cls, usage: Any | None) -> "TokenUsage | None":
        """Build usage from an API ``usage`` object, or ``None`` if absent."""
        if usage is None:
            return None

        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        total = int(getattr(usage, "total_tokens", 0) or 0) or (prompt + completion)

        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )

    def cost(
        self,
        prompt_cost_per_1k: float,
        completion_cost_per_1k: float,
    ) -> float:
        """Approximate request cost from per-1k token prices."""
        return (
            self.prompt_tokens / 1000 * prompt_cost_per_1k
            + self.completion_tokens / 1000 * completion_cost_per_1k
        )
