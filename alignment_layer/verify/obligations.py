from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class ProofObligation:
    obligation_id: str
    kind: str
    baseline_scope: List[str]
    optimized_scope: List[str]
    status: str
    note: str | None = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ProofObligation":
        return cls(
            obligation_id=str(payload.get("obligation_id", "")),
            kind=str(payload.get("kind", "")),
            baseline_scope=[str(item) for item in payload.get("baseline_scope", [])],
            optimized_scope=[str(item) for item in payload.get("optimized_scope", [])],
            status=str(payload.get("status", "")),
            note=str(payload.get("note")) if payload.get("note") is not None else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
