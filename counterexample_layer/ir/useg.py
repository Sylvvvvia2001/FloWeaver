from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from alignment_layer.output.alignment_map import AlignedBlock, AlignedPair, AlignmentMap
from counterexample_layer.ir.ir_types import IRProgram
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema


@dataclass
class USEGNode:
    useg_node_id: str
    kind: str
    baseline_node_ids: List[str] = field(default_factory=list)
    optimized_node_ids: List[str] = field(default_factory=list)
    suspicious_region_id: str | None = None
    unsupported_alignment: bool = False
    crosses_observation_boundary: bool = False
    merge_target: Tuple[str | None, str | None] | None = None
    weight: int = 0


@dataclass
class USEG:
    nodes: List[USEGNode] = field(default_factory=list)


def _region_lookup(suspicious_regions: Sequence[object] | None) -> Dict[Tuple[str, ...], Dict[str, object]]:
    lookup: Dict[Tuple[str, ...], Dict[str, object]] = {}
    for region in suspicious_regions or []:
        if hasattr(region, "to_dict"):
            region = region.to_dict()
        region = dict(region)
        baseline_ids = tuple(sorted(str(item) for item in region.get("baseline_node_ids", [])))
        optimized_ids = tuple(sorted(str(item) for item in region.get("optimized_node_ids", [])))
        lookup[baseline_ids + ("|",) + optimized_ids] = region
    return lookup


def _crosses_observation_boundary(program: IRProgram, node_ids: List[str], schema: CounterexampleObservationSchema) -> bool:
    semantic_ops = set(schema.semantic_ops)
    for node_id in node_ids:
        summary = program.nodes[node_id].summary
        if summary.emits_observation or summary.op in semantic_ops or program.nodes[node_id].metadata.get("observation_boundary"):
            return True
    return False


def _summary_signature(program: IRProgram, node_id: str) -> Tuple[object, ...]:
    summary = program.nodes[node_id].summary
    resource_effects = tuple(
        sorted(
            (
                str(effect.get("resource_kind", "")),
                str(effect.get("action", "")),
                str(effect.get("key", "")),
            )
            for effect in summary.resource_effects
        )
    )
    return (
        summary.provider,
        summary.op,
        summary.target,
        summary.phase,
        tuple(sorted(summary.params.items())),
        resource_effects,
        summary.exception_category,
    )


def _pair_compatible(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    item: AlignedPair,
) -> bool:
    if item.confidence < 0.75:
        return False
    if item.relation not in {"EXACT", "STUTTER", "REORDER_EQ", "REUSE_EQ", "BATCH_EQ", "SERIAL_EQ"}:
        return False
    return _summary_signature(baseline_ir, item.baseline_node_id) == _summary_signature(optimized_ir, item.optimized_node_id)


def _alignment_region_key(baseline_node_ids: List[str], optimized_node_ids: List[str]) -> Tuple[str, ...]:
    return tuple(sorted(baseline_node_ids)) + ("|",) + tuple(sorted(optimized_node_ids))


def _is_supported_region(region_payload: Dict[str, object] | None) -> bool:
    if not region_payload:
        return True
    reason = str(region_payload.get("reason", "")).strip().upper()
    if bool(region_payload.get("unsupported_alignment", False)):
        return False
    return reason not in {"LOW_CONFIDENCE_ALIGNMENT", "UNSUPPORTED_ALIGNMENT"}


def _aligned_node(
    baseline_node_ids: List[str],
    optimized_node_ids: List[str],
    confidence: float,
    relation: str,
    split_open: bool,
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    observation_schema: CounterexampleObservationSchema,
    region_payload: Dict[str, object] | None,
    index: int,
) -> USEGNode:
    suspicious_region_id = str(region_payload.get("region_id", "")) or None if region_payload else None
    crosses_boundary = _crosses_observation_boundary(baseline_ir, baseline_node_ids, observation_schema) or _crosses_observation_boundary(
        optimized_ir, optimized_node_ids, observation_schema
    )
    supported = _is_supported_region(region_payload)
    compatible = confidence >= 0.75 and supported
    kind = "MERGE" if split_open and compatible else ("UNIFIED" if compatible else "SPLIT")
    unsupported = bool(
        region_payload
        and (
            bool(region_payload.get("unsupported_alignment", False))
            or str(region_payload.get("reason", "")).upper() in {"LOW_CONFIDENCE_ALIGNMENT", "UNSUPPORTED_ALIGNMENT"}
        )
    )
    return USEGNode(
        useg_node_id=f"useg_{index:04d}",
        kind=kind,
        baseline_node_ids=list(baseline_node_ids),
        optimized_node_ids=list(optimized_node_ids),
        suspicious_region_id=suspicious_region_id,
        unsupported_alignment=unsupported,
        crosses_observation_boundary=crosses_boundary,
        merge_target=(baseline_node_ids[-1] if baseline_node_ids else None, optimized_node_ids[-1] if optimized_node_ids else None) if split_open else None,
        weight=0 if compatible else 1,
    )


def build_useg(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    alignment_map: AlignmentMap,
    observation_schema: CounterexampleObservationSchema,
    suspicious_regions: List[Dict[str, object]] | None = None,
) -> USEG:
    region_lookup = _region_lookup(suspicious_regions or alignment_map.suspicious_regions)
    node_pairs = {(item.baseline_node_id, item.optimized_node_id): item for item in alignment_map.node_alignments}
    block_alignments = list(alignment_map.block_alignments)

    nodes: List[USEGNode] = []
    i = 0
    j = 0
    split_open = False

    while i < len(baseline_ir.order) or j < len(optimized_ir.order):
        block_match: AlignedBlock | None = None
        for block in block_alignments:
            b_ids = block.baseline_node_ids
            o_ids = block.optimized_node_ids
            if b_ids and baseline_ir.order[i : i + len(b_ids)] != b_ids:
                continue
            if o_ids and optimized_ir.order[j : j + len(o_ids)] != o_ids:
                continue
            if not b_ids and not o_ids:
                continue
            block_match = block
            break
        if block_match is not None:
            region_payload = region_lookup.get(_alignment_region_key(block_match.baseline_node_ids, block_match.optimized_node_ids), {})
            nodes.append(
                _aligned_node(
                    block_match.baseline_node_ids,
                    block_match.optimized_node_ids,
                    block_match.confidence,
                    block_match.relation,
                    split_open,
                    baseline_ir,
                    optimized_ir,
                    observation_schema,
                    region_payload,
                    len(nodes),
                )
            )
            split_open = nodes[-1].kind == "SPLIT"
            i += len(block_match.baseline_node_ids)
            j += len(block_match.optimized_node_ids)
            continue

        baseline_node_id = baseline_ir.order[i] if i < len(baseline_ir.order) else None
        optimized_node_id = optimized_ir.order[j] if j < len(optimized_ir.order) else None
        if baseline_node_id is not None and optimized_node_id is not None and (baseline_node_id, optimized_node_id) in node_pairs:
            item = node_pairs[(baseline_node_id, optimized_node_id)]
            region_payload = region_lookup.get(_alignment_region_key([baseline_node_id], [optimized_node_id]), {})
            confidence = item.confidence if _pair_compatible(baseline_ir, optimized_ir, item) else min(item.confidence, 0.54)
            nodes.append(
                _aligned_node(
                    [baseline_node_id],
                    [optimized_node_id],
                    confidence,
                    item.relation,
                    split_open,
                    baseline_ir,
                    optimized_ir,
                    observation_schema,
                    region_payload,
                    len(nodes),
                )
            )
            split_open = nodes[-1].kind == "SPLIT"
            i += 1
            j += 1
            continue

        baseline_segment: List[str] = []
        optimized_segment: List[str] = []
        while i < len(baseline_ir.order):
            candidate = baseline_ir.order[i]
            if any(candidate in block.baseline_node_ids for block in block_alignments) or any(candidate == pair.baseline_node_id for pair in alignment_map.node_alignments):
                break
            baseline_segment.append(candidate)
            i += 1
        while j < len(optimized_ir.order):
            candidate = optimized_ir.order[j]
            if any(candidate in block.optimized_node_ids for block in block_alignments) or any(candidate == pair.optimized_node_id for pair in alignment_map.node_alignments):
                break
            optimized_segment.append(candidate)
            j += 1
        region_payload = region_lookup.get(_alignment_region_key(baseline_segment, optimized_segment), {})
        nodes.append(
            USEGNode(
                useg_node_id=f"useg_{len(nodes):04d}",
                kind="SPLIT",
                baseline_node_ids=baseline_segment,
                optimized_node_ids=optimized_segment,
                suspicious_region_id=str(region_payload.get("region_id", "")) or None,
                unsupported_alignment=bool(
                    bool(region_payload.get("unsupported_alignment", False))
                    or str(region_payload.get("reason", "")).upper() in {"LOW_CONFIDENCE_ALIGNMENT", "UNSUPPORTED_ALIGNMENT"}
                ),
                crosses_observation_boundary=_crosses_observation_boundary(baseline_ir, baseline_segment, observation_schema)
                or _crosses_observation_boundary(optimized_ir, optimized_segment, observation_schema),
                weight=2,
            )
        )
        split_open = True

    return USEG(nodes=nodes)
