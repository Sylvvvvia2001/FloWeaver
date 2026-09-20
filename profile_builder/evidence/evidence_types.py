from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class CounterexampleEvidence:
    evidence_id: str
    source_witness_id: str | None
    violated_property: str
    trigger_pattern: str
    protocol_context: str
    phase_context: str
    resource_context: str
    entity_scope: str
    divergence_point: Dict[str, Any] = field(default_factory=dict)
    minimal_conditions: Dict[str, Any] = field(default_factory=dict)
    baseline_trace_signature: Tuple[str, ...] = field(default_factory=tuple)
    optimized_trace_signature: Tuple[str, ...] = field(default_factory=tuple)
    suspected_rule_gap: str | None = None
    suggested_refinement: str | None = None
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CounterexampleCluster:
    cluster_id: str
    bucket_key: Tuple[str, str, str, str]
    violated_property: str
    protocol_context: str
    phase_context: str
    trigger_pattern: str
    suspected_rule_gap: str | None
    resource_context: str | None
    member_evidence_ids: List[str] = field(default_factory=list)
    representative_trace_signature: Tuple[str, ...] = field(default_factory=tuple)
    representative_minimal_conditions: Dict[str, Any] = field(default_factory=dict)
    suggested_refinement: str | None = None
    cluster_confidence: float = 0.70

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClusterPack:
    cluster_id: str
    semantic_tag: str
    violated_property: str
    protocol_context: str
    phase_context: str
    trigger_pattern: str
    supporting_counterexample_ids: List[str] = field(default_factory=list)
    supporting_doc_ids: List[str] = field(default_factory=list)
    supporting_code_ids: List[str] = field(default_factory=list)
    suspected_rule_gap: str | None = None
    candidate_rule_patch: str | None = None
    suggested_refinement: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
