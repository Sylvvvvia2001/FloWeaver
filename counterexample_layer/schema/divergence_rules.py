from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List

from dsl.contracts import Event, Trace
from runtime.trace import compare_traces, normalize_op_name

from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel
from counterexample_layer.symbolic.sym_state import SymConfig
from counterexample_layer.witness.witness import ViolatedProperty

RESOURCE_PROTOCOL_OPS = {
    "SUBSCRIBE",
    "UNSUBSCRIBE",
    "BLE_CONNECT",
    "BLE_DISCONNECT",
    "CLOUD_SESSION_REUSE",
    "ENTRY_UNLOAD",
}


@dataclass
class DivergenceResult:
    is_divergent: bool
    violated_property: str | None = None
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


def _trace_from_events(events: List[Event]) -> Trace:
    return Trace(events=list(events), meta={})


def _latest_hunk(diff_hunks: List[Any]) -> Dict[str, Any]:
    if not diff_hunks:
        return {}
    hunk = diff_hunks[0]
    if hasattr(hunk, "__dict__"):
        return dict(hunk.__dict__)
    if isinstance(hunk, dict):
        return dict(hunk)
    return {}


def _final_state_values(trace: Trace) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for event in trace.events:
        if normalize_op_name(event.op) != "STATE_WRITE":
            continue
        params = event.params_abst if isinstance(event.params_abst, dict) else {}
        for key in ("state", "value", "payload_hash", "body_hash", "json_hash"):
            if key in params:
                values[str(event.target)] = params[key]
                break
        else:
            values[str(event.target)] = params
    return values


def _resource_keys(state: Dict[str, Any]) -> List[str]:
    keys: List[str] = []
    for resource_kind, resources in state.items():
        if not isinstance(resources, dict):
            continue
        for key, payload in resources.items():
            if not isinstance(payload, dict):
                continue
            if int(payload.get("count", 0)):
                keys.append(f"{resource_kind}:{key}")
    return sorted(keys)


def check_trace_mismatch(cfg: SymConfig, observation_schema: CounterexampleObservationSchema) -> DivergenceResult:
    diff = compare_traces(
        cfg.trace_b,
        cfg.trace_o,
        config=observation_schema.trace_compare_config,
    )
    if diff.tolerant_equal:
        return DivergenceResult(is_divergent=False)

    latest = _latest_hunk(diff.diff_signature)
    ops = set()
    for token in latest.get("baseline_ops", []) + latest.get("optimized_ops", []):
        text = str(token)
        parts = text.split(":", 3)
        if len(parts) >= 3:
            ops.add(normalize_op_name(parts[2]))
        else:
            ops.add(normalize_op_name(text))
    resource_only = bool(ops) and ops.issubset(RESOURCE_PROTOCOL_OPS)
    if resource_only:
        return DivergenceResult(is_divergent=False, details={"defer_to_resource_protocol": True})

    return DivergenceResult(
        is_divergent=True,
        violated_property=ViolatedProperty.TRACE_MISMATCH.value,
        reason="trace_prefix_mismatch",
        details={
            "compare_meta": dict(diff.meta),
            "diff_hunks": [dict(hunk.__dict__) for hunk in diff.diff_signature],
        },
    )


def check_final_state_mismatch(cfg: SymConfig, observation_schema: CounterexampleObservationSchema) -> DivergenceResult:
    baseline_values = _final_state_values(cfg.trace_b)
    optimized_values = _final_state_values(cfg.trace_o)
    if baseline_values != optimized_values:
        return DivergenceResult(
            is_divergent=True,
            violated_property=ViolatedProperty.FINAL_STATE_MISMATCH.value,
            reason="final_state_values_differ",
            details={
                "baseline_final_state": baseline_values,
                "optimized_final_state": optimized_values,
            },
        )

    if cfg.semantic_state_b.get("exception_category") != cfg.semantic_state_o.get("exception_category"):
        return DivergenceResult(
            is_divergent=True,
            violated_property=ViolatedProperty.FINAL_STATE_MISMATCH.value,
            reason="exception_category_differ",
            details={
                "baseline_exception": cfg.semantic_state_b.get("exception_category"),
                "optimized_exception": cfg.semantic_state_o.get("exception_category"),
            },
        )

    for entity_id, expected in observation_schema.required_final_state.items():
        if baseline_values.get(entity_id) != optimized_values.get(entity_id):
            return DivergenceResult(
                is_divergent=True,
                violated_property=ViolatedProperty.FINAL_STATE_MISMATCH.value,
                reason="required_final_state_mismatch",
                details={
                    "entity_id": entity_id,
                    "baseline": baseline_values.get(entity_id),
                    "optimized": optimized_values.get(entity_id),
                    "expected": expected,
                },
            )
    return DivergenceResult(is_divergent=False)


def _op_sequence(trace: Trace) -> List[str]:
    return [normalize_op_name(event.op) for event in trace.events]


def _required_before_violated(trace: Trace, required_before: List[str], acquire_ops: List[str]) -> bool:
    acquired = False
    for event in trace.events:
        op = normalize_op_name(event.op)
        if op in acquire_ops:
            acquired = True
        if op in required_before and not acquired:
            return True
    return False


def check_resource_protocol_violation(cfg: SymConfig, resource_model: ResourceModel) -> DivergenceResult:
    details: List[Dict[str, Any]] = []
    at_terminal = bool(cfg.divergence_status.get("at_terminal"))
    for resource_kind, rule in resource_model.rules.items():
        left = cfg.resource_state_b.get(resource_kind, {})
        right = cfg.resource_state_o.get(resource_kind, {})
        all_keys = sorted(set(left) | set(right))
        for key in all_keys:
            left_payload = left.get(key, {}) if isinstance(left.get(key, {}), dict) else {}
            right_payload = right.get(key, {}) if isinstance(right.get(key, {}), dict) else {}
            left_count = int(left_payload.get("count", 0))
            right_count = int(right_payload.get("count", 0))
            if left_payload.get("premature_release") or right_payload.get("premature_release"):
                return DivergenceResult(
                    is_divergent=True,
                    violated_property=ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value,
                    reason="premature_cleanup",
                    details={"resource_kind": resource_kind, "resource_key": key},
                )
            if rule.forbid_overlap and (left_count > 1 or right_count > 1):
                return DivergenceResult(
                    is_divergent=True,
                    violated_property=ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value,
                    reason="illegal_overlap",
                    details={"resource_kind": resource_kind, "resource_key": key, "counts": [left_count, right_count]},
                )
            if at_terminal and rule.must_release and (left_count != 0 or right_count != 0):
                return DivergenceResult(
                    is_divergent=True,
                    violated_property=ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value,
                    reason="missing_release_or_unsubscribe",
                    details={"resource_kind": resource_kind, "resource_key": key, "counts": [left_count, right_count]},
                )
            if at_terminal and left_count != right_count:
                details.append(
                    {
                        "resource_kind": resource_kind,
                        "resource_key": key,
                        "baseline_count": left_count,
                        "optimized_count": right_count,
                    }
                )
        if at_terminal and rule.required_before:
            baseline_missing = _required_before_violated(cfg.trace_b, rule.required_before, rule.acquire_ops)
            optimized_missing = _required_before_violated(cfg.trace_o, rule.required_before, rule.acquire_ops)
            if baseline_missing != optimized_missing:
                return DivergenceResult(
                    is_divergent=True,
                    violated_property=ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value,
                    reason="wrong_session_reuse_or_missing_required_before",
                    details={
                        "resource_kind": resource_kind,
                        "required_before": list(rule.required_before),
                        "baseline_missing": baseline_missing,
                        "optimized_missing": optimized_missing,
                    },
                )

    left_trace_ops = Counter(normalize_op_name(event.op) for event in cfg.trace_b.events)
    right_trace_ops = Counter(normalize_op_name(event.op) for event in cfg.trace_o.events)
    if at_terminal and left_trace_ops.get("ENTRY_UNLOAD", 0) != right_trace_ops.get("ENTRY_UNLOAD", 0):
        details.append({"resource_kind": "lifecycle", "reason": "setup_unload_boundary_violation"})

    if details:
        return DivergenceResult(
            is_divergent=True,
            violated_property=ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value,
            reason="resource_state_diverged",
            details={"differences": details},
        )
    return DivergenceResult(is_divergent=False)


def check_unsupported_alignment(cfg: SymConfig) -> DivergenceResult:
    current = cfg.divergence_status.get("current_useg_node", {})
    if current.get("unsupported_alignment") and current.get("crosses_observation_boundary"):
        return DivergenceResult(
            is_divergent=True,
            violated_property=ViolatedProperty.UNSUPPORTED_ALIGNMENT.value,
            reason="split_region_crosses_observation_boundary",
            details={"suspicious_region_id": current.get("suspicious_region_id")},
        )
    return DivergenceResult(is_divergent=False)


def check_divergence(
    cfg: SymConfig,
    observation_schema: CounterexampleObservationSchema,
    resource_model: ResourceModel,
) -> DivergenceResult:
    unsupported = check_unsupported_alignment(cfg)
    if unsupported.is_divergent:
        return unsupported

    trace_result = check_trace_mismatch(cfg, observation_schema)
    if trace_result.is_divergent:
        return trace_result

    current = cfg.divergence_status.get("current_useg_node", {})
    at_terminal = bool(cfg.divergence_status.get("at_terminal"))
    if at_terminal:
        final_state_result = check_final_state_mismatch(cfg, observation_schema)
        if final_state_result.is_divergent:
            return final_state_result

    resource_result = check_resource_protocol_violation(cfg, resource_model)
    if resource_result.is_divergent:
        return resource_result

    return DivergenceResult(is_divergent=False, details={"current_useg_node": current})
