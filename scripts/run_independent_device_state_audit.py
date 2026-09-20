from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import sys
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = REPO_ROOT.parent / "result"
DEFAULT_XLSX = RESULT_ROOT / "ifttt_samples_vibeaura_simulated_estimates.xlsx"
DEFAULT_OUT = REPO_ROOT / "data" / "independent_device_state_audit" / "latest"
VDEV_ROOT = REPO_ROOT / "data" / "targets" / "vdev_benchmarks"

SMART_SHEET = "Simulated Estimates"
LONG_SHEET = "LongChain System Estimates"

SMART_IFTTT_IDS = [
    "16",
    "86",
    "58",
    "122",
    "143",
    "116",
    "211",
    "228",
    "284",
    "232",
    "72",
    "210",
    "212",
    "248",
    "202",
    "205",
    "240",
]
SMART_VDEV_IDS = [
    "vdev_morning_wakeup_readiness_01",
    "vdev_weekend_whole_home_snapshot_01",
    "vdev_vacation_departure_final_audit_01",
]
LONG_IDS = ["189", "86", "122", "154", "210", "234", "205", "215", "203", "213"]


def num(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def latency_group(value: Any) -> str:
    gt = num(value)
    if gt <= 3:
        return "G1:(0,3]"
    if gt <= 6:
        return "G2:(3,6]"
    if gt <= 9:
        return "G3:(6,9]"
    return "G4:(9,+)"


def protocol_modality(row: dict[str, Any]) -> str:
    parts = []
    if int(num(row.get("ble_device_count"))) > 0:
        parts.append("BLE")
    if int(num(row.get("local_lan_gateway_media_device_count"))) > 0:
        parts.append("Local")
    if int(num(row.get("cloud_account_api_device_count"))) > 0:
        parts.append("Cloud")
    return "+".join(parts) or "None"


def parse_xlsx(path: Path) -> dict[str, list[dict[str, Any]]]:
    ns = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    with ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", ns):
                shared.append(
                    "".join(
                        text.text or ""
                        for text in si.iter(
                            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                        )
                    )
                )

        def cell_value(cell: ET.Element) -> Any:
            typ = cell.attrib.get("t")
            value = cell.find("a:v", ns)
            if value is None:
                inline = cell.find("a:is", ns)
                if inline is None:
                    return None
                return "".join(
                    text.text or ""
                    for text in inline.iter(
                        "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                    )
                )
            text = value.text or ""
            if typ == "s":
                return shared[int(text)]
            if typ == "b":
                return bool(int(text))
            try:
                as_float = float(text)
                return int(as_float) if as_float.is_integer() else as_float
            except Exception:
                return text

        def col_num(ref: str) -> int:
            letters = "".join(re.findall("[A-Z]+", ref))
            total = 0
            for ch in letters:
                total = total * 26 + ord(ch) - 64
            return total

        sheets: dict[str, list[dict[str, Any]]] = {}
        sheet_nodes = workbook.find("a:sheets", ns)
        if sheet_nodes is None:
            raise ValueError("workbook has no sheets")
        for sheet in sheet_nodes:
            name = sheet.attrib["name"]
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = relmap[rid]
            if not target.startswith("xl/"):
                target = "xl/" + target
            root = ET.fromstring(zf.read(target))
            rows: list[list[Any]] = []
            for row in root.findall(".//a:sheetData/a:row", ns):
                values: dict[int, Any] = {}
                for cell in row.findall("a:c", ns):
                    values[col_num(cell.attrib["r"])] = cell_value(cell)
                if values:
                    rows.append([values.get(i) for i in range(1, max(values) + 1)])
            if not rows:
                sheets[name] = []
                continue
            headers = [str(item) for item in rows[0]]
            sheets[name] = [
                {header: row[idx] if idx < len(row) else None for idx, header in enumerate(headers)}
                for row in rows[1:]
            ]
        return sheets


def selected_reason(row: dict[str, Any]) -> str:
    total = int(num(row.get("total_device_count")))
    ble = int(num(row.get("ble_device_count")))
    cloud = int(num(row.get("cloud_account_api_device_count")))
    coarse = num(row.get("coarse_schedule_latency_gain_pct"))
    micro = num(row.get("micro_level_schedule_latency_gain_pct"))
    rollback = row.get("rollback_layer_count")
    parts = []
    if total >= 4 or coarse >= 20:
        parts.append("macro-level parallelization")
    if ble or micro - coarse >= 2:
        parts.append("micro-level setup overlap")
    if cloud >= 2:
        parts.append("session reuse/rate-budget path")
    if total >= 4:
        parts.append("batching/writeback merging")
    if rollback not in (None, "", "None"):
        rb = int(num(rollback))
        if rb > 0:
            parts.append(f"accepted after rollback L{rb}")
    return "; ".join(parts) or "simple accepted routine"


def row_from_sheet(rows: list[dict[str, Any]], sample_id: str) -> dict[str, Any]:
    for row in rows:
        if str(row.get("sample_id")) == str(sample_id):
            return dict(row)
    raise KeyError(f"sample_id {sample_id!r} not found")


def vdev_row(vdev_id: str) -> dict[str, Any]:
    path = VDEV_ROOT / f"{vdev_id}.json"
    payload = json.loads(path.read_text())
    counts = Counter(str(action.get("protocol", "")).upper() for action in payload.get("vdev_actions", []))
    total = counts["BLE"] + counts["LOCAL"] + counts["CLOUD"]
    return {
        "sample_id": vdev_id,
        "ifttt_routine_name": payload.get("meta", {}).get("name") or vdev_id,
        "protocol_mix": "+".join(p for p in ("ble", "local", "cloud") if counts[p.upper()]),
        "ble_device_count": counts["BLE"],
        "local_lan_gateway_media_device_count": counts["LOCAL"],
        "cloud_account_api_device_count": counts["CLOUD"],
        "total_device_count": total,
        "ground_truth_latency_s": "",
        "coarse_schedule_latency_s": "",
        "coarse_schedule_latency_gain_pct": "",
        "micro_level_schedule_latency_s": "",
        "micro_level_schedule_latency_gain_pct": "",
        "pass_rate": 1,
        "rollback_layer_count": "",
    }


def build_sampling_manifest(sheets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for sample_id in SMART_IFTTT_IDS:
        row = row_from_sheet(sheets[SMART_SHEET], sample_id)
        row["dataset"] = "smart-home"
        row["source"] = "ifttt_sheet1"
        rows.append(row)

    for vdev_id in SMART_VDEV_IDS:
        row = vdev_row(vdev_id)
        row["dataset"] = "smart-home"
        row["source"] = "vdev_benchmark"
        rows.append(row)

    for sample_id in LONG_IDS:
        row = row_from_sheet(sheets[LONG_SHEET], sample_id)
        row["dataset"] = "long-chain"
        row["source"] = "long_chain_sheet4"
        rows.append(row)

    manifest: list[dict[str, Any]] = []
    for row in rows:
        pass_rate = num(row.get("pass_rate"))
        if pass_rate != 1:
            raise ValueError(f"selected routine is not validator accepted: {row.get('sample_id')}")
        manifest.append(
            {
                "audit_id": f"{row['dataset']}:{row.get('sample_id')}",
                "dataset": row["dataset"],
                "routine_id": str(row.get("sample_id")),
                "routine_name": str(row.get("ifttt_routine_name")),
                "source": row["source"],
                "latency_group": latency_group(row.get("ground_truth_latency_s")),
                "protocol_modality": protocol_modality(row),
                "ble_count": int(num(row.get("ble_device_count"))),
                "local_count": int(num(row.get("local_lan_gateway_media_device_count"))),
                "cloud_count": int(num(row.get("cloud_account_api_device_count"))),
                "total_device_count": int(num(row.get("total_device_count"))),
                "gt_latency_s": row.get("ground_truth_latency_s"),
                "coarse_latency_s": row.get("coarse_schedule_latency_s"),
                "micro_latency_s": row.get("micro_level_schedule_latency_s"),
                "validator_pass": int(pass_rate),
                "rollback_layer_count": row.get("rollback_layer_count"),
                "selected_reason": selected_reason(row),
            }
        )
    return manifest


def provider_from_name(name: str, modality: str) -> str:
    lower = name.lower()
    for token in (
        "blink",
        "roborock",
        "home_connect",
        "ecobee",
        "netatmo",
        "smartthings",
        "switchbot",
        "hue",
        "nanoleaf",
        "kasa",
        "tplink",
    ):
        if token.replace("_", " ") in lower or token in lower:
            return token
    if modality == "BLE":
        return "ble_device"
    if modality == "Cloud":
        return "cloud_device"
    return "local_device"


def expected_value(name: str, field: str) -> Any:
    lower = name.lower()
    if "turn off" in lower or "disarm" in lower:
        return "off" if field in {"power", "state"} else "disarmed"
    if "arm" in lower:
        return "armed"
    if "open" in lower:
        return "open" if field != "position" else 100
    if "roborock" in lower and ("home" in lower or "dock" in lower):
        return "docked"
    if "sabbath" in lower or "super cooling" in lower:
        return "enabled"
    if field in {"brightness", "volume"}:
        return 50
    if field in {"position"}:
        return 0
    if field in {"mode", "setpoint", "fan_mode"}:
        return "default"
    return "on"


def oracle_spec(row: dict[str, Any]) -> dict[str, Any]:
    rid = row["routine_id"]
    name = row["routine_name"]
    modalities = row["protocol_modality"].split("+") if row["protocol_modality"] != "None" else []

    device_fields = []
    platform_fields = []
    required_events = []
    lifecycle_events = []

    for modality in modalities:
        provider = provider_from_name(name, modality)
        device = f"{provider}.{rid}.{modality.lower()}"
        field = "state"
        if "curtain" in name.lower() or "cover" in name.lower() or "switchbot" in name.lower():
            field = "position"
        elif "temperature" in name.lower() or "ecobee" in name.lower():
            field = "mode"
        elif "light" in name.lower() or "hue" in name.lower() or "nanoleaf" in name.lower():
            field = "power"
        device_fields.append(
            {
                "device": device,
                "source": "vendor_or_device_api",
                "fields": [field],
            }
        )
        platform_fields.append(
            {
                "entity": f"{modality.lower()}.{provider}_{rid}",
                "source": "home_assistant_state",
                "fields": ["state"],
            }
        )
        required_events.append(
            {
                "name": f"{modality.lower()}_command",
                "normalized_key": f"device_command:{provider}:{modality.lower()}",
            }
        )
        if modality == "BLE":
            lifecycle_events += [
                {"normalized_key": f"ble_connect:{provider}"},
                {"normalized_key": f"ble_disconnect:{provider}"},
            ]
        if modality == "Cloud":
            lifecycle_events.append({"normalized_key": f"cloud_session:{provider}"})

    platform_fields.append(
        {
            "entity": f"sensor.routine_summary_{rid}",
            "source": "home_assistant_state",
            "fields": ["state"],
        }
    )
    required_events.append(
        {
            "name": "summary_writeback",
            "normalized_key": f"state_write:ha:routine_summary:{rid}",
        }
    )

    return {
        "audit_id": row["audit_id"],
        "routine_id": rid,
        "routine_name": name,
        "oracle_mode": "simulated",
        "initial_state": {
            field["device"]: {field["fields"][0]: "default"} for field in device_fields
        },
        "device_side_fields": device_fields,
        "platform_side_fields": platform_fields,
        "required_events": required_events,
        "lifecycle_events": lifecycle_events,
        "comparison_rules": {
            "ignore_fields": ["timestamp", "request_id", "uuid", "nonce"],
            "numeric_tolerance": {"brightness": 1, "position": 2, "temperature": 0.1},
        },
    }


def execution_record(row: dict[str, Any], spec: dict[str, Any], run_id: int, variant: str) -> dict[str, Any]:
    order = "baseline_first" if run_id % 2 else "optimized_first"
    name = row["routine_name"]
    device_snapshot = {}
    for item in spec["device_side_fields"]:
        field = item["fields"][0]
        device_snapshot[item["device"]] = {field: expected_value(name, field)}
    platform_snapshot = {
        item["entity"]: {field: "done" for field in item["fields"]}
        for item in spec["platform_side_fields"]
    }
    required_counts = {event["normalized_key"]: 1 for event in spec["required_events"]}
    lifecycle_counts = {event["normalized_key"]: 1 for event in spec["lifecycle_events"]}
    return {
        "dataset": row["dataset"],
        "routine_id": row["routine_id"],
        "routine_name": name,
        "run_id": run_id,
        "variant": variant,
        "oracle_mode": "simulated",
        "execution_order": order,
        "initial_state_match": True,
        "reset_attempts": 1,
        "scenario_input_hash": hashlib.sha1(f"{row['audit_id']}:{run_id}".encode()).hexdigest()[:12],
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "device_side_snapshot": device_snapshot,
        "platform_side_snapshot": platform_snapshot,
        "required_event_counts": required_counts,
        "lifecycle_event_counts": lifecycle_counts,
        "exception_category": None,
        "oracle_source_counts": {
            "vendor_device_api_fields": sum(len(item["fields"]) for item in spec["device_side_fields"]),
            "home_assistant_state_fields": sum(len(item["fields"]) for item in spec["platform_side_fields"]),
        },
        "oracle_read_status": "ok",
    }


def count_fields(snapshot: dict[str, dict[str, Any]]) -> int:
    return sum(len(fields) for fields in snapshot.values())


def matched_fields(left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]) -> int:
    matched = 0
    for device, fields in left.items():
        for field, value in fields.items():
            if right.get(device, {}).get(field) == value:
                matched += 1
    return matched


def matched_counts(left: dict[str, int], right: dict[str, int]) -> int:
    keys = sorted(set(left) | set(right))
    return sum(1 for key in keys if left.get(key, 0) == right.get(key, 0))


def pair_comparison(row: dict[str, Any], run_id: int, baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    dev_total = count_fields(baseline["device_side_snapshot"])
    dev_matched = matched_fields(baseline["device_side_snapshot"], optimized["device_side_snapshot"])
    plat_total = count_fields(baseline["platform_side_snapshot"])
    plat_matched = matched_fields(baseline["platform_side_snapshot"], optimized["platform_side_snapshot"])
    req_total = len(set(baseline["required_event_counts"]) | set(optimized["required_event_counts"]))
    req_matched = matched_counts(baseline["required_event_counts"], optimized["required_event_counts"])
    life_total = len(set(baseline["lifecycle_event_counts"]) | set(optimized["lifecycle_event_counts"]))
    life_matched = matched_counts(baseline["lifecycle_event_counts"], optimized["lifecycle_event_counts"])
    exception_match = baseline["exception_category"] == optimized["exception_category"]
    routine_match = dev_matched == dev_total and plat_matched == plat_total
    event_match = req_matched == req_total
    lifecycle_match = life_matched == life_total
    pass_all = routine_match and event_match and lifecycle_match and exception_match
    timing_only = bool(num(row.get("micro_latency_s")) and num(row.get("micro_latency_s")) != num(row.get("gt_latency_s")))
    return {
        "dataset": row["dataset"],
        "routine_id": row["routine_id"],
        "run_id": run_id,
        "baseline_execution_id": f"{row['audit_id']}:run{run_id}:baseline",
        "optimized_execution_id": f"{row['audit_id']}:run{run_id}:optimized",
        "device_side_field_total": dev_total,
        "device_side_field_matched": dev_matched,
        "platform_side_field_total": plat_total,
        "platform_side_field_matched": plat_matched,
        "routine_level_state_match": int(routine_match),
        "required_event_total": req_total,
        "required_event_matched": req_matched,
        "intermediate_event_match": int(event_match),
        "exception_match": int(exception_match),
        "resource_lifecycle_total": life_total,
        "resource_lifecycle_matched": life_matched,
        "resource_lifecycle_match": int(lifecycle_match),
        "timing_only_difference": int(timing_only and pass_all),
        "independent_oracle_pass": int(pass_all),
        "invalid_run": 0,
        "invalid_reason": "",
        "mismatch_type": "" if pass_all else "semantic_mismatch",
        "mismatch_detail": "",
    }


def rate(numer: float, denom: float) -> float:
    return round((100.0 * numer / denom) if denom else 100.0, 2)


def summarize(manifest: list[dict[str, Any]], pairs: list[dict[str, Any]], executions: list[dict[str, Any]]) -> dict[str, Any]:
    by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pairs:
        by_dataset[row["dataset"]].append(row)
    exec_by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in executions:
        exec_by_dataset[row["dataset"]].append(row)

    datasets = {}
    for dataset, rows in sorted(by_dataset.items()):
        routines = {row["routine_id"] for row in rows}
        dev_total = sum(int(row["device_side_field_total"]) for row in rows)
        dev_match = sum(int(row["device_side_field_matched"]) for row in rows)
        plat_total = sum(int(row["platform_side_field_total"]) for row in rows)
        plat_match = sum(int(row["platform_side_field_matched"]) for row in rows)
        req_total = sum(int(row["required_event_total"]) for row in rows)
        req_match = sum(int(row["required_event_matched"]) for row in rows)
        life_total = sum(int(row["resource_lifecycle_total"]) for row in rows)
        life_match = sum(int(row["resource_lifecycle_matched"]) for row in rows)
        vendor_fields = sum(int(row["oracle_source_counts"]["vendor_device_api_fields"]) for row in exec_by_dataset[dataset])
        ha_fields = sum(int(row["oracle_source_counts"]["home_assistant_state_fields"]) for row in exec_by_dataset[dataset])
        datasets[dataset] = {
            "routines": len(routines),
            "paired_runs": len(rows),
            "device_side_state_match_pct": rate(dev_match, dev_total),
            "platform_side_state_match_pct": rate(plat_match, plat_total),
            "routine_level_state_match_pct": rate(sum(int(r["routine_level_state_match"]) for r in rows), len(rows)),
            "required_event_match_pct": rate(req_match, req_total),
            "exception_match_pct": rate(sum(int(r["exception_match"]) for r in rows), len(rows)),
            "resource_lifecycle_match_pct": rate(life_match, life_total),
            "timing_only_difference_pct": rate(sum(int(r["timing_only_difference"]) for r in rows), len(rows)),
            "validator_accepted_executions": len(rows),
            "independent_oracle_passed": sum(int(r["independent_oracle_pass"]) for r in rows),
            "agreement_pct": rate(sum(int(r["independent_oracle_pass"]) for r in rows), len(rows)),
            "vendor_device_api_fields": vendor_fields,
            "home_assistant_state_fields": ha_fields,
            "vendor_device_api_coverage_pct": rate(vendor_fields, vendor_fields + ha_fields),
        }
    overall_pairs = len(pairs)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "oracle_mode": "simulated",
        "note": "Simulated mode validates the audit pipeline and file formats; it is not a real-device result.",
        "routines": len(manifest),
        "paired_runs": overall_pairs,
        "datasets": datasets,
        "overall_agreement_pct": rate(sum(int(r["independent_oracle_pass"]) for r in pairs), overall_pairs),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Independent Device-State Audit",
        "",
        f"- Oracle mode: `{summary['oracle_mode']}`",
        f"- Note: {summary['note']}",
        f"- Routines: {summary['routines']}",
        f"- Paired runs: {summary['paired_runs']}",
        f"- Overall agreement: {summary['overall_agreement_pct']}%",
        "",
        "| Dataset | Routines | Paired Runs | Device State | Platform State | Routine Match | Event Match | Exception | Lifecycle | Timing-only | Agreement | Vendor API Coverage |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset, row in summary["datasets"].items():
        lines.append(
            f"| {dataset} | {row['routines']} | {row['paired_runs']} | "
            f"{row['device_side_state_match_pct']}% | {row['platform_side_state_match_pct']}% | "
            f"{row['routine_level_state_match_pct']}% | {row['required_event_match_pct']}% | "
            f"{row['exception_match_pct']}% | {row['resource_lifecycle_match_pct']}% | "
            f"{row['timing_only_difference_pct']}% | {row['agreement_pct']}% | "
            f"{row['vendor_device_api_coverage_pct']}% |"
        )
    path.write_text("\n".join(lines) + "\n")


def write_readme(path: Path) -> None:
    path.write_text(
        "# Independent Device-State Audit Files\n\n"
        "This directory records the local audit run for FloWeaver's independent device-state experiment.\n\n"
        "## Scope\n\n"
        "- Smart-home dataset: 20 validator-accepted routines, including 17 IFTTT-derived rows and 3 vdev mixed routines.\n"
        "- Long-chain dataset: 10 validator-accepted routines from the long-chain sheet.\n"
        "- Repeated runs: configured by `--runs`; the default local run uses 5 paired baseline/optimized executions per routine.\n"
        "- Oracle mode: `simulated`. This validates the audit pipeline and file formats only; replace the execution adapter with real vendor/device queries before reporting real-device results.\n\n"
        "## Reset and Audit Model\n\n"
        "Each paired run records reset verification, baseline execution, optimized execution, device-side snapshots, platform-side snapshots, required events, lifecycle events, exception category, and pairwise comparison results. Timing/order changes are treated as descriptive differences, not failures, when final states and required observables match.\n\n"
        "## Files\n\n"
        "- `experiment_config.json`: reproducible run configuration and selected sample IDs.\n"
        "- `sampling_manifest.csv`: selected routines, groups, modalities, validator/rollback metadata, and selection reasons.\n"
        "- `oracle_specs.json`: per-routine oracle fields, required events, lifecycle events, and comparison rules.\n"
        "- `execution_audit.jsonl`: one record per baseline or optimized execution.\n"
        "- `pair_comparison.csv`: one record per paired baseline/optimized run.\n"
        "- `summary.json`: machine-readable aggregate metrics.\n"
        "- `SUMMARY.md`: paper-facing aggregate summary table.\n"
    )


def run(args: argparse.Namespace) -> None:
    sheets = parse_xlsx(Path(args.input_xlsx))
    manifest = build_sampling_manifest(sheets)
    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.clean:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    specs = {row["audit_id"]: oracle_spec(row) for row in manifest}
    executions: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []

    for row in manifest:
        spec = specs[row["audit_id"]]
        for run_id in range(1, int(args.runs) + 1):
            baseline = execution_record(row, spec, run_id, "baseline")
            optimized = execution_record(row, spec, run_id, "optimized")
            executions.extend([baseline, optimized])
            pairs.append(pair_comparison(row, run_id, baseline, optimized))

    summary = summarize(manifest, pairs, executions)
    config = {
        "created_at": summary["created_at"],
        "input_xlsx": str(Path(args.input_xlsx)),
        "runs_per_routine": int(args.runs),
        "oracle_mode": "simulated",
        "smart_sheet": SMART_SHEET,
        "long_chain_sheet": LONG_SHEET,
        "smart_ifttt_ids": SMART_IFTTT_IDS,
        "smart_vdev_ids": SMART_VDEV_IDS,
        "long_chain_ids": LONG_IDS,
        "reset_policy": "reset, verify initial state, run baseline/optimized pair, compare independent observables",
    }

    (out_dir / "experiment_config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    write_csv(out_dir / "sampling_manifest.csv", manifest)
    (out_dir / "oracle_specs.json").write_text(json.dumps(specs, indent=2, sort_keys=True) + "\n")
    write_jsonl(out_dir / "execution_audit.jsonl", executions)
    write_csv(out_dir / "pair_comparison.csv", pairs)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_summary_md(out_dir / "SUMMARY.md", summary)
    write_readme(out_dir / "README.md")

    print(f"Wrote audit files to {out_dir}")
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Independent Device-State Audit locally.")
    parser.add_argument("--input-xlsx", default=str(DEFAULT_XLSX))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--clean", action="store_true", help="Remove the output directory before writing.")
    args = parser.parse_args(argv)
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    run(args)


if __name__ == "__main__":
    main()
