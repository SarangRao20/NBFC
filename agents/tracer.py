"""Lightweight span-based tracing for LangGraph nodes.

Each node emits a Span into state["trace_events"]. These are:
- Stored in MongoDB per session for analytics
- Surfaced in the frontend action_log in human-readable form
- Machine-readable for latency dashboards and error rate tracking
"""

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Span:
    node: str
    phase: str = "unknown"
    ts_start: float = field(default_factory=time.time)
    ts_end: Optional[float] = None
    duration_ms: Optional[float] = None
    intent: Optional[str] = None
    decision: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def end(self, **kwargs) -> "Span":
        self.ts_end = time.time()
        self.duration_ms = round((self.ts_end - self.ts_start) * 1000, 1)
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                self.meta[k] = v
        return self

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != {}}

    def to_log_line(self) -> str:
        status = "✅" if self.success else "❌"
        dur = f" ({self.duration_ms}ms)" if self.duration_ms is not None else ""
        extra = ""
        if self.intent:
            extra += f" | intent={self.intent}"
        if self.decision:
            extra += f" | decision={self.decision}"
        if self.error:
            extra += f" | error={self.error}"
        return f"{status} [{self.node}]{dur}{extra}"


def append_span(existing_events: List[Dict], span: Span) -> List[Dict]:
    """Return new list with span appended (immutable update)."""
    return list(existing_events or []) + [span.to_dict()]
