from __future__ import annotations

from typing import Any, Dict, List

from alignment_layer.api.run_alignment_verification import run_alignment_verification
from alignment_layer.output.alignment_map import AlignedPair as AlignmentItem
from alignment_layer.output.alignment_map import AlignmentMap
from alignment_layer.output.suspicious_regions import SuspiciousRegion
from alignment_layer.rules.alignment_rules import AlignmentConfig, DEFAULT_ALIGNMENT_RULES
from counterexample_layer.ir.ir_types import IRProgram
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel


def infer_alignment_map(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    observation_schema: CounterexampleObservationSchema | None = None,
    resource_model: ResourceModel | None = None,
    alignment_rules: List[str] | None = None,
    alignment_config: AlignmentConfig | Dict[str, Any] | None = None,
) -> AlignmentMap:
    schema = observation_schema or CounterexampleObservationSchema()
    resources = resource_model or ResourceModel.from_observation_schema(schema)
    result = run_alignment_verification(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        observation_schema=schema,
        resource_model=resources,
        alignment_rules=alignment_rules or DEFAULT_ALIGNMENT_RULES,
        alignment_config=alignment_config or AlignmentConfig(),
    )
    return result.alignment_map


def suspicious_regions_from_diff_hunks(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    diff_hunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    del baseline_ir, optimized_ir
    regions: List[Dict[str, Any]] = []
    for idx, hunk in enumerate(diff_hunks):
        regions.append(
            SuspiciousRegion(
                region_id=f"sr_{idx:03d}",
                baseline_node_ids=[str(item) for item in hunk.get("baseline_node_ids", [])],
                optimized_node_ids=[str(item) for item in hunk.get("optimized_node_ids", [])],
                reason="OBSERVATION_BOUNDARY_RISK",
                severity=0.8,
            ).to_dict()
        )
    return regions
