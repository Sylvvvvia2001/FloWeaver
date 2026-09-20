from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class CounterexampleVerdict(str, Enum):
    DIFF_FOUND = "DIFF_FOUND"
    NO_DIFF_WITHIN_BOUND = "NO_DIFF_WITHIN_BOUND"
    INCONCLUSIVE = "INCONCLUSIVE"


class ViolatedProperty(str, Enum):
    TRACE_MISMATCH = "TRACE_MISMATCH"
    FINAL_STATE_MISMATCH = "FINAL_STATE_MISMATCH"
    RESOURCE_PROTOCOL_VIOLATION = "RESOURCE_PROTOCOL_VIOLATION"
    UNSUPPORTED_ALIGNMENT = "UNSUPPORTED_ALIGNMENT"


@dataclass
class CounterexampleWitness:
    verdict: str
    violated_property: str | None = None
    input_assumptions: Dict[str, Any] = field(default_factory=dict)
    environment_assumptions: Dict[str, Any] = field(default_factory=dict)
    baseline_trace_prefix: List[Dict[str, Any]] = field(default_factory=list)
    optimized_trace_prefix: List[Dict[str, Any]] = field(default_factory=list)
    divergence_point: Dict[str, Any] = field(default_factory=dict)
    baseline_state_at_divergence: Dict[str, Any] = field(default_factory=dict)
    optimized_state_at_divergence: Dict[str, Any] = field(default_factory=dict)
    minimal_conditions: List[str] = field(default_factory=list)
    suspicious_region_id: str | None = None
    refinement_hint: str | Dict[str, Any] | None = None
    protocol_context: str | None = None
    phase_context: str | None = None
    trigger_pattern: str | None = None
    suspected_rule_gap: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
