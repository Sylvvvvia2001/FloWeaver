from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class AlignmentViolation:
    violation_id: str
    kind: str
    baseline_scope: List[str]
    optimized_scope: List[str]
    note: str | None = None
    severity: float = 1.0

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AlignmentViolation":
        return cls(
            violation_id=str(payload.get("violation_id", "")),
            kind=str(payload.get("kind", "")),
            baseline_scope=[str(item) for item in payload.get("baseline_scope", [])],
            optimized_scope=[str(item) for item in payload.get("optimized_scope", [])],
            note=str(payload.get("note")) if payload.get("note") is not None else None,
            severity=float(payload.get("severity", 1.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
