from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from dsl.contracts import OptimizationTarget, Trace, to_dict

from alignment_layer.api.run_alignment_verification import run_alignment_verification
from alignment_layer.rules.alignment_rules import AlignmentConfig, DEFAULT_ALIGNMENT_RULES
from counterexample_layer.ir.alignment_map import AlignmentMap, infer_alignment_map, suspicious_regions_from_diff_hunks
from counterexample_layer.ir.ir_types import IRProgram
from counterexample_layer.ir.summaries import trace_to_ir_program
from counterexample_layer.ir.useg import USEG, build_useg
from counterexample_layer.schema.divergence_rules import DivergenceResult, check_divergence
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel
from counterexample_layer.symbolic.executor import (
    init_symbolic_config,
    pop_config,
    push_config,
    rank_config,
    step_bound_exceeded,
    step_useg,
)
from counterexample_layer.symbolic.solver import minimal_assumptions
from counterexample_layer.symbolic.sym_state import SymConfig
from counterexample_layer.witness.minimizer import minimize_witnesses
from counterexample_layer.witness.refinement_hint import infer_refinement_hint
from counterexample_layer.witness.witness import CounterexampleVerdict, CounterexampleWitness
from runtime.trace import TraceCompareConfig


@dataclass
class CounterexampleInputBundle:
    baseline_ir: IRProgram
    optimized_ir: IRProgram
    alignment_map: AlignmentMap
    observation_schema: CounterexampleObservationSchema
    environment_model: Dict[str, Any]
    resource_model: ResourceModel
    suspicious_regions: List[Dict[str, Any]]


def build_counterexample_useg(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    alignment_map: AlignmentMap,
    observation_schema: CounterexampleObservationSchema,
    suspicious_regions: List[Dict[str, Any]] | None = None,
) -> USEG:
    return build_useg(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        alignment_map=alignment_map,
        observation_schema=observation_schema,
        suspicious_regions=suspicious_regions,
    )


def _event_rows(trace: Trace) -> List[Dict[str, Any]]:
    return [to_dict(event) for event in trace.events]


def _protocol_context_from_cfg(cfg: SymConfig, status: DivergenceResult) -> str | None:
    for event in list(cfg.trace_b.events)[-4:] + list(cfg.trace_o.events)[-4:]:
        provider = str(event.provider).upper()
        if provider == "BLE":
            return "BLE"
        if provider == "CLOUD":
            return "CLOUD"
        if provider == "HA":
            return "LOCAL_API"
    reason = str(status.reason or "").lower()
    if "ble" in reason:
        return "BLE"
    if "session" in reason or "cloud" in reason:
        return "CLOUD"
    return "UNKNOWN"


def _phase_context_from_cfg(cfg: SymConfig) -> str | None:
    for event in list(cfg.trace_b.events)[-2:] + list(cfg.trace_o.events)[-2:]:
        phase = str(getattr(event, "phase", "") or "").upper()
        if phase in {"SETUP", "RUNTIME", "TEARDOWN"}:
            return phase
    return "UNKNOWN"


def _trigger_pattern_from_status(status: DivergenceResult) -> str | None:
    mapping = {
        "premature_cleanup": "premature_cleanup",
        "missing_release_or_unsubscribe": "missing_unsubscribe",
        "wrong_session_reuse_or_missing_required_before": "wrong_session_reuse",
        "trace_prefix_mismatch": "state_write_order_mismatch",
        "final_state_values_differ": "return_value_mismatch",
        "exception_category_differ": "exception_category_mismatch",
        "required_final_state_mismatch": "state_write_order_mismatch",
        "split_region_crosses_observation_boundary": "unsupported_alignment_pattern",
    }
    return mapping.get(str(status.reason or ""), "unknown_trigger")


def _suspected_rule_gap_from_status(status: DivergenceResult) -> str | None:
    mapping = {
        "premature_cleanup": "MISSING_HARD_LIFECYCLE_EDGE",
        "missing_release_or_unsubscribe": "MISSING_HARD_LIFECYCLE_EDGE",
        "wrong_session_reuse_or_missing_required_before": "RESOURCE_REUSE_RULE_TOO_LOOSE",
        "trace_prefix_mismatch": "OBSERVATION_BOUNDARY_TOO_COARSE",
        "split_region_crosses_observation_boundary": "ALIGNMENT_RULE_MISSING",
    }
    return mapping.get(str(status.reason or ""))


def solve_and_materialize_witness(cfg: SymConfig, status: DivergenceResult) -> CounterexampleWitness:
    input_assumptions, environment_assumptions, minimal_conditions = minimal_assumptions(cfg)
    current = cfg.divergence_status.get("current_useg_node", {})
    suspicious_region_id = cfg.suspicious_region_id or current.get("suspicious_region_id")
    witness = CounterexampleWitness(
        verdict=CounterexampleVerdict.DIFF_FOUND.value,
        violated_property=str(status.violated_property),
        input_assumptions=input_assumptions,
        environment_assumptions=environment_assumptions,
        baseline_trace_prefix=_event_rows(cfg.trace_b),
        optimized_trace_prefix=_event_rows(cfg.trace_o),
        divergence_point={
            "step": cfg.useg_index,
            "useg_node_id": current.get("useg_node_id"),
            "kind": current.get("kind"),
            "reason": status.reason,
            "details": dict(status.details),
        },
        baseline_state_at_divergence={
            "state_writes": dict(cfg.semantic_state_b.get("state_writes", {})),
            "exception_category": cfg.semantic_state_b.get("exception_category"),
            "resource_keys": list(cfg.semantic_state_b.get("resource_keys", [])),
        },
        optimized_state_at_divergence={
            "state_writes": dict(cfg.semantic_state_o.get("state_writes", {})),
            "exception_category": cfg.semantic_state_o.get("exception_category"),
            "resource_keys": list(cfg.semantic_state_o.get("resource_keys", [])),
        },
        minimal_conditions=minimal_conditions,
        suspicious_region_id=suspicious_region_id,
        protocol_context=_protocol_context_from_cfg(cfg, status),
        phase_context=_phase_context_from_cfg(cfg),
        trigger_pattern=_trigger_pattern_from_status(status),
        suspected_rule_gap=_suspected_rule_gap_from_status(status),
        metadata={
            "visited_useg_nodes": list(cfg.visited_useg_nodes),
            "mode": cfg.mode,
        },
    )
    return witness


def make_inconclusive_witness() -> CounterexampleWitness:
    return CounterexampleWitness(
        verdict=CounterexampleVerdict.INCONCLUSIVE.value,
        violated_property=None,
        refinement_hint="insufficient_bound_or_model",
    )


def make_no_diff_within_bound_witness() -> CounterexampleWitness:
    return CounterexampleWitness(
        verdict=CounterexampleVerdict.NO_DIFF_WITHIN_BOUND.value,
        violated_property=None,
        refinement_hint="no_counterexample_within_current_bound",
    )


def _normalize_environment_model(environment_model: Dict[str, Any] | None) -> Dict[str, Any]:
    payload = dict(environment_model or {})
    return {
        "inputs": dict(payload.get("inputs", {})),
        "request_params": dict(payload.get("request_params", {})),
        "device_results": dict(payload.get("device_results", {})),
        "toggles": dict(payload.get("toggles", {})),
        "framework_events": list(payload.get("framework_events", [])),
        "assumptions": list(payload.get("assumptions", [])),
        "branches": dict(payload.get("branches", {})),
    }


def build_input_bundle(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    alignment_map: AlignmentMap,
    observation_schema: CounterexampleObservationSchema,
    environment_model: Dict[str, Any] | None,
    resource_model: ResourceModel,
    suspicious_regions: List[Dict[str, Any]] | None = None,
) -> CounterexampleInputBundle:
    return CounterexampleInputBundle(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        alignment_map=alignment_map,
        observation_schema=observation_schema,
        environment_model=_normalize_environment_model(environment_model),
        resource_model=resource_model,
        suspicious_regions=[dict(item) for item in suspicious_regions or []],
    )


def generate_counterexample(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    alignment_map: AlignmentMap,
    observation_schema: CounterexampleObservationSchema,
    environment_model: Dict[str, Any] | None,
    resource_model: ResourceModel,
    suspicious_regions: List[Dict[str, Any]] | None = None,
    max_steps: int = 200,
    max_paths: int = 5000,
) -> CounterexampleWitness:
    bundle = build_input_bundle(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        alignment_map=alignment_map,
        observation_schema=observation_schema,
        environment_model=environment_model,
        resource_model=resource_model,
        suspicious_regions=suspicious_regions,
    )
    useg = build_counterexample_useg(
        baseline_ir=bundle.baseline_ir,
        optimized_ir=bundle.optimized_ir,
        alignment_map=bundle.alignment_map,
        observation_schema=bundle.observation_schema,
        suspicious_regions=bundle.suspicious_regions,
    )

    init_cfg = init_symbolic_config(
        useg=useg,
        environment_model=bundle.environment_model,
        resource_model=bundle.resource_model,
        observation_schema=bundle.observation_schema,
    )

    worklist: List[Any] = []
    push_config(worklist, rank_config(init_cfg, suspicious_regions), 0, init_cfg)
    candidate_witnesses: List[CounterexampleWitness] = []

    explored = 0
    push_index = 1
    while worklist and explored < max_paths:
        cfg = pop_config(worklist)
        explored += 1

        if step_bound_exceeded(cfg, max_steps):
            continue

        status = check_divergence(cfg, bundle.observation_schema, bundle.resource_model)
        if status.is_divergent:
            candidate_witnesses.append(solve_and_materialize_witness(cfg, status))
            continue

        succs = step_useg(
            cfg,
            useg,
            bundle.baseline_ir,
            bundle.optimized_ir,
            bundle.observation_schema,
            bundle.resource_model,
        )
        for succ in succs:
            priority = rank_config(succ, suspicious_regions)
            push_config(worklist, priority, push_index, succ)
            push_index += 1

    if not candidate_witnesses:
        if explored >= max_paths:
            return make_inconclusive_witness()
        return make_no_diff_within_bound_witness()

    minimized = minimize_witnesses(candidate_witnesses)
    minimized.refinement_hint = infer_refinement_hint(minimized)
    return minimized


def generate_counterexample_from_traces(
    baseline_trace: Trace,
    optimized_trace: Trace,
    optimization_target: OptimizationTarget | None = None,
    compare_config: TraceCompareConfig | None = None,
    alignment_map: AlignmentMap | None = None,
    observation_schema: CounterexampleObservationSchema | None = None,
    environment_model: Dict[str, Any] | None = None,
    resource_model: ResourceModel | None = None,
    suspicious_regions: List[Dict[str, Any]] | None = None,
    max_steps: int = 200,
    max_paths: int = 5000,
) -> CounterexampleWitness:

    schema = observation_schema or CounterexampleObservationSchema.from_optimization_target(optimization_target)
    baseline_ir = trace_to_ir_program(
        baseline_trace,
        program_id="baseline",
        compare_config=compare_config or schema.trace_compare_config,
    )
    optimized_ir = trace_to_ir_program(
        optimized_trace,
        program_id="optimized",
        compare_config=compare_config or schema.trace_compare_config,
    )
    active_resource_model = resource_model or ResourceModel.from_observation_schema(schema)
    alignment_result = run_alignment_verification(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        observation_schema=schema,
        resource_model=active_resource_model,
        alignment_rules=DEFAULT_ALIGNMENT_RULES,
        alignment_config=AlignmentConfig(),
    )
    inferred_alignment = alignment_map or alignment_result.alignment_map
    return generate_counterexample(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        alignment_map=inferred_alignment,
        observation_schema=schema,
        environment_model=environment_model or {},
        resource_model=active_resource_model,
        suspicious_regions=suspicious_regions or [item.to_dict() for item in alignment_result.suspicious_regions],
        max_steps=max_steps,
        max_paths=max_paths,
    )


__all__ = [
    "CounterexampleInputBundle",
    "build_counterexample_useg",
    "build_input_bundle",
    "generate_counterexample",
    "generate_counterexample_from_traces",
    "infer_alignment_map",
    "suspicious_regions_from_diff_hunks",
]
