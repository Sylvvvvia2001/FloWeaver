from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dsl.contracts import Event, MSSU, OptimizationTarget, Rule, RuleStatus, Trace, TypedDAG
from optimizer.m6_trust import TrustLayer
from runtime.replay import ReplayResult, _counterexample_runtime_artifacts
from runtime.scenarios import Scenario


DEFAULT_MANIFEST = REPO_ROOT / "data" / "independent_device_state_audit" / "latest" / "sampling_manifest.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "mutation_injected_divergence" / "latest"

MUTATION_TARGETS = {
    "M1_dependent_action_swap": 20,
    "M2_premature_state_writeback": 20,
    "M3_missing_refresh_status_query": 20,
    "M4_ble_serialization_violation": 12,
    "M5_cloud_rate_session_violation": 18,
    "M6_wrong_batching_writeback_merge": 20,
    "M7_same_device_ordering_violation": 20,
    "M8_cleanup_lifecycle_violation": 20,
}

MUTATION_LABELS = {
    "M1_dependent_action_swap": "Dependent-action swap",
    "M2_premature_state_writeback": "Premature state writeback",
    "M3_missing_refresh_status_query": "Missing refresh/status query",
    "M4_ble_serialization_violation": "BLE serialization violation",
    "M5_cloud_rate_session_violation": "Cloud rate/session violation",
    "M6_wrong_batching_writeback_merge": "Wrong batching/writeback merge",
    "M7_same_device_ordering_violation": "Same-device ordering violation",
    "M8_cleanup_lifecycle_violation": "Cleanup/lifecycle violation",
}

EXPECTED_COMPATIBLE = {
    "M1_dependent_action_swap": {"order_violation"},
    "M2_premature_state_writeback": {"order_violation", "semantic_delta"},
    "M3_missing_refresh_status_query": {"missing_prerequisite"},
    "M4_ble_serialization_violation": {"order_violation", "semantic_delta"},
    "M5_cloud_rate_session_violation": {"missing_prerequisite"},
    "M6_wrong_batching_writeback_merge": {"missing_prerequisite", "order_violation", "semantic_delta"},
    "M7_same_device_ordering_violation": {"order_violation"},
    "M8_cleanup_lifecycle_violation": {"order_violation", "missing_prerequisite", "semantic_delta"},
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def event(ts: float, provider: str, op: str, target: str, action_id: str) -> Event:
    return Event(ts=ts, provider=provider, op=op, target=target, params_abst={"action_id": action_id})


def provider(row: dict[str, str]) -> str:
    modality = row["protocol_modality"]
    if "BLE" in modality:
        return "BLE"
    if "Cloud" in modality:
        return "CLOUD"
    if "Local" in modality:
        return "LOCAL"
    return "HA"


def target(row: dict[str, str], suffix: str) -> str:
    safe = row["routine_id"].replace(":", "_").replace("/", "_")
    return f"{row['dataset']}:{safe}:{suffix}"


def mutation_traces(row: dict[str, str], mutation_type: str) -> tuple[Trace, Trace]:
    p = provider(row)
    root = target(row, mutation_type[:2].lower())
    if mutation_type == "M1_dependent_action_swap":
        base = [
            event(1, p, "READ_SENSOR", f"{root}:sensor", "A_read"),
            event(2, p, "DEVICE_COMMAND", f"{root}:actuator", "A_act"),
            event(3, "HA", "STATE_WRITE", f"{root}:summary", "A_write"),
        ]
        opt = [base[1], base[0], base[2]]
    elif mutation_type == "M2_premature_state_writeback":
        base = [
            event(1, p, "DEVICE_COMMAND", f"{root}:device", "A_cmd"),
            event(2, p, "RESPONSE_RECV", f"{root}:device", "A_resp"),
            event(3, "HA", "STATE_WRITE", f"{root}:entity", "A_write"),
        ]
        opt = [base[2], base[0], base[1]]
    elif mutation_type == "M3_missing_refresh_status_query":
        base = [
            event(1, p, "REFRESH_STATUS", f"{root}:device", "A_refresh"),
            event(2, "HA", "STATE_WRITE", f"{root}:entity", "A_write"),
        ]
        opt = [base[1]]
    elif mutation_type == "M4_ble_serialization_violation":
        base = [
            event(1, "BLE", "BLE_CONNECT", f"{root}:ble", "A_connect"),
            event(2, "BLE", "BLE_GATT_OP", f"{root}:ble", "A_gatt"),
            event(3, "BLE", "BLE_DISCONNECT", f"{root}:ble", "A_disconnect"),
        ]
        opt = [base[1], base[0], base[2]]
    elif mutation_type == "M5_cloud_rate_session_violation":
        base = [
            event(1, "CLOUD", "CLOUD_AUTH_CHECK", f"{root}:api", "A_auth"),
            event(2, "CLOUD", "CLOUD_RATE_CHECK", f"{root}:api", "A_rate"),
            event(3, "CLOUD", "CLOUD_HTTP_CALL", f"{root}:api", "A_call"),
            event(4, "CLOUD", "CLOUD_RESPONSE_RECV", f"{root}:api", "A_resp"),
            event(5, "HA", "STATE_WRITE", f"{root}:entity", "A_write"),
        ]
        opt = [base[2], base[3], base[4]]
    elif mutation_type == "M6_wrong_batching_writeback_merge":
        base = [
            event(1, p, "DEVICE_COMMAND", f"{root}:light", "A_light_cmd"),
            event(2, "HA", "STATE_WRITE", f"{root}:light_state", "A_light_write"),
            event(3, p, "DEVICE_COMMAND", f"{root}:plug", "A_plug_cmd"),
            event(4, "HA", "STATE_WRITE", f"{root}:plug_state", "A_plug_write"),
        ]
        opt = [base[0], base[1], base[2], event(4, "HA", "STATE_WRITE", f"{root}:light_state", "A_plug_write")]
    elif mutation_type == "M7_same_device_ordering_violation":
        base = [
            event(1, p, "DEVICE_COMMAND", f"{root}:same_device:on", "A_on"),
            event(2, p, "DEVICE_COMMAND", f"{root}:same_device:level", "A_level"),
            event(3, "HA", "STATE_WRITE", f"{root}:entity", "A_write"),
        ]
        opt = [base[1], base[0], base[2]]
    elif mutation_type == "M8_cleanup_lifecycle_violation":
        base = [
            event(1, p, "SUBSCRIBE", f"{root}:stream", "A_sub"),
            event(2, p, "EVENT_RECV", f"{root}:stream", "A_recv"),
            event(3, p, "UNSUBSCRIBE", f"{root}:stream", "A_unsub"),
        ]
        opt = [base[0], base[2], base[1]]
    else:
        raise ValueError(f"unknown mutation type: {mutation_type}")
    return Trace(base, {"variant": "baseline"}), Trace(opt, {"variant": "mutated_optimized"})


def applicable(row: dict[str, str], mutation_type: str) -> bool:
    modality = row["protocol_modality"]
    if mutation_type == "M4_ble_serialization_violation":
        return "BLE" in modality
    if mutation_type == "M5_cloud_rate_session_violation":
        return "Cloud" in modality
    return True


def build_mutation_manifest(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for mutation_type, count in MUTATION_TARGETS.items():
        eligible = [row for row in rows if applicable(row, mutation_type)]
        if not eligible:
            raise ValueError(f"no eligible routines for {mutation_type}")
        for idx in range(count):

            row = eligible[(idx * len(eligible)) // count % len(eligible)]
            mutation_id = f"mut_{len(manifest) + 1:03d}"
            manifest.append(
                {
                    "mutation_id": mutation_id,
                    "dataset": row["dataset"],
                    "routine_id": row["routine_id"],
                    "routine_name": row["routine_name"],
                    "latency_group": row["latency_group"],
                    "protocol_modality": row["protocol_modality"],
                    "rollback_layer_count": row["rollback_layer_count"],
                    "mutation_type": mutation_type,
                    "mutation_label": MUTATION_LABELS[mutation_type],
                    "expected_compatible_categories": ",".join(sorted(EXPECTED_COMPATIBLE[mutation_type])),
                    "valid_mutation": 1,
                    "selection_index": idx,
                }
            )
    routine_counts = Counter((row["dataset"], row["routine_id"]) for row in manifest)
    missing = [row for row in rows if routine_counts[(row["dataset"], row["routine_id"])] == 0]
    for row in missing:
        for idx in range(len(manifest) - 1, -1, -1):
            mutation_type = str(manifest[idx]["mutation_type"])
            old_key = (str(manifest[idx]["dataset"]), str(manifest[idx]["routine_id"]))
            if routine_counts[old_key] <= 1:
                continue
            if not applicable(row, mutation_type):
                continue
            mutation_id = str(manifest[idx]["mutation_id"])
            selection_index = manifest[idx]["selection_index"]
            routine_counts[old_key] -= 1
            manifest[idx].update(
                {
                    "mutation_id": mutation_id,
                    "dataset": row["dataset"],
                    "routine_id": row["routine_id"],
                    "routine_name": row["routine_name"],
                    "latency_group": row["latency_group"],
                    "protocol_modality": row["protocol_modality"],
                    "rollback_layer_count": row["rollback_layer_count"],
                    "selection_index": selection_index,
                }
            )
            routine_counts[(row["dataset"], row["routine_id"])] += 1
            break
    return manifest


def validation_inputs(case: dict[str, Any], base: Trace, opt: Trace, artifacts: dict[str, Any]) -> tuple[ReplayResult, OptimizationTarget, TypedDAG, list[Rule]]:
    actions = sorted({event.params_abst["action_id"] for event in base.events + opt.events})
    vdev_actions = [
        {
            "action_id": action_id,
            "protocol": "HA",
            "critical": True,
            "exec": {"kind": "synthetic_trace_event"},
            "target": {"kind": "synthetic", "id": action_id},
        }
        for action_id in actions
    ]
    target = OptimizationTarget(
        meta={"vdev_id": case["routine_id"], "mutation_id": case["mutation_id"]},
        source_scope={"files": ["/tmp/synthetic_mutation_replay.py"]},
        vdev_actions=vdev_actions,
        target_anchors={
            "entities": sorted({event.target for event in base.events + opt.events}),
            "anchor_ops": sorted({event.op for event in base.events + opt.events}),
        },
        validation={
            "observation": {"canonicalization_version": "v1"},
            "trust": {
                "max_counterexample_cases": 1,
                "max_counterexample_hunks": 20,
                "counterexample_budget_seconds": 2,
            },
        },
        critical_action_ids=actions,
    )
    dag = TypedDAG(
        nodes={
            f"m{idx:02d}": MSSU(
                mssu_id=f"m{idx:02d}",
                mssu_type="ACT",
                phase="RUNTIME",
                node_ids=[f"n{idx:02d}"],
                action_refs=[action_id],
                primary_action_ref=action_id,
                critical=True,
            )
            for idx, action_id in enumerate(actions, start=1)
        }
    )
    rules = [
        Rule(
            rule_id=f"rule_{case['mutation_type']}",
            title=f"Mutation detection rule for {case['mutation_label']}",
            category="mutation_safety",
            status=RuleStatus.SOFT.value,
            marker_hints=sorted({event.op for event in base.events + opt.events}),
            evidence_ids=["mutation_suite"],
        )
    ]
    replay = ReplayResult(case["mutation_id"], base, opt, artifacts)
    return replay, target, dag, rules


def run_case(case: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    base, opt = mutation_traces(case, case["mutation_type"])
    scenario = Scenario(case["mutation_id"], ["runtime"], {"mutation_type": case["mutation_type"]})
    artifacts = _counterexample_runtime_artifacts(scenario, base, opt)
    replay, target, dag, rules = validation_inputs(case, base, opt, artifacts)
    case_dir = out_dir / "cases" / case["mutation_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    result = TrustLayer(case["mutation_id"], str(case_dir)).evaluate(
        replay_results=[replay],
        dag=dag,
        rules=rules,
        profile_version="mutation_suite/v1",
        optimization_target=target,
        rollback_max_steps=1,
    )
    counterexamples = result.counterexamples
    rejected = bool(counterexamples) or result.summary.get("tolerant_pass", 0) == 0
    accepted_without_signal = not rejected
    first = counterexamples[0] if counterexamples else None
    verdict = str(first.diff_summary.get("counterexample_verdict", "")) if first else ""
    diff_kind = str(first.diff_summary.get("kind", "")) if first else ""
    trace_only = verdict == "TRACE_ONLY"
    concrete_cex = bool(first and not trace_only)
    compatible = diff_kind in EXPECTED_COMPATIBLE[case["mutation_type"]]
    return {
        **case,
        "validator_verdict": "REJECT" if rejected else "ACCEPT",
        "mutation_rejected": int(rejected),
        "accepted_without_rejection_or_counterexample": int(accepted_without_signal),
        "false_positive": int(accepted_without_signal),
        "counterexample_found": int(bool(counterexamples)),
        "concrete_counterexample": int(concrete_cex),
        "trace_only_rejection": int(rejected and not concrete_cex),
        "counterexample_verdict": verdict,
        "validator_diff_kind": diff_kind,
        "compatible_violation_type": int(bool(rejected and compatible)),
        "rollback_attempted": 0,
        "rollback_repaired": 0,
        "final_accept_after_rollback": "",
        "alignment_status": str(artifacts.get("alignment_status", "")),
        "m6_case_dir": str(case_dir),
    }


def pct(num: float, den: float) -> float:
    return round(100.0 * num / den, 2) if den else 0.0


def aggregate(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row[key])].append(row)
    out: dict[str, dict[str, Any]] = {}
    for name, items in sorted(buckets.items()):
        n = len(items)
        rejected = sum(int(row["mutation_rejected"]) for row in items)
        false_pos = sum(int(row["false_positive"]) for row in items)
        concrete = sum(int(row["concrete_counterexample"]) for row in items)
        trace_only = sum(int(row["trace_only_rejection"]) for row in items)
        compatible = sum(int(row["compatible_violation_type"]) for row in items)
        out[name] = {
            "mutations": n,
            "mutation_rejection_rate_pct": pct(rejected, n),
            "false_positive_rate_pct": pct(false_pos, n),
            "counterexample_yield_pct": pct(concrete, n),
            "trace_only_reject_pct": pct(trace_only, n),
            "violation_type_accuracy_pct": pct(compatible, rejected),
            "false_positive_count": false_pos,
            "counterexample_count": sum(int(row["counterexample_found"]) for row in items),
        }
    return out


def write_summary(out_dir: Path, manifest: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    summary = {
        "oracle_mode": "synthetic_mutation_replay",
        "note": "Synthetic semantic-breaking traces are fed through the existing M6 TrustLayer; this does not execute real Home Assistant routines.",
        "routines": len({(row["dataset"], row["routine_id"]) for row in manifest}),
        "valid_injected_mutations": total,
        "datasets": aggregate(results, "dataset"),
        "mutation_types": aggregate(results, "mutation_type"),
        "overall": aggregate([{**row, "overall": "overall"} for row in results], "overall")["overall"],
        "modality_counts": dict(Counter(row["protocol_modality"] for row in manifest)),
        "latency_group_counts": dict(Counter(row["latency_group"] for row in manifest)),
        "counterexample_verdict_counts": dict(Counter(row["counterexample_verdict"] for row in results)),
        "validator_diff_kind_counts": dict(Counter(row["validator_diff_kind"] for row in results)),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Mutation-Injected Divergence Analysis",
        "",
        f"- Oracle mode: `{summary['oracle_mode']}`",
        f"- Note: {summary['note']}",
        f"- Routines: {summary['routines']}",
        f"- Valid injected mutations: {summary['valid_injected_mutations']}",
        "",
        "## Overall",
        "",
        "| Scope | # Mut. | MRR | FPR | CEY | Trace-only Reject | VTA |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in {**summary["datasets"], "Overall": summary["overall"]}.items():
        lines.append(
            f"| {name} | {row['mutations']} | {row['mutation_rejection_rate_pct']}% | "
            f"{row['false_positive_rate_pct']}% | {row['counterexample_yield_pct']}% | "
            f"{row['trace_only_reject_pct']}% | {row['violation_type_accuracy_pct']}% |"
        )
    lines += [
        "",
        "## By Mutation Type",
        "",
        "| Mutation Type | # Cases | MRR | FPR | CEY | Trace-only Reject | VTA |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mutation_type, row in summary["mutation_types"].items():
        lines.append(
            f"| {MUTATION_LABELS.get(mutation_type, mutation_type)} | {row['mutations']} | "
            f"{row['mutation_rejection_rate_pct']}% | {row['false_positive_rate_pct']}% | "
            f"{row['counterexample_yield_pct']}% | {row['trace_only_reject_pct']}% | "
            f"{row['violation_type_accuracy_pct']}% |"
        )
    lines += [
        "",
        "## Detection Evidence",
        "",
        "| Evidence Type | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(summary["counterexample_verdict_counts"].items()):
        lines.append(f"| counterexample verdict: {key} | {value} |")
    for key, value in sorted(summary["validator_diff_kind_counts"].items()):
        lines.append(f"| validator diff kind: {key} | {value} |")
    lines += [
        "",
        "## Coverage",
        "",
        "| Coverage Type | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(summary["modality_counts"].items()):
        lines.append(f"| modality: {key} | {value} |")
    for key, value in sorted(summary["latency_group_counts"].items()):
        lines.append(f"| latency group: {key} | {value} |")
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    (out_dir / "README.md").write_text(
        "# Mutation-Injected Divergence Analysis Files\n\n"
        "This directory contains a local synthetic replay of semantic-breaking mutations through the existing M6 TrustLayer.\n\n"
        "- `experiment_config.json`: run configuration and false-positive definition.\n"
        "- `mutation_manifest.csv`: selected routine/mutation pairs before validation.\n"
        "- `mutation_results.csv`: one row per injected mutation with validator verdict and counterexample fields.\n"
        "- `summary.json`: machine-readable aggregate metrics.\n"
        "- `SUMMARY.md`: paper-facing summary tables.\n"
        "- `cases/<mutation_id>/`: raw M6 artifacts for each mutation, including trace compare rows, counterexamples, certificate, rollback log, and validation stats.\n\n"
        "`synthetic_mutation_replay` means the script tests M6 validator behavior on synthetic semantic-divergence traces; it does not execute Home Assistant integrations or real devices.\n"
    )
    return summary


def run(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.clean:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_csv(Path(args.manifest))
    manifest = build_mutation_manifest(rows)
    results = [run_case(case, out_dir) for case in manifest]
    assert len(results) == sum(MUTATION_TARGETS.values())
    write_csv(out_dir / "mutation_manifest.csv", manifest)
    write_csv(out_dir / "mutation_results.csv", results)
    config = {
        "manifest": str(Path(args.manifest)),
        "mutation_targets": MUTATION_TARGETS,
        "mode": "synthetic_mutation_replay",
        "false_positive_definition": "accepted without rejection or counterexample before rollback repair",
        "rollback_repair": "not attempted; this script measures initial validation detection only",
    }
    (out_dir / "experiment_config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    summary = write_summary(out_dir, manifest, results)
    print(f"Wrote mutation audit files to {out_dir}")
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Mutation-Injected Divergence Analysis.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--clean", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
