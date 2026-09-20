from __future__ import annotations

from typing import List

from counterexample_layer.witness.witness import CounterexampleWitness


def _sort_key(witness: CounterexampleWitness) -> tuple[int, int, int, int, int]:
    divergence_step = int(witness.divergence_point.get("step", 10**9))
    prefix_len = max(len(witness.baseline_trace_prefix), len(witness.optimized_trace_prefix))
    env_count = (
        len(witness.environment_assumptions.get("path_assumptions", []))
        + len(witness.environment_assumptions.get("device_results", {}))
        + len(witness.environment_assumptions.get("toggle_assumptions", {}))
        + len(witness.environment_assumptions.get("framework_events", []))
    )
    resource_count = len(witness.environment_assumptions.get("resource_assumptions", []))
    input_count = sum(
        len(value) if isinstance(value, dict) else 1
        for value in witness.input_assumptions.values()
    )
    return (divergence_step, prefix_len, env_count, resource_count, input_count)


def minimize_witnesses(candidate_witnesses: List[CounterexampleWitness]) -> CounterexampleWitness:
    if not candidate_witnesses:
        raise ValueError("candidate_witnesses cannot be empty")
    return sorted(candidate_witnesses, key=_sort_key)[0]
