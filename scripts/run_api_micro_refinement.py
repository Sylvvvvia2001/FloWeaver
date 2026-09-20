from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dsl.contracts import ExecutionPlan, OptimizationTarget, ensure_optimization_target, to_dict
from dsl.io import dump_json, load_json
from optimizer.api_micro_refinement import (
    APIMicroCaseResult,
    APIMicroRefinementPolicy,
    ConservativeAPIMicroRefiner,
    execution_plan_from_dict,
)


TARGET_ROOT = REPO_ROOT / "data" / "targets" / "vdev_benchmarks"
MANIFEST_PATH = TARGET_ROOT / "manifest.json"
DEFAULT_CONFIG_PATH = TARGET_ROOT / "api_micro_refinement_defaults.json"
RUN_ROOT = REPO_ROOT / "data" / "optimizer_runs" / "vdev_benchmarks"
OUTPUT_ROOT = REPO_ROOT / "data" / "optimizer_runs" / "vdev_benchmarks_api_micro_refined"
REPORT_PATH = TARGET_ROOT / "API_MICRO_REFINEMENT_REPORT.md"


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


def _load_policy(path: Path) -> APIMicroRefinementPolicy:
    return APIMicroRefinementPolicy.from_dict(load_json(path))


def _load_case_result(case: Dict[str, Any], refiner: ConservativeAPIMicroRefiner) -> APIMicroCaseResult:
    vdev_id = str(case.get("vdev_id", "")).strip()
    case_name = str(case.get("name", "")).strip() or vdev_id
    target_path = Path(str(case.get("target_path", "")).strip())
    target = _raw_to_target(load_json(target_path))
    plan_path = RUN_ROOT / vdev_id / "m5_execution_plan.json"
    plan = execution_plan_from_dict(load_json(plan_path))
    return refiner.refine_case(vdev_id=vdev_id, case_name=case_name, target=target, plan=plan)


def _write_case_output(result: APIMicroCaseResult, case: Dict[str, Any], policy: APIMicroRefinementPolicy) -> None:
    case_dir = OUTPUT_ROOT / result.vdev_id
    case_dir.mkdir(parents=True, exist_ok=True)
    dump_json(
        case_dir / "api_micro_refinement.json",
        {
            "vdev_id": result.vdev_id,
            "case_name": result.case_name,
            "group": case.get("group"),
            "target_path": case.get("target_path"),
            "policy": policy.to_dict(),
            "original_estimated_latency_ms": result.original_estimated_latency_ms,
            "refined_estimated_latency_ms": result.refined_estimated_latency_ms,
            "added_savings_ms": result.added_savings_ms,
            "added_savings_ratio": result.added_savings_ratio,
            "selected_corridors": [
                {
                    "corridor_id": row.corridor.corridor_id,
                    "protocol": row.corridor.protocol,
                    "phase_kind": row.corridor.phase_kind,
                    "step_ids": row.corridor.step_ids,
                    "batch_ids": row.corridor.batch_ids,
                    "action_ids": row.corridor.action_ids,
                    "original_latency_ms": row.corridor.original_latency_ms,
                    "overlap_candidate_pairs": row.corridor.overlap_candidate_pairs,
                    "refined_latency_ms": row.refined_latency_ms,
                    "latency_saved_ms": row.latency_saved_ms,
                    "serial_events": [event.__dict__ for event in row.serial_events],
                    "refined_events": [event.__dict__ for event in row.refined_events],
                    "validation": row.validation.__dict__,
                }
                for row in result.selected_corridors
            ],
        },
    )
    dump_json(case_dir / "api_micro_refined_plan_overlay.json", to_dict(result.refined_plan))


def _write_summary(results: List[APIMicroCaseResult], cases: List[Dict[str, Any]], policy: APIMicroRefinementPolicy) -> None:
    rows = []
    total_original = 0
    total_refined = 0
    for case, result in zip(cases, results):
        total_original += result.original_estimated_latency_ms
        total_refined += result.refined_estimated_latency_ms
        rows.append(
            {
                "vdev_id": result.vdev_id,
                "name": result.case_name,
                "group": case.get("group"),
                "original_estimated_latency_ms": result.original_estimated_latency_ms,
                "refined_estimated_latency_ms": result.refined_estimated_latency_ms,
                "added_savings_ms": result.added_savings_ms,
                "added_savings_ratio": result.added_savings_ratio,
                "corridor_count": len(result.selected_corridors),
                "validated_corridor_count": sum(1 for row in result.selected_corridors if row.validation.passed),
            }
        )
    dump_json(
        OUTPUT_ROOT / "summary.json",
        {
            "policy": policy.to_dict(),
            "case_count": len(rows),
            "total_original_estimated_latency_ms": total_original,
            "total_refined_estimated_latency_ms": total_refined,
            "total_added_savings_ms": max(0, total_original - total_refined),
            "total_added_savings_ratio": (float(total_original - total_refined) / float(total_original)) if total_original else 0.0,
            "cases": rows,
        },
    )


def _write_markdown(results: List[APIMicroCaseResult], cases: List[Dict[str, Any]], policy: APIMicroRefinementPolicy) -> None:
    lines: List[str] = []
    lines.append("# API Micro-Refinement Report")
    lines.append("")
    lines.append("This report applies post-processing to benchmark M5 plans.")
    lines.append("The policy permits bounded pre-request overlap under coordinator, shared-session, rate-limit, and backoff constraints.")
    lines.append("")
    lines.append("## Policy")
    lines.append("")
    for key, value in policy.to_dict().items():
        lines.append(f"- `{key}` = `{value}`")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("| Case | Corridors | Current Est. | Refined Est. | Added Saving | Added Saving % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for result in results:
        lines.append(
            f"| {result.vdev_id} | {len(result.selected_corridors)} | "
            f"{result.original_estimated_latency_ms} ms | {result.refined_estimated_latency_ms} ms | "
            f"{result.added_savings_ms} ms | {result.added_savings_ratio * 100:.1f}% |"
        )
    lines.append("")
    lines.append("## Case Details")
    lines.append("")
    for case, result in zip(cases, results):
        lines.append(f"### {result.case_name} (`{result.vdev_id}`)")
        lines.append("")
        lines.append(f"- Group: {case.get('group', '')}")
        lines.append(f"- Current estimated latency: `{result.original_estimated_latency_ms} ms`")
        lines.append(f"- Refined estimated latency: `{result.refined_estimated_latency_ms} ms`")
        lines.append(f"- Additional saving from API micro-refinement: `{result.added_savings_ms} ms` (`{result.added_savings_ratio * 100:.1f}%`)")
        if not result.selected_corridors:
            lines.append("- Selected corridors: none")
            lines.append("")
            continue
        for corridor in result.selected_corridors:
            lines.append(
                f"- Corridor `{corridor.corridor.corridor_id}`: "
                f"`{' -> '.join(corridor.corridor.step_ids)}`; "
                f"protocol `{corridor.corridor.protocol}` / kind `{corridor.corridor.phase_kind}`; "
                f"candidate pairs `{corridor.corridor.overlap_candidate_pairs}`; "
                f"serial `{corridor.corridor.original_latency_ms} ms` -> refined `{corridor.refined_latency_ms} ms`; "
                f"validator `{str(corridor.validation.passed).lower()}`"
            )
            lines.append(
                f"  constraints: coordinator=`{corridor.validation.coordinator_constraints_ok}`, "
                f"parallel_updates=`{corridor.validation.parallel_updates_constraints_ok}`, "
                f"session=`{corridor.validation.session_constraints_ok}`, "
                f"backoff=`{corridor.validation.backoff_constraints_ok}`, "
                f"event_loop=`{corridor.validation.event_loop_constraints_ok}`, "
                f"availability=`{corridor.validation.availability_constraints_ok}`"
            )
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run conservative API micro-refinement over existing benchmark plans.")
    parser.add_argument("--cases", nargs="*", default=[], help="Optional subset of vdev_id values.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Policy JSON path.")
    args = parser.parse_args()

    selected = {str(item).strip() for item in args.cases if str(item).strip()}
    cases = [case for case in _load_cases() if not selected or str(case.get("vdev_id", "")).strip() in selected]
    policy = _load_policy(Path(str(args.config)).expanduser())
    refiner = ConservativeAPIMicroRefiner(policy=policy)
    results = [_load_case_result(case, refiner) for case in cases]
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for case, result in zip(cases, results):
        _write_case_output(result, case, policy)
    _write_summary(results, cases, policy)
    _write_markdown(results, cases, policy)
    print(f"refined_cases={len(results)} report={REPORT_PATH} config={args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
