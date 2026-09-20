from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from alignment_layer.api.run_alignment_verification import run_alignment_verification
from alignment_layer.rules.alignment_rules import AlignmentConfig, DEFAULT_ALIGNMENT_RULES
from counterexample_layer.ir.summaries import trace_to_ir_program
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel
from dsl.contracts import Trace
from runtime.events import TraceCollector
from runtime.scenarios import Scenario
from runtime.trace import TraceCompareConfig


RunnerFn = Callable[[Any, Scenario], None]


@dataclass
class ReplayResult:
    scenario_id: str
    baseline_trace: Trace
    optimized_trace: Trace
    runtime_artifacts: Dict[str, Any] = field(default_factory=dict)


def _counterexample_runtime_artifacts(scenario: Scenario, baseline: Trace, optimized: Trace) -> Dict[str, Any]:
    compare_config = TraceCompareConfig()
    observation_schema = CounterexampleObservationSchema.from_optimization_target(None)
    observation_schema.canonicalization_version = compare_config.canonicalization_version
    observation_schema.trace_compare_config = compare_config
    resource_model = ResourceModel.from_observation_schema(observation_schema)
    baseline_ir = trace_to_ir_program(baseline, "baseline", compare_config)
    optimized_ir = trace_to_ir_program(optimized, "optimized", compare_config)
    alignment_result = run_alignment_verification(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        observation_schema=observation_schema,
        resource_model=resource_model,
        alignment_rules=DEFAULT_ALIGNMENT_RULES,
        alignment_config=AlignmentConfig(),
    )
    return {
        "baseline_ir": baseline_ir.to_dict(),
        "optimized_ir": optimized_ir.to_dict(),
        "alignment_result": alignment_result.to_dict(),
        "alignment_map": alignment_result.alignment_map.to_dict(),
        "observation_schema": observation_schema.to_dict(),
        "resource_model": resource_model.to_dict(),
        "suspicious_regions": [item.to_dict() for item in alignment_result.suspicious_regions],
        "environment_model": {
            "inputs": {"scenario_id": scenario.scenario_id},
            "request_params": {},
            "device_results": {},
            "toggles": dict(scenario.faults),
            "framework_events": list(scenario.phases),
            "assumptions": [f"scenario:{scenario.scenario_id}"],
            "branches": {},
        },
        "alignment_status": alignment_result.verdict,
        "run_counterexample_search": alignment_result.verdict != "PROVED",
    }


def replay_scenarios(
    integration: str,
    scenarios: List[Scenario],
    baseline_runner: RunnerFn,
    optimized_runner: RunnerFn,
) -> List[ReplayResult]:
    results: List[ReplayResult] = []

    for scenario in scenarios:
        collector = TraceCollector(integration=integration, scenario_id=scenario.scenario_id)
        baseline = collector.run_variant_sync(
            "baseline",
            lambda rec: baseline_runner(rec, scenario),
        )
        optimized = collector.run_variant_sync(
            "optimized",
            lambda rec: optimized_runner(rec, scenario),
        )
        results.append(
            ReplayResult(
                scenario_id=scenario.scenario_id,
                baseline_trace=baseline,
                optimized_trace=optimized,
                runtime_artifacts=_counterexample_runtime_artifacts(scenario, baseline, optimized),
            )
        )

    return results


def summarize_replay(results: List[ReplayResult]) -> Dict[str, Any]:
    return {
        "scenarios": [r.scenario_id for r in results],
        "count": len(results),
    }
