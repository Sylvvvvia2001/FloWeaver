from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List

from dsl.contracts import DiffResult, OptimizationTarget, Trace
from runtime.trace import (
    TraceCompareConfig,
    assert_trace_contract,
    canonicalize_trace,
    compare_traces,
    normalize_op_name,
    trace_compare_meta,
)

TRACE_EVENT_OPS = {
    "ENTRY_SETUP",
    "ENTRY_UNLOAD",
    "COORD_REFRESH",
    "STATE_WRITE",
    "SUBSCRIBE",
    "UNSUBSCRIBE",
    "BLE_CONNECT",
    "BLE_DISCONNECT",
    "BLE_GATT_OP",
    "BLE_SCAN",
    "BLE_RETRY_OR_TIMEOUT",
    "CLOUD_HTTP_CALL",
    "CLOUD_TOKEN_REFRESH",
    "CLOUD_429_CHECK",
    "CLOUD_BACKOFF_SLEEP",
    "CLOUD_SESSION_REUSE",
    "CLOUD_BATCH_CALL",
    "EXCEPTION",
}


@dataclass
class ObservationSchema:
    semantic_ops: List[str] = field(
        default_factory=lambda: [
            "ENTRY_SETUP",
            "ENTRY_UNLOAD",
            "COORD_REFRESH",
            "STATE_WRITE",
            "SUBSCRIBE",
            "UNSUBSCRIBE",
            "BLE_CONNECT",
            "BLE_DISCONNECT",
            "BLE_GATT_OP",
            "BLE_SCAN",
            "BLE_RETRY_OR_TIMEOUT",
            "CLOUD_HTTP_CALL",
            "CLOUD_TOKEN_REFRESH",
            "CLOUD_429_CHECK",
            "CLOUD_BACKOFF_SLEEP",
            "EXCEPTION",
        ]
    )
    canonicalization_version: str = "v1"
    required_state_writes: List[str] = field(default_factory=list)
    required_final_state: Dict[str, Any] = field(default_factory=dict)
    op_count_bounds: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    op_count_factor_upper: Dict[str, float] = field(default_factory=dict)
    anchor_ops: List[str] = field(default_factory=list)
    ignored_anchor_ops: List[str] = field(default_factory=list)
    equivalence_whitelist: List[Any] = field(default_factory=list)


class ObservationEngine:
    def __init__(self, schema: ObservationSchema | None = None) -> None:
        self.schema = schema or ObservationSchema()

    @classmethod
    def from_optimization_target(cls, target: OptimizationTarget) -> "ObservationEngine":
        validation = target.validation.get("observation", {}) if isinstance(target.validation, dict) else {}
        configured_ops = validation.get("semantic_ops", []) if isinstance(validation.get("semantic_ops", []), list) else []
        raw_anchor_ops = list(target.target_anchors.get("anchor_ops", []))

        anchor_ops: List[str] = []
        ignored_anchor_ops: List[str] = []
        for item in raw_anchor_ops:
            token = normalize_op_name(item)
            if not token:
                continue
            if token in TRACE_EVENT_OPS:
                if token not in anchor_ops:
                    anchor_ops.append(token)
            else:
                if token not in ignored_anchor_ops:
                    ignored_anchor_ops.append(token)

        semantic_base = configured_ops if configured_ops else ObservationSchema().semantic_ops
        semantic_ops: List[str] = []
        for op in semantic_base + anchor_ops:
            token = normalize_op_name(op)
            if token and token not in semantic_ops:
                semantic_ops.append(token)

        required_state_writes = list(target.target_anchors.get("required_state_writes", []))
        if not required_state_writes and isinstance(validation.get("required_state_writes", []), list):
            required_state_writes = [str(item) for item in validation.get("required_state_writes", []) if str(item).strip()]

        required_final_state = validation.get("required_final_state", {})
        if not isinstance(required_final_state, dict):
            required_final_state = {}

        op_count_bounds = validation.get("op_count_bounds", {})
        if not isinstance(op_count_bounds, dict):
            op_count_bounds = {}

        op_count_factor_upper = validation.get("op_count_factor_upper", {})
        if not isinstance(op_count_factor_upper, dict):
            op_count_factor_upper = {}
        normalized_factor_upper: Dict[str, float] = {}
        for op_name, factor in op_count_factor_upper.items():
            normalized_op = normalize_op_name(op_name)
            if not normalized_op:
                continue
            try:
                normalized_factor_upper[normalized_op] = float(factor)
            except (TypeError, ValueError):
                continue

        whitelist = validation.get("equivalence_whitelist", [])
        if not isinstance(whitelist, list):
            whitelist = []

        schema = ObservationSchema(
            semantic_ops=semantic_ops,
            canonicalization_version=str(validation.get("canonicalization_version", "v1")),
            required_state_writes=required_state_writes,
            required_final_state=required_final_state,
            op_count_bounds=op_count_bounds,
            op_count_factor_upper=normalized_factor_upper,
            anchor_ops=anchor_ops,
            ignored_anchor_ops=ignored_anchor_ops,
            equivalence_whitelist=whitelist,
        )
        return cls(schema=schema)

    def _trace_compare_config(self) -> TraceCompareConfig:
        return TraceCompareConfig.from_observation(
            canonicalization_version=self.schema.canonicalization_version,
            equivalence_whitelist=self.schema.equivalence_whitelist,
        )

    def canonicalize(self, trace: Trace) -> Trace:
        return canonicalize_trace(trace, config=self._trace_compare_config())

    def compare(self, baseline: Trace, optimized: Trace) -> DiffResult:
        return compare_traces(baseline, optimized, config=self._trace_compare_config())

    @staticmethod
    def _extract_last_state_values(trace: Trace) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        for event in trace.events:
            if event.op != "STATE_WRITE":
                continue
            params = event.params_abst if isinstance(event.params_abst, dict) else {}
            if "state" in params:
                values[event.target] = params["state"]
            elif "value" in params:
                values[event.target] = params["value"]
            elif "payload_hash" in params:
                values[event.target] = params["payload_hash"]
            elif "body_hash" in params:
                values[event.target] = params["body_hash"]
            elif "json_hash" in params:
                values[event.target] = params["json_hash"]
            else:
                values[event.target] = params
        return values

    @staticmethod
    def _normalize_expected_state(expected: Any) -> Any:
        if isinstance(expected, dict):
            for key in ("state", "value", "payload_hash", "body_hash", "json_hash"):
                if key in expected:
                    return expected[key]
        return expected

    def assert_contract(self, trace: Trace, baseline_trace: Trace | None = None) -> Dict[str, Any]:
        canonical = self.canonicalize(trace)
        result = assert_trace_contract(canonical, self.schema.semantic_ops)
        write_targets = {
            event.target
            for event in canonical.events
            if event.op == "STATE_WRITE"
        }
        missing_writes = [entity_id for entity_id in self.schema.required_state_writes if entity_id not in write_targets]

        last_state_values = self._extract_last_state_values(canonical)
        final_state_mismatches: List[Dict[str, Any]] = []
        for entity_id, expected in self.schema.required_final_state.items():
            expected_value = self._normalize_expected_state(expected)
            actual_value = last_state_values.get(entity_id)
            if entity_id not in last_state_values or actual_value != expected_value:
                final_state_mismatches.append(
                    {
                        "entity_id": entity_id,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )

        op_counts = Counter(event.op for event in canonical.events)
        op_count_violations: List[Dict[str, Any]] = []
        for op_name, bounds in self.schema.op_count_bounds.items():
            if not isinstance(bounds, dict):
                continue
            normalized_op = normalize_op_name(op_name)
            if not normalized_op:
                continue
            count = int(op_counts.get(normalized_op, 0))
            min_count = bounds.get("min")
            max_count = bounds.get("max")
            if min_count is not None and count < int(min_count):
                op_count_violations.append(
                    {"op": normalized_op, "count": count, "min": int(min_count), "max": max_count}
                )
                continue
            if max_count is not None and count > int(max_count):
                op_count_violations.append(
                    {"op": normalized_op, "count": count, "min": min_count, "max": int(max_count)}
                )

        op_count_factor_violations: List[Dict[str, Any]] = []
        if baseline_trace is not None and self.schema.op_count_factor_upper:
            baseline_canonical = self.canonicalize(baseline_trace)
            baseline_counts = Counter(event.op for event in baseline_canonical.events)
            for op_name, factor in self.schema.op_count_factor_upper.items():
                normalized_op = normalize_op_name(op_name)
                if not normalized_op:
                    continue
                if factor <= 0:
                    continue
                base_count = int(baseline_counts.get(normalized_op, 0))
                max_allowed = int(base_count * factor)
                count = int(op_counts.get(normalized_op, 0))
                if count > max_allowed:
                    op_count_factor_violations.append(
                        {
                            "op": normalized_op,
                            "count": count,
                            "baseline_count": base_count,
                            "factor": factor,
                            "max_allowed": max_allowed,
                        }
                    )

        compare_meta = trace_compare_meta(self._trace_compare_config())
        passed = (
            result.passed
            and not missing_writes
            and not final_state_mismatches
            and not op_count_violations
            and not op_count_factor_violations
        )
        return {
            "passed": passed,
            "failed_ops": result.failed_rules,
            "missing_required_state_writes": missing_writes,
            "final_state_mismatches": final_state_mismatches,
            "op_count_violations": op_count_violations,
            "op_count_factor_violations": op_count_factor_violations,
            "canonicalization_version": self.schema.canonicalization_version,
            "trace_compare_config_hash": compare_meta["config_hash"],
            "effective_commutable_ops": compare_meta["commutable_ops"],
            "effective_equivalence_rules": compare_meta["equivalence_rules"],
            "ignored_anchor_ops": list(self.schema.ignored_anchor_ops),
        }
