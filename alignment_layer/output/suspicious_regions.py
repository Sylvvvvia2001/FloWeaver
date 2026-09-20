from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class SuspiciousRegion:
    region_id: str
    baseline_node_ids: List[str]
    optimized_node_ids: List[str]
    reason: str
    severity: float

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SuspiciousRegion":
        return cls(
            region_id=str(payload.get("region_id", "")),
            baseline_node_ids=[str(item) for item in payload.get("baseline_node_ids", [])],
            optimized_node_ids=[str(item) for item in payload.get("optimized_node_ids", [])],
            reason=str(payload.get("reason", "")),
            severity=float(payload.get("severity", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
