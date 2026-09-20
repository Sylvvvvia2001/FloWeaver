from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dsl.contracts import OptimizationTarget, ensure_optimization_target, to_dict
from dsl.io import dump_json, load_json
from optimizer.api_micro_refinement import APIMicroRefinementPolicy, execution_plan_from_dict
from optimizer.ble_micro_refinement import BLEMicroRefinementPolicy
from optimizer.combined_micro_refinement import (
    CombinedMicroCaseResult,
    CombinedMicroRefinementPolicy,
    ConservativeCombinedMicroRefiner,
)


TARGET_ROOT = REPO_ROOT / "data" / "targets" / "vdev_benchmarks"
MANIFEST_PATH = TARGET_ROOT / "manifest.json"
BLE_CONFIG_PATH = TARGET_ROOT / "ble_micro_refinement_defaults.json"
API_CONFIG_PATH = TARGET_ROOT / "api_micro_refinement_defaults.json"
RUN_ROOT = REPO_ROOT / "data" / "optimizer_runs" / "vdev_benchmarks"
OUTPUT_ROOT = REPO_ROOT / "data" / "optimizer_runs" / "vdev_benchmarks_combined_micro_refined"
REPORT_PATH = TARGET_ROOT / "COMBINED_MICRO_REFINEMENT_REPORT.md"


def _raw_to_target(raw: Dict[str, Any]) -> OptimizationTarget:
    target = OptimizationTarget(
        meta=raw.get("meta", {}),
        source_scope=raw.get("source_scope", {}),
        vdev_actions=raw.get("vdev_actions", []),
        target_anchors=raw.get("target_anchors", {}),
        entrypoint=raw.get("entrypoint", {}),
        objectives=raw.get("objectives", {}),
        constraints=raw.get("constraints", {}),
        validation=raw.get("validation", {}),
        hard_dependencies=raw.get("hard_dependencies", []),
        soft_dependencies=raw.get("soft_dependencies", []),
        critical_action_ids=raw.get("critical_action_ids", []),
    )
    ensure_optimization_target(target)
    return target


def _load_cases() -> List[Dict[str, Any]]:
    payload = load_json(MANIFEST_PATH)
    return [dict(row) for row in payload.get("cases", []) if isinstance(row, dict)]


def _load_case_result(case: Dict[str, Any], refiner: ConservativeCombinedMicroRefiner) -> CombinedMicroCaseResult:
    vdev_id = str(case.get("vdev_id", "")).strip()
    case_name = str(case.get("name", "")).strip() or vdev_id
    target_path = Path(str(case.get("target_path", "")).strip())
    target = _raw_to_target(load_json(target_path))
    plan = execution_plan_from_dict(load_json(RUN_ROOT / vdev_id / "m5_execution_plan.json"))
    return refiner.refine_case(vdev_id=vdev_id, case_name=case_name, target=target, plan=plan)


def _write_case_output(result: CombinedMicroCaseResult, case: Dict[str, Any]) -> None:
    case_dir = OUTPUT_ROOT / result.vdev_id
    case_dir.mkdir(parents=True, exist_ok=True)
    dump_json(
        case_dir / "combined_micro_refinement.json",
        {
            "vdev_id": result.vdev_id,
            "case_name": result.case_name,
            "group": case.get("group"),
            "target_path": case.get("target_path"),
            "original_estimated_latency_ms": result.original_estimated_latency_ms,
            "ble_added_savings_ms": result.ble_added_savings_ms,
            "api_added_savings_ms": result.api_added_savings_ms,
            "combined_added_savings_ms": result.combined_added_savings_ms,
            "combined_added_savings_ratio": result.combined_added_savings_ratio,
            "combined_refined_estimated_latency_ms": result.combined_refined_estimated_latency_ms,
            "conflict_count": result.conflict_count,
            "validation": {
                "passed": result.validation.passed,
                "component_validations_ok": result.validation.component_validations_ok,
                "conflict_free": result.validation.conflict_free,
                "contiguous_coverage_ok": result.validation.contiguous_coverage_ok,
                "savings_consistency_ok": result.validation.savings_consistency_ok,
                "batch_order_preserved": result.validation.batch_order_preserved,
                "projection_ok": result.validation.projection_ok,
                "ble_constraints_ok": result.validation.ble_constraints_ok,
                "api_constraints_ok": result.validation.api_constraints_ok,
                "event_loop_constraints_ok": result.validation.event_loop_constraints_ok,
                "simulated_total_ms": result.validation.simulated_total_ms,
                "simulated_event_count": result.validation.simulated_event_count,
                "reasons": list(result.validation.reasons),
            },
            "accepted_corridors": result.accepted_corridors,
            "rejected_corridors": result.rejected_corridors,
        },
    )
    dump_json(
        case_dir / "combined_micro_simulation.json",
        {
            "vdev_id": result.vdev_id,
            "case_name": result.case_name,
            "simulated_event_count": len(result.simulated_events),
            "events": [
                {
                    "source": event.source,
                    "corridor_id": event.corridor_id,
                    "owner_id": event.owner_id,
                    "batch_id": event.batch_id,
                    "phase": event.phase,
                    "start_ms": event.start_ms,
                    "end_ms": event.end_ms,
                    "protocol": event.protocol,
                    "host_key": event.host_key,
                    "bucket_key": event.bucket_key,
                    "session_key": event.session_key,
                    "endpoint_key": event.endpoint_key,
                }
                for event in result.simulated_events
            ],
        },
    )
    dump_json(case_dir / "combined_micro_refined_plan_overlay.json", to_dict(result.refined_plan))


def _write_summary(results: List[CombinedMicroCaseResult], cases: List[Dict[str, Any]]) -> None:
    rows = []
    total_original = 0
    total_ble = 0
    total_api = 0
    total_combined = 0
    total_conflicts = 0
    for case, result in zip(cases, results):
        total_original += result.original_estimated_latency_ms
        total_ble += result.ble_added_savings_ms
        total_api += result.api_added_savings_ms
        total_combined += result.combined_added_savings_ms
        total_conflicts += result.conflict_count
        rows.append(
            {
                "vdev_id": result.vdev_id,
                "name": result.case_name,
                "group": case.get("group"),
                "original_estimated_latency_ms": result.original_estimated_latency_ms,
                "ble_added_savings_ms": result.ble_added_savings_ms,
                "api_added_savings_ms": result.api_added_savings_ms,
                "combined_added_savings_ms": result.combined_added_savings_ms,
                "combined_added_savings_ratio": result.combined_added_savings_ratio,
                "combined_refined_estimated_latency_ms": result.combined_refined_estimated_latency_ms,
                "conflict_count": result.conflict_count,
                "validation_passed": result.validation.passed,
                "simulated_event_count": result.validation.simulated_event_count,
                "validation_reasons": list(result.validation.reasons),
                "accepted_corridor_count": len(result.accepted_corridors),
                "rejected_corridor_count": len(result.rejected_corridors),
            }
        )
    dump_json(
        OUTPUT_ROOT / "summary.json",
        {
            "case_count": len(rows),
            "total_original_estimated_latency_ms": total_original,
            "total_ble_added_savings_ms": total_ble,
            "total_api_added_savings_ms": total_api,
            "total_combined_added_savings_ms": total_combined,
            "total_combined_added_savings_ratio": (float(total_combined) / float(total_original)) if total_original else 0.0,
            "total_conflict_count": total_conflicts,
            "cases": rows,
        },
    )


def _write_markdown(
    results: List[CombinedMicroCaseResult],
    cases: List[Dict[str, Any]],
    ble_policy: BLEMicroRefinementPolicy,
    api_policy: APIMicroRefinementPolicy,
    combined_policy: CombinedMicroRefinementPolicy,
) -> None:
    lines: List[str] = []
    lines.append("# Combined BLE + API Micro-Refinement Report")
    lines.append("")
    lines.append("This report combines BLE and API micro-refinement over the M5 plan.")
    lines.append("The combined layer checks conflicts and validates the merged schedule.")
    lines.append("")
    lines.append("## Combined Policy")
    lines.append("")
    for key, value in combined_policy.to_dict().items():
        lines.append(f"- `{key}` = `{value}`")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("| Case | BLE Save | API Save | Combined Save | Combined % | Conflicts | Validator |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for result in results:
        lines.append(
            f"| {result.vdev_id} | {result.ble_added_savings_ms} ms | {result.api_added_savings_ms} ms | "
            f"{result.combined_added_savings_ms} ms | {result.combined_added_savings_ratio * 100:.1f}% | {result.conflict_count} | "
            f"{'pass' if result.validation.passed else 'fail'} |"
        )
    lines.append("")
    lines.append("## Case Details")
    lines.append("")
    for case, result in zip(cases, results):
        lines.append(f"### {result.case_name} (`{result.vdev_id}`)")
        lines.append("")
        lines.append(f"- Group: {case.get('group', '')}")
        lines.append(f"- Original estimated latency: `{result.original_estimated_latency_ms} ms`")
        lines.append(f"- BLE additional saving: `{result.ble_added_savings_ms} ms`")
        lines.append(f"- API additional saving: `{result.api_added_savings_ms} ms`")
        lines.append(f"- Combined additional saving: `{result.combined_added_savings_ms} ms` (`{result.combined_added_savings_ratio * 100:.1f}%`)")
        lines.append(f"- Combined refined estimated latency: `{result.combined_refined_estimated_latency_ms} ms`")
        lines.append(f"- Conflict count: `{result.conflict_count}`")
        lines.append(f"- Validator passed: `{result.validation.passed}`")
        lines.append(f"- Simulated event count: `{result.validation.simulated_event_count}`")
        lines.append(f"- Projection / order / resource checks:")
        lines.append(f"  - `component_validations_ok = {result.validation.component_validations_ok}`")
        lines.append(f"  - `conflict_free = {result.validation.conflict_free}`")
        lines.append(f"  - `contiguous_coverage_ok = {result.validation.contiguous_coverage_ok}`")
        lines.append(f"  - `savings_consistency_ok = {result.validation.savings_consistency_ok}`")
        lines.append(f"  - `batch_order_preserved = {result.validation.batch_order_preserved}`")
        lines.append(f"  - `projection_ok = {result.validation.projection_ok}`")
        lines.append(f"  - `ble_constraints_ok = {result.validation.ble_constraints_ok}`")
        lines.append(f"  - `api_constraints_ok = {result.validation.api_constraints_ok}`")
        lines.append(f"  - `event_loop_constraints_ok = {result.validation.event_loop_constraints_ok}`")
        if result.validation.reasons:
            lines.append(f"- Validator reasons:")
            for reason in result.validation.reasons:
                lines.append(f"  - `{reason}`")
        if result.accepted_corridors:
            lines.append("- Accepted corridors:")
            for row in result.accepted_corridors:
                lines.append(
                    f"  - `{row['source']}:{row['corridor_id']}` batches=`{row['batch_ids']}` actions=`{row['action_ids']}` save=`{row['latency_saved_ms']} ms`"
                )
        else:
            lines.append("- Accepted corridors: none")
        if result.rejected_corridors:
            lines.append("- Rejected corridors:")
            for row in result.rejected_corridors:
                lines.append(
                    f"  - `{row['source']}:{row['corridor_id']}` batches=`{row['batch_ids']}` actions=`{row['action_ids']}` save=`{row['latency_saved_ms']} ms`"
                )
        lines.append("")
    lines.append("## Component Policies")
    lines.append("")
    lines.append("### BLE")
    lines.append("")
    for key, value in ble_policy.to_dict().items():
        lines.append(f"- `{key}` = `{value}`")
    lines.append("")
    lines.append("### API")
    lines.append("")
    for key, value in api_policy.to_dict().items():
        lines.append(f"- `{key}` = `{value}`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run conflict-free combined BLE + API micro-refinement.")
    parser.add_argument("--cases", nargs="*", default=[], help="Optional subset of vdev_id values.")
    parser.add_argument("--ble-config", default=str(BLE_CONFIG_PATH), help="BLE policy JSON path.")
    parser.add_argument("--api-config", default=str(API_CONFIG_PATH), help="API policy JSON path.")
    args = parser.parse_args()

    selected = {str(item).strip() for item in args.cases if str(item).strip()}
    cases = [case for case in _load_cases() if not selected or str(case.get("vdev_id", "")).strip() in selected]
    ble_policy = BLEMicroRefinementPolicy.from_dict(load_json(Path(str(args.ble_config)).expanduser()))
    api_policy = APIMicroRefinementPolicy.from_dict(load_json(Path(str(args.api_config)).expanduser()))
    combined_policy = CombinedMicroRefinementPolicy()
    refiner = ConservativeCombinedMicroRefiner(
        ble_policy=ble_policy,
        api_policy=api_policy,
        combined_policy=combined_policy,
    )
    results = [_load_case_result(case, refiner) for case in cases]
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for case, result in zip(cases, results):
        _write_case_output(result, case)
    _write_summary(results, cases)
    _write_markdown(results, cases, ble_policy, api_policy, combined_policy)
    print(f"refined_cases={len(results)} report={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
