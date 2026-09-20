from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

_ALLOWED_TRIGGER_PATTERNS = {
    "cleanup_before_act",
    "missing_unsubscribe",
    "premature_cleanup",
    "illegal_overlap",
    "wrong_session_reuse",
    "update_before_ready",
    "refresh_before_setup_done",
    "state_write_order_mismatch",
    "return_value_mismatch",
    "exception_category_mismatch",
    "unsupported_alignment_pattern",
    "unknown_trigger",
}

_ALLOWED_REFINEMENTS = {
    "add hard pairing between SUBSCRIBE and UNSUBSCRIBE",
    "promote NO_OVERLAP to hard constraint",
    "forbid early cleanup for this resource class",
    "split shared-context reuse rule by protocol",
    "add alignment rule for listener-preserving batch",
    "refine observation boundary around state-write ordering",
    "strengthen final-state equivalence check",
    "preserve exception category at observation boundary",
}


def _ops(trace_prefix: Iterable[Dict[str, Any]]) -> list[str]:
    return [str(item.get("op", "")) for item in trace_prefix if isinstance(item, dict)]


def infer_trigger_pattern(normalized_witness: dict, context: dict) -> str:
    explicit = str(normalized_witness.get("trigger_pattern", "") or "").strip()
    if explicit in _ALLOWED_TRIGGER_PATTERNS:
        return explicit

    violated_property = str(normalized_witness.get("violated_property", ""))
    reason = str(normalized_witness.get("divergence_point", {}).get("reason", "")).lower()
    baseline_ops = _ops(normalized_witness.get("baseline_trace_prefix", []))
    optimized_ops = _ops(normalized_witness.get("optimized_trace_prefix", []))
    combined = baseline_ops + optimized_ops

    if violated_property == "UNSUPPORTED_ALIGNMENT":
        return "unsupported_alignment_pattern"
    if violated_property == "FINAL_STATE_MISMATCH":
        if "exception" in reason:
            return "exception_category_mismatch"
        return "return_value_mismatch"
    if violated_property == "RESOURCE_PROTOCOL_VIOLATION":
        if "overlap" in reason:
            return "illegal_overlap"
        if "session" in reason:
            return "wrong_session_reuse"
        if "unsubscribe" in reason or "missing_release" in reason:
            return "missing_unsubscribe"
        if "cleanup" in reason or "premature" in reason:
            if any(op in {"ENTRY_UNLOAD", "UNSUBSCRIBE", "BLE_DISCONNECT"} for op in baseline_ops[-1:] + optimized_ops[-1:]):
                return "premature_cleanup"
            return "cleanup_before_act"
    if violated_property == "TRACE_MISMATCH":
        if "COORD_REFRESH" in combined and "ENTRY_SETUP" in combined:
            return "refresh_before_setup_done"
        if "STATE_WRITE" in combined and "COORD_REFRESH" in combined:
            return "state_write_order_mismatch"
        if context.get("phase_context") == "SETUP":
            return "update_before_ready"
    return "unknown_trigger"


def infer_rule_gap_and_refinement(
    violated_property: str,
    trigger_pattern: str,
    context: dict,
) -> tuple[str | None, str | None]:
    _ = violated_property
    if trigger_pattern == "unsupported_alignment_pattern":
        if context.get("resource_context") == "CLOUD_LISTENER":
            return ("ALIGNMENT_RULE_MISSING", "add alignment rule for listener-preserving batch")
        return ("ALIGNMENT_RULE_MISSING", None)

    mapping = {
        "missing_unsubscribe": (
            "MISSING_LIFECYCLE_PAIRING_RULE",
            "add hard pairing between SUBSCRIBE and UNSUBSCRIBE",
        ),
        "wrong_session_reuse": (
            "RESOURCE_REUSE_RULE_TOO_LOOSE",
            "split shared-context reuse rule by protocol",
        ),
        "cleanup_before_act": (
            "MISSING_HARD_LIFECYCLE_EDGE",
            "forbid early cleanup for this resource class",
        ),
        "premature_cleanup": (
            "MISSING_HARD_LIFECYCLE_EDGE",
            "forbid early cleanup for this resource class",
        ),
        "illegal_overlap": (
            "NO_OVERLAP_TOO_WEAK",
            "promote NO_OVERLAP to hard constraint",
        ),
        "update_before_ready": (
            "MISSING_HARD_LIFECYCLE_EDGE",
            None,
        ),
        "refresh_before_setup_done": (
            "MISSING_HARD_LIFECYCLE_EDGE",
            None,
        ),
        "state_write_order_mismatch": (
            "OBSERVATION_BOUNDARY_TOO_COARSE",
            "refine observation boundary around state-write ordering",
        ),
        "return_value_mismatch": (
            "OBSERVATION_BOUNDARY_TOO_COARSE",
            "strengthen final-state equivalence check",
        ),
        "exception_category_mismatch": (
            "OBSERVATION_BOUNDARY_TOO_COARSE",
            "preserve exception category at observation boundary",
        ),
    }
    return mapping.get(trigger_pattern, ("UNKNOWN_RULE_GAP", None))


def normalize_refinement_template(value: str | None) -> str | None:
    token = str(value or "").strip()
    if not token:
        return None
    return token if token in _ALLOWED_REFINEMENTS else None
