from __future__ import annotations

from counterexample_layer.witness.witness import CounterexampleWitness, ViolatedProperty


def infer_refinement_hint(witness: CounterexampleWitness) -> str:
    violated = str(witness.violated_property or "")
    if violated == ViolatedProperty.TRACE_MISMATCH.value:
        return "check_observation_schema_or_alignment_rule"
    if violated == ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value:
        return "upgrade_soft_constraint_or_add_guard"
    if violated == ViolatedProperty.UNSUPPORTED_ALIGNMENT.value:
        return "add_realignment_rule_or_expand_ir_summary"
    if violated == ViolatedProperty.FINAL_STATE_MISMATCH.value:
        return "inspect_data_and_lifecycle_boundary_crossing"
    return "insufficient_signal_for_refinement"
