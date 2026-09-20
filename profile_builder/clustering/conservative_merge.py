from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from profile_builder.evidence.evidence_types import CounterexampleCluster, CounterexampleEvidence

_KEY_FIELDS = ("concurrency_level", "bucket_size", "timeout_enabled", "retry_count")


def _stable_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _conditions_compatible(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    for key in _KEY_FIELDS:
        left_value = left.get(key)
        right_value = right.get(key)
        if left_value is None or right_value is None:
            continue
        if left_value != right_value:
            return False
    return True


def _merge_conditions(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(left)
    for key in _KEY_FIELDS:
        if merged.get(key) is None and right.get(key) is not None:
            merged[key] = right.get(key)
    merged.setdefault("raw_conditions", list(left.get("raw_conditions", [])))
    for item in right.get("raw_conditions", []):
        if item not in merged["raw_conditions"]:
            merged["raw_conditions"].append(item)
    return merged


def _cluster_confidence(size: int, has_gap: bool) -> float:
    if has_gap and size >= 3:
        return 0.95
    if has_gap and size == 2:
        return 0.85
    return 0.70


def merge_bucket_to_clusters(
    bucket: list[CounterexampleEvidence],
) -> list[CounterexampleCluster]:
    if not bucket:
        return []

    sorted_bucket = sorted(bucket, key=lambda item: item.evidence_id)
    clusters: List[CounterexampleCluster] = []
    optimized_signatures: Dict[str, tuple[str, ...]] = {}
    for evidence in sorted_bucket:
        placed = False
        for cluster in clusters:
            if cluster.suspected_rule_gap != evidence.suspected_rule_gap:
                continue
            if cluster.resource_context != evidence.resource_context:
                continue
            if cluster.representative_trace_signature != evidence.baseline_trace_signature:
                continue
            if optimized_signatures.get(cluster.cluster_id, tuple()) != evidence.optimized_trace_signature:
                continue
            if not _conditions_compatible(cluster.representative_minimal_conditions, evidence.minimal_conditions):
                continue
            cluster.member_evidence_ids.append(evidence.evidence_id)
            cluster.representative_minimal_conditions = _merge_conditions(cluster.representative_minimal_conditions, evidence.minimal_conditions)
            cluster.cluster_confidence = _cluster_confidence(len(cluster.member_evidence_ids), bool(cluster.suspected_rule_gap))
            if not cluster.suggested_refinement and evidence.suggested_refinement:
                cluster.suggested_refinement = evidence.suggested_refinement
            placed = True
            break
        if placed:
            continue
        bucket_key = (
            evidence.violated_property,
            evidence.protocol_context,
            evidence.phase_context,
            evidence.trigger_pattern,
        )
        rep_conditions = dict(evidence.minimal_conditions)
        cluster_id = _stable_id("CEXCL", "::".join([evidence.evidence_id, *bucket_key]))
        clusters.append(
            CounterexampleCluster(
                cluster_id=cluster_id,
                bucket_key=bucket_key,
                violated_property=evidence.violated_property,
                protocol_context=evidence.protocol_context,
                phase_context=evidence.phase_context,
                trigger_pattern=evidence.trigger_pattern,
                suspected_rule_gap=evidence.suspected_rule_gap,
                resource_context=evidence.resource_context,
                member_evidence_ids=[evidence.evidence_id],
                representative_trace_signature=evidence.baseline_trace_signature,
                representative_minimal_conditions=rep_conditions,
                suggested_refinement=evidence.suggested_refinement,
                cluster_confidence=_cluster_confidence(1, bool(evidence.suspected_rule_gap)),
            )
        )
        optimized_signatures[cluster_id] = evidence.optimized_trace_signature
    return clusters
