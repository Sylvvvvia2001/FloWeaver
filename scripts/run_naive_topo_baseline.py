from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dsl.contracts import Batch, Event, ExecutionPlan, MSSU, OptimizationTarget, Rule, RuleStatus, Trace, TypedDAG, to_dict
from dsl.io import dump_json
from optimizer.m6_trust import TrustLayer
from optimizer.naive_topo_parallel import NaiveTopoParallelScheduler
from runtime.replay import ReplayResult, _counterexample_runtime_artifacts
from runtime.scenarios import Scenario


TARGET_ROOT = REPO_ROOT / "data" / "targets" / "vdev_benchmarks"
OUT_DIR = REPO_ROOT / "data" / "baselines" / "naive_topo_parallel" / "latest"


def load_targets(root: Path) -> list[tuple[Path, OptimizationTarget]]:
    rows: list[tuple[Path, OptimizationTarget]] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.load(path.open())
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("vdev_actions"):
            rows.append((path, OptimizationTarget(**payload)))
    return rows


def protocol(action: dict[str, Any]) -> str:
    value = str(action.get("protocol") or "").strip().upper()
    return "LOCAL" if value == "MQTT" else value if value in {"BLE", "CLOUD", "LOCAL", "HA"} else "UNKNOWN"


def action_latency_s(action: dict[str, Any]) -> float:
    return {"BLE": 1.8, "CLOUD": 0.9, "LOCAL": 0.12, "HA": 0.05, "UNKNOWN": 0.5}.get(protocol(action), 0.5)


def plan_order(plan) -> list[str]:
    return [aid for batch in plan.ordered_batches for group in batch.parallel_groups for aid in group]


def plan_latency_s(target: OptimizationTarget, plan) -> float:
    actions = {str(a.get("action_id")): a for a in target.vdev_actions}
    total = 0.0
    for batch in plan.ordered_batches:
        batch_lat = 0.0
        for group in batch.parallel_groups:
            if group:
                batch_lat = max(batch_lat, max(action_latency_s(actions[aid]) for aid in group if aid in actions))
        total += batch_lat
    return round(total, 4)


def native_latency_s(target: OptimizationTarget) -> float:
    return round(sum(action_latency_s(a) for a in target.vdev_actions), 4)


def action_op(action: dict[str, Any]) -> str:
    hints = action.get("marker_hints", [])
    if isinstance(hints, list) and hints:
        return str(hints[0])
    if protocol(action) == "CLOUD":
        return "CLOUD_HTTP_CALL"
    if protocol(action) == "BLE":
        return "BLE_GATT_OP"
    if protocol(action) == "LOCAL":
        return "LOCAL_API_READ"
    return "STATE_WRITE" if protocol(action) == "HA" else "ACTION_EXEC"


def action_target(action: dict[str, Any]) -> str:
    target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
    exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
    data = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
    return str(
        target.get("entity_id")
        or target.get("device_id")
        or target.get("id")
        or data.get("entity_id")
        or data.get("device_id")
        or action.get("action_id")
    )


def baseline_order(target: OptimizationTarget) -> list[str]:
    scheduler = NaiveTopoParallelScheduler()
    actions = scheduler._action_index(target)
    out, indegree = scheduler._explicit_graph(target, actions)
    ready = [aid for aid, degree in indegree.items() if degree == 0]
    order: list[str] = []
    while ready:
        aid = sorted(ready, key=lambda item: list(actions).index(item))[0]
        ready.remove(aid)
        order.append(aid)
        for nxt in sorted(out.get(aid, set()), key=lambda item: list(actions).index(item)):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
    order.extend(aid for aid in actions if aid not in order)
    return order


def trace_for_order(target: OptimizationTarget, order: list[str], variant: str) -> Trace:
    actions = {str(a.get("action_id")): a for a in target.vdev_actions}
    events = [
        Event(
            ts=float(idx),
            provider=protocol(actions[aid]),
            op=action_op(actions[aid]),
            target=action_target(actions[aid]),
            params_abst={"action_id": aid},
            phase="RUNTIME",
        )
        for idx, aid in enumerate(order, start=1)
        if aid in actions
    ]
    return Trace(events=events, meta={"variant": variant})


def validation_inputs(target: OptimizationTarget, plan, scenario_id: str) -> tuple[ReplayResult, TypedDAG, list[Rule]]:
    base = trace_for_order(target, baseline_order(target), "baseline")
    opt = trace_for_order(target, plan_order(plan), "naive_topo")
    scenario = Scenario(scenario_id, ["runtime"], {})
    artifacts = _counterexample_runtime_artifacts(scenario, base, opt)
    replay = ReplayResult(scenario_id, base, opt, artifacts)
    dag = TypedDAG(
        nodes={
            f"m{idx:03d}": MSSU(
                mssu_id=f"m{idx:03d}",
                mssu_type="ACT",
                phase="RUNTIME",
                node_ids=[f"n{idx:03d}"],
                action_refs=[str(action.get("action_id"))],
                primary_action_ref=str(action.get("action_id")),
                critical=bool(action.get("critical", False)),
            )
            for idx, action in enumerate(target.vdev_actions, start=1)
        }
    )
    rules = [
        Rule(
            rule_id="naive_topo_check_only",
            title="NaiveTopo check-only validation",
            category="baseline_validation",
            status=RuleStatus.SOFT.value,
            marker_hints=["STATE_WRITE", "BLE_GATT_OP", "CLOUD_HTTP_CALL", "LOCAL_API_READ"],
            evidence_ids=["baseline"],
        )
    ]
    return replay, dag, rules


def run_case(path: Path, target: OptimizationTarget, out_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    case_id = str(target.meta.get("vdev_id") or path.stem)
    scheduler = NaiveTopoParallelScheduler()
    plan = scheduler.schedule(target)
    case_dir = out_dir / "validation" / case_id
    plan_dir = out_dir / "plans"
    plan_dir.mkdir(parents=True, exist_ok=True)
    dump_json(plan_dir / f"{case_id}_plan.json", to_dict(plan))

    replay, dag, rules = validation_inputs(target, plan, case_id)
    result = TrustLayer(case_id, str(case_dir)).evaluate(
        replay_results=[replay],
        dag=dag,
        rules=rules,
        profile_version="naive_topo_parallel/v1",
        optimization_target=target,
        execution_plan=plan,
        replay_with_plan=None,
        replan_with_dag=None,
    )
    native = native_latency_s(target)
    naive = plan_latency_s(target, plan)
    failure_type = ""
    if result.counterexamples:
        failure_type = str(result.counterexamples[0].diff_summary.get("kind", "counterexample"))
    batch_widths = [len(group) for batch in plan.ordered_batches for group in batch.parallel_groups]
    protocols = Counter(protocol(a) for a in target.vdev_actions)
    return {
        "case_id": case_id,
        "target_file": str(path),
        "case_name": str(target.meta.get("name") or case_id),
        "action_count": len(target.vdev_actions),
        "ble_count": protocols.get("BLE", 0),
        "cloud_count": protocols.get("CLOUD", 0),
        "local_count": protocols.get("LOCAL", 0),
        "ha_count": protocols.get("HA", 0),
        "native_latency_s": native,
        "naive_topo_latency_s": naive,
        "latency_gain_s": round(native - naive, 4),
        "latency_gain_pct": round((native - naive) / native * 100.0, 2) if native else 0.0,
        "validation_pass": int(not result.counterexamples),
        "validation_failure_type": failure_type,
        "batch_count": len(plan.ordered_batches),
        "max_batch_width": max(batch_widths) if batch_widths else 0,
        "runtime_s": round(time.perf_counter() - started, 4),
        "micro_not_applicable": True,
        "validation_dir": str(case_dir),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    passed = sum(int(r["validation_pass"]) for r in rows)
    return {
        "baseline": "naive_topo_parallel",
        "mode": "action_level_topological_batching_check_only_validation",
        "case_count": n,
        "validation_pass_count": passed,
        "validation_pass_rate_pct": round(passed / n * 100.0, 2) if n else 0.0,
        "avg_native_latency_s": round(sum(float(r["native_latency_s"]) for r in rows) / n, 4) if n else 0.0,
        "avg_naive_topo_latency_s": round(sum(float(r["naive_topo_latency_s"]) for r in rows) / n, 4) if n else 0.0,
        "avg_latency_gain_s": round(sum(float(r["latency_gain_s"]) for r in rows) / n, 4) if n else 0.0,
        "avg_latency_gain_pct": round(sum(float(r["latency_gain_pct"]) for r in rows) / n, 2) if n else 0.0,
        "avg_runtime_s": round(sum(float(r["runtime_s"]) for r in rows) / n, 4) if n else 0.0,
        "failure_types": dict(Counter(r["validation_failure_type"] or "PASS" for r in rows)),
    }


def _dependency_closure(out: dict[str, set[str]]) -> dict[str, set[str]]:
    reach = {aid: set() for aid in out}
    for aid in out:
        stack = list(out[aid])
        while stack:
            cur = stack.pop()
            if cur in reach[aid]:
                continue
            reach[aid].add(cur)
            stack.extend(out.get(cur, set()) - reach[aid])
    return reach


def classify_failure(target: OptimizationTarget, plan: ExecutionPlan) -> tuple[str, list[tuple[str, str]]]:
    scheduler = NaiveTopoParallelScheduler()
    actions = scheduler._action_index(target)
    out, _ = scheduler._explicit_graph(target, actions)
    reach = _dependency_closure(out)
    baseline_positions = {aid: idx for idx, aid in enumerate(baseline_order(target))}
    plan_positions = {aid: idx for idx, aid in enumerate(plan_order(plan))}
    categories: dict[str, list[tuple[str, str]]] = {
        "explicit_dependency_violation": [],
        "same_device_reorder": [],
        "ha_writeback_before_other_lane_work": [],
        "read_write_independent_reorder": [],
        "cross_batch_independent_reorder": [],
    }
    action_ids = list(actions)
    for idx, left in enumerate(action_ids):
        for right in action_ids[idx + 1 :]:
            if baseline_positions.get(left, 0) < baseline_positions.get(right, 0) and plan_positions.get(left, 0) > plan_positions.get(right, 0):
                left_proto = scheduler._protocol(actions[left])
                right_proto = scheduler._protocol(actions[right])
                if right in reach.get(left, set()):
                    categories["explicit_dependency_violation"].append((left, right))
                elif scheduler._target_key(actions[left]) and scheduler._target_key(actions[left]) == scheduler._target_key(actions[right]):
                    categories["same_device_reorder"].append((left, right))
                elif left_proto == "HA" or right_proto == "HA":
                    categories["ha_writeback_before_other_lane_work"].append((left, right))
                elif scheduler._read_only(actions[left]) != scheduler._read_only(actions[right]):
                    categories["read_write_independent_reorder"].append((left, right))
                else:
                    categories["cross_batch_independent_reorder"].append((left, right))
    for category, pairs in categories.items():
        if pairs:
            return category, pairs[:5]
    return "unknown_or_trace_only", []


def write_failure_audit(out_dir: Path, rows: list[dict[str, Any]]) -> None:
    details: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    examples: dict[str, dict[str, Any]] = {}
    for row in rows:
        if int(row["validation_pass"]):
            continue
        target_path = Path(str(row["target_file"]))
        plan_path = out_dir / "plans" / f"{row['case_id']}_plan.json"
        if not target_path.exists() or not plan_path.exists():
            category, pairs = "missing_audit_input", []
        else:
            target = OptimizationTarget(**json.load(target_path.open()))
            payload = json.load(plan_path.open())
            plan = ExecutionPlan(
                ordered_batches=[Batch(**batch) for batch in payload.get("ordered_batches", [])],
                meta=payload.get("meta", {}),
            )
            category, pairs = classify_failure(target, plan)
        counts[category] += 1
        row_detail = {"case_id": row["case_id"], "classification": category, "sample_pairs": pairs}
        details.append(row_detail)
        examples.setdefault(category, row_detail)

    audit = {
        "failed_case_count": len(details),
        "counts": dict(counts),
        "examples": examples,
        "details": details,
    }
    dump_json(out_dir / "failure_audit.json", audit)
    lines = [
        "# NaiveTopo Failure Audit",
        "",
        f"- Failed cases: {audit['failed_case_count']}",
        "",
        "| Classification | Count | Example |",
        "|---|---:|---|",
    ]
    for category, count in sorted(counts.items()):
        example = examples.get(category, {})
        lines.append(f"| {category} | {count} | {example.get('case_id', '')} |")
    (out_dir / "FAILURE_AUDIT.md").write_text("\n".join(lines) + "\n")


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# NaiveTopo-Parallel Baseline",
        "",
        f"- Cases: {summary['case_count']}",
        f"- Validation pass rate: {summary['validation_pass_rate_pct']}%",
        f"- Average HA-native latency: {summary['avg_native_latency_s']}s",
        f"- Average NaiveTopo latency: {summary['avg_naive_topo_latency_s']}s",
        f"- Average latency gain: {summary['avg_latency_gain_s']}s ({summary['avg_latency_gain_pct']}%)",
        f"- Average runtime: {summary['avg_runtime_s']}s",
        "",
        "| Failure Type | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(summary["failure_types"].items()):
        lines.append(f"| {key} | {value} |")
    path.write_text("\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.clean:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = load_targets(Path(args.target_root))
    rows = [run_case(path, target, out_dir) for path, target in targets]
    write_csv(out_dir / "naive_topo_results.csv", rows)
    summary = summarize(rows)
    dump_json(out_dir / "naive_topo_summary.json", summary)
    write_failure_audit(out_dir, rows)
    write_summary_md(out_dir / "SUMMARY.md", summary)
    (out_dir / "README.md").write_text(
        "NaiveTopo-Parallel is an action-level topological batching baseline. "
        "Validation is check-only: counterexamples are recorded as failures and no rollback or hardening is applied.\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NaiveTopo-Parallel baseline on vdev targets.")
    parser.add_argument("--target-root", default=str(TARGET_ROOT))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--clean", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
