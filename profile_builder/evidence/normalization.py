from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Tuple

from runtime.trace import normalize_op_name

from counterexample_layer.witness.witness import CounterexampleWitness

_UNKNOWN_PROTOCOL = "UNKNOWN"
_UNKNOWN_PHASE = "UNKNOWN"

_KEY_FIELDS = {"concurrency_level", "bucket_size", "timeout_enabled", "retry_count"}
_KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.+)$")


def _stable_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _normalize_protocol(value: Any) -> str:
    token = str(value or _UNKNOWN_PROTOCOL).strip().upper() or _UNKNOWN_PROTOCOL
    if token == "HA":
        return "LOCAL_API"
    return token if token in {"BLE", "CLOUD", "LOCAL_API", _UNKNOWN_PROTOCOL} else _UNKNOWN_PROTOCOL


def _normalize_phase(value: Any) -> str:
    token = str(value or _UNKNOWN_PHASE).strip().upper() or _UNKNOWN_PHASE
    return token if token in {"SETUP", "RUNTIME", "TEARDOWN", _UNKNOWN_PHASE} else _UNKNOWN_PHASE


def _normalize_trace_prefix(trace_prefix: List[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for row in trace_prefix or []:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "provider": str(row.get("provider", "")).upper(),
                "op": normalize_op_name(str(row.get("op", ""))),
                "target": str(row.get("target", "")),
                "phase": _normalize_phase(row.get("phase")),
                "params_abst": dict(row.get("params_abst", {})) if isinstance(row.get("params_abst", {}), dict) else {},
            }
        )
    return normalized


def _coerce_scalar(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null", "unknown"}:
        return None
    if re.fullmatch(r"-?\d+", value.strip()):
        return int(value.strip())
    if re.fullmatch(r"-?\d+\.\d+", value.strip()):
        return float(value.strip())
    return value.strip().strip("\"'")


def _parse_minimal_conditions(
    raw_conditions: List[str],
    input_assumptions: Dict[str, Any],
    environment_assumptions: Dict[str, Any],
) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {"raw_conditions": [str(item) for item in raw_conditions if str(item).strip()]}

    for condition in normalized["raw_conditions"]:
        if "." in condition:
            _, _, tail = condition.partition(".")
        else:
            tail = condition
        match = _KEY_VALUE_RE.search(tail)
        if not match:
            continue
        key = match.group("key")
        if key not in _KEY_FIELDS:
            continue
        normalized[key] = _coerce_scalar(match.group("value"))

    for mapping in (
        dict(input_assumptions.get("request_params", {})),
        dict(input_assumptions.get("symbolic_inputs", {})),
        dict(environment_assumptions.get("toggle_assumptions", {})),
        dict(environment_assumptions.get("device_results", {})),
    ):
        for key, value in mapping.items():
            normalized_key = str(key)
            if normalized_key in _KEY_FIELDS and normalized.get(normalized_key) is None:
                normalized[normalized_key] = value
            if "timeout" in normalized_key and "timeout_enabled" not in normalized:
                normalized["timeout_enabled"] = bool(value)

    for key in _KEY_FIELDS:
        normalized.setdefault(key, None)
    return normalized


def _witness_id(witness: CounterexampleWitness) -> str:
    explicit = witness.metadata.get("witness_id") if isinstance(witness.metadata, dict) else None
    if explicit:
        return str(explicit)
    payload = "::".join(
        [
            str(witness.verdict),
            str(witness.violated_property),
            str(witness.divergence_point),
            str(witness.suspicious_region_id),
            "|".join(str(item) for item in witness.minimal_conditions),
        ]
    )
    return _stable_id("WIT", payload)


def make_trace_signature(trace_prefix: List[Dict[str, Any]], k: int = 4) -> tuple[str, ...]:
    def target_scope(target: str) -> str:
        lowered = target.lower()
        if "." in target and not target.startswith("/"):
            return "ENTITY"
        if "entry" in lowered:
            return "ENTRY"
        if "coordinator" in lowered:
            return "COORDINATOR"
        if any(token in lowered for token in ("manager", "listener", "session")):
            return "MANAGER"
        if target.startswith("/") or "device" in lowered or lowered.startswith("ble:"):
            return "DEVICE"
        return "UNKNOWN_SCOPE"

    rows = _normalize_trace_prefix(trace_prefix)
    compact = [f"{row['op']}:{target_scope(row['target'])}" for row in rows if row.get("op")]
    return tuple(compact[-max(1, k):])


def normalize_witness(witness: CounterexampleWitness) -> Dict[str, Any]:
    baseline_trace_prefix = _normalize_trace_prefix(witness.baseline_trace_prefix)
    optimized_trace_prefix = _normalize_trace_prefix(witness.optimized_trace_prefix)
    divergence_point = dict(witness.divergence_point or {})
    divergence_point.setdefault("details", {})
    return {
        "witness_id": _witness_id(witness),
        "verdict": str(witness.verdict),
        "violated_property": str(witness.violated_property or "UNKNOWN_VIOLATION"),
        "input_assumptions": dict(witness.input_assumptions or {}),
        "environment_assumptions": dict(witness.environment_assumptions or {}),
        "baseline_trace_prefix": baseline_trace_prefix,
        "optimized_trace_prefix": optimized_trace_prefix,
        "divergence_point": divergence_point,
        "baseline_state_at_divergence": dict(witness.baseline_state_at_divergence or {}),
        "optimized_state_at_divergence": dict(witness.optimized_state_at_divergence or {}),
        "minimal_conditions": _parse_minimal_conditions(
            [str(item) for item in witness.minimal_conditions],
            dict(witness.input_assumptions or {}),
            dict(witness.environment_assumptions or {}),
        ),
        "suspicious_region_id": witness.suspicious_region_id,
        "refinement_hint": witness.refinement_hint,
        "protocol_context": _normalize_protocol(witness.protocol_context),
        "phase_context": _normalize_phase(witness.phase_context),
        "trigger_pattern": str(witness.trigger_pattern or ""),
        "suspected_rule_gap": str(witness.suspected_rule_gap) if witness.suspected_rule_gap else None,
        "metadata": dict(witness.metadata or {}),
    }
