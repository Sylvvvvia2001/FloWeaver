from __future__ import annotations

from typing import Iterable, List

from counterexample_layer.witness.witness import CounterexampleWitness
from profile_builder.clustering.conservative_merge import merge_bucket_to_clusters
from profile_builder.clustering.typed_grouping import bucket_evidence_by_type
from profile_builder.evidence.counterexample_projection import project_witnesses_to_evidence
from profile_builder.evidence.evidence_types import ClusterPack, CounterexampleCluster


def build_cluster_pack(
    cluster: CounterexampleCluster,
    supporting_doc_ids: Iterable[str] | None = None,
    supporting_code_ids: Iterable[str] | None = None,
) -> ClusterPack:
    semantic_tag = f"{cluster.protocol_context}:{cluster.phase_context}:{cluster.trigger_pattern}"
    return ClusterPack(
        cluster_id=cluster.cluster_id,
        semantic_tag=semantic_tag,
        violated_property=cluster.violated_property,
        protocol_context=cluster.protocol_context,
        phase_context=cluster.phase_context,
        trigger_pattern=cluster.trigger_pattern,
        supporting_counterexample_ids=list(cluster.member_evidence_ids),
        supporting_doc_ids=list(supporting_doc_ids or []),
        supporting_code_ids=list(supporting_code_ids or []),
        suspected_rule_gap=cluster.suspected_rule_gap,
        candidate_rule_patch=cluster.suspected_rule_gap,
        suggested_refinement=cluster.suggested_refinement,
    )


def build_counterexample_cluster_packs(
    witnesses: list[CounterexampleWitness],
) -> list[ClusterPack]:
    evidence_list = project_witnesses_to_evidence(witnesses)
    buckets = bucket_evidence_by_type(evidence_list)
    clusters = []
    for _, bucket in sorted(buckets.items(), key=lambda item: item[0]):
        clusters.extend(merge_bucket_to_clusters(bucket))
    return [build_cluster_pack(cluster) for cluster in clusters]
