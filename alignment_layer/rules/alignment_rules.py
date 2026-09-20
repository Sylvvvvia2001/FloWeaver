from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

INDEPENDENT_ACT_SWAP = "INDEPENDENT_ACT_SWAP"
SETUP_PREFIX_STUTTER = "SETUP_PREFIX_STUTTER"
SHARED_CONTEXT_REUSE = "SHARED_CONTEXT_REUSE"
LISTENER_PRESERVING_BATCH = "LISTENER_PRESERVING_BATCH"
TEARDOWN_HOISTING_FORBIDDEN = "TEARDOWN_HOISTING_FORBIDDEN"

DEFAULT_ALIGNMENT_RULES = [
    INDEPENDENT_ACT_SWAP,
    SETUP_PREFIX_STUTTER,
    SHARED_CONTEXT_REUSE,
    LISTENER_PRESERVING_BATCH,
    TEARDOWN_HOISTING_FORBIDDEN,
]


@dataclass
class AlignmentConfig:
    max_candidate_pairs: int = 64
    max_rule_applications: int = 24
    confidence_threshold: float = 0.55
    high_confidence_threshold: float = 0.75
    allow_partial_alignment: bool = True
    enable_stutter_matching: bool = True
    beam_width: int = 8

    @classmethod
    def from_any(cls, payload: Any) -> "AlignmentConfig":
        if isinstance(payload, cls):
            return payload
        if isinstance(payload, dict):
            return cls(
                max_candidate_pairs=int(payload.get("max_candidate_pairs", 64)),
                max_rule_applications=int(payload.get("max_rule_applications", 24)),
                confidence_threshold=float(payload.get("confidence_threshold", 0.55)),
                high_confidence_threshold=float(payload.get("high_confidence_threshold", 0.75)),
                allow_partial_alignment=bool(payload.get("allow_partial_alignment", True)),
                enable_stutter_matching=bool(payload.get("enable_stutter_matching", True)),
                beam_width=int(payload.get("beam_width", 8)),
            )
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_alignment_rules(rules: List[str] | None) -> List[str]:
    normalized = [str(item).strip().upper() for item in (rules or DEFAULT_ALIGNMENT_RULES) if str(item).strip()]
    ordered: List[str] = []
    for item in normalized:
        if item not in ordered:
            ordered.append(item)
    return ordered
