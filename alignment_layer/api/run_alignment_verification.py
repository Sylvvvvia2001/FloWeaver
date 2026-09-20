from __future__ import annotations

from counterexample_layer.ir.ir_types import IRProgram
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel

from alignment_layer.graph.alignment_graph import build_alignment_graph
from alignment_layer.graph.candidate_generation import generate_alignment_candidates
from alignment_layer.ir.normalize import normalize_ir
from alignment_layer.output.alignment_map import AlignmentMap
from alignment_layer.output.result import AlignmentResult
from alignment_layer.output.suspicious_regions_builder import infer_suspicious_regions
from alignment_layer.rules.alignment_rules import AlignmentConfig, normalize_alignment_rules
from alignment_layer.rules.rule_engine import apply_realignment_rules
from alignment_layer.search.search_alignment import ProvisionalAlignment, search_alignment
from alignment_layer.verify.relational_check import check_relational_consistency


def _pair_intersects_scope(pair, baseline_scope: set[str], optimized_scope: set[str]) -> bool:
    return bool(
        pair.baseline_node_id in baseline_scope
        or pair.optimized_node_id in optimized_scope
    )


def _block_intersects_scope(block, baseline_scope: set[str], optimized_scope: set[str]) -> bool:
    return bool(
        set(block.baseline_node_ids).intersection(baseline_scope)
        or set(block.optimized_node_ids).intersection(optimized_scope)
    )


def _ordered_unique(items):
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def materialize_alignment_map(
    provisional_alignment: ProvisionalAlignment,
    proof_obligations,
    violations,
) -> AlignmentMap:
    trace_conflicts = [item for item in violations if item.kind == "TRACE_ANCHOR_CONFLICT"]
    retained_pairs = []
    for pair in provisional_alignment.aligned_pairs:
        if any(
            _pair_intersects_scope(
                pair,
                set(violation.baseline_scope),
                set(violation.optimized_scope),
            )
            for violation in trace_conflicts
        ):
            continue
        retained_pairs.append(pair)

    retained_blocks = []
    for block in provisional_alignment.aligned_blocks:
        if any(
            _block_intersects_scope(
                block,
                set(violation.baseline_scope),
                set(violation.optimized_scope),
            )
            for violation in trace_conflicts
        ):
            continue
        retained_blocks.append(block)

    aligned_baseline = {pair.baseline_node_id for pair in retained_pairs}
    aligned_optimized = {pair.optimized_node_id for pair in retained_pairs}
    for block in retained_blocks:
        aligned_baseline.update(block.baseline_node_ids)
        aligned_optimized.update(block.optimized_node_ids)

    unmatched_baseline = list(provisional_alignment.unmatched_baseline_nodes)
    unmatched_optimized = list(provisional_alignment.unmatched_optimized_nodes)
    for obligation in proof_obligations:
        if obligation.status == "DISCHARGED":
            continue
        unmatched_baseline.extend(
            node_id for node_id in obligation.baseline_scope if node_id not in aligned_baseline
        )
        unmatched_optimized.extend(
            node_id for node_id in obligation.optimized_scope if node_id not in aligned_optimized
        )

    return AlignmentMap(
        node_alignments=retained_pairs,
        block_alignments=retained_blocks,
        unmatched_baseline_nodes=_ordered_unique(unmatched_baseline),
        unmatched_optimized_nodes=_ordered_unique(unmatched_optimized),
        suspicious_regions=[],
    )


def build_alignment_summary(alignment_map: AlignmentMap, verdict: str, provisional_alignment: ProvisionalAlignment) -> dict:
    return {
        "verdict": verdict,
        "aligned_pair_count": len(alignment_map.node_alignments),
        "aligned_block_count": len(alignment_map.block_alignments),
        "unmatched_baseline_count": len(alignment_map.unmatched_baseline_nodes),
        "unmatched_optimized_count": len(alignment_map.unmatched_optimized_nodes),
        "coverage": dict(provisional_alignment.coverage),
    }


def run_alignment_verification(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    observation_schema: CounterexampleObservationSchema,
    resource_model: ResourceModel,
    alignment_rules,
    alignment_config,
) -> AlignmentResult:
    config = AlignmentConfig.from_any(alignment_config)
    rules = normalize_alignment_rules(alignment_rules)

    normalized_baseline = normalize_ir(baseline_ir, observation_schema)
    normalized_optimized = normalize_ir(optimized_ir, observation_schema)
    candidate_pairs, candidate_blocks = generate_alignment_candidates(
        normalized_baseline,
        normalized_optimized,
        observation_schema,
        resource_model,
        config,
    )
    expanded_pairs, expanded_blocks = apply_realignment_rules(
        normalized_baseline,
        normalized_optimized,
        candidate_pairs,
        candidate_blocks,
        rules,
        observation_schema,
        resource_model,
        max_rule_applications=config.max_rule_applications,
    )
    alignment_graph = build_alignment_graph(
        normalized_baseline,
        normalized_optimized,
        expanded_pairs,
        expanded_blocks,
        observation_schema,
        resource_model,
    )
    provisional_alignment = search_alignment(alignment_graph, config)
    proof_obligations, violations, verdict = check_relational_consistency(
        provisional_alignment,
        normalized_baseline,
        normalized_optimized,
        observation_schema,
        resource_model,
    )
    alignment_map = materialize_alignment_map(provisional_alignment, proof_obligations, violations)
    suspicious_regions = infer_suspicious_regions(
        alignment_map,
        proof_obligations,
        violations,
        normalized_baseline,
        normalized_optimized,
    )
    alignment_map.suspicious_regions = list(suspicious_regions)
    return AlignmentResult(
        verdict=verdict,
        alignment_map=alignment_map,
        aligned_pairs=list(alignment_map.node_alignments),
        aligned_blocks=list(alignment_map.block_alignments),
        unaligned_baseline_nodes=list(alignment_map.unmatched_baseline_nodes),
        unaligned_optimized_nodes=list(alignment_map.unmatched_optimized_nodes),
        suspicious_regions=list(suspicious_regions),
        proof_obligations=list(proof_obligations),
        violations=list(violations),
        summary=build_alignment_summary(alignment_map, verdict, provisional_alignment),
    )
