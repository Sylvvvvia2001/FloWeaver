from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from dsl.contracts import Batch, ExecutionPlan, OptimizationTarget
from optimizer.api_micro_refinement import (
    APIBatchStep,
    APIMicroCaseResult,
    APIMicroCorridorResult,
    APIMicroEvent,
    APIMicroRefinementPolicy,
    ConservativeAPIMicroRefiner,
)
from optimizer.ble_micro_refinement import (
    BLEMicroCaseResult,
    BLEMicroCorridorResult,
    BLEMicroEvent,
    BLEMicroRefinementPolicy,
    ConservativeBLEMicroRefiner,
)


_BLE_DURATION_MS: Dict[str, int] = {
    "set_cover_position": 950,
    "refresh_cover": 850,
    "read_sensor": 750,
    "read_status": 650,
    "connect": 1200,
    "subscribe": 450,
    "set_percentage": 850,
    "turn_on": 850,
    "turn_off": 800,
}
_DEFAULT_BLE_DURATION_MS = 800


@dataclass(frozen=True)
class CombinedMicroRefinementPolicy:
    conflict_policy: str = "highest_saving_wins"
    forbid_batch_overlap: bool = True
    forbid_action_overlap: bool = True
    require_component_validation: bool = True
    require_contiguous_corridor_batches: bool = True
    require_segment_local_refinement: bool = True
    enforce_batch_order_projection: bool = True
    ble_global_xfer_limit: int = 1
    ble_global_connect_prepare_limit: int = 1
    cloud_host_request_limit: int = 1
    cloud_bucket_request_limit: int = 1
    local_endpoint_request_limit: int = 1
    local_session_request_limit: int = 1
    max_global_parse_overlap: int = 1
    adjacent_batch_gap_threshold: int = 1
    forbid_adjacent_same_ble_session_domain: bool = True
    forbid_adjacent_same_api_host_domain: bool = False
    forbid_adjacent_same_api_endpoint_domain: bool = False

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "CombinedMicroRefinementPolicy":
        if not isinstance(payload, dict):
            return cls()
        fields = {name: payload[name] for name in cls.__dataclass_fields__ if name in payload}
        return cls(**fields)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CombinedCandidate:
    source: str
    corridor_id: str
    batch_ids: List[str]
    action_ids: List[str]
    latency_saved_ms: int
    validation_passed: bool
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CombinedDecision:
    accepted: List[CombinedCandidate]
    rejected: List[CombinedCandidate]
    conflicts: List[Dict[str, Any]]


@dataclass(frozen=True)
class CombinedSimulatedEvent:
    source: str
    corridor_id: str
    owner_id: str
    batch_id: str
    phase: str
    start_ms: int
    end_ms: int
    protocol: str
    host_key: str = ""
    bucket_key: str = ""
    session_key: str = ""
    endpoint_key: str = ""


@dataclass
class CombinedMicroValidationResult:
    passed: bool
    component_validations_ok: bool
    conflict_free: bool
    contiguous_coverage_ok: bool
    savings_consistency_ok: bool
    batch_order_preserved: bool
    projection_ok: bool
    ble_constraints_ok: bool
    api_constraints_ok: bool
    event_loop_constraints_ok: bool
    simulated_total_ms: int
    simulated_event_count: int
    reasons: List[str] = field(default_factory=list)


@dataclass
class CombinedMicroCaseResult:
    vdev_id: str
    case_name: str
    ble_added_savings_ms: int
    api_added_savings_ms: int
    combined_added_savings_ms: int
    combined_added_savings_ratio: float
    original_estimated_latency_ms: int
    combined_refined_estimated_latency_ms: int
    conflict_count: int
    accepted_corridors: List[Dict[str, Any]]
    rejected_corridors: List[Dict[str, Any]]
    validation: CombinedMicroValidationResult
    simulated_events: List[CombinedSimulatedEvent]
    refined_plan: ExecutionPlan


def _action_index(target: OptimizationTarget) -> Dict[str, Dict[str, Any]]:
    return {
        str(action.get("action_id", "")).strip(): action
        for action in target.vdev_actions
        if str(action.get("action_id", "")).strip()
    }


def _action_protocol(action: Dict[str, Any]) -> str:
    token = str(action.get("protocol", "") or "").strip().upper()
    if token == "MQTT":
        return "LOCAL"
    return token or "UNKNOWN"


def _action_kind(action: Dict[str, Any]) -> str:
    for key in ("action_kind", "type", "kind"):
        token = str(action.get(key, "") or "").strip().lower()
        if token:
            return token
    exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
    return str(exec_cfg.get("service", "") or "").strip().lower() or "unknown"


def _is_control_like(action: Dict[str, Any]) -> bool:
    kind = _action_kind(action)
    return any(
        token in kind
        for token in (
            "turn_on",
            "turn_off",
            "set_",
            "open",
            "close",
            "play_media",
            "set_volume",
            "set_cover_position",
        )
    )


def _estimated_action_latency_ms(action: Dict[str, Any]) -> int:
    protocol = _action_protocol(action)
    kind = _action_kind(action)
    if protocol == "BLE":
        return int(_BLE_DURATION_MS.get(kind, _DEFAULT_BLE_DURATION_MS))
    if protocol == "CLOUD":
        if "runtime" in kind:
            return 450
        return 400 if _is_control_like(action) else 350
    if protocol == "LOCAL":
        return 80 if "read_last_message" in kind else 100
    if protocol == "HA":
        return 50
    return 100


def _group_latency_ms(group: Sequence[str], action_lookup: Dict[str, Dict[str, Any]]) -> int:
    if not group:
        return 0
    actions = [action_lookup[action_id] for action_id in group if action_id in action_lookup]
    if not actions:
        return 0
    protocols = {_action_protocol(action) for action in actions}
    costs = [_estimated_action_latency_ms(action) for action in actions]
    if protocols == {"BLE"}:
        return sum(costs)
    if protocols == {"LOCAL"}:
        return max(costs) + max(0, 20 * (len(costs) - 1))
    if protocols == {"HA"}:
        return max(costs) + max(0, 10 * (len(costs) - 1))
    if protocols == {"CLOUD"}:
        return max(costs) + max(0, 120 * (len(costs) - 1))
    return max(costs)


def _batch_latency_ms(batch: Batch, action_lookup: Dict[str, Dict[str, Any]]) -> int:
    if not batch.parallel_groups:
        return 0
    return max(_group_latency_ms(group, action_lookup) for group in batch.parallel_groups)


def estimate_plan_latency_ms(plan: ExecutionPlan, target: OptimizationTarget) -> int:
    action_lookup = _action_index(target)
    return int(sum(_batch_latency_ms(batch, action_lookup) for batch in plan.ordered_batches))


def _normalize_candidate(candidate: CombinedCandidate) -> CombinedCandidate:
    return CombinedCandidate(
        source=str(candidate.source).strip().upper(),
        corridor_id=str(candidate.corridor_id).strip(),
        batch_ids=[str(item).strip() for item in candidate.batch_ids if str(item).strip()],
        action_ids=[str(item).strip() for item in candidate.action_ids if str(item).strip()],
        latency_saved_ms=max(0, int(candidate.latency_saved_ms)),
        validation_passed=bool(candidate.validation_passed),
        payload=dict(candidate.payload) if isinstance(candidate.payload, dict) else {},
    )


def _candidate_conflict_reasons(
    left: CombinedCandidate,
    right: CombinedCandidate,
    policy: CombinedMicroRefinementPolicy,
) -> List[str]:
    reasons: List[str] = []
    if policy.forbid_batch_overlap and set(left.batch_ids) & set(right.batch_ids):
        reasons.append("batch_overlap")
    if policy.forbid_action_overlap and set(left.action_ids) & set(right.action_ids):
        reasons.append("action_overlap")
    reasons.extend(_candidate_resource_domain_conflict_reasons(left, right, policy))
    return reasons


def _batch_ordinals(batch_ids: Sequence[str]) -> List[int]:
    values: List[int] = []
    for batch_id in batch_ids:
        token = str(batch_id).strip()
        if not token.startswith("batch_"):
            continue
        try:
            values.append(int(token.split("_", 1)[1]))
        except ValueError:
            continue
    return sorted(values)


def _ranges_adjacent_or_overlap(left: Sequence[str], right: Sequence[str], gap_threshold: int) -> bool:
    left_ordinals = _batch_ordinals(left)
    right_ordinals = _batch_ordinals(right)
    if not left_ordinals or not right_ordinals:
        return False
    left_min, left_max = left_ordinals[0], left_ordinals[-1]
    right_min, right_max = right_ordinals[0], right_ordinals[-1]
    if left_max >= right_min and right_max >= left_min:
        return True
    if left_max < right_min:
        return (right_min - left_max) <= (gap_threshold + 1)
    return (left_min - right_max) <= (gap_threshold + 1)


def _candidate_resource_domain_conflict_reasons(
    left: CombinedCandidate,
    right: CombinedCandidate,
    policy: CombinedMicroRefinementPolicy,
) -> List[str]:
    reasons: List[str] = []
    if left.source != right.source:
        return reasons
    if not _ranges_adjacent_or_overlap(left.batch_ids, right.batch_ids, policy.adjacent_batch_gap_threshold):
        return reasons

    left_domains = dict(left.payload.get("resource_domains", {})) if isinstance(left.payload.get("resource_domains", {}), dict) else {}
    right_domains = dict(right.payload.get("resource_domains", {})) if isinstance(right.payload.get("resource_domains", {}), dict) else {}
    if left.source == "BLE" and policy.forbid_adjacent_same_ble_session_domain:
        left_sessions = {str(item).strip() for item in left_domains.get("session_groups", []) if str(item).strip()}
        right_sessions = {str(item).strip() for item in right_domains.get("session_groups", []) if str(item).strip()}
        left_devices = {str(item).strip() for item in left_domains.get("device_ids", []) if str(item).strip()}
        right_devices = {str(item).strip() for item in right_domains.get("device_ids", []) if str(item).strip()}
        if (left_sessions & right_sessions) or (left_devices & right_devices):
            reasons.append("ble_resource_domain_adjacent")
    if left.source == "API":
        if policy.forbid_adjacent_same_api_host_domain:
            left_hosts = {str(item).strip() for item in left_domains.get("host_keys", []) if str(item).strip()}
            right_hosts = {str(item).strip() for item in right_domains.get("host_keys", []) if str(item).strip()}
            if left_hosts & right_hosts:
                reasons.append("api_host_domain_adjacent")
        if policy.forbid_adjacent_same_api_endpoint_domain:
            left_endpoints = {str(item).strip() for item in left_domains.get("endpoint_keys", []) if str(item).strip()}
            right_endpoints = {str(item).strip() for item in right_domains.get("endpoint_keys", []) if str(item).strip()}
            if left_endpoints & right_endpoints:
                reasons.append("api_endpoint_domain_adjacent")
    return reasons


def resolve_combined_candidates(
    ble_candidates: Sequence[CombinedCandidate],
    api_candidates: Sequence[CombinedCandidate],
    policy: CombinedMicroRefinementPolicy,
) -> CombinedDecision:
    accepted: List[CombinedCandidate] = []
    rejected: List[CombinedCandidate] = []
    conflicts: List[Dict[str, Any]] = []

    pool = [_normalize_candidate(row) for row in list(ble_candidates) + list(api_candidates)]
    pool.sort(key=lambda row: (-row.latency_saved_ms, row.source, row.corridor_id))

    for candidate in pool:
        if policy.require_component_validation and not candidate.validation_passed:
            rejected.append(candidate)
            conflicts.append(
                {
                    "winner": None,
                    "loser": candidate.corridor_id,
                    "loser_source": candidate.source,
                    "reasons": ["component_validation_failed"],
                }
            )
            continue
        if candidate.latency_saved_ms <= 0:
            rejected.append(candidate)
            conflicts.append(
                {
                    "winner": None,
                    "loser": candidate.corridor_id,
                    "loser_source": candidate.source,
                    "reasons": ["non_positive_saving"],
                }
            )
            continue

        winner: CombinedCandidate | None = None
        reasons: List[str] = []
        for existing in accepted:
            overlap_reasons = _candidate_conflict_reasons(existing, candidate, policy)
            if overlap_reasons:
                winner = existing
                reasons = overlap_reasons
                break

        if winner is None:
            accepted.append(candidate)
            continue

        rejected.append(candidate)
        conflicts.append(
            {
                "winner": winner.corridor_id,
                "winner_source": winner.source,
                "loser": candidate.corridor_id,
                "loser_source": candidate.source,
                "reasons": reasons,
            }
        )

    accepted.sort(key=lambda row: (row.source, row.corridor_id))
    rejected.sort(key=lambda row: (row.source, row.corridor_id))
    return CombinedDecision(accepted=accepted, rejected=rejected, conflicts=conflicts)


def _ble_event_map(events: Sequence[BLEMicroEvent]) -> Dict[str, int]:
    completion: Dict[str, int] = {}
    for event in events:
        if event.phase == "BLE_SETTLE":
            completion[event.action_id] = max(completion.get(event.action_id, 0), event.end_ms)
    return completion


def _api_event_map(events: Sequence[APIMicroEvent]) -> Dict[str, int]:
    completion: Dict[str, int] = {}
    for event in events:
        completion[event.step_id] = max(completion.get(event.step_id, 0), event.end_ms)
    return completion


def _sweep_max_overlap(
    events: Sequence[CombinedSimulatedEvent],
    *,
    phase_filter: Iterable[str] | None = None,
    key_fn: Any = None,
) -> Dict[str, int]:
    filtered = [event for event in events if phase_filter is None or event.phase in set(phase_filter)]
    if not filtered:
        return {}
    time_points = sorted({event.start_ms for event in filtered} | {event.end_ms for event in filtered})
    maxima: Dict[str, int] = {}
    for point in time_points:
        active = [event for event in filtered if event.start_ms <= point < event.end_ms]
        buckets: Dict[str, int] = {}
        for event in active:
            key = key_fn(event) if key_fn is not None else "__all__"
            buckets[key] = buckets.get(key, 0) + 1
        for key, count in buckets.items():
            maxima[key] = max(maxima.get(key, 0), count)
    return maxima


def _batch_index_map(plan: ExecutionPlan) -> Dict[str, int]:
    return {batch.batch_id: index for index, batch in enumerate(plan.ordered_batches)}


def _candidate_batch_range(
    candidate: CombinedCandidate,
    batch_index_by_id: Dict[str, int],
    policy: CombinedMicroRefinementPolicy,
) -> Tuple[int, int, bool, List[str]]:
    reasons: List[str] = []
    indexes = [batch_index_by_id[batch_id] for batch_id in candidate.batch_ids if batch_id in batch_index_by_id]
    if len(indexes) != len(candidate.batch_ids):
        reasons.append("unknown_batch_id")
        return -1, -1, False, reasons
    indexes_sorted = sorted(indexes)
    contiguous = indexes_sorted == list(range(indexes_sorted[0], indexes_sorted[-1] + 1))
    if policy.require_contiguous_corridor_batches and not contiguous:
        reasons.append("non_contiguous_batch_range")
    return indexes_sorted[0], indexes_sorted[-1], contiguous, reasons


def _build_ble_candidates(
    result: BLEMicroCaseResult,
    target: OptimizationTarget,
) -> List[CombinedCandidate]:
    action_lookup = _action_index(target)
    candidates: List[CombinedCandidate] = []
    for row in result.selected_corridors:
        actions = [action_lookup[action_id] for action_id in row.corridor.action_ids if action_id in action_lookup]
        candidates.append(
            CombinedCandidate(
                source="BLE",
                corridor_id=row.corridor.corridor_id,
                batch_ids=list(row.corridor.batch_ids),
                action_ids=list(row.corridor.action_ids),
                latency_saved_ms=row.latency_saved_ms,
                validation_passed=row.validation.passed,
                payload={
                    "original_latency_ms": row.corridor.original_latency_ms,
                    "refined_latency_ms": row.refined_latency_ms,
                    "events": list(row.refined_events),
                    "owner_ids": list(row.corridor.action_ids),
                    "resource_domains": {
                        "device_ids": sorted(
                            {
                                _normalized_device_key(action)
                                for action in actions
                                if _normalized_device_key(action)
                            }
                        ),
                        "session_groups": sorted(
                            {
                                _normalized_session_key(action)
                                for action in actions
                                if _normalized_session_key(action)
                            }
                        ),
                        "profile_class": row.corridor.profile_class,
                    },
                },
            )
        )
    return candidates


def _build_api_candidates(
    result: APIMicroCaseResult,
    steps_by_id: Dict[str, APIBatchStep],
) -> List[CombinedCandidate]:
    candidates: List[CombinedCandidate] = []
    for row in result.selected_corridors:
        steps = [steps_by_id[step_id] for step_id in row.corridor.step_ids if step_id in steps_by_id]
        candidates.append(
            CombinedCandidate(
                source="API",
                corridor_id=row.corridor.corridor_id,
                batch_ids=list(row.corridor.batch_ids),
                action_ids=list(row.corridor.action_ids),
                latency_saved_ms=row.latency_saved_ms,
                validation_passed=row.validation.passed,
                payload={
                    "original_latency_ms": row.corridor.original_latency_ms,
                    "refined_latency_ms": row.refined_latency_ms,
                    "events": list(row.refined_events),
                    "steps": steps,
                    "owner_ids": list(row.corridor.step_ids),
                    "resource_domains": {
                        "host_keys": sorted({step.host_key for step in steps if step.host_key}),
                        "bucket_keys": sorted({step.bucket_key for step in steps if step.bucket_key}),
                        "session_keys": sorted({step.session_key for step in steps if step.session_key}),
                        "endpoint_keys": sorted({step.endpoint_key for step in steps if step.endpoint_key}),
                        "phase_kind": row.corridor.phase_kind,
                        "capability_class": row.corridor.capability_class,
                    },
                },
            )
        )
    return candidates


def _simulate_candidate_segment(
    candidate: CombinedCandidate,
    *,
    shift_ms: int,
    action_lookup: Dict[str, Dict[str, Any]],
) -> Tuple[List[CombinedSimulatedEvent], Dict[str, int], int, List[str]]:
    reasons: List[str] = []
    shifted_events: List[CombinedSimulatedEvent] = []
    batch_completion: Dict[str, int] = {}

    if candidate.source == "BLE":
        raw_events: Sequence[BLEMicroEvent] = list(candidate.payload.get("events", []))
        owner_ids = list(candidate.payload.get("owner_ids", candidate.action_ids))
        if len(owner_ids) != len(candidate.batch_ids):
            reasons.append("ble_batch_owner_cardinality_mismatch")
            return [], {}, 0, reasons
        batch_by_owner = {owner_id: batch_id for owner_id, batch_id in zip(owner_ids, candidate.batch_ids)}
        owner_completion = _ble_event_map(raw_events)
        for owner_id in owner_ids:
            if owner_id not in owner_completion:
                reasons.append(f"ble_missing_completion:{owner_id}")
        for event in raw_events:
            batch_id = batch_by_owner.get(event.action_id, "")
            shifted_events.append(
                CombinedSimulatedEvent(
                    source="BLE",
                    corridor_id=candidate.corridor_id,
                    owner_id=event.action_id,
                    batch_id=batch_id,
                    phase=event.phase,
                    start_ms=shift_ms + event.start_ms,
                    end_ms=shift_ms + event.end_ms,
                    protocol="BLE",
                    session_key=_normalized_session_key(action_lookup.get(event.action_id, {})),
                    endpoint_key=_normalized_device_key(action_lookup.get(event.action_id, {})),
                )
            )
        ordered_completion = [owner_completion.get(owner_id, -1) for owner_id in owner_ids]
        if ordered_completion != sorted(ordered_completion):
            reasons.append("ble_owner_completion_order_changed")
        for owner_id, batch_id in zip(owner_ids, candidate.batch_ids):
            batch_completion[batch_id] = shift_ms + owner_completion.get(owner_id, 0)
        local_end = max((event.end_ms for event in raw_events), default=0)
        return shifted_events, batch_completion, local_end, reasons

    raw_events = list(candidate.payload.get("events", []))
    steps: Sequence[APIBatchStep] = list(candidate.payload.get("steps", []))
    step_by_id = {step.step_id: step for step in steps}
    owner_ids = list(candidate.payload.get("owner_ids", [step.step_id for step in steps]))
    if len(owner_ids) != len(candidate.batch_ids):
        reasons.append("api_batch_owner_cardinality_mismatch")
        return [], {}, 0, reasons
    owner_completion = _api_event_map(raw_events)
    for owner_id in owner_ids:
        if owner_id not in owner_completion:
            reasons.append(f"api_missing_completion:{owner_id}")
    for event in raw_events:
        step = step_by_id.get(event.step_id)
        shifted_events.append(
            CombinedSimulatedEvent(
                source="API",
                corridor_id=candidate.corridor_id,
                owner_id=event.step_id,
                batch_id=event.step_id,
                phase=event.phase,
                start_ms=shift_ms + event.start_ms,
                end_ms=shift_ms + event.end_ms,
                protocol=step.protocol if step is not None else "",
                host_key=step.host_key if step is not None else "",
                bucket_key=step.bucket_key if step is not None else "",
                session_key=step.session_key if step is not None else "",
                endpoint_key=step.endpoint_key if step is not None else "",
            )
        )
    ordered_completion = [owner_completion.get(owner_id, -1) for owner_id in owner_ids]
    if ordered_completion != sorted(ordered_completion):
        reasons.append("api_owner_completion_order_changed")
    for owner_id, batch_id in zip(owner_ids, candidate.batch_ids):
        batch_completion[batch_id] = shift_ms + owner_completion.get(owner_id, 0)
    local_end = max((event.end_ms for event in raw_events), default=0)
    return shifted_events, batch_completion, local_end, reasons


def _normalized_device_key(action: Dict[str, Any]) -> str:
    if not isinstance(action, dict):
        return ""
    target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
    for value in (target.get("device_id"), target.get("id"), target.get("endpoint")):
        token = str(value or "").strip()
        if token:
            return token
    return ""


def _normalized_session_key(action: Dict[str, Any]) -> str:
    if not isinstance(action, dict):
        return ""
    target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
    for key in ("session_group", "connection_group", "device_session_group"):
        token = str(target.get(key, "") or "").strip()
        if token:
            return token
    device = _normalized_device_key(action)
    if device:
        return device
    return ""


def validate_combined_candidates(
    *,
    plan: ExecutionPlan,
    target: OptimizationTarget,
    accepted_candidates: Sequence[CombinedCandidate],
    rejected_candidates: Sequence[CombinedCandidate],
    conflicts: Sequence[Dict[str, Any]],
    ble_policy: BLEMicroRefinementPolicy,
    api_policy: APIMicroRefinementPolicy,
    combined_policy: CombinedMicroRefinementPolicy,
) -> Tuple[CombinedMicroValidationResult, List[CombinedSimulatedEvent], int]:
    reasons: List[str] = []
    action_lookup = _action_index(target)
    batch_index_by_id = _batch_index_map(plan)
    batch_latency_by_id = {
        batch.batch_id: _batch_latency_ms(batch, action_lookup) for batch in plan.ordered_batches
    }
    original_total_ms = sum(batch_latency_by_id.values())

    component_validations_ok = all(candidate.validation_passed for candidate in accepted_candidates)
    conflict_free = not conflicts
    contiguous_coverage_ok = True
    savings_consistency_ok = True
    batch_order_preserved = True
    projection_ok = True
    ble_constraints_ok = True
    api_constraints_ok = True
    event_loop_constraints_ok = True

    accepted_ranges: List[Tuple[int, int, CombinedCandidate]] = []
    for candidate in accepted_candidates:
        start_idx, end_idx, contiguous, local_reasons = _candidate_batch_range(candidate, batch_index_by_id, combined_policy)
        if local_reasons:
            reasons.extend(f"{candidate.source}:{candidate.corridor_id}:{reason}" for reason in local_reasons)
        if not contiguous:
            contiguous_coverage_ok = False
        accepted_ranges.append((start_idx, end_idx, candidate))

    accepted_ranges.sort(key=lambda row: (row[0], row[1], row[2].source, row[2].corridor_id))
    by_start_index: Dict[int, Tuple[int, CombinedCandidate]] = {}
    for start_idx, end_idx, candidate in accepted_ranges:
        if start_idx in by_start_index:
            contiguous_coverage_ok = False
            reasons.append(f"{candidate.source}:{candidate.corridor_id}:duplicate_start_index")
        by_start_index[start_idx] = (end_idx, candidate)

    simulated_events: List[CombinedSimulatedEvent] = []
    batch_completion: Dict[str, int] = {}
    actual_total_saved_ms = 0
    cursor = 0
    index = 0
    while index < len(plan.ordered_batches):
        batch = plan.ordered_batches[index]
        if index in by_start_index:
            end_idx, candidate = by_start_index[index]
            segment_batch_ids = [plan.ordered_batches[pos].batch_id for pos in range(index, end_idx + 1)]
            if segment_batch_ids != candidate.batch_ids:
                contiguous_coverage_ok = False
                reasons.append(f"{candidate.source}:{candidate.corridor_id}:batch_projection_mismatch")
            original_segment_ms = sum(batch_latency_by_id[batch_id] for batch_id in segment_batch_ids)
            local_events, local_completion, local_end, local_reasons = _simulate_candidate_segment(
                candidate,
                shift_ms=cursor,
                action_lookup=action_lookup,
            )
            if local_reasons:
                projection_ok = False
                reasons.extend(f"{candidate.source}:{candidate.corridor_id}:{reason}" for reason in local_reasons)
            if combined_policy.require_segment_local_refinement and local_end > original_segment_ms:
                savings_consistency_ok = False
                reasons.append(f"{candidate.source}:{candidate.corridor_id}:refined_segment_longer_than_original")
            actual_segment_saving = max(0, original_segment_ms - local_end)
            if actual_segment_saving != candidate.latency_saved_ms:
                savings_consistency_ok = False
                reasons.append(
                    f"{candidate.source}:{candidate.corridor_id}:reported_saving_mismatch:{candidate.latency_saved_ms}!={actual_segment_saving}"
                )
            actual_total_saved_ms += actual_segment_saving
            simulated_events.extend(local_events)
            batch_completion.update(local_completion)
            cursor += local_end
            index = end_idx + 1
            continue

        duration = batch_latency_by_id[batch.batch_id]
        simulated_events.append(
            CombinedSimulatedEvent(
                source="COARSE",
                corridor_id="",
                owner_id=batch.batch_id,
                batch_id=batch.batch_id,
                phase="COARSE_BATCH",
                start_ms=cursor,
                end_ms=cursor + duration,
                protocol="MIXED",
            )
        )
        batch_completion[batch.batch_id] = cursor + duration
        cursor += duration
        index += 1

    simulated_total_ms = cursor
    if original_total_ms - simulated_total_ms != actual_total_saved_ms:
        savings_consistency_ok = False
        reasons.append("global_savings_mismatch")

    completion_list = [batch_completion.get(batch.batch_id, -1) for batch in plan.ordered_batches]
    if any(value < 0 for value in completion_list):
        batch_order_preserved = False
        reasons.append("missing_batch_completion")
    elif completion_list != sorted(completion_list):
        batch_order_preserved = False
        reasons.append("batch_completion_order_changed")

    if combined_policy.enforce_batch_order_projection:
        accepted_batch_ids = {batch_id for candidate in accepted_candidates for batch_id in candidate.batch_ids}
        for batch in plan.ordered_batches:
            if batch.batch_id not in batch_completion:
                projection_ok = False
                reasons.append(f"projection_missing:{batch.batch_id}")
            if batch.batch_id not in accepted_batch_ids:
                baseline_completion = 0
                for prior in plan.ordered_batches[: batch_index_by_id[batch.batch_id] + 1]:
                    baseline_completion += batch_latency_by_id[prior.batch_id]
                if batch_completion[batch.batch_id] > baseline_completion:
                    projection_ok = False
                    reasons.append(f"projection_non_refined_batch_delayed:{batch.batch_id}")

    ble_xfer_overlap = _sweep_max_overlap(
        simulated_events,
        phase_filter={"BLE_XFER"},
    )
    if any(count > combined_policy.ble_global_xfer_limit for count in ble_xfer_overlap.values()):
        ble_constraints_ok = False
        reasons.append("ble_xfer_global_limit_exceeded")

    ble_connect_prepare_overlap = _sweep_max_overlap(
        simulated_events,
        phase_filter={"PREPARE_CONNECT_SIDE"},
    )
    if ble_policy.enforce_connection_slot_guard and any(
        count > combined_policy.ble_global_connect_prepare_limit for count in ble_connect_prepare_overlap.values()
    ):
        ble_constraints_ok = False
        reasons.append("ble_connect_prepare_global_limit_exceeded")

    cloud_by_host = _sweep_max_overlap(
        simulated_events,
        phase_filter={"CLOUD_REQUEST_SEND"},
        key_fn=lambda event: event.host_key or "__missing__",
    )
    if any(count > combined_policy.cloud_host_request_limit for count in cloud_by_host.values()):
        api_constraints_ok = False
        reasons.append("cloud_host_request_limit_exceeded")

    cloud_by_bucket = _sweep_max_overlap(
        simulated_events,
        phase_filter={"CLOUD_REQUEST_SEND"},
        key_fn=lambda event: event.bucket_key or "__missing__",
    )
    if any(count > combined_policy.cloud_bucket_request_limit for count in cloud_by_bucket.values()):
        api_constraints_ok = False
        reasons.append("cloud_bucket_request_limit_exceeded")

    local_by_endpoint = _sweep_max_overlap(
        simulated_events,
        phase_filter={"LOCAL_REQUEST_SEND"},
        key_fn=lambda event: event.endpoint_key or "__missing__",
    )
    if any(count > combined_policy.local_endpoint_request_limit for count in local_by_endpoint.values()):
        api_constraints_ok = False
        reasons.append("local_endpoint_request_limit_exceeded")

    local_by_session = _sweep_max_overlap(
        simulated_events,
        phase_filter={"LOCAL_REQUEST_SEND"},
        key_fn=lambda event: event.session_key or "__missing__",
    )
    if any(count > combined_policy.local_session_request_limit for count in local_by_session.values()):
        api_constraints_ok = False
        reasons.append("local_session_request_limit_exceeded")

    parse_overlap = _sweep_max_overlap(
        simulated_events,
        phase_filter={
            "API_PARSE_NORMALIZE",
            "API_AGGREGATE",
            "LOCAL_PARSE",
            "LOCAL_CACHE_UPDATE",
            "MQTT_CACHE_PARSE",
        },
    )
    if any(count > combined_policy.max_global_parse_overlap for count in parse_overlap.values()):
        event_loop_constraints_ok = False
        reasons.append("global_parse_overlap_limit_exceeded")

    backoff_events = [
        event
        for event in simulated_events
        if event.phase == "CLOUD_BACKOFF_WAIT" and event.host_key and event.end_ms > event.start_ms
    ]
    for backoff_event in backoff_events:
        for event in simulated_events:
            if event.host_key != backoff_event.host_key or event.owner_id == backoff_event.owner_id:
                continue
            if event.phase in {"CLOUD_AUTH_CHECK", "CLOUD_RATE_BUDGET_CHECK", "API_PREPARE", "CLOUD_REQUEST_SEND"}:
                if event.start_ms < backoff_event.end_ms:
                    api_constraints_ok = False
                    reasons.append(f"cloud_backoff_bypass:{backoff_event.batch_id}->{event.batch_id}")
                    break

    simulated_by_owner: Dict[str, List[CombinedSimulatedEvent]] = {}
    for event in simulated_events:
        if event.source == "API":
            simulated_by_owner.setdefault(event.owner_id, []).append(event)
    for owner_events in simulated_by_owner.values():
        owner_events.sort(key=lambda row: (row.start_ms, row.end_ms, row.phase))

    for candidate in accepted_candidates:
        if candidate.source != "API":
            continue
        owner_ids = list(candidate.payload.get("owner_ids", []))
        for left_owner, right_owner in zip(owner_ids, owner_ids[1:]):
            left_events = simulated_by_owner.get(left_owner, [])
            right_events = simulated_by_owner.get(right_owner, [])
            left_write = next((event for event in left_events if event.phase == "HA_STATE_WRITE"), None)
            left_request = next((event for event in left_events if event.phase in {"CLOUD_REQUEST_SEND", "LOCAL_REQUEST_SEND", "MQTT_LAST_MSG_READ"}), None)
            left_response = next((event for event in left_events if event.phase in {"API_RESPONSE_RECV", "LOCAL_RESPONSE_RECV"}), None)
            right_request = next((event for event in right_events if event.phase in {"CLOUD_REQUEST_SEND", "LOCAL_REQUEST_SEND", "MQTT_LAST_MSG_READ"}), None)
            if left_write is not None and right_request is not None and right_request.start_ms < left_write.end_ms:
                api_constraints_ok = False
                reasons.append(f"api_request_before_previous_write:{left_owner}->{right_owner}")
            if left_request is not None and left_response is not None:
                right_overlap_events = [
                    event
                    for event in right_events
                    if event.phase in {"CLOUD_AUTH_CHECK", "CLOUD_RATE_BUDGET_CHECK", "API_PREPARE", "LOCAL_ENDPOINT_RESOLVE", "LOCAL_SESSION_READY"}
                ]
                for event in right_overlap_events:
                    if event.start_ms < left_request.start_ms:
                        api_constraints_ok = False
                        reasons.append(f"api_prepare_started_too_early:{left_owner}->{right_owner}:{event.phase}")
                    if event.end_ms > left_response.end_ms:
                        api_constraints_ok = False
                        reasons.append(f"api_prepare_window_violation:{left_owner}->{right_owner}:{event.phase}")

    passed = all(
        (
            component_validations_ok,
            conflict_free,
            contiguous_coverage_ok,
            savings_consistency_ok,
            batch_order_preserved,
            projection_ok,
            ble_constraints_ok,
            api_constraints_ok,
            event_loop_constraints_ok,
        )
    )
    result = CombinedMicroValidationResult(
        passed=passed,
        component_validations_ok=component_validations_ok,
        conflict_free=conflict_free,
        contiguous_coverage_ok=contiguous_coverage_ok,
        savings_consistency_ok=savings_consistency_ok,
        batch_order_preserved=batch_order_preserved,
        projection_ok=projection_ok,
        ble_constraints_ok=ble_constraints_ok,
        api_constraints_ok=api_constraints_ok,
        event_loop_constraints_ok=event_loop_constraints_ok,
        simulated_total_ms=simulated_total_ms,
        simulated_event_count=len(simulated_events),
        reasons=reasons,
    )
    return result, simulated_events, actual_total_saved_ms


class ConservativeCombinedMicroRefiner:


    def __init__(
        self,
        *,
        ble_policy: BLEMicroRefinementPolicy | None = None,
        api_policy: APIMicroRefinementPolicy | None = None,
        combined_policy: CombinedMicroRefinementPolicy | None = None,
    ) -> None:
        self.ble_policy = ble_policy or BLEMicroRefinementPolicy()
        self.api_policy = api_policy or APIMicroRefinementPolicy()
        self.combined_policy = combined_policy or CombinedMicroRefinementPolicy()
        self.ble_refiner = ConservativeBLEMicroRefiner(policy=self.ble_policy)
        self.api_refiner = ConservativeAPIMicroRefiner(policy=self.api_policy)

    def _refined_plan_overlay(
        self,
        plan: ExecutionPlan,
        *,
        ble_result: BLEMicroCaseResult,
        api_result: APIMicroCaseResult,
        validation: CombinedMicroValidationResult,
        accepted_corridors: List[Dict[str, Any]],
        rejected_corridors: List[Dict[str, Any]],
    ) -> ExecutionPlan:
        plan_copy = ExecutionPlan(
            ordered_batches=[
                Batch(
                    batch_id=batch.batch_id,
                    parallel_groups=[list(group) for group in batch.parallel_groups],
                    constraints=list(batch.constraints),
                    session_policy=dict(batch.session_policy),
                    rate_policy=dict(batch.rate_policy),
                    guards=[dict(item) for item in batch.guards],
                    fallback=[dict(item) for item in batch.fallback],
                )
                for batch in plan.ordered_batches
            ],
            meta=dict(plan.meta),
        )
        plan_copy.meta["ble_micro_refinement"] = ble_result.refined_plan.meta.get("ble_micro_refinement", {})
        plan_copy.meta["api_micro_refinement"] = api_result.refined_plan.meta.get("api_micro_refinement", {})
        plan_copy.meta["combined_micro_refinement"] = {
            "enabled": True,
            "policy": self.combined_policy.to_dict(),
            "accepted_corridors": accepted_corridors,
            "rejected_corridors": rejected_corridors,
            "validation": asdict(validation),
        }
        return plan_copy

    def refine_case(
        self,
        *,
        vdev_id: str,
        case_name: str,
        target: OptimizationTarget,
        plan: ExecutionPlan,
    ) -> CombinedMicroCaseResult:
        original_total_ms = estimate_plan_latency_ms(plan, target)

        ble_result = self.ble_refiner.refine_case(vdev_id=vdev_id, case_name=case_name, target=target, plan=plan)
        api_result = self.api_refiner.refine_case(vdev_id=vdev_id, case_name=case_name, target=target, plan=plan)
        api_steps, _ = self.api_refiner._select_corridors(plan, target)
        api_steps_by_id = {step.step_id: step for step in api_steps}

        ble_candidates = _build_ble_candidates(ble_result, target)
        api_candidates = _build_api_candidates(api_result, api_steps_by_id)
        decision = resolve_combined_candidates(ble_candidates, api_candidates, self.combined_policy)
        validation, simulated_events, combined_saved_ms = validate_combined_candidates(
            plan=plan,
            target=target,
            accepted_candidates=decision.accepted,
            rejected_candidates=decision.rejected,
            conflicts=decision.conflicts,
            ble_policy=self.ble_policy,
            api_policy=self.api_policy,
            combined_policy=self.combined_policy,
        )

        accepted_corridors = [
            {
                "source": candidate.source,
                "corridor_id": candidate.corridor_id,
                "batch_ids": list(candidate.batch_ids),
                "action_ids": list(candidate.action_ids),
                "latency_saved_ms": candidate.latency_saved_ms,
                "validation_passed": candidate.validation_passed,
            }
            for candidate in decision.accepted
        ]
        rejected_corridors = [
            {
                "source": candidate.source,
                "corridor_id": candidate.corridor_id,
                "batch_ids": list(candidate.batch_ids),
                "action_ids": list(candidate.action_ids),
                "latency_saved_ms": candidate.latency_saved_ms,
                "validation_passed": candidate.validation_passed,
            }
            for candidate in decision.rejected
        ]
        refined_plan = self._refined_plan_overlay(
            plan,
            ble_result=ble_result,
            api_result=api_result,
            validation=validation,
            accepted_corridors=accepted_corridors,
            rejected_corridors=rejected_corridors,
        )
        return CombinedMicroCaseResult(
            vdev_id=vdev_id,
            case_name=case_name,
            ble_added_savings_ms=ble_result.added_savings_ms,
            api_added_savings_ms=api_result.added_savings_ms,
            combined_added_savings_ms=combined_saved_ms,
            combined_added_savings_ratio=(float(combined_saved_ms) / float(original_total_ms)) if original_total_ms else 0.0,
            original_estimated_latency_ms=original_total_ms,
            combined_refined_estimated_latency_ms=validation.simulated_total_ms,
            conflict_count=len(decision.conflicts),
            accepted_corridors=accepted_corridors,
            rejected_corridors=rejected_corridors,
            validation=validation,
            simulated_events=simulated_events,
            refined_plan=refined_plan,
        )


MicroLevelScheduler = ConservativeCombinedMicroRefiner
