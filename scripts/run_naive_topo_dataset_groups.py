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

from dsl.contracts import OptimizationTarget, to_dict
from dsl.io import dump_json
from optimizer.naive_topo_parallel import NaiveTopoParallelScheduler
from scripts.run_independent_device_state_audit import parse_xlsx
from scripts.run_naive_topo_baseline import plan_order, trace_for_order, validation_inputs
from optimizer.m6_trust import TrustLayer


DEFAULT_XLSX = REPO_ROOT.parent / "result" / "ifttt_samples_vibeaura_simulated_estimates.xlsx"
DEFAULT_OUT = REPO_ROOT / "data" / "baselines" / "naive_topo_parallel" / "dataset_groups_latest"

DATASETS = {
    "smart-home": {
        "sheet": "Simulated Estimates",
        "bins": [("Group1", 0.0, 3.0), ("Group2", 3.0, 6.0), ("Group3", 6.0, 9.0), ("Group4", 9.0, None)],
    },
    "long-chain": {
        "sheet": "LongChain System Estimates",
        "bins": [("Group1", 0.0, 9.0), ("Group2", 9.0, 18.0), ("Group3", 18.0, 27.0), ("Group4", 27.0, None)],
    },
}


def num(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def count(row: dict[str, Any], key: str) -> int:
    return max(0, int(round(num(row.get(key)))))


def latency_group(value: float, bins: list[tuple[str, float, float | None]]) -> str:
    for name, lo, hi in bins:
        if value > lo and (hi is None or value <= hi):
            return name
    return bins[0][0]


def synthesize_target(dataset: str, row: dict[str, Any]) -> tuple[OptimizationTarget, dict[str, float]]:
    sample_id = str(row.get("sample_id"))
    name = str(row.get("ifttt_routine_name") or sample_id)
    protocol_counts = {
        "BLE": count(row, "ble_device_count"),
        "LOCAL": count(row, "local_lan_gateway_media_device_count"),
        "CLOUD": count(row, "cloud_account_api_device_count"),
    }
    actions: list[dict[str, Any]] = []
    deps: list[dict[str, str]] = []
    lanes: dict[str, list[str]] = {"BLE": [], "LOCAL": [], "CLOUD": []}

    for proto, n in protocol_counts.items():
        for idx in range(1, n + 1):
            action_id = f"A_{proto.lower()}_{idx:03d}"
            lanes[proto].append(action_id)
            actions.append(
                {
                    "action_id": action_id,
                    "protocol": proto,
                    "type": {"BLE": "read_sensor", "LOCAL": "get_state", "CLOUD": "status"}[proto],
                    "target": {"id": f"{dataset}:{sample_id}:{proto.lower()}:{idx}", "kind": f"{proto.lower()}_endpoint"},
                }
            )

    ha_ids: list[str] = []
    for proto, ids in lanes.items():
        if not ids:
            continue
        write_id = f"A_ha_{proto.lower()}"
        ha_ids.append(write_id)
        actions.append(
            {
                "action_id": write_id,
                "protocol": "HA",
                "type": "write",
                "target": {"entity_id": f"sensor.{dataset}.{sample_id}.{proto.lower()}_lane"},
            }
        )
        deps.extend({"before": action_id, "after": write_id, "reason": f"{proto.lower()}_lane_write"} for action_id in ids)

    if len(ha_ids) > 1:
        overall_id = "A_ha_overall"
        actions.append(
            {
                "action_id": overall_id,
                "protocol": "HA",
                "type": "write",
                "target": {"entity_id": f"sensor.{dataset}.{sample_id}.overall"},
            }
        )
        deps.extend({"before": action_id, "after": overall_id, "reason": "overall_write"} for action_id in ha_ids)

    weights = {"BLE": 1.8, "CLOUD": 0.9, "LOCAL": 0.12, "HA": 0.05}
    raw = {str(action["action_id"]): weights.get(str(action.get("protocol")), 0.5) for action in actions}
    gt = max(0.001, num(row.get("ground_truth_latency_s")))
    scale = gt / sum(raw.values()) if raw else 1.0
    lat_ms = {action_id: value * scale * 1000.0 for action_id, value in raw.items()}
    target = OptimizationTarget(
        meta={"vdev_id": f"naive_{dataset}_{sample_id}", "name": name, "dataset": dataset},
        vdev_actions=actions,
        hard_dependencies=deps,
    )
    return target, lat_ms


def plan_latency_s(target: OptimizationTarget, plan: Any, lat_ms: dict[str, float]) -> float:
    total = 0.0
    for batch in plan.ordered_batches:
        batch_latency = 0.0
        for group in batch.parallel_groups:
            if group:
                batch_latency = max(batch_latency, max(lat_ms.get(action_id, 500.0) for action_id in group) / 1000.0)
        total += batch_latency
    return round(total, 4)


def run_row(dataset: str, row: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    sample_id = str(row.get("sample_id"))
    case_id = f"naive_{dataset}_{sample_id}"
    target, lat_ms = synthesize_target(dataset, row)
    scheduler = NaiveTopoParallelScheduler()
    plan = scheduler.schedule(target, runtime_metrics={"latency_ms": lat_ms})

    plan_dir = out_dir / dataset / "plans"
    validation_dir = out_dir / dataset / "validation" / case_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    dump_json(plan_dir / f"{case_id}_plan.json", to_dict(plan))

    replay, dag, rules = validation_inputs(target, plan, case_id)
    result = TrustLayer(case_id, str(validation_dir)).evaluate(
        replay_results=[replay],
        dag=dag,
        rules=rules,
        profile_version="naive_topo_parallel/dataset_groups",
        optimization_target=target,
        execution_plan=plan,
        replay_with_plan=None,
        replan_with_dag=None,
    )

    gt = round(num(row.get("ground_truth_latency_s")), 4)
    naive = plan_latency_s(target, plan, lat_ms)
    failure_type = ""
    if result.counterexamples:
        failure_type = str(result.counterexamples[0].diff_summary.get("kind", "counterexample"))
    batch_widths = [len(group) for batch in plan.ordered_batches for group in batch.parallel_groups]
    protocol_counts = Counter(str(action.get("protocol")).upper() for action in target.vdev_actions)
    return {
        "dataset": dataset,
        "sample_id": sample_id,
        "routine_name": str(row.get("ifttt_routine_name") or sample_id),
        "latency_group": latency_group(gt, DATASETS[dataset]["bins"]),
        "ble_count": count(row, "ble_device_count"),
        "local_count": count(row, "local_lan_gateway_media_device_count"),
        "cloud_count": count(row, "cloud_account_api_device_count"),
        "total_device_count": count(row, "total_device_count"),
        "ha_action_count": protocol_counts.get("HA", 0),
        "native_latency_s": gt,
        "naive_topo_latency_s": naive,
        "latency_gain_s": round(gt - naive, 4),
        "latency_gain_pct": round((gt - naive) / gt * 100.0, 2) if gt else 0.0,
        "validation_pass": int(not result.counterexamples),
        "validation_failure_type": failure_type,
        "batch_count": len(plan.ordered_batches),
        "max_batch_width": max(batch_widths) if batch_widths else 0,
        "runtime_s": round(time.perf_counter() - started, 4),
        "validation_dir": str(validation_dir),
    }


def mean(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(num(row.get(key)) for row in rows) / len(rows), 4) if rows else 0.0


def group_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for dataset, config in DATASETS.items():
        dataset_rows = [row for row in rows if row["dataset"] == dataset]
        for group, lo, hi in config["bins"]:
            group_rows = [row for row in dataset_rows if row["latency_group"] == group]
            passed = [row for row in group_rows if int(row["validation_pass"]) == 1]
            label = f"({lo:g},{hi:g}]s" if hi is not None else f"({lo:g},inf)s"
            out.append(
                {
                    "dataset": dataset,
                    "group": group,
                    "latency_bin": label,
                    "case_count": len(group_rows),
                    "pass_count": len(passed),
                    "pass_rate_pct": round(len(passed) / len(group_rows) * 100.0, 2) if group_rows else 0.0,
                    "avg_native_latency_s": mean(group_rows, "native_latency_s"),
                    "avg_naive_topo_latency_s": mean(group_rows, "naive_topo_latency_s"),
                    "avg_latency_gain_s": mean(group_rows, "latency_gain_s"),
                    "avg_latency_gain_pct": mean(group_rows, "latency_gain_pct"),
                    "passed_avg_naive_topo_latency_s": mean(passed, "naive_topo_latency_s"),
                    "passed_avg_latency_gain_pct": mean(passed, "latency_gain_pct"),
                    "avg_runtime_s": mean(group_rows, "runtime_s"),
                    "failure_types": json.dumps(dict(Counter(row["validation_failure_type"] or "PASS" for row in group_rows)), sort_keys=True),
                }
            )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = ["# NaiveTopo Dataset Group Results", ""]
    for dataset in DATASETS:
        lines.extend([f"## {dataset}", "", "| Group | Bin | Cases | Pass Rate | Native Avg | NaiveTopo Avg | Gain | Gain % |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
        for row in [item for item in rows if item["dataset"] == dataset]:
            lines.append(
                f"| {row['group']} | {row['latency_bin']} | {row['case_count']} | {row['pass_rate_pct']}% | "
                f"{row['avg_native_latency_s']}s | {row['avg_naive_topo_latency_s']}s | "
                f"{row['avg_latency_gain_s']}s | {row['avg_latency_gain_pct']}% |"
            )
        lines.append("")
    path.write_text("\n".join(lines))


def run(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.clean:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sheets = parse_xlsx(Path(args.xlsx))
    rows: list[dict[str, Any]] = []
    for dataset, config in DATASETS.items():
        for row in sheets[config["sheet"]]:
            rows.append(run_row(dataset, row, out_dir))

    summaries = group_summary(rows)
    write_csv(out_dir / "naive_topo_dataset_results.csv", rows)
    write_csv(out_dir / "naive_topo_group_summary.csv", summaries)
    dump_json(out_dir / "naive_topo_group_summary.json", {"rows": summaries})
    write_summary_md(out_dir / "SUMMARY.md", summaries)
    print(json.dumps({"out_dir": str(out_dir), "group_summary": summaries}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NaiveTopo on smart-home and long-chain Excel datasets.")
    parser.add_argument("--xlsx", default=str(DEFAULT_XLSX))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--clean", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
