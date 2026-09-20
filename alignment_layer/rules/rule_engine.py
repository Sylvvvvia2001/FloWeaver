from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

from counterexample_layer.ir.ir_types import IRProgram, IRNode
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel

from alignment_layer.graph.candidate_generation import CandidateBlock, CandidatePair
from alignment_layer.ir.compatibility import block_observation_signature
from alignment_layer.rules.alignment_rules import (
    INDEPENDENT_ACT_SWAP,
    LISTENER_PRESERVING_BATCH,
    SETUP_PREFIX_STUTTER,
    SHARED_CONTEXT_REUSE,
    TEARDOWN_HOISTING_FORBIDDEN,
)


def _pair_lookup(candidate_pairs: List[CandidatePair]) -> Dict[Tuple[str, str], CandidatePair]:
    return {(item.baseline_node_id, item.optimized_node_id): item for item in candidate_pairs}


def _node_kind(program: IRProgram, node_id: str) -> str:
    return str(program.nodes[node_id].metadata.get("node_kind", "ACT"))


def _resource_conflict(node_a: IRNode, node_b: IRNode) -> bool:
    claims_a = {str(item).split(":", 2)[2] for item in node_a.metadata.get("resource_claims", [])}
    claims_b = {str(item).split(":", 2)[2] for item in node_b.metadata.get("resource_claims", [])}
    return bool(claims_a and claims_b and claims_a.intersection(claims_b))


def _is_stutter_candidate(node: IRNode) -> bool:
    return (
        str(node.metadata.get("node_kind", "")) in {"INIT", "PREPARE"}
        and not node.metadata.get("observation_boundary")
        and not node.summary.semantic_updates
        and not node.summary.resource_effects
    )


def _shared_context_reuse_block(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    pair_lookup: Dict[Tuple[str, str], CandidatePair],
    baseline_start: int,
    optimized_start: int,
) -> CandidateBlock | None:
    if baseline_start + 3 >= len(baseline_ir.order) or optimized_start + 3 >= len(optimized_ir.order):
        return None
    b_ids = baseline_ir.order[baseline_start : baseline_start + 4]
    o_ids = optimized_ir.order[optimized_start : optimized_start + 4]
    b_kinds = [_node_kind(baseline_ir, node_id) for node_id in b_ids]
    o_kinds = [_node_kind(optimized_ir, node_id) for node_id in o_ids]
    if b_kinds != ["PREPARE", "ACT", "PREPARE", "ACT"]:
        return None
    if o_kinds != ["PREPARE", "ACT", "ACT", "CLEANUP"]:
        return None
    if (b_ids[1], o_ids[1]) not in pair_lookup or (b_ids[3], o_ids[2]) not in pair_lookup:
        return None
    left_resource = Counter(item.split(":", 1)[0] for item in baseline_ir.nodes[b_ids[0]].metadata.get("resource_claims", []))
    right_resource = Counter(item.split(":", 1)[0] for item in optimized_ir.nodes[o_ids[0]].metadata.get("resource_claims", []))
    if not left_resource or left_resource != right_resource:
        return None
    return CandidateBlock(
        baseline_node_ids=b_ids,
        optimized_node_ids=o_ids,
        relation="REUSE_EQ",
        confidence=0.82,
        supporting_rules=[SHARED_CONTEXT_REUSE],
    )


def apply_realignment_rules(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    candidate_pairs: List[CandidatePair],
    candidate_blocks: List[CandidateBlock],
    alignment_rules: List[str],
    observation_schema: CounterexampleObservationSchema,
    resource_model: ResourceModel,
    max_rule_applications: int | None = None,
) -> Tuple[List[CandidatePair], List[CandidateBlock]]:
    del observation_schema, resource_model
    rules = set(alignment_rules)
    pair_lookup = _pair_lookup(candidate_pairs)
    expanded_blocks = list(candidate_blocks)
    applications = 0
    limit = max(1, int(max_rule_applications or 24))

    if INDEPENDENT_ACT_SWAP in rules:
        for i in range(len(baseline_ir.order) - 1):
            b1, b2 = baseline_ir.order[i], baseline_ir.order[i + 1]
            if _node_kind(baseline_ir, b1) != "ACT" or _node_kind(baseline_ir, b2) != "ACT":
                continue
            if _resource_conflict(baseline_ir.nodes[b1], baseline_ir.nodes[b2]):
                continue
            for j in range(len(optimized_ir.order) - 1):
                o1, o2 = optimized_ir.order[j], optimized_ir.order[j + 1]
                if _node_kind(optimized_ir, o1) != "ACT" or _node_kind(optimized_ir, o2) != "ACT":
                    continue
                if (b1, o2) not in pair_lookup or (b2, o1) not in pair_lookup:
                    continue
                if block_observation_signature(baseline_ir, [b1, b2]) != block_observation_signature(optimized_ir, [o1, o2]):
                    continue
                expanded_blocks.append(
                    CandidateBlock(
                        baseline_node_ids=[b1, b2],
                        optimized_node_ids=[o1, o2],
                        relation="REORDER_EQ",
                        confidence=min(pair_lookup[(b1, o2)].confidence, pair_lookup[(b2, o1)].confidence),
                        supporting_rules=[INDEPENDENT_ACT_SWAP],
                    )
                )
                applications += 1
                if applications >= limit:
                    break
            if applications >= limit:
                break

    if SETUP_PREFIX_STUTTER in rules:
        for node_id in optimized_ir.order:
            node = optimized_ir.nodes[node_id]
            if _is_stutter_candidate(node):
                expanded_blocks.append(
                    CandidateBlock(
                        baseline_node_ids=[],
                        optimized_node_ids=[node_id],
                        relation="STUTTER",
                        confidence=0.80,
                        supporting_rules=[SETUP_PREFIX_STUTTER],
                    )
                )

    if SHARED_CONTEXT_REUSE in rules:
        for i in range(len(baseline_ir.order)):
            for j in range(len(optimized_ir.order)):
                block = _shared_context_reuse_block(baseline_ir, optimized_ir, pair_lookup, i, j)
                if block is not None:
                    expanded_blocks.append(block)
                    applications += 1
                    if applications >= limit:
                        break
            if applications >= limit:
                break

    if LISTENER_PRESERVING_BATCH in rules:
        for i in range(len(baseline_ir.order) - 1):
            b_ids = baseline_ir.order[i : i + 2]
            if any(_node_kind(baseline_ir, node_id) != "UPDATE" for node_id in b_ids):
                continue
            for j in range(len(optimized_ir.order) - 1):
                o_ids = optimized_ir.order[j : j + 2]
                if any(_node_kind(optimized_ir, node_id) != "UPDATE" for node_id in o_ids):
                    continue
                if block_observation_signature(baseline_ir, b_ids) != block_observation_signature(optimized_ir, o_ids):
                    continue
                expanded_blocks.append(
                    CandidateBlock(
                        baseline_node_ids=b_ids,
                        optimized_node_ids=o_ids,
                        relation="BATCH_EQ",
                        confidence=0.78,
                        supporting_rules=[LISTENER_PRESERVING_BATCH],
                    )
                )

    if TEARDOWN_HOISTING_FORBIDDEN in rules:
        filtered_pairs: List[CandidatePair] = []
        for candidate in candidate_pairs:
            baseline_idx = baseline_ir.order.index(candidate.baseline_node_id)
            optimized_idx = optimized_ir.order.index(candidate.optimized_node_id)
            b_kind = _node_kind(baseline_ir, candidate.baseline_node_id)
            o_kind = _node_kind(optimized_ir, candidate.optimized_node_id)
            if b_kind == "CLEANUP" and o_kind == "CLEANUP" and optimized_idx < baseline_idx:
                continue
            filtered_pairs.append(candidate)
        candidate_pairs = filtered_pairs

    deduped_blocks: List[CandidateBlock] = []
    seen = set()
    for block in expanded_blocks:
        key = (tuple(block.baseline_node_ids), tuple(block.optimized_node_ids), block.relation)
        if key in seen:
            continue
        seen.add(key)
        deduped_blocks.append(block)
    return candidate_pairs, deduped_blocks
