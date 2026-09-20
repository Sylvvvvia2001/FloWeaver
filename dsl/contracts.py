from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


CANONICALIZATION_VERSION = "v1"
PROFILE_SCHEMA_VERSION = "ha_profile/v1"
CERT_SCHEMA_VERSION = "execution_certificate/v1"


class Provider(str, Enum):
    HA = "HA"
    BLE = "BLE"
    CLOUD = "CLOUD"
    SYS = "SYS"


class Phase(str, Enum):
    SETUP = "SETUP"
    RUNTIME = "RUNTIME"
    TEARDOWN = "TEARDOWN"


class MarkerStrength(str, Enum):
    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"


class RuleStatus(str, Enum):
    SOFT = "SOFT"
    HARD = "HARD"
    DISABLED = "DISABLED"


class EdgeKind(str, Enum):
    HARD_DATA = "HARD_DATA"
    HARD_CONTROL = "HARD_CONTROL"
    HARD_LIFECYCLE = "HARD_LIFECYCLE"
    MAY_DEP = "MAY_DEP"


class SoftConstraintKind(str, Enum):
    SOFT_ORDER = "SOFT_ORDER"
    MIN_GAP = "MIN_GAP"
    NO_OVERLAP = "NO_OVERLAP"
    SAME_SESSION_GROUP = "SAME_SESSION_GROUP"
    BUDGET_K = "BUDGET_K"
    RATE_LIMIT = "RATE_LIMIT"
    BATCH_GROUP = "BATCH_GROUP"
    COALESCE_STATE_WRITE = "COALESCE_STATE_WRITE"
    BACKOFF_WINDOW = "BACKOFF_WINDOW"


@dataclass
class Event:
    ts: float
    provider: str
    op: str
    target: str
    params_abst: Dict[str, Any] = field(default_factory=dict)
    phase: str = Phase.RUNTIME.value
    corr_id: Optional[str] = None


@dataclass
class Trace:
    events: List[Event] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Marker:
    marker_id: str
    marker_type: str
    file_path: str
    function_name: str
    line_start: int
    line_end: int
    strength: str = MarkerStrength.MEDIUM.value
    phase: str = Phase.RUNTIME.value
    evidence: List[str] = field(default_factory=list)
    primary_action_id: str | None = None
    secondary_action_ids: List[str] = field(default_factory=list)
    related_action_ids: List[str] = field(default_factory=list)
    binding_reason: List[str] = field(default_factory=list)
    binding_score: float = 0.0


@dataclass
class GraphNode:
    node_id: str
    file_path: str
    function_name: str
    line_start: int
    line_end: int
    stmt_kind: str
    col_start: int = 0
    col_end: int = 0
    raw_repr: str = ""
    effects: Set[str] = field(default_factory=set)
    defs: Set[str] = field(default_factory=set)
    uses: Set[str] = field(default_factory=set)
    marker_refs: List[str] = field(default_factory=list)


@dataclass
class GraphEdge:
    src: str
    dst: str
    edge_type: str


@dataclass
class ReducedGraph:
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)
    mapping: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class MSSU:
    mssu_id: str
    mssu_type: str
    phase: str
    node_ids: List[str]
    inputs: Set[str] = field(default_factory=set)
    outputs: Set[str] = field(default_factory=set)
    side_effect_sig: Set[str] = field(default_factory=set)
    exceptions: Set[str] = field(default_factory=set)
    required_guards: List[str] = field(default_factory=list)
    critical: bool = False
    primary_action_ref: str | None = None
    secondary_action_refs: List[str] = field(default_factory=list)
    action_refs: List[str] = field(default_factory=list)
    is_shared_infra: bool = False
    is_aggregate_sink: bool = False
    lane_tag: str | None = None
    resource_instance_tag: str | None = None


@dataclass
class DependencyEdge:
    src_mssu: str
    dst_mssu: str
    kind: str
    justification: List[str] = field(default_factory=list)
    guardable: bool = False


@dataclass
class SoftConstraint:
    kind: str
    scope: List[str]
    params: Dict[str, Any] = field(default_factory=dict)
    guard: str = "true"
    fallback: str = "fallback_to_sequential"


@dataclass
class TypedDAG:
    nodes: Dict[str, MSSU] = field(default_factory=dict)
    hard_edges: List[DependencyEdge] = field(default_factory=list)
    soft_constraints: List[SoftConstraint] = field(default_factory=list)
    resources: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class Batch:
    batch_id: str
    parallel_groups: List[List[str]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    session_policy: Dict[str, Any] = field(default_factory=dict)
    rate_policy: Dict[str, Any] = field(default_factory=dict)
    guards: List[Dict[str, Any]] = field(default_factory=list)
    fallback: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    ordered_batches: List[Batch] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiffHunk:
    anchor: str
    baseline_ops: List[str]
    optimized_ops: List[str]
    severity: str


@dataclass
class DiffResult:
    strict_equal: bool
    tolerant_equal: bool
    diff_signature: List[DiffHunk] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CounterExample:
    counterexample_id: str
    scenario_id: str
    violated_assertion: str
    culprit_ids: List[str] = field(default_factory=list)
    diff_summary: Dict[str, Any] = field(default_factory=dict)
    alignment_status: str | None = None
    suspicious_region_count: int = 0
    trust_plan_hash: str | None = None
    execution_plan_hash: str | None = None


@dataclass
class DocEvidence:
    evidence_id: str
    source_path: str
    line_no: int
    modality: str
    text: str
    section_title: str | None = None
    is_code_block: bool = False
    is_table_row: bool = False
    doc_kind: str = "NORMATIVE_SENTENCE"
    normative_strength: str = "INFO"
    specificity: str = "GENERIC"
    source_type: str = "doc"
    source_commit: str | None = None
    extractor_version: str = "profile_builder_doc/v2"
    normalization_flags: List[str] = field(default_factory=list)
    confidence: float = 0.9
    typed_anchor: str = "UNKNOWN"
    semantic_level: str = "POLICY"
    semantic_anchor: str = "UNKNOWN"


@dataclass
class CodeEvidence:
    evidence_id: str
    source_path: str
    pattern: str
    line_no: int
    frequency: int = 1
    specificity: str = "FRAMEWORK"
    source_type: str = "code"
    source_commit: str | None = None
    extractor_version: str = "profile_builder_code/v2"
    normalization_flags: List[str] = field(default_factory=list)
    confidence: float = 0.85
    typed_anchor: str = "UNKNOWN"
    signal_strength: str = "AST_STRONG"
    effective_typed_anchor: str | None = None
    semantic_level: str = "RUNTIME"
    semantic_anchor: str = "UNKNOWN"


@dataclass
class TestEvidence:
    __test__ = False
    evidence_id: str
    source_path: str
    pattern: str
    test_name: str | None
    line_no: int
    assertion_kind: str
    target_symbol: str | None = None
    frequency: int = 1
    specificity: str = "FRAMEWORK"
    source_type: str = "test"
    source_commit: str | None = None
    extractor_version: str = "profile_builder_test/v2"
    normalization_flags: List[str] = field(default_factory=list)
    confidence: float = 0.85
    typed_anchor: str = "UNKNOWN"
    protocol_hypothesis: str | None = None
    semantic_level: str = "BEHAVIOR"
    semantic_anchor: str = "UNKNOWN"
    behavior_category: str | None = None


@dataclass
class Rule:
    rule_id: str
    title: str
    category: str
    status: str = RuleStatus.SOFT.value
    semantic_tag: str = ""
    marker_hints: List[str] = field(default_factory=list)
    hard_edge_templates: List[Dict[str, Any]] = field(default_factory=list)
    soft_constraint_templates: List[Dict[str, Any]] = field(default_factory=list)
    guard: str = "true"
    fallback: str = "disable_rule"
    evidence_ids: List[str] = field(default_factory=list)
    match_pattern: Dict[str, Any] = field(default_factory=dict)
    effect: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    source_type: str = "profile_builder_rule"
    source_commit: str | None = None
    extractor_version: str = "profile_builder_norm/v2"
    normalization_flags: List[str] = field(default_factory=list)
    confidence: float = 0.8
    hardening_state: str = "UNKNOWN"
    hardening_reason: str | None = None
    validation_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HAPProfile:
    profile_id: str
    schema_version: str
    created_at: str
    provenance: Dict[str, Any]
    marker_detectors: List[Dict[str, Any]] = field(default_factory=list)
    lifecycle_templates: List[Dict[str, Any]] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)
    profile_heuristics: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationStats:
    rule_id: str
    n_matched: int = 0
    n_applied: int = 0
    n_success: int = 0
    n_counterexamples: int = 0
    trace_preserved_rate: float = 0.0
    final_state_preserved_rate: float = 0.0
    resource_protocol_preserved_rate: float = 0.0
    avg_latency_delta_ms: float | None = None
    p95_latency_delta_ms: float | None = None
    last_updated_at: str | None = None


@dataclass
class ExecutionCertificate:
    certificate_id: str
    schema_version: str
    generated_at: str
    integration: str
    profile_version: str
    canonicalization_version: str
    mssu_signatures: List[Dict[str, Any]] = field(default_factory=list)
    hard_edge_proof: Dict[str, Any] = field(default_factory=dict)
    soft_constraints: List[Dict[str, Any]] = field(default_factory=list)
    plan_summary: Dict[str, Any] = field(default_factory=dict)
    differential_summary: Dict[str, Any] = field(default_factory=dict)
    counterexamples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ResourcePoolState:
    ble: Dict[str, Any] = field(default_factory=dict)
    cloud: Dict[str, Any] = field(default_factory=dict)
    ha: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceFileBinding:
    device_id: str
    integration: str
    file_path: str
    protocols: List[str] = field(default_factory=list)


@dataclass
class OptimizationTarget:
    meta: Dict[str, Any] = field(default_factory=dict)
    source_scope: Dict[str, Any] = field(default_factory=dict)
    vdev_actions: List[Dict[str, Any]] = field(default_factory=list)
    target_anchors: Dict[str, List[str]] = field(default_factory=dict)
    entrypoint: Dict[str, Any] = field(default_factory=dict)
    objectives: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    hard_dependencies: List[Dict[str, Any]] = field(default_factory=list)
    soft_dependencies: List[Dict[str, Any]] = field(default_factory=list)
    critical_action_ids: List[str] = field(default_factory=list)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, set):
        return sorted(_to_plain(v) for v in value)
    if isinstance(value, Path):
        return str(value)
    return value


def to_dict(obj: Any) -> Dict[str, Any]:
    if not is_dataclass(obj):
        raise TypeError(f"Expected dataclass, got {type(obj)!r}")
    return _to_plain(obj)


def ensure_profile(profile: HAPProfile) -> None:
    if profile.schema_version != PROFILE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported profile schema '{profile.schema_version}', expected '{PROFILE_SCHEMA_VERSION}'"
        )
    for rule in profile.rules:
        if not rule.rule_id:
            raise ValueError("rule_id is required")
        if not rule.evidence_ids:
            raise ValueError(f"Rule '{rule.rule_id}' must reference evidence ids")


def ensure_certificate(cert: ExecutionCertificate) -> None:
    if cert.schema_version != CERT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported certificate schema '{cert.schema_version}', expected '{CERT_SCHEMA_VERSION}'"
        )


def ensure_optimization_target(target: OptimizationTarget) -> None:
    if not target.source_scope.get("files"):
        raise ValueError("OptimizationTarget.source_scope.files cannot be empty")
    if not target.vdev_actions:
        raise ValueError("OptimizationTarget.vdev_actions cannot be empty")
    for action in target.vdev_actions:
        action_id = action.get("action_id")
        if not action_id:
            raise ValueError("Each vdev action must include action_id")
        exec_primitive = action.get("exec")
        if not isinstance(exec_primitive, dict):
            raise ValueError(f"Action '{action_id}' must include executable mapping in 'exec'")
        if not exec_primitive.get("kind"):
            raise ValueError(f"Action '{action_id}' exec.kind is required")


DEFAULT_MARKER_DETECTORS: List[Dict[str, Any]] = [
    {
        "id": "func:async_setup_entry",
        "type": "ENTRY_SETUP",
        "match": {"function_names": ["async_setup_entry"]},
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.SETUP.value,
    },
    {
        "id": "func:async_unload_entry",
        "type": "ENTRY_UNLOAD",
        "match": {"function_names": ["async_unload_entry", "async_remove_entry"]},
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.TEARDOWN.value,
    },
    {
        "id": "call:state_write",
        "type": "STATE_WRITE",
        "match": {"call_attrs": ["async_write_ha_state", "schedule_update_ha_state"]},
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.RUNTIME.value,
    },
    {
        "id": "call:coordinator_refresh",
        "type": "COORD_REFRESH",
        "match": {
            "call_attrs": [
                "async_config_entry_first_refresh",
                "_async_update_data",
                "_async_setup",
            ]
        },
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.RUNTIME.value,
    },
    {
        "id": "call:subscribe",
        "type": "SUBSCRIBE",
        "match": {
            "call_attrs": [
                "dispatcher_connect",
                "async_track_state_change_event",
                "add_listener",
            ]
        },
        "strength": MarkerStrength.MEDIUM.value,
        "phase": Phase.RUNTIME.value,
    },
    {
        "id": "call:unsubscribe",
        "type": "UNSUBSCRIBE",
        "match": {"call_attrs": ["unsub", "unsubscribe"]},
        "strength": MarkerStrength.MEDIUM.value,
        "phase": Phase.TEARDOWN.value,
    },
    {
        "id": "call:ble",
        "type": "BLE_OP",
        "match": {
            "call_attrs": ["connect", "disconnect", "read_gatt_char", "write_gatt_char"]
        },
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.RUNTIME.value,
    },
    {
        "id": "call:cloud",
        "type": "CLOUD_OP",
        "match": {"call_attrs": ["get", "post", "request", "call_api"]},
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.RUNTIME.value,
    },
]


DEFAULT_LIFECYCLE_TEMPLATES: List[Dict[str, Any]] = [
    {
        "template_id": "pair:subscribe_unsubscribe",
        "requires": ["SUBSCRIBE", "UNSUBSCRIBE"],
        "edge_kind": EdgeKind.HARD_LIFECYCLE.value,
    },
    {
        "template_id": "precedence:first_refresh_before_state_write",
        "requires_order": ["COORD_REFRESH", "STATE_WRITE"],
        "edge_kind": EdgeKind.HARD_LIFECYCLE.value,
    },
    {
        "template_id": "pair:acquire_release",
        "requires": ["LOCK_ACQUIRE", "LOCK_RELEASE"],
        "edge_kind": EdgeKind.HARD_LIFECYCLE.value,
    },
]
