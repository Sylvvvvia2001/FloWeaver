from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List

from profile_builder.evidence.evidence_types import CounterexampleEvidence
from profile_builder.evidence.normalization import make_trace_signature, normalize_witness
from profile_builder.evidence.trigger_patterns import (
    infer_rule_gap_and_refinement,
    infer_trigger_pattern,
    normalize_refinement_template,
)
from counterexample_layer.witness.witness import CounterexampleWitness


def _stable_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _latest_target(normalized_witness: dict) -> str:
    for row in list(normalized_witness.get("optimized_trace_prefix", []))[-1:] + list(normalized_witness.get("baseline_trace_prefix", []))[-1:]:
        target = str(row.get("target", "")).strip()
        if target:
            return target
    details = dict(normalized_witness.get("divergence_point", {}).get("details", {}))
    return str(details.get("entity_id") or details.get("target") or "")


def _resource_keys(normalized_witness: dict) -> list[str]:
    baseline = list(normalized_witness.get("baseline_state_at_divergence", {}).get("resource_keys", []))
    optimized = list(normalized_witness.get("optimized_state_at_divergence", {}).get("resource_keys", []))
    return [str(item) for item in baseline + optimized if str(item)]


def infer_context(normalized_witness: dict) -> dict:
    protocol_context = str(normalized_witness.get("protocol_context", "UNKNOWN") or "UNKNOWN")
    if protocol_context == "UNKNOWN":
        providers = [str(item.get("provider", "")).upper() for item in normalized_witness.get("baseline_trace_prefix", []) + normalized_witness.get("optimized_trace_prefix", [])]
        if "BLE" in providers:
            protocol_context = "BLE"
        elif "CLOUD" in providers:
            protocol_context = "CLOUD"
        elif "HA" in providers:
            protocol_context = "LOCAL_API"

    phase_context = str(normalized_witness.get("phase_context", "UNKNOWN") or "UNKNOWN")
    if phase_context == "UNKNOWN":
        for row in list(normalized_witness.get("optimized_trace_prefix", []))[-2:] + list(normalized_witness.get("baseline_trace_prefix", []))[-2:]:
            phase = str(row.get("phase", "UNKNOWN") or "UNKNOWN")
            if phase != "UNKNOWN":
                phase_context = phase
                break

    resource_context = None
    resource_keys = _resource_keys(normalized_witness)
    joined = " ".join(resource_keys).lower()
    trigger = str(normalized_witness.get("trigger_pattern", "") or "")
    if phase_context == "TEARDOWN" and any(token in trigger for token in ("cleanup", "unsubscribe")):
        resource_context = "CLEANUP_HOOK"
    elif protocol_context == "BLE":
        if "manager" in joined or "coordinator" in joined:
            resource_context = "BLE_COORDINATOR"
        elif any(token in joined for token in ("connection", "device")):
            resource_context = "BLE_DEVICE_CONTEXT"
    elif protocol_context == "CLOUD":
        if "listener" in joined:
            resource_context = "CLOUD_LISTENER"
        elif "mq" in joined:
            resource_context = "CLOUD_MQ_CHANNEL"
        elif any(token in joined for token in ("session", "manager")):
            resource_context = "CLOUD_MANAGER"
    elif protocol_context == "LOCAL_API":
        if any(token in joined for token in ("manager", "coordinator")):
            resource_context = "LOCAL_MANAGER"
        else:
            resource_context = "LOCAL_API_CLIENT"
    resource_context = resource_context or "UNKNOWN_RESOURCE"

    target = _latest_target(normalized_witness)
    lowered = target.lower()
    entity_scope = "UNKNOWN_SCOPE"
    if "entry" in lowered:
        entity_scope = "ENTRY"
    elif "coordinator" in lowered:
        entity_scope = "COORDINATOR"
    elif any(token in lowered for token in ("manager", "listener", "session")):
        entity_scope = "MANAGER"
    elif "." in target and not target.startswith("/"):
        entity_scope = "ENTITY"
    elif target.startswith("/") or "device" in lowered or lowered.startswith("ble:"):
        entity_scope = "DEVICE"

    return {
        "protocol_context": protocol_context,
        "phase_context": phase_context,
        "resource_context": resource_context,
        "entity_scope": entity_scope,
    }


def _confidence(violated_property: str, trigger_pattern: str, suspected_rule_gap: str | None) -> float:
    if violated_property and violated_property != "UNSUPPORTED_ALIGNMENT" and trigger_pattern != "unknown_trigger":
        return 0.9
    if violated_property and suspected_rule_gap is None:
        return 0.7
    return 0.5


def witness_to_evidence(witness: CounterexampleWitness) -> CounterexampleEvidence:
    normalized = normalize_witness(witness)
    context = infer_context(normalized)
    trigger_pattern = infer_trigger_pattern(normalized, context)
    baseline_trace_signature = make_trace_signature(normalized.get("baseline_trace_prefix", []), k=4)
    optimized_trace_signature = make_trace_signature(normalized.get("optimized_trace_prefix", []), k=4)
    suspected_rule_gap, suggested_refinement = infer_rule_gap_and_refinement(
        str(normalized.get("violated_property", "")),
        trigger_pattern,
        context,
    )
    if normalized.get("suspected_rule_gap"):
        suspected_rule_gap = normalized["suspected_rule_gap"]
    if not suggested_refinement:
        explicit_refinement = normalized.get("refinement_hint")
        if isinstance(explicit_refinement, dict):
            explicit_refinement = explicit_refinement.get("template")
        suggested_refinement = normalize_refinement_template(
            str(explicit_refinement) if explicit_refinement is not None else None
        )
    confidence = _confidence(str(normalized.get("violated_property", "")), trigger_pattern, suspected_rule_gap)
    source_witness_id = str(normalized.get("witness_id")) if normalized.get("witness_id") else None
    evidence_id = _stable_id(
        "CEX",
        "::".join(
            [
                str(source_witness_id),
                str(normalized.get("violated_property", "")),
                trigger_pattern,
                context["protocol_context"],
                context["phase_context"],
                "|".join(baseline_trace_signature),
                "|".join(optimized_trace_signature),
            ]
        ),
    )
    return CounterexampleEvidence(
        evidence_id=evidence_id,
        source_witness_id=source_witness_id,
        violated_property=str(normalized.get("violated_property", "UNKNOWN_VIOLATION")),
        trigger_pattern=trigger_pattern,
        protocol_context=context["protocol_context"],
        phase_context=context["phase_context"],
        resource_context=context["resource_context"],
        entity_scope=context["entity_scope"],
        divergence_point=dict(normalized.get("divergence_point", {})),
        minimal_conditions=dict(normalized.get("minimal_conditions", {})),
        baseline_trace_signature=baseline_trace_signature,
        optimized_trace_signature=optimized_trace_signature,
        suspected_rule_gap=suspected_rule_gap,
        suggested_refinement=suggested_refinement,
        confidence=confidence,
    )


def project_witnesses_to_evidence(witnesses: List[CounterexampleWitness]) -> List[CounterexampleEvidence]:
    return [witness_to_evidence(witness) for witness in witnesses]
