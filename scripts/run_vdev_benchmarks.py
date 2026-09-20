from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from itertools import combinations
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, Iterable, List
import uuid

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from optimizer.pipeline import FloWeaverOptimizer


SNAPSHOT_ROOT = REPO_ROOT / "data" / "repo_snapshot"
PROFILE_PATH = REPO_ROOT / "data" / "profiles" / "default" / "ha_profile.json"
TARGET_ROOT = REPO_ROOT / "data" / "targets" / "vdev_benchmarks"
RUN_ROOT = REPO_ROOT / "data" / "optimizer_runs" / "vdev_benchmarks"
CACHE_ROOT = RUN_ROOT / "_llm_detector_cache"
README_PATH = TARGET_ROOT / "README.md"
LATEST_RUN_REPORT_PATH = TARGET_ROOT / "LATEST_BENCHMARK_RUN.md"

BLE_STATUS_HINTS = ["BLE_OP", "BLE_GATT_OP"]
BLE_CONNECT_HINTS = ["BLE_CONNECT", "BLE_OP", "BLE_GATT_OP"]
BLE_SUBSCRIBE_HINTS = ["BLE_NOTIFY_SUBSCRIBE", "SUBSCRIBE", "BLE_OP", "BLE_GATT_OP"]
CLOUD_STATUS_HINTS = ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"]
CLOUD_CONTROL_HINTS = ["CLOUD_OP", "CLOUD_HTTP_CALL"]
LOCAL_API_HINTS = ["LOCAL_API_READ"]
MQTT_READ_HINTS = ["MQTT_SUBSCRIBE", "SUBSCRIBE"]

VALIDATION_TEMPLATE: Dict[str, Any] = {
    "differential_tests": {
        "enabled": True,
        "runs_per_scenario": 2,
        "scenarios": [
            "baseline_happy_path",
            "fault_cloud_429",
            "fault_ble_disconnect",
        ],
    },
    "fault_model": {
        "ble_disconnect": True,
        "cloud_429": True,
        "network_jitter": True,
    },
    "observation": {
        "canonicalization_version": "v1",
        "equivalence_whitelist": ["COALESCE_STATE_WRITE"],
        "semantic_ops": [
            "ENTRY_SETUP",
            "COORD_REFRESH",
            "STATE_WRITE",
            "SUBSCRIBE",
            "UNSUBSCRIBE",
            "MQTT_SUBSCRIBE",
            "BLE_CONNECT",
            "BLE_DISCONNECT",
            "BLE_NOTIFY_SUBSCRIBE",
            "BLE_OP",
            "BLE_GATT_OP",
            "CLOUD_STATUS_CALL",
            "CLOUD_HTTP_CALL",
            "CLOUD_429_CHECK",
            "CLOUD_BACKOFF_SLEEP",
            "CLOUD_BATCH_CALL",
            "CLOUD_SESSION_REUSE",
            "LOCAL_API_READ",
            "POLL_UPDATE",
        ],
    },
    "llm_detector": {
        "enabled": True,
        "timeout_s": int(os.environ.get("FLOWEAVER_BENCH_LLM_TIMEOUT_S") or 45),
        "max_attempts": 0,
        "retry_backoff_s": float(os.environ.get("FLOWEAVER_BENCH_LLM_RETRY_BACKOFF_S") or 0.5),
    },
    "profile_version": "ha_profile_default",
    "sampling": {},
}


def abs_repo(*parts: str) -> str:
    return str((SNAPSHOT_ROOT.joinpath(*parts)).resolve())


def repo_binding(
    *,
    target_id: str,
    file_rel: str,
    integration: str,
    protocols: List[str],
) -> Dict[str, Any]:
    return {
        "device_id": target_id,
        "file_path": abs_repo(*file_rel.split("/")),
        "integration": integration,
        "protocols": protocols,
    }


def ble_action(
    action_id: str,
    device_id: str,
    *,
    service: str,
    file_rel: str,
    integration: str,
    hints: List[str],
    domain: str,
    action_type: str | None = None,
    extra_data_template: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    data_template: Dict[str, Any] = {"device_id": device_id}
    if isinstance(extra_data_template, dict):
        data_template.update(extra_data_template)
    return {
        "action_id": action_id,
        "type": action_type or service,
        "protocol": "BLE",
        "critical": True,
        "marker_hints": hints,
        "must_happen_before": [],
        "side_effects": [],
        "target_kind": "ble_device",
        "target": {"id": device_id, "kind": "ble_device", "device_id": device_id},
        "exec": {
            "blocking": True,
            "kind": "ha_service_call",
            "domain": domain,
            "service": service,
            "data_template": data_template,
        },
        "_binding": repo_binding(
            target_id=device_id,
            file_rel=file_rel,
            integration=integration,
            protocols=["BLE", "HA"],
        ),
    }


def cloud_action(
    action_id: str,
    endpoint: str,
    *,
    service: str,
    file_rel: str,
    integration: str,
    domain: str,
    provider: str | None = None,
    idempotent: bool = True,
    endpoint_group_key: str | None = None,
    host_group_key: str | None = None,
    action_type: str | None = None,
    marker_hints: List[str] | None = None,
    extra_data_template: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    data_template: Dict[str, Any] = {"endpoint": endpoint}
    if endpoint_group_key:
        data_template["endpoint_group_key"] = endpoint_group_key
    if host_group_key:
        data_template["host_group_key"] = host_group_key
    if isinstance(extra_data_template, dict):
        data_template.update(extra_data_template)
    return {
        "action_id": action_id,
        "type": action_type or service,
        "protocol": "CLOUD",
        "critical": True,
        "idempotent": idempotent,
        "provider": provider or integration,
        "marker_hints": marker_hints or CLOUD_STATUS_HINTS,
        "must_happen_before": [],
        "side_effects": [],
        "target_kind": "cloud_endpoint",
        "target": {"id": endpoint, "kind": "cloud_endpoint", "endpoint": endpoint},
        "exec": {
            "blocking": True,
            "kind": "ha_service_call",
            "domain": domain,
            "service": service,
            "provider": provider or integration,
            "data_template": data_template,
        },
        "_binding": repo_binding(
            target_id=endpoint,
            file_rel=file_rel,
            integration=integration,
            protocols=["CLOUD", "HA"],
        ),
    }


def local_action(
    action_id: str,
    endpoint: str,
    *,
    service: str,
    file_rel: str,
    integration: str,
    domain: str,
    marker_hints: List[str],
    target_kind: str = "local_endpoint",
    provider: str | None = None,
    idempotent: bool = True,
    endpoint_group_key: str | None = None,
    host_group_key: str | None = None,
    action_type: str | None = None,
    extra_data_template: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    data_template: Dict[str, Any] = {"endpoint": endpoint}
    if endpoint_group_key:
        data_template["endpoint_group_key"] = endpoint_group_key
    if host_group_key:
        data_template["host_group_key"] = host_group_key
    if isinstance(extra_data_template, dict):
        data_template.update(extra_data_template)
    return {
        "action_id": action_id,
        "type": action_type or service,
        "protocol": "LOCAL",
        "critical": True,
        "idempotent": idempotent,
        "provider": provider or integration,
        "marker_hints": marker_hints,
        "must_happen_before": [],
        "side_effects": [],
        "target_kind": target_kind,
        "target": {"id": endpoint, "kind": target_kind, "endpoint": endpoint, "provider": provider or integration},
        "exec": {
            "blocking": True,
            "kind": "ha_service_call",
            "domain": domain,
            "service": service,
            "provider": provider or integration,
            "data_template": data_template,
        },
        "_binding": repo_binding(
            target_id=endpoint,
            file_rel=file_rel,
            integration=integration,
            protocols=["LOCAL", "HA"],
        ),
    }


def mqtt_action(
    action_id: str,
    topic_id: str,
    *,
    service: str,
    file_rel: str,
    integration: str = "mqtt",
    domain: str = "mqtt",
    extra_data_template: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    data_template: Dict[str, Any] = {"endpoint": topic_id}
    if isinstance(extra_data_template, dict):
        data_template.update(extra_data_template)
    return {
        "action_id": action_id,
        "type": service,
        "protocol": "LOCAL",
        "critical": True,
        "idempotent": True,
        "provider": integration,
        "marker_hints": MQTT_READ_HINTS,
        "must_happen_before": [],
        "side_effects": [],
        "target_kind": "mqtt_topic",
        "target": {"id": topic_id, "kind": "mqtt_topic", "endpoint": topic_id, "provider": integration},
        "exec": {
            "blocking": True,
            "kind": "ha_service_call",
            "domain": domain,
            "service": service,
            "provider": integration,
            "data_template": data_template,
        },
        "_binding": repo_binding(
            target_id=topic_id,
            file_rel=file_rel,
            integration=integration,
            protocols=["LOCAL", "HA"],
        ),
    }


def write_action(
    action_id: str,
    entity_id: str,
    *,
    file_rel: str,
    integration: str,
    domain: str = "sensor",
    service: str = "publish",
) -> Dict[str, Any]:
    return {
        "action_id": action_id,
        "type": "write",
        "protocol": "HA",
        "critical": True,
        "marker_hints": ["STATE_WRITE"],
        "must_happen_before": [],
        "side_effects": ["state_write"],
        "target_kind": "ha_entity",
        "target": {"entity_id": entity_id, "id": entity_id, "kind": "ha_entity"},
        "exec": {
            "blocking": True,
            "kind": "ha_service_call",
            "domain": domain,
            "service": service,
            "data_template": {"entity_id": entity_id},
        },
        "_binding": repo_binding(
            target_id=entity_id,
            file_rel=file_rel,
            integration=integration,
            protocols=["HA"],
        ),
    }


def ble_budget_pairs(action_ids: Iterable[str]) -> List[Dict[str, Any]]:
    return [
        {"before": left, "after": right, "reason": "shared_radio_or_transport_budget"}
        for left, right in combinations(list(action_ids), 2)
    ]


def action_dep(before: str, after: str, reason: str) -> Dict[str, Any]:
    return {"before": before, "after": after, "reason": reason}


def case_target(
    *,
    vdev_id: str,
    name: str,
    group: str,
    story: str,
    strengths: List[str],
    focus_areas: List[str],
    lanes: Dict[str, List[Dict[str, Any]]],
    writebacks: Dict[str, Dict[str, Any]],
    mixed_source_protocols: List[str],
    connect_before_subscribe: List[tuple[str, str]] | None = None,
    ble_soft_pairs: List[Dict[str, Any]] | None = None,
    objectives: Dict[str, Any] | None = None,
    extra_hard_dependencies: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    connect_before_subscribe = connect_before_subscribe or []
    ble_soft_pairs = ble_soft_pairs or []
    extra_hard_dependencies = extra_hard_dependencies or []
    actions: List[Dict[str, Any]] = []
    source_actions: List[Dict[str, Any]] = []
    file_bindings: List[Dict[str, Any]] = []

    for lane_actions in lanes.values():
        for action in lane_actions:
            binding = action.pop("_binding")
            actions.append(action)
            source_actions.append(action)
            file_bindings.append(binding)

    for action in writebacks.values():
        binding = action.pop("_binding")
        actions.append(action)
        file_bindings.append(binding)

    domains = sorted({binding["integration"] for binding in file_bindings})
    files = sorted({binding["file_path"] for binding in file_bindings})
    protocols = sorted({"HA", *mixed_source_protocols})

    ble_ids = [str(action["target"]["device_id"]) for action in source_actions if str(action.get("protocol", "")).upper() == "BLE"]
    cloud_endpoints = [str(action["target"]["endpoint"]) for action in source_actions if str(action.get("protocol", "")).upper() == "CLOUD"]
    entities = [str(action["target"]["entity_id"]) for action in actions if str(action.get("protocol", "")).upper() == "HA"]
    anchor_ops = sorted(
        {
            hint
            for action in actions
            for hint in action.get("marker_hints", [])
            if str(hint).strip()
        }
    )

    service_name = f"run_{vdev_id.removeprefix('vdev_')}"
    hard_dependencies: List[Dict[str, Any]] = []
    for before, after in connect_before_subscribe:
        hard_dependencies.append(
            {
                "before": before,
                "after": after,
                "reason": "transport_connect_before_subscription",
            }
        )

    for lane_name, lane_publish in writebacks.items():
        if lane_name == "overall":
            continue
        publish_id = str(lane_publish["action_id"])
        for action in lanes.get(lane_name, []):
            hard_dependencies.append(
                {
                    "before": str(action["action_id"]),
                    "after": publish_id,
                    "reason": f"{lane_name}_write_depends_on_{str(action['action_id']).lower()}",
                }
            )

    overall = writebacks.get("overall")
    if overall:
        overall_id = str(overall["action_id"])
        for lane_name, lane_publish in writebacks.items():
            if lane_name == "overall":
                continue
            hard_dependencies.append(
                {
                    "before": str(lane_publish["action_id"]),
                    "after": overall_id,
                    "reason": f"overall_write_depends_on_{lane_name}_lane",
                }
            )
    hard_dependencies.extend(copy.deepcopy(extra_hard_dependencies))

    target = {
        "meta": {
            "spec_version": "0.1",
            "vdev_id": vdev_id,
            "name": name,
            "benchmark": {
                "group": group,
                "story": story,
                "strengths": strengths,
                "focus_areas": focus_areas,
            },
        },
        "source_scope": {
            "repo_path": str(SNAPSHOT_ROOT.resolve()),
            "commit": "HEAD",
            "domains": domains,
            "platforms": sorted({str(action["exec"]["domain"]) for action in actions if action.get("exec")}),
            "protocols": protocols,
            "files": files,
            "file_bindings": file_bindings,
            "entrypoints": [{"kind": "ha_service", "service": {"domain": "floweaver", "name": service_name}}],
        },
        "vdev_actions": actions,
        "target_anchors": {
            "device_ids": ble_ids,
            "endpoints": cloud_endpoints,
            "entities": entities,
            "characteristics": [],
            "required_state_writes": entities,
            "service_entrypoints": [f"floweaver.{service_name}"],
            "anchor_ops": anchor_ops,
        },
        "entrypoint": {"kind": "ha_service", "service": {"domain": "floweaver", "name": service_name}},
        "objectives": objectives
        or {
            "primary": "minimize_tail_latency_under_mixed_transport",
            "metrics": {
                "e2e_latency_ms": {"p95": 2200},
                "lane_completion_ms": {
                    "ble_lane_p95": 900,
                    "cloud_lane_p95": 1400,
                    "local_lane_p95": 600,
                },
            },
        },
        "constraints": {
            "source_protocols": protocols,
            "optimization_knobs": {
                "allow_concurrency": True,
                "max_concurrency": {"ble": 1, "cloud": 4, "local": 6, "total": 10},
            },
        },
        "validation": {**VALIDATION_TEMPLATE, "source_protocols": protocols},
        "hard_dependencies": hard_dependencies,
        "soft_dependencies": ble_soft_pairs,
        "critical_action_ids": [str(action["action_id"]) for action in actions],
    }
    return target


def build_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    morning_group = "Morning and Leaving Home Routines"
    comfort_group = "Coming Home and Evening Comfort Routines"
    monitoring_group = "Night and Energy Monitoring Routines"
    control_group = "Scene Activation and Comfort Control Routines"
    stress_group = "Household Stress and Abnormality Routines"

    cases.append(
        case_target(
            vdev_id="vdev_morning_wakeup_readiness_01",
            name="Morning Wake-Up Readiness Routine",
            group=morning_group,
            story="Before residents wake up, the system collects bedroom and hallway readiness signals to decide whether the home is already in a comfortable morning state.",
            strengths=[
                "Three real lanes: BLE, cloud, and local Hue bridge reads.",
                "Contains BLE connect plus subscribe, not only status reads.",
                "Final aggregation is naturally lane-first, then overall.",
            ],
            focus_areas=[
                "BLE connect-before-subscribe",
                "BLE curtain refresh vs sensor/status gap control",
                "Cloud status batching",
                "Local API lane should stay cheap and independent",
                "Overall writeback should depend on lane-level publishes only",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_bedroom_left", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A2", "ble:switchbot:curtain_bedroom_right", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A3", "ble:xiaomi_ble:bedside_lamp_left", service="read_status", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_status"),
                    ble_action("A4", "ble:xiaomi_ble:bedside_lamp_right", service="read_status", file_rel="xiaomi_ble/device.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="device", action_type="read_status"),
                    ble_action("A5", "ble:xiaomi_ble:temp_humidity_sensor_bedroom", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A6", "ble:esphome:air_node_bedroom", service="connect", file_rel="esphome/__init__.py", integration="esphome", hints=BLE_CONNECT_HINTS, domain="esphome", action_type="connect"),
                    ble_action("A7", "ble:esphome:relay_node_bedroom", service="subscribe", file_rel="esphome/manager.py", integration="esphome", hints=BLE_SUBSCRIBE_HINTS, domain="manager", action_type="subscribe"),
                ],
                "cloud": [
                    cloud_action("A8", "tuya:climate.master_bedroom.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="morning_climate", host_group_key="tuya", action_type="status"),
                    cloud_action("A9", "tuya:light.hallway.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="morning_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A10", "tuya:light.living_room.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="morning_lights", host_group_key="tuya", action_type="status"),
                ],
                "local": [
                    local_action("A11", "hue:bridge_1:bedroom_ceiling_group", service="get_state", file_rel="hue/v2/light.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A12", "hue:bridge_1:hallway_motion_sensor", service="get_state", file_rel="hue/v2/sensor.py", integration="hue", domain="sensor", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                ],
            },
            writebacks={
                "ble": write_action("A13", "sensor.vdev_morning_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A14", "sensor.vdev_morning_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A15", "sensor.vdev_morning_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A16", "sensor.vdev_morning_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            connect_before_subscribe=[("A6", "A7")],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6", "A7"]),
            objectives={
                "primary": "minimize_morning_readiness_latency",
                "metrics": {"e2e_latency_ms": {"p95": 2200}, "lane_completion_ms": {"ble_lane_p95": 950, "cloud_lane_p95": 900, "local_lane_p95": 550}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_leaving_home_safety_check_01",
            name="Leaving Home Safety Check Routine",
            group=morning_group,
            story="Before residents leave, the routine checks curtains, key lights, energy strips, climate, and entry sensors, then writes one leave-home safety summary.",
            strengths=[
                "Realistic safety checklist rather than an abstract transport test.",
                "Heavy Tuya status burst plus a smaller BLE sweep and local confirmation.",
                "Natural whole-home overall summary target.",
            ],
            focus_areas=[
                "Cloud burst batching",
                "BLE refresh and read ordering",
                "Local API should not be slowed by cloud or BLE noise",
                "Overall writeback should preserve a short hard-edge backbone",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_living_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A2", "ble:switchbot:curtain_study", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A3", "ble:xiaomi_ble:door_sensor_entry", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A4", "ble:xiaomi_ble:window_sensor_bedroom", service="read_sensor", file_rel="xiaomi_ble/event.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="event", action_type="read_sensor"),
                    ble_action("A5", "ble:xiaomi_ble:bedside_lamp_bedroom", service="read_status", file_rel="xiaomi_ble/device.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="device", action_type="read_status"),
                ],
                "cloud": [
                    cloud_action("A6", "tuya:light.living_room_1.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="leave_home_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A7", "tuya:light.living_room_2.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="leave_home_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A8", "tuya:climate.master_bedroom.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="leave_home_hvac", host_group_key="tuya", action_type="status"),
                    cloud_action("A9", "tuya:switch.energy_strip_tv.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="leave_home_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A10", "tuya:switch.energy_strip_desk.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="leave_home_energy", host_group_key="tuya", action_type="status"),
                ],
                "local": [
                    local_action("A11", "tplink:plug.coffee_machine", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="tplink_plugs", host_group_key="tplink_local", action_type="get_state"),
                    local_action("A12", "hue:bridge_1:dining_room_group", service="get_state", file_rel="hue/v2/light.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                ],
            },
            writebacks={
                "ble": write_action("A13", "sensor.vdev_leave_home_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A14", "sensor.vdev_leave_home_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A15", "sensor.vdev_leave_home_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A16", "sensor.vdev_leave_home_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5"]),
            objectives={
                "primary": "minimize_leave_home_check_latency",
                "metrics": {"e2e_latency_ms": {"p95": 2100}, "lane_completion_ms": {"ble_lane_p95": 820, "cloud_lane_p95": 1100, "local_lane_p95": 500}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_arrival_comfort_preparation_01",
            name="Coming Home Comfort Preparation Routine",
            group=comfort_group,
            story="Before arrival, the routine prepares a comfort snapshot by combining BLE sensors and curtains, cloud HVAC and lights, a Hue bridge read, and one MQTT air-quality read.",
            strengths=[
                "Natural arrival routine with cross-transport coordination.",
                "BLE and cloud both contain meaningful work, not padding.",
                "MQTT introduces a cheap local monitoring source inside a mixed case.",
            ],
            focus_areas=[
                "BLE connect-before-subscribe",
                "BLE refresh vs sensor reads",
                "Cloud batching across status calls",
                "MQTT and Hue local reads should remain cheap",
                "Lane-level publish and overall aggregation order",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:xiaomi_ble:motion_sensor_entry", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A2", "ble:xiaomi_ble:temp_sensor_living_room", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A3", "ble:switchbot:curtain_living_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A4", "ble:switchbot:curtain_dining_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A5", "ble:esphome:air_node_living_room", service="connect", file_rel="esphome/__init__.py", integration="esphome", hints=BLE_CONNECT_HINTS, domain="esphome", action_type="connect"),
                    ble_action("A6", "ble:esphome:relay_node_living_room", service="subscribe", file_rel="esphome/manager.py", integration="esphome", hints=BLE_SUBSCRIBE_HINTS, domain="manager", action_type="subscribe"),
                ],
                "cloud": [
                    cloud_action("A7", "tuya:light.hallway.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="arrival_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A8", "tuya:light.living_room.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="arrival_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A9", "tuya:climate.living_room.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="arrival_hvac", host_group_key="tuya", action_type="status"),
                    cloud_action("A10", "ecobee:thermostat.home_1", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="arrival_ecobee", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
                "local": [
                    local_action("A11", "hue:bridge_1:living_room_group", service="get_state", file_rel="hue/v2/light.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                    mqtt_action("A12", "mqtt:air_quality_node_living_room", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A13", "sensor.vdev_arrival_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A14", "sensor.vdev_arrival_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A15", "sensor.vdev_arrival_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A16", "sensor.vdev_arrival_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            connect_before_subscribe=[("A5", "A6")],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6"]),
            objectives={
                "primary": "prepare_arrival_comfort_snapshot_quickly",
                "metrics": {"e2e_latency_ms": {"p95": 2300}, "lane_completion_ms": {"ble_lane_p95": 900, "cloud_lane_p95": 1200, "local_lane_p95": 500}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_dinner_home_mode_01",
            name="Dinner Time Home Mode Routine",
            group=comfort_group,
            story="Before dinner, the routine checks dining, kitchen, and living-room readiness across curtains, lights, HVAC, and energy sensors to decide whether the home is ready for dinner mode.",
            strengths=[
                "Heavy multi-light cloud lane plus local API and MQTT reads.",
                "BLE lane remains meaningful with both curtain and sensor state.",
                "Very natural room-based evening routine.",
            ],
            focus_areas=[
                "Cloud multi-light batching",
                "Local API plus MQTT should remain a cheap lane",
                "BLE curtain refresh ordering",
                "Short lane publish to overall publish hard-edge chain",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_dining_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A2", "ble:switchbot:curtain_living_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A3", "ble:xiaomi_ble:temp_sensor_dining_room", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A4", "ble:xiaomi_ble:motion_sensor_kitchen_entry", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A5", "tuya:light.dining_room_main.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="dinner_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A6", "tuya:light.kitchen_ceiling.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="dinner_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A7", "tuya:light.living_room_corner.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="dinner_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A8", "tuya:climate.dining_room.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="dinner_hvac", host_group_key="tuya", action_type="status"),
                    cloud_action("A9", "tuya:switch.energy_strip_kitchen.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="dinner_energy", host_group_key="tuya", action_type="status"),
                ],
                "local": [
                    local_action("A10", "hue:bridge_1:dining_room_group", service="get_state", file_rel="hue/v2/light.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A11", "tplink:plug.rice_cooker", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="tplink_kitchen", host_group_key="tplink_local", action_type="get_state"),
                    mqtt_action("A12", "mqtt:power_meter_kitchen", service="read_last_message", file_rel="mqtt/sensor.py"),
                ],
            },
            writebacks={
                "ble": write_action("A13", "sensor.vdev_dinner_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A14", "sensor.vdev_dinner_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A15", "sensor.vdev_dinner_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A16", "sensor.vdev_dinner_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4"]),
            objectives={
                "primary": "prepare_dinner_mode_snapshot_with_low_tail_latency",
                "metrics": {"e2e_latency_ms": {"p95": 2200}, "lane_completion_ms": {"ble_lane_p95": 800, "cloud_lane_p95": 1150, "local_lane_p95": 480}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_night_shutdown_01",
            name="Night Shutdown Routine",
            group=monitoring_group,
            story="Before sleep, the routine confirms curtains, bedside lights, selected energy plugs, climate, and safety sensors, then writes a night shutdown summary.",
            strengths=[
                "Dense but realistic night routine with enough BLE and cloud work.",
                "Strong overall writeback semantics from three lanes.",
                "Energy and climate both present, not only lighting.",
            ],
            focus_areas=[
                "Large mixed BLE and cloud status collection",
                "Cloud grouping across lights and plugs",
                "Local cheap checks should stay separate",
                "Final overall summary should remain short and explainable",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_bedroom_left", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A2", "ble:switchbot:curtain_bedroom_right", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A3", "ble:xiaomi_ble:bedside_lamp_left", service="read_status", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_status"),
                    ble_action("A4", "ble:xiaomi_ble:bedside_lamp_right", service="read_status", file_rel="xiaomi_ble/device.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="device", action_type="read_status"),
                    ble_action("A5", "ble:xiaomi_ble:window_sensor_bedroom", service="read_sensor", file_rel="xiaomi_ble/event.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="event", action_type="read_sensor"),
                    ble_action("A6", "ble:xiaomi_ble:door_sensor_balcony", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A7", "tuya:light.hallway.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="night_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A8", "tuya:light.living_room.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="night_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A9", "tuya:switch.energy_strip_tv.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="night_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A10", "tuya:switch.energy_strip_desk.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="night_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A11", "tuya:climate.bedroom.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="night_hvac", host_group_key="tuya", action_type="status"),
                ],
                "local": [
                    local_action("A12", "tplink:plug.bedside_heater", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="night_tplink", host_group_key="tplink_local", action_type="get_state"),
                    local_action("A13", "hue:bridge_1:hallway_group", service="get_state", file_rel="hue/v2/light.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                ],
            },
            writebacks={
                "ble": write_action("A14", "sensor.vdev_night_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A15", "sensor.vdev_night_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A16", "sensor.vdev_night_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A17", "sensor.vdev_night_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6"]),
            objectives={
                "primary": "confirm_night_shutdown_state_with_low_tail_latency",
                "metrics": {"e2e_latency_ms": {"p95": 2300}, "lane_completion_ms": {"ble_lane_p95": 900, "cloud_lane_p95": 1200, "local_lane_p95": 500}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_overnight_health_safety_monitoring_01",
            name="Overnight Health & Safety Monitoring Routine",
            group=monitoring_group,
            story="During the night, the routine snapshots temperature, door and window safety, air quality, power usage, and remote HVAC state into one overnight monitoring summary.",
            strengths=[
                "Monitoring-first routine, not control-heavy.",
                "Strong cloud burst plus cheap MQTT monitoring lane.",
                "Good benchmark for writeback-heavy aggregation with minimal actuation.",
            ],
            focus_areas=[
                "Burst cloud status scheduling",
                "BLE sensor sweep ordering",
                "MQTT lane should stay cheap",
                "Lane writeback and overall aggregation should remain compact",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:xiaomi_ble:temp_sensor_bedroom", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A2", "ble:xiaomi_ble:temp_sensor_baby_room", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A3", "ble:xiaomi_ble:door_sensor_entry", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A4", "ble:xiaomi_ble:window_sensor_study", service="read_sensor", file_rel="xiaomi_ble/event.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="event", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A5", "tuya:climate.bedroom.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="overnight_tuya_hvac", host_group_key="tuya", action_type="status"),
                    cloud_action("A6", "tuya:climate.baby_room.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="overnight_tuya_hvac", host_group_key="tuya", action_type="status"),
                    cloud_action("A7", "tuya:switch.energy_strip_server.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="overnight_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A8", "tuya:switch.energy_strip_bedroom.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="overnight_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A9", "ecobee:thermostat.home_1", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="overnight_ecobee", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                    cloud_action("A10", "ecobee:thermostat.home_2", service="read_runtime", file_rel="ecobee/sensor.py", integration="ecobee", domain="sensor", provider="ecobee", endpoint_group_key="overnight_ecobee", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
                "local": [
                    mqtt_action("A11", "mqtt:air_quality_node_bedroom", service="read_last_message", file_rel="mqtt/subscription.py"),
                    mqtt_action("A12", "mqtt:air_quality_node_baby_room", service="read_last_message", file_rel="mqtt/sensor.py"),
                ],
            },
            writebacks={
                "ble": write_action("A13", "sensor.vdev_overnight_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A14", "sensor.vdev_overnight_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A15", "sensor.vdev_overnight_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A16", "sensor.vdev_overnight_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4"]),
            objectives={
                "primary": "minimize_overnight_monitoring_tail_latency",
                "metrics": {"e2e_latency_ms": {"p95": 2100}, "lane_completion_ms": {"ble_lane_p95": 700, "cloud_lane_p95": 1200, "local_lane_p95": 450}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_weekend_whole_home_snapshot_01",
            name="Weekend Whole-Home Snapshot Routine",
            group=monitoring_group,
            story="During a weekend whole-home snapshot, the routine checks several curtains, rooms, sensors, climate endpoints, lights, plugs, and a few local monitoring sources to generate one house-wide summary.",
            strengths=[
                "Largest everyday mixed benchmark in the suite.",
                "Good single 'main benchmark' candidate because it is realistic and large.",
                "Exercises all three source lanes plus layered writeback.",
            ],
            focus_areas=[
                "BLE congestion with connect-plus-subscribe",
                "Cloud multi-room batching and grouping",
                "Cheap local lane parallelism",
                "Minimal overall aggregation chain under a large routine",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_living_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A2", "ble:switchbot:curtain_bedroom", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A3", "ble:switchbot:curtain_study", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A4", "ble:xiaomi_ble:temp_sensor_living_room", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A5", "ble:xiaomi_ble:temp_sensor_bedroom", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A6", "ble:xiaomi_ble:motion_sensor_hallway", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A7", "ble:esphome:air_node_1", service="connect", file_rel="esphome/__init__.py", integration="esphome", hints=BLE_CONNECT_HINTS, domain="esphome", action_type="connect"),
                    ble_action("A8", "ble:esphome:relay_node_1", service="subscribe", file_rel="esphome/manager.py", integration="esphome", hints=BLE_SUBSCRIBE_HINTS, domain="manager", action_type="subscribe"),
                ],
                "cloud": [
                    cloud_action("A9", "tuya:light.living_room_1.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="weekend_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A10", "tuya:light.living_room_2.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="weekend_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A11", "tuya:light.bedroom_1.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="weekend_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A12", "tuya:climate.living_room.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="weekend_hvac", host_group_key="tuya", action_type="status"),
                    cloud_action("A13", "tuya:climate.bedroom.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="weekend_hvac", host_group_key="tuya", action_type="status"),
                    cloud_action("A14", "tuya:switch.energy_strip_tv.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="weekend_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A15", "tuya:switch.energy_strip_study.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="weekend_energy", host_group_key="tuya", action_type="status"),
                ],
                "local": [
                    local_action("A16", "hue:bridge_1:living_room_group", service="get_state", file_rel="hue/v2/light.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A17", "hue:bridge_1:bedroom_group", service="get_state", file_rel="hue/v2/light.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A18", "tplink:plug.coffee_machine", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="weekend_tplink", host_group_key="tplink_local", action_type="get_state"),
                    mqtt_action("A19", "mqtt:power_meter_home_main", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A20", "sensor.vdev_weekend_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A21", "sensor.vdev_weekend_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A22", "sensor.vdev_weekend_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A23", "sensor.vdev_weekend_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            connect_before_subscribe=[("A7", "A8")],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]),
            objectives={
                "primary": "maximize_signal_density_per_unit_latency_for_whole_home_snapshot",
                "metrics": {"e2e_latency_ms": {"p95": 2800}, "lane_completion_ms": {"ble_lane_p95": 1200, "cloud_lane_p95": 1450, "local_lane_p95": 650}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_party_preparation_01",
            name="Party Preparation Routine",
            group=comfort_group,
            story="Before guests arrive, the routine checks party-scene lighting, curtains, climate, speaker power, TV power, and air quality to decide whether the home is ready for a party scene.",
            strengths=[
                "Strong multi-light cloud lane with real local scene-group reads.",
                "BLE lane still matters for curtains and entry state.",
                "Balanced case for cloud, local, and overall publish structure.",
            ],
            focus_areas=[
                "Cloud batching under a dense lighting routine",
                "Local scene and plug reads should remain cheap",
                "BLE curtain refresh should stay ordered but not over-serialized",
                "Final party-readiness summary should keep a short dependency chain",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_living_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A2", "ble:switchbot:curtain_dining_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A3", "ble:xiaomi_ble:motion_sensor_entry", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A4", "ble:xiaomi_ble:temp_sensor_living_room", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A5", "tuya:light.living_room_main.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="party_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A6", "tuya:light.dining_room_main.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="party_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A7", "tuya:light.hallway.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="party_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A8", "tuya:climate.living_room.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="party_hvac", host_group_key="tuya", action_type="status"),
                    cloud_action("A9", "tuya:switch.energy_strip_speaker.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="party_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A10", "tuya:switch.energy_strip_tv.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="party_energy", host_group_key="tuya", action_type="status"),
                ],
                "local": [
                    local_action("A11", "hue:bridge_1:party_scene_group", service="get_state", file_rel="hue/v2/light.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A12", "tplink:plug.coffee_machine", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="party_tplink", host_group_key="tplink_local", action_type="get_state"),
                    mqtt_action("A13", "mqtt:air_quality_node_living_room", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A14", "sensor.vdev_party_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A15", "sensor.vdev_party_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A16", "sensor.vdev_party_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A17", "sensor.vdev_party_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4"]),
            objectives={
                "primary": "prepare_party_mode_snapshot_with_visible_parallelism",
                "metrics": {"e2e_latency_ms": {"p95": 2400}, "lane_completion_ms": {"ble_lane_p95": 800, "cloud_lane_p95": 1300, "local_lane_p95": 500}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_party_scene_activation_01",
            name="Party Scene Activation Routine",
            group=control_group,
            story="Before guests arrive, the routine actively stages a party scene by repositioning curtains, setting multiple Tuya lights to party brightness and color temperature, adjusting comfort controls, then verifying key scene state before publishing summaries.",
            strengths=[
                "Control-heavy routine rather than a read-only snapshot.",
                "Large same-provider Tuya control wave followed by explicit verification reads.",
                "BLE curtain movement, cloud scene activation, and local readback all coexist in one realistic pre-party flow.",
            ],
            focus_areas=[
                "BLE physical-action serialization for multiple curtain moves",
                "Cloud control batching for same-provider light and climate commands",
                "Control-to-verify ordering inside the cloud lane",
                "Local readback should stay cheap while not overtaking scene activation",
                "Lane summaries should still collapse to a short overall writeback tail",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_living_room_left", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 30}),
                    ble_action("A2", "ble:switchbot:curtain_living_room_right", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 30}),
                    ble_action("A3", "ble:switchbot:curtain_dining_room", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 45}),
                    ble_action("A4", "ble:switchbot:roller_shade_balcony", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 60}),
                    ble_action("A5", "ble:xiaomi_ble:motion_sensor_entry", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A6", "ble:xiaomi_ble:temp_sensor_dining_room", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A7", "tuya:light.living_room_main.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="party_scene_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 200, "color_temp_kelvin": 3000}),
                    cloud_action("A8", "tuya:light.dining_room_main.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="party_scene_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 190, "color_temp_kelvin": 3100}),
                    cloud_action("A9", "tuya:light.hallway.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="party_scene_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 140, "color_temp_kelvin": 3300}),
                    cloud_action("A10", "tuya:light.kitchen_ceiling.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="party_scene_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 155, "color_temp_kelvin": 3400}),
                    cloud_action("A11", "tuya:climate.living_room.set_temperature", service="set_temperature", file_rel="tuya/climate.py", integration="tuya", domain="climate", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="party_scene_hvac_controls", host_group_key="tuya", action_type="set_temperature", extra_data_template={"temperature": 23}),
                    cloud_action("A12", "tuya:climate.living_room.set_fan_mode", service="set_fan_mode", file_rel="tuya/climate.py", integration="tuya", domain="climate", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="party_scene_hvac_controls", host_group_key="tuya", action_type="set_fan_mode", extra_data_template={"fan_mode": "medium"}),
                    cloud_action("A13", "tuya:fan.living_room_ceiling.set_percentage", service="set_percentage", file_rel="tuya/fan.py", integration="tuya", domain="fan", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="party_scene_fan_controls", host_group_key="tuya", action_type="set_percentage", extra_data_template={"percentage": 65}),
                    cloud_action("A14", "tuya:light.living_room_main.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="party_scene_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A15", "tuya:light.dining_room_main.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="party_scene_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A16", "tuya:light.hallway.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="party_scene_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A17", "tuya:light.kitchen_ceiling.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="party_scene_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A18", "tuya:climate.living_room.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="party_scene_hvac_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A19", "ecobee:thermostat.home_1", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="party_scene_runtime_verify", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
                "local": [
                    local_action("A20", "hue:bridge_1:party_scene_group", service="get_state", file_rel="hue/v2/group.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1_party", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A21", "tplink:plug.speaker_power", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="party_scene_tplink", host_group_key="tplink_local", action_type="get_state"),
                    mqtt_action("A22", "mqtt:air_quality_node_living_room", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A23", "sensor.vdev_party_scene_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A24", "sensor.vdev_party_scene_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A25", "sensor.vdev_party_scene_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A26", "sensor.vdev_party_scene_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6"]),
            extra_hard_dependencies=[
                action_dep("A7", "A14", "verify_living_room_main_after_control"),
                action_dep("A8", "A15", "verify_dining_room_main_after_control"),
                action_dep("A9", "A16", "verify_hallway_after_control"),
                action_dep("A10", "A17", "verify_kitchen_ceiling_after_control"),
                action_dep("A11", "A18", "verify_living_room_hvac_after_temperature_set"),
                action_dep("A12", "A18", "verify_living_room_hvac_after_fan_mode_set"),
            ],
            objectives={
                "primary": "minimize_party_scene_activation_latency_with_explicit_verify_wave",
                "metrics": {"e2e_latency_ms": {"p95": 4200}, "lane_completion_ms": {"ble_lane_p95": 1700, "cloud_lane_p95": 2600, "local_lane_p95": 650}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_movie_night_blackout_01",
            name="Movie Night Blackout Routine",
            group=control_group,
            story="Before a movie starts, the routine darkens the viewing area by closing multiple covers, shifting lights into a dim warm scene, adjusting climate and fan comfort, then verifying the blackout state before publishing movie-night readiness summaries.",
            strengths=[
                "High-action-count scene orchestration rather than a read-only audit.",
                "Explicit control-to-verify structure inside the cloud lane.",
                "Naturally mixed routine with BLE cover movement, cloud lighting/HVAC control, and local confirmation reads.",
            ],
            focus_areas=[
                "Preserve blackout ordering while still batching cloud light controls",
                "Treat BLE cover movement as the conservative lane and overlap cloud/local where safe",
                "Keep verification reads after the corresponding scene-control actions",
                "Avoid over-stretching the writeback tail after a large control wave",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_living_room_left", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 5}),
                    ble_action("A2", "ble:switchbot:curtain_living_room_right", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 5}),
                    ble_action("A3", "ble:switchbot:roller_shade_study", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 10}),
                    ble_action("A4", "ble:switchbot:curtain_corridor", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 15}),
                    ble_action("A5", "ble:xiaomi_ble:motion_sensor_living_room", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A6", "ble:xiaomi_ble:door_sensor_balcony", service="read_sensor", file_rel="xiaomi_ble/event.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="event", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A7", "tuya:light.living_room_main.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="movie_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 60, "color_temp_kelvin": 2700}),
                    cloud_action("A8", "tuya:light.tv_backlight.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="movie_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 35, "color_temp_kelvin": 2400}),
                    cloud_action("A9", "tuya:light.hallway.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="movie_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 25, "color_temp_kelvin": 2400}),
                    cloud_action("A10", "tuya:light.kitchen_ceiling.turn_off", service="turn_off", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="movie_light_controls", host_group_key="tuya", action_type="turn_off"),
                    cloud_action("A11", "tuya:climate.living_room.set_hvac_mode", service="set_hvac_mode", file_rel="tuya/climate.py", integration="tuya", domain="climate", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="movie_hvac_controls", host_group_key="tuya", action_type="set_hvac_mode", extra_data_template={"hvac_mode": "cool"}),
                    cloud_action("A12", "tuya:climate.living_room.set_temperature", service="set_temperature", file_rel="tuya/climate.py", integration="tuya", domain="climate", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="movie_hvac_controls", host_group_key="tuya", action_type="set_temperature", extra_data_template={"temperature": 22}),
                    cloud_action("A13", "tuya:fan.living_room_ceiling.set_percentage", service="set_percentage", file_rel="tuya/fan.py", integration="tuya", domain="fan", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="movie_fan_controls", host_group_key="tuya", action_type="set_percentage", extra_data_template={"percentage": 35}),
                    cloud_action("A14", "tuya:light.living_room_main.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="movie_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A15", "tuya:light.tv_backlight.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="movie_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A16", "tuya:light.hallway.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="movie_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A17", "tuya:light.kitchen_ceiling.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="movie_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A18", "tuya:climate.living_room.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="movie_hvac_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A19", "ecobee:thermostat.home_1", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="movie_runtime_verify", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
                "local": [
                    local_action("A20", "hue:bridge_1:theater_group", service="get_state", file_rel="hue/v2/group.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1_theater", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A21", "tplink:plug.projector_strip", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="movie_tplink", host_group_key="tplink_local", action_type="get_state"),
                    mqtt_action("A22", "mqtt:air_quality_node_living_room", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A23", "sensor.vdev_movie_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A24", "sensor.vdev_movie_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A25", "sensor.vdev_movie_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A26", "sensor.vdev_movie_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6"]),
            extra_hard_dependencies=[
                action_dep("A7", "A14", "verify_living_room_main_after_movie_scene"),
                action_dep("A8", "A15", "verify_tv_backlight_after_movie_scene"),
                action_dep("A9", "A16", "verify_hallway_after_movie_scene"),
                action_dep("A10", "A17", "verify_kitchen_blackout_after_turn_off"),
                action_dep("A11", "A18", "verify_living_room_hvac_after_mode_set"),
                action_dep("A12", "A18", "verify_living_room_hvac_after_temperature_set"),
            ],
            objectives={
                "primary": "minimize_movie_scene_blackout_latency_without_breaking_verify_order",
                "metrics": {"e2e_latency_ms": {"p95": 4300}, "lane_completion_ms": {"ble_lane_p95": 1700, "cloud_lane_p95": 2700, "local_lane_p95": 650}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_morning_wakeup_ramp_01",
            name="Morning Wake-Up Ramp Routine",
            group=control_group,
            story="At wake-up time, the routine opens multiple covers, ramps key lights to morning brightness and color temperature, nudges HVAC and fan comfort, then verifies representative state before publishing one wake-up summary.",
            strengths=[
                "Transforms the old morning snapshot pattern into a true control-and-verify automation.",
                "Large cloud light-control wave with explicit comfort-setting and follow-up readback.",
                "Still realistic for a household with multiple curtains and staggered room lighting.",
            ],
            focus_areas=[
                "Keep BLE curtain movement conservative while compressing the cloud morning ramp",
                "Batch same-provider light controls before status verification",
                "Allow local confirmation reads to stay cheap without leapfrogging control intent",
                "Preserve a short writeback chain after a large mixed-lane morning orchestration",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_master_bedroom_left", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 100}),
                    ble_action("A2", "ble:switchbot:curtain_master_bedroom_right", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 100}),
                    ble_action("A3", "ble:switchbot:curtain_living_room", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 90}),
                    ble_action("A4", "ble:switchbot:roller_shade_kitchen", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 85}),
                    ble_action("A5", "ble:xiaomi_ble:temp_humidity_sensor_bedroom", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A6", "ble:xiaomi_ble:motion_sensor_hallway", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A7", "tuya:light.hallway.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="wakeup_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 170, "color_temp_kelvin": 4200}),
                    cloud_action("A8", "tuya:light.kitchen_ceiling.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="wakeup_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 200, "color_temp_kelvin": 4500}),
                    cloud_action("A9", "tuya:light.living_room.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="wakeup_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 180, "color_temp_kelvin": 4000}),
                    cloud_action("A10", "tuya:light.master_bedroom.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="wakeup_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 110, "color_temp_kelvin": 3600}),
                    cloud_action("A11", "tuya:climate.master_bedroom.set_hvac_mode", service="set_hvac_mode", file_rel="tuya/climate.py", integration="tuya", domain="climate", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="wakeup_hvac_controls", host_group_key="tuya", action_type="set_hvac_mode", extra_data_template={"hvac_mode": "heat"}),
                    cloud_action("A12", "tuya:climate.master_bedroom.set_temperature", service="set_temperature", file_rel="tuya/climate.py", integration="tuya", domain="climate", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="wakeup_hvac_controls", host_group_key="tuya", action_type="set_temperature", extra_data_template={"temperature": 22}),
                    cloud_action("A13", "tuya:fan.living_room_ceiling.set_percentage", service="set_percentage", file_rel="tuya/fan.py", integration="tuya", domain="fan", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="wakeup_fan_controls", host_group_key="tuya", action_type="set_percentage", extra_data_template={"percentage": 45}),
                    cloud_action("A14", "tuya:light.hallway.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="wakeup_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A15", "tuya:light.kitchen_ceiling.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="wakeup_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A16", "tuya:light.living_room.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="wakeup_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A17", "tuya:light.master_bedroom.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="wakeup_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A18", "tuya:climate.master_bedroom.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="wakeup_hvac_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A19", "ecobee:thermostat.home_1", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="wakeup_runtime_verify", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
                "local": [
                    local_action("A20", "hue:bridge_1:kitchen_group", service="get_state", file_rel="hue/v2/group.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1_kitchen", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A21", "hue:bridge_1:hallway_motion_sensor", service="get_state", file_rel="hue/v2/sensor.py", integration="hue", domain="sensor", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1_hallway", host_group_key="hue_bridge_1", action_type="get_state"),
                    mqtt_action("A22", "mqtt:air_quality_node_living_room", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A23", "sensor.vdev_wakeup_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A24", "sensor.vdev_wakeup_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A25", "sensor.vdev_wakeup_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A26", "sensor.vdev_wakeup_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6"]),
            extra_hard_dependencies=[
                action_dep("A7", "A14", "verify_hallway_after_wakeup_control"),
                action_dep("A8", "A15", "verify_kitchen_ceiling_after_wakeup_control"),
                action_dep("A9", "A16", "verify_living_room_after_wakeup_control"),
                action_dep("A10", "A17", "verify_master_bedroom_after_wakeup_control"),
                action_dep("A11", "A18", "verify_master_bedroom_hvac_after_mode_set"),
                action_dep("A12", "A18", "verify_master_bedroom_hvac_after_temperature_set"),
            ],
            objectives={
                "primary": "minimize_morning_ramp_latency_while_preserving_control_then_verify",
                "metrics": {"e2e_latency_ms": {"p95": 4200}, "lane_completion_ms": {"ble_lane_p95": 1700, "cloud_lane_p95": 2600, "local_lane_p95": 650}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_workday_focus_mode_01",
            name="Workday Focus Mode Routine",
            group=control_group,
            story="At the start of a work block, the routine repositions shades, enables desk airflow and task lighting, applies a focused lighting and climate profile, then verifies representative cloud and local state before publishing one focus-mode summary.",
            strengths=[
                "Large mixed control routine with meaningful BLE device movement and cloud comfort changes.",
                "Separates control wave and verification wave, which is closer to a real scene activation than a status snapshot.",
                "Includes representative local verification without relying on unsupported local-control semantics.",
            ],
            focus_areas=[
                "BLE physical-device control serialization across multiple covers and near-desk peripherals",
                "Cloud control grouping across Tuya lighting and Ecobee comfort actions",
                "Post-control verification should remain a distinct phase instead of blending into acquisition",
                "Local verification should stay cheap and grouped behind the verification frontier",
                "Lane writeback should remain short and deterministic after a larger control routine",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:roller_shade_office_left", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 72}),
                    ble_action("A2", "ble:switchbot:roller_shade_office_right", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 72}),
                    ble_action("A3", "ble:switchbot:roller_shade_study", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 68}),
                    ble_action("A4", "ble:switchbot:desk_fan", service="set_percentage", file_rel="switchbot/fan.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="fan", action_type="set_percentage", extra_data_template={"percentage": 55}),
                    ble_action("A5", "ble:switchbot:task_light", service="turn_on", file_rel="switchbot/light.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="light", action_type="turn_on"),
                    ble_action("A6", "ble:xiaomi_ble:motion_sensor_office_entry", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A7", "ble:xiaomi_ble:temp_sensor_office", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A8", "tuya:light.office_main.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="focus_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 205, "color_temp_kelvin": 4100}),
                    cloud_action("A9", "tuya:light.office_task.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="focus_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 195, "color_temp_kelvin": 4200}),
                    cloud_action("A10", "tuya:light.study_bookshelf.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="focus_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 170, "color_temp_kelvin": 3900}),
                    cloud_action("A11", "tuya:switch.energy_strip_desk.turn_on", service="turn_on", file_rel="tuya/switch.py", integration="tuya", domain="switch", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="focus_switch_controls", host_group_key="tuya", action_type="turn_on"),
                    cloud_action("A12", "ecobee:thermostat.office.set_hvac_mode", service="set_hvac_mode", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="focus_hvac_controls", host_group_key="ecobee", action_type="set_hvac_mode", extra_data_template={"hvac_mode": "cool"}),
                    cloud_action("A13", "ecobee:thermostat.office.set_fan_mode", service="set_fan_mode", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="focus_hvac_controls", host_group_key="ecobee", action_type="set_fan_mode", extra_data_template={"fan_mode": "on"}),
                    cloud_action("A14", "ecobee:thermostat.office.set_temperature", service="set_temperature", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="focus_hvac_controls", host_group_key="ecobee", action_type="set_temperature", extra_data_template={"temperature": 22}),
                    cloud_action("A15", "tuya:light.office_main.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="focus_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A16", "tuya:light.office_task.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="focus_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A17", "tuya:light.study_bookshelf.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="focus_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A18", "tuya:switch.energy_strip_desk.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="focus_switch_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A19", "ecobee:thermostat.office", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="focus_runtime_verify", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
                "local": [
                    local_action("A20", "hue:bridge_1:office_group", service="get_state", file_rel="hue/v2/group.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1_office", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A21", "tplink:plug.monitor_power", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="focus_tplink", host_group_key="tplink_local", action_type="get_state"),
                    mqtt_action("A22", "mqtt:desk_air_quality_node", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A23", "sensor.vdev_workday_focus_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A24", "sensor.vdev_workday_focus_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A25", "sensor.vdev_workday_focus_local_lane", file_rel="hue/v2/group.py", integration="hue"),
                "overall": write_action("A26", "sensor.vdev_workday_focus_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6", "A7"]),
            extra_hard_dependencies=[
                action_dep("A8", "A15", "verify_office_main_after_focus_control"),
                action_dep("A9", "A16", "verify_office_task_after_focus_control"),
                action_dep("A10", "A17", "verify_bookshelf_after_focus_control"),
                action_dep("A11", "A18", "verify_desk_strip_after_focus_control"),
                action_dep("A12", "A19", "verify_ecobee_runtime_after_focus_mode"),
                action_dep("A13", "A19", "verify_ecobee_runtime_after_focus_fan_mode"),
                action_dep("A14", "A19", "verify_ecobee_runtime_after_focus_temperature"),
            ],
            objectives={
                "primary": "minimize_focus_mode_activation_latency_while_preserving_control_then_verify",
                "metrics": {"e2e_latency_ms": {"p95": 5200}, "lane_completion_ms": {"ble_lane_p95": 2100, "cloud_lane_p95": 3200, "local_lane_p95": 700}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_guest_suite_welcome_01",
            name="Guest Suite Welcome Routine",
            group=control_group,
            story="Before guests arrive, the routine opens suite shades, enables airflow and welcome lighting, applies a comfort preset, then verifies representative scene state before publishing a guest-suite readiness summary.",
            strengths=[
                "Adds another large control-and-verify routine without reusing the exact same device mix as the earlier three control cases.",
                "Combines Tuya light and climate control with Ecobee comfort control and local welcome-state confirmation.",
                "Large enough to surface schedule-quality regressions in control sequencing and verification handling.",
            ],
            focus_areas=[
                "BLE cover and peripheral control ordering",
                "Cloud control grouping across welcome lighting and guest comfort settings",
                "Ecobee post-control verification should stay behind comfort-control actions",
                "Local verification should stay grouped without overtaking cloud verification",
                "Writeback tail should remain compact after a high-action-count routine",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_guest_suite_left", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 82}),
                    ble_action("A2", "ble:switchbot:curtain_guest_suite_right", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 82}),
                    ble_action("A3", "ble:switchbot:roller_shade_guest_suite", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 76}),
                    ble_action("A4", "ble:switchbot:guest_suite_fan", service="set_percentage", file_rel="switchbot/fan.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="fan", action_type="set_percentage", extra_data_template={"percentage": 48}),
                    ble_action("A5", "ble:switchbot:guest_suite_bedside_light", service="turn_on", file_rel="switchbot/light.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="light", action_type="turn_on"),
                    ble_action("A6", "ble:xiaomi_ble:motion_sensor_guest_entry", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A7", "ble:xiaomi_ble:temp_sensor_guest_suite", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A8", "tuya:light.guest_suite_main.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="guest_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 180, "color_temp_kelvin": 3200}),
                    cloud_action("A9", "tuya:light.guest_suite_bedside.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="guest_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 145, "color_temp_kelvin": 3000}),
                    cloud_action("A10", "tuya:light.guest_suite_entry.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="guest_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 130, "color_temp_kelvin": 3300}),
                    cloud_action("A11", "tuya:climate.guest_suite.set_hvac_mode", service="set_hvac_mode", file_rel="tuya/climate.py", integration="tuya", domain="climate", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="guest_hvac_controls", host_group_key="tuya", action_type="set_hvac_mode", extra_data_template={"hvac_mode": "cool"}),
                    cloud_action("A12", "tuya:climate.guest_suite.set_temperature", service="set_temperature", file_rel="tuya/climate.py", integration="tuya", domain="climate", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="guest_hvac_controls", host_group_key="tuya", action_type="set_temperature", extra_data_template={"temperature": 24}),
                    cloud_action("A13", "ecobee:thermostat.guest_suite.set_fan_mode", service="set_fan_mode", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="guest_runtime_controls", host_group_key="ecobee", action_type="set_fan_mode", extra_data_template={"fan_mode": "auto"}),
                    cloud_action("A14", "ecobee:thermostat.guest_suite.set_preset_mode", service="set_preset_mode", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="guest_runtime_controls", host_group_key="ecobee", action_type="set_preset_mode", extra_data_template={"preset_mode": "home"}),
                    cloud_action("A15", "tuya:light.guest_suite_main.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="guest_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A16", "tuya:light.guest_suite_bedside.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="guest_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A17", "tuya:light.guest_suite_entry.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="guest_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A18", "tuya:climate.guest_suite.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="guest_hvac_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A19", "ecobee:thermostat.guest_suite", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="guest_runtime_verify", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
                "local": [
                    local_action("A20", "hue:bridge_1:guest_suite_group", service="get_state", file_rel="hue/v2/group.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1_guest_suite", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A21", "tplink:plug.guest_suite_heater", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="guest_tplink", host_group_key="tplink_local", action_type="get_state"),
                    mqtt_action("A22", "mqtt:guest_suite_air_quality_node", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A23", "sensor.vdev_guest_suite_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A24", "sensor.vdev_guest_suite_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A25", "sensor.vdev_guest_suite_local_lane", file_rel="hue/v2/group.py", integration="hue"),
                "overall": write_action("A26", "sensor.vdev_guest_suite_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6", "A7"]),
            extra_hard_dependencies=[
                action_dep("A8", "A15", "verify_guest_main_after_welcome_control"),
                action_dep("A9", "A16", "verify_guest_bedside_after_welcome_control"),
                action_dep("A10", "A17", "verify_guest_entry_after_welcome_control"),
                action_dep("A11", "A18", "verify_guest_hvac_after_mode_set"),
                action_dep("A12", "A18", "verify_guest_hvac_after_temperature_set"),
                action_dep("A13", "A19", "verify_guest_runtime_after_fan_mode"),
                action_dep("A14", "A19", "verify_guest_runtime_after_preset_mode"),
            ],
            objectives={
                "primary": "minimize_guest_suite_activation_latency_while_preserving_control_then_verify",
                "metrics": {"e2e_latency_ms": {"p95": 5200}, "lane_completion_ms": {"ble_lane_p95": 2100, "cloud_lane_p95": 3200, "local_lane_p95": 700}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_storm_lockdown_safety_01",
            name="Storm Lockdown Safety Routine",
            group=control_group,
            story="Before a storm front arrives, the routine closes exposed shades, powers down selected outdoor loads, enables safety lighting and HVAC lockdown settings, then verifies representative state before publishing a whole-home storm-lockdown summary.",
            strengths=[
                "Control-heavy safety routine with a different device mix from party or wake-up scenes.",
                "Exercises light, switch, siren-adjacent, and climate control in one flow while still requiring a verification phase.",
                "Good generalization test because it is safety-oriented rather than ambience-oriented.",
            ],
            focus_areas=[
                "BLE cover-control ordering under a larger safety routine",
                "Cloud control grouping across lights, switches, and HVAC settings",
                "Verification phase should stay separate from control and preserve readback ordering",
                "Local verification should remain grouped but should not overtake cloud verification",
                "Writeback tail should remain compact and predictable under a larger control case",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:roller_shade_entry", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 0}),
                    ble_action("A2", "ble:switchbot:roller_shade_living_room", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 0}),
                    ble_action("A3", "ble:switchbot:roller_shade_study", service="set_cover_position", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="set_cover_position", extra_data_template={"position": 0}),
                    ble_action("A4", "ble:switchbot:patio_fan", service="turn_off", file_rel="switchbot/fan.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="fan", action_type="turn_off"),
                    ble_action("A5", "ble:xiaomi_ble:window_sensor_study", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A6", "ble:xiaomi_ble:door_sensor_back_patio", service="read_sensor", file_rel="xiaomi_ble/event.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="event", action_type="read_sensor"),
                ],
                "cloud": [
                    cloud_action("A7", "tuya:light.entry.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="storm_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 160, "color_temp_kelvin": 3600}),
                    cloud_action("A8", "tuya:light.porch.turn_on", service="turn_on", file_rel="tuya/light.py", integration="tuya", domain="light", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="storm_light_controls", host_group_key="tuya", action_type="turn_on", extra_data_template={"brightness": 180, "color_temp_kelvin": 3500}),
                    cloud_action("A9", "tuya:switch.patio_heater.turn_off", service="turn_off", file_rel="tuya/switch.py", integration="tuya", domain="switch", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="storm_switch_controls", host_group_key="tuya", action_type="turn_off"),
                    cloud_action("A10", "tuya:switch.fountain_pump.turn_off", service="turn_off", file_rel="tuya/switch.py", integration="tuya", domain="switch", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="storm_switch_controls", host_group_key="tuya", action_type="turn_off"),
                    cloud_action("A11", "tuya:siren.entry.turn_on", service="turn_on", file_rel="tuya/siren.py", integration="tuya", domain="siren", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="storm_alert_controls", host_group_key="tuya", action_type="turn_on"),
                    cloud_action("A12", "ecobee:thermostat.home_1.set_hvac_mode", service="set_hvac_mode", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="storm_hvac_controls", host_group_key="ecobee", action_type="set_hvac_mode", extra_data_template={"hvac_mode": "heat"}),
                    cloud_action("A13", "ecobee:thermostat.home_1.set_fan_mode", service="set_fan_mode", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="storm_hvac_controls", host_group_key="ecobee", action_type="set_fan_mode", extra_data_template={"fan_mode": "auto"}),
                    cloud_action("A14", "ecobee:thermostat.home_1.set_temperature", service="set_temperature", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", marker_hints=CLOUD_CONTROL_HINTS, endpoint_group_key="storm_hvac_controls", host_group_key="ecobee", action_type="set_temperature", extra_data_template={"temperature": 21}),
                    cloud_action("A15", "tuya:light.entry.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="storm_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A16", "tuya:light.porch.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="storm_light_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A17", "tuya:switch.patio_heater.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="storm_switch_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A18", "tuya:switch.fountain_pump.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="storm_switch_verify", host_group_key="tuya", action_type="status"),
                    cloud_action("A19", "ecobee:thermostat.home_1", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="storm_runtime_verify", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
                "local": [
                    local_action("A20", "hue:bridge_1:entry_group", service="get_state", file_rel="hue/v2/group.py", integration="hue", domain="light", marker_hints=LOCAL_API_HINTS, provider="hue_local", endpoint_group_key="bridge_1_entry", host_group_key="hue_bridge_1", action_type="get_state"),
                    local_action("A21", "tplink:plug.emergency_backup", service="get_state", file_rel="tplink/entity.py", integration="tplink", domain="switch", marker_hints=LOCAL_API_HINTS, provider="tplink_local", endpoint_group_key="storm_tplink", host_group_key="tplink_local", action_type="get_state"),
                    mqtt_action("A22", "mqtt:weather_station_home", service="read_last_message", file_rel="mqtt/subscription.py"),
                ],
            },
            writebacks={
                "ble": write_action("A23", "sensor.vdev_storm_lockdown_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A24", "sensor.vdev_storm_lockdown_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A25", "sensor.vdev_storm_lockdown_local_lane", file_rel="hue/v2/group.py", integration="hue"),
                "overall": write_action("A26", "sensor.vdev_storm_lockdown_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6"]),
            extra_hard_dependencies=[
                action_dep("A7", "A15", "verify_entry_light_after_lockdown_control"),
                action_dep("A8", "A16", "verify_porch_light_after_lockdown_control"),
                action_dep("A9", "A17", "verify_patio_heater_after_lockdown_control"),
                action_dep("A10", "A18", "verify_fountain_pump_after_lockdown_control"),
                action_dep("A12", "A19", "verify_storm_runtime_after_hvac_mode"),
                action_dep("A13", "A19", "verify_storm_runtime_after_fan_mode"),
                action_dep("A14", "A19", "verify_storm_runtime_after_temperature"),
            ],
            objectives={
                "primary": "minimize_storm_lockdown_activation_latency_while_preserving_control_then_verify",
                "metrics": {"e2e_latency_ms": {"p95": 5400}, "lane_completion_ms": {"ble_lane_p95": 1900, "cloud_lane_p95": 3400, "local_lane_p95": 700}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_ble_safety_sweep_stress_01",
            name="BLE Congestion Routine Stress",
            group=stress_group,
            story="A fast whole-home BLE safety sweep checks curtains, room sensors, and one ESPHome transport pair, acting as a realistic high-contention BLE routine rather than an abstract stress synthetic.",
            strengths=[
                "Still clearly a routine, but with maximal BLE contention.",
                "Contains both repeated reads and transport setup/subscription.",
                "Good upper-bound test for radio budget and min-gap handling.",
            ],
            focus_areas=[
                "BLE overlap budget",
                "MIN_GAP and NO_OVERLAP behavior",
                "Connect-before-subscribe under heavy BLE load",
                "BLE lane writeback should remain minimal and clean",
            ],
            lanes={
                "ble": [
                    ble_action("A1", "ble:switchbot:curtain_living_room", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A2", "ble:switchbot:curtain_bedroom", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A3", "ble:switchbot:curtain_study", service="refresh_cover", file_rel="switchbot/cover.py", integration="switchbot", hints=BLE_STATUS_HINTS, domain="cover", action_type="refresh_cover"),
                    ble_action("A4", "ble:xiaomi_ble:temp_sensor_1", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A5", "ble:xiaomi_ble:temp_sensor_2", service="read_sensor", file_rel="xiaomi_ble/sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="sensor", action_type="read_sensor"),
                    ble_action("A6", "ble:xiaomi_ble:temp_sensor_3", service="read_sensor", file_rel="xiaomi_ble/binary_sensor.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="binary_sensor", action_type="read_sensor"),
                    ble_action("A7", "ble:xiaomi_ble:door_sensor_entry", service="read_sensor", file_rel="xiaomi_ble/event.py", integration="xiaomi_ble", hints=BLE_STATUS_HINTS, domain="event", action_type="read_sensor"),
                    ble_action("A8", "ble:esphome:air_node_1", service="connect", file_rel="esphome/__init__.py", integration="esphome", hints=BLE_CONNECT_HINTS, domain="esphome", action_type="connect"),
                    ble_action("A9", "ble:esphome:relay_node_1", service="subscribe", file_rel="esphome/manager.py", integration="esphome", hints=BLE_SUBSCRIBE_HINTS, domain="manager", action_type="subscribe"),
                ],
            },
            writebacks={
                "ble": write_action("A10", "sensor.vdev_ble_safety_sweep_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "overall": write_action("A11", "sensor.vdev_ble_safety_sweep_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE"],
            connect_before_subscribe=[("A8", "A9")],
            ble_soft_pairs=ble_budget_pairs(["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"]),
            objectives={
                "primary": "stress_ble_congestion_under_realistic_safety_sweep",
                "metrics": {"e2e_latency_ms": {"p95": 2600}, "lane_completion_ms": {"ble_lane_p95": 1350}},
            },
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_energy_hvac_audit_01",
            name="Cloud Burst Energy & HVAC Audit Routine",
            group=stress_group,
            story="At a fixed audit time, the routine gathers multiple Tuya lights, energy strips, climate states, and two Ecobee runtime reads to generate one energy and HVAC audit summary.",
            strengths=[
                "Realistic cloud burst instead of a bare synthetic provider stress case.",
                "Combines same-provider Tuya batching with cross-provider Ecobee reads.",
                "Good benchmark for cloud session reuse, batching, and backoff policy.",
            ],
            focus_areas=[
                "Tuya batching buckets",
                "Cross-provider parallelism",
                "Session reuse and host grouping",
                "Backoff and shrink-before-disable behavior",
                "Short overall writeback chain after a large cloud burst",
            ],
            lanes={
                "cloud": [
                    cloud_action("A1", "tuya:light.living_room_1.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="energy_hvac_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A2", "tuya:light.living_room_2.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="energy_hvac_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A3", "tuya:light.bedroom_1.status", service="status", file_rel="tuya/light.py", integration="tuya", domain="light", endpoint_group_key="energy_hvac_lights", host_group_key="tuya", action_type="status"),
                    cloud_action("A4", "tuya:switch.energy_strip_1.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="energy_hvac_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A5", "tuya:switch.energy_strip_2.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="energy_hvac_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A6", "tuya:switch.energy_strip_3.status", service="status", file_rel="tuya/switch.py", integration="tuya", domain="switch", endpoint_group_key="energy_hvac_energy", host_group_key="tuya", action_type="status"),
                    cloud_action("A7", "tuya:climate.master_bedroom.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="energy_hvac_climate", host_group_key="tuya", action_type="status"),
                    cloud_action("A8", "tuya:climate.guest_room.status", service="status", file_rel="tuya/climate.py", integration="tuya", domain="climate", endpoint_group_key="energy_hvac_climate", host_group_key="tuya", action_type="status"),
                    cloud_action("A9", "ecobee:thermostat.home_1", service="read_runtime", file_rel="ecobee/climate.py", integration="ecobee", domain="climate", provider="ecobee", endpoint_group_key="energy_hvac_ecobee", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                    cloud_action("A10", "ecobee:thermostat.home_2", service="read_runtime", file_rel="ecobee/sensor.py", integration="ecobee", domain="sensor", provider="ecobee", endpoint_group_key="energy_hvac_ecobee", host_group_key="ecobee", action_type="read_runtime", marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"]),
                ],
            },
            writebacks={
                "cloud": write_action("A11", "sensor.vdev_energy_hvac_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "overall": write_action("A12", "sensor.vdev_energy_hvac_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["CLOUD"],
            objectives={
                "primary": "stress_cloud_burst_audit_with_mixed_providers",
                "metrics": {"e2e_latency_ms": {"p95": 2100}, "lane_completion_ms": {"cloud_lane_p95": 1250}},
            },
        )
    )

    cases.extend(build_expansion_cases())
    cases.extend(build_profile_coverage_cases())

    return cases


def build_expansion_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    morning_group = "Morning and Leaving Home Routines"
    comfort_group = "Coming Home and Evening Comfort Routines"
    monitoring_group = "Night and Energy Monitoring Routines"
    control_group = "Scene Activation and Comfort Control Routines"
    stress_group = "Household Stress and Abnormality Routines"
    context_group = "Weather and Contextual Adjustment Routines"
    family_group = "Family Care and Room-Level Snapshot Routines"
    survey_group = "Whole-Home Survey and Audit Routines"

    def switchbot_cover(action_id: str, device_id: str) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="refresh_cover",
            file_rel="switchbot/cover.py",
            integration="switchbot",
            hints=BLE_STATUS_HINTS,
            domain="cover",
            action_type="refresh_cover",
        )

    def switchbot_status(action_id: str, device_id: str, *, domain: str = "fan", file_rel: str = "switchbot/fan.py") -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="read_status",
            file_rel=file_rel,
            integration="switchbot",
            hints=BLE_STATUS_HINTS,
            domain=domain,
            action_type="read_status",
        )

    def xiaomi_sensor(action_id: str, device_id: str, *, domain: str = "sensor", file_rel: str = "xiaomi_ble/sensor.py") -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="read_sensor",
            file_rel=file_rel,
            integration="xiaomi_ble",
            hints=BLE_STATUS_HINTS,
            domain=domain,
            action_type="read_sensor",
        )

    def xiaomi_status(action_id: str, device_id: str, *, domain: str = "device", file_rel: str = "xiaomi_ble/device.py") -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="read_status",
            file_rel=file_rel,
            integration="xiaomi_ble",
            hints=BLE_STATUS_HINTS,
            domain=domain,
            action_type="read_status",
        )

    def esphome_connect(action_id: str, device_id: str) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="connect",
            file_rel="esphome/__init__.py",
            integration="esphome",
            hints=BLE_CONNECT_HINTS,
            domain="esphome",
            action_type="connect",
        )

    def esphome_subscribe(action_id: str, device_id: str) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="subscribe",
            file_rel="esphome/manager.py",
            integration="esphome",
            hints=BLE_SUBSCRIBE_HINTS,
            domain="manager",
            action_type="subscribe",
        )

    def tuya_status(
        action_id: str,
        endpoint: str,
        *,
        domain: str,
        endpoint_group_key: str,
        action_type: str = "status",
    ) -> Dict[str, Any]:
        file_rel = {
            "light": "tuya/light.py",
            "switch": "tuya/switch.py",
            "climate": "tuya/climate.py",
        }[domain]
        return cloud_action(
            action_id,
            endpoint,
            service="status",
            file_rel=file_rel,
            integration="tuya",
            domain=domain,
            endpoint_group_key=endpoint_group_key,
            host_group_key="tuya",
            action_type=action_type,
        )

    def ecobee_runtime(
        action_id: str,
        endpoint: str,
        *,
        endpoint_group_key: str,
        domain: str = "climate",
        file_rel: str = "ecobee/climate.py",
    ) -> Dict[str, Any]:
        return cloud_action(
            action_id,
            endpoint,
            service="read_runtime",
            file_rel=file_rel,
            integration="ecobee",
            domain=domain,
            provider="ecobee",
            endpoint_group_key=endpoint_group_key,
            host_group_key="ecobee",
            action_type="read_runtime",
            marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"],
        )

    def hue_state(
        action_id: str,
        endpoint: str,
        *,
        domain: str = "light",
        file_rel: str = "hue/v2/light.py",
        endpoint_group_key: str = "bridge_1",
        host_group_key: str = "hue_bridge_1",
    ) -> Dict[str, Any]:
        return local_action(
            action_id,
            endpoint,
            service="get_state",
            file_rel=file_rel,
            integration="hue",
            domain=domain,
            marker_hints=LOCAL_API_HINTS,
            provider="hue_local",
            endpoint_group_key=endpoint_group_key,
            host_group_key=host_group_key,
            action_type="get_state",
        )

    def tplink_state(
        action_id: str,
        endpoint: str,
        *,
        endpoint_group_key: str,
        domain: str = "switch",
    ) -> Dict[str, Any]:
        return local_action(
            action_id,
            endpoint,
            service="get_state",
            file_rel="tplink/entity.py",
            integration="tplink",
            domain=domain,
            marker_hints=LOCAL_API_HINTS,
            provider="tplink_local",
            endpoint_group_key=endpoint_group_key,
            host_group_key="tplink_local",
            action_type="get_state",
        )

    def mqtt_last(action_id: str, topic_id: str, *, file_rel: str = "mqtt/subscription.py") -> Dict[str, Any]:
        return mqtt_action(action_id, topic_id, service="read_last_message", file_rel=file_rel)

    def mixed_protocols(lanes: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        protocols: List[str] = []
        if lanes.get("ble"):
            protocols.append("BLE")
        if lanes.get("cloud"):
            protocols.append("CLOUD")
        if lanes.get("local"):
            protocols.append("LOCAL")
        return protocols

    def soft_ble_pairs(lanes: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        return ble_budget_pairs([str(action["action_id"]) for action in lanes.get("ble", [])])

    cases.append(
        case_target(
            vdev_id="vdev_arrive_home_lighting_climate_prep_01",
            name="Arrive-Home Lighting and Climate Prep",
            group=comfort_group,
            story="Before residents get home, the routine checks living-room, hallway, and bedroom lights, curtains, climate, and air quality to decide whether the house is ready to enter a welcome-home state.",
            strengths=[
                "Arrival routine is realistic and still mixed across BLE, cloud, and local lanes.",
                "Contains BLE connect plus subscribe instead of only stateless reads.",
                "Both Hue local states and cloud runtime reads contribute to the same welcome-home decision.",
            ],
            focus_areas=[
                "BLE connect-before-subscribe under a realistic arrival lane",
                "Cloud light plus climate batching",
                "Local Hue and sensor reads should stay cheap",
                "Lane-first publish followed by one overall welcome-home summary",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_living_room_left"),
                    switchbot_cover("A2", "ble:switchbot:curtain_living_room_right"),
                    xiaomi_sensor("A3", "ble:xiaomi_ble:motion_sensor_entry_arrival", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:temp_sensor_bedroom_arrival"),
                    esphome_connect("A5", "ble:esphome:air_node_arrival"),
                    esphome_subscribe("A6", "ble:esphome:relay_node_arrival"),
                ],
                "cloud": [
                    tuya_status("A7", "tuya:light.living_room_welcome_1.status", domain="light", endpoint_group_key="arrive_home_welcome_lights"),
                    tuya_status("A8", "tuya:light.living_room_welcome_2.status", domain="light", endpoint_group_key="arrive_home_welcome_lights"),
                    tuya_status("A9", "tuya:climate.bedroom_arrival.status", domain="climate", endpoint_group_key="arrive_home_climate"),
                    ecobee_runtime("A10", "ecobee:thermostat.arrival_home_1", endpoint_group_key="arrive_home_ecobee"),
                ],
                "local": [
                    hue_state("A11", "hue:bridge_1:living_room_main_left"),
                    hue_state("A12", "hue:bridge_1:living_room_main_center"),
                    hue_state("A13", "hue:bridge_1:living_room_main_right"),
                    hue_state("A14", "hue:bridge_1:hallway_presence_arrival", domain="sensor", file_rel="hue/v2/sensor.py"),
                ],
            },
            writebacks={
                "ble": write_action("A15", "sensor.vdev_arrive_home_lighting_climate_prep_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A16", "sensor.vdev_arrive_home_lighting_climate_prep_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A17", "sensor.vdev_arrive_home_lighting_climate_prep_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A18", "sensor.vdev_arrive_home_lighting_climate_prep_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            connect_before_subscribe=[("A5", "A6")],
            ble_soft_pairs=soft_ble_pairs(
                {
                    "ble": [
                        {"action_id": "A1"},
                        {"action_id": "A2"},
                        {"action_id": "A3"},
                        {"action_id": "A4"},
                        {"action_id": "A5"},
                        {"action_id": "A6"},
                    ]
                }
            ),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_leave_home_safety_energy_sweep_01",
            name="Leave-Home Safety and Energy Sweep",
            group=morning_group,
            story="When everyone leaves, the routine checks lights, curtains, plugs, climate, and entry sensors, then publishes one leave-home safety and energy summary.",
            strengths=[
                "Balanced mixed case with heavier cloud burst than the smaller leaving-home benchmark.",
                "BLE lane includes both curtain refresh and simple safety reads.",
                "Local TP-Link and Hue reads make the local lane materially useful.",
            ],
            focus_areas=[
                "Cloud burst batching across lights, switches, and climate",
                "BLE refresh versus read ordering under one departure sweep",
                "Cheap local lane should not be delayed by cloud burst",
                "Short publish chain from lane summaries to one overall result",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_living_room_departure"),
                    switchbot_cover("A2", "ble:switchbot:curtain_bedroom_departure"),
                    switchbot_cover("A3", "ble:switchbot:curtain_study_departure"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:door_sensor_entry_departure", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A5", "ble:xiaomi_ble:window_sensor_kitchen_departure", domain="event", file_rel="xiaomi_ble/event.py"),
                    xiaomi_status("A6", "ble:xiaomi_ble:bedside_lamp_departure", domain="device", file_rel="xiaomi_ble/device.py"),
                ],
                "cloud": [
                    tuya_status("A7", "tuya:switch.foyer_strip.status", domain="switch", endpoint_group_key="leave_energy_switches"),
                    tuya_status("A8", "tuya:switch.media_strip.status", domain="switch", endpoint_group_key="leave_energy_switches"),
                    tuya_status("A9", "tuya:switch.kitchen_strip.status", domain="switch", endpoint_group_key="leave_energy_switches"),
                    tuya_status("A10", "tuya:climate.master_departure.status", domain="climate", endpoint_group_key="leave_energy_hvac"),
                    tuya_status("A11", "tuya:light.entry_departure.status", domain="light", endpoint_group_key="leave_energy_lights"),
                    tuya_status("A12", "tuya:light.hall_departure.status", domain="light", endpoint_group_key="leave_energy_lights"),
                ],
                "local": [
                    tplink_state("A13", "tplink:plug.coffee_station_departure", endpoint_group_key="leave_tplink_departure"),
                    tplink_state("A14", "tplink:plug.workstation_departure", endpoint_group_key="leave_tplink_departure"),
                    hue_state("A15", "hue:bridge_1:dining_group_left_home", file_rel="hue/v2/group.py"),
                    hue_state("A16", "hue:bridge_1:dining_group_accent_left_home"),
                ],
            },
            writebacks={
                "ble": write_action("A17", "sensor.vdev_leave_home_safety_energy_sweep_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A18", "sensor.vdev_leave_home_safety_energy_sweep_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A19", "sensor.vdev_leave_home_safety_energy_sweep_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A20", "sensor.vdev_leave_home_safety_energy_sweep_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs(
                {"ble": [{"action_id": f"A{i}"} for i in range(1, 7)]}
            ),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_good_morning_whole_floor_readiness_01",
            name="Good-Morning Whole-Floor Readiness",
            group=morning_group,
            story="After wake-up time, the routine collects bedroom, living-room, and dining-room temperatures, lights, curtains, and climate states to decide whether the floor is already in morning mode.",
            strengths=[
                "Read-heavy whole-floor routine with no artificial padding.",
                "BLE lane is long enough to expose ordering and transport budget issues.",
                "Cloud climate plus light grouping is naturally present.",
            ],
            focus_areas=[
                "BLE read-heavy corridor ordering",
                "Cloud climate and light batching",
                "Local Hue groups should stay cheap",
                "Lane publish structure should remain explainable",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_master_morning"),
                    switchbot_cover("A2", "ble:switchbot:curtain_living_morning"),
                    xiaomi_sensor("A3", "ble:xiaomi_ble:temp_sensor_master_morning"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:temp_sensor_dining_morning"),
                    xiaomi_status("A5", "ble:xiaomi_ble:bedside_lamp_left_morning", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_status("A6", "ble:xiaomi_ble:bedside_lamp_right_morning", domain="device", file_rel="xiaomi_ble/device.py"),
                ],
                "cloud": [
                    tuya_status("A7", "tuya:climate.master_floor.status", domain="climate", endpoint_group_key="morning_floor_hvac"),
                    tuya_status("A8", "tuya:climate.living_floor.status", domain="climate", endpoint_group_key="morning_floor_hvac"),
                    tuya_status("A9", "tuya:light.master_floor.status", domain="light", endpoint_group_key="morning_floor_lights"),
                    tuya_status("A10", "tuya:light.dining_floor.status", domain="light", endpoint_group_key="morning_floor_lights"),
                    ecobee_runtime("A11", "ecobee:thermostat.morning_floor_1", endpoint_group_key="morning_floor_ecobee"),
                ],
                "local": [
                    hue_state("A12", "hue:bridge_1:bedroom_group_morning", file_rel="hue/v2/group.py"),
                    hue_state("A13", "hue:bridge_1:hallway_group_morning", file_rel="hue/v2/group.py"),
                ],
            },
            writebacks={
                "ble": write_action("A14", "sensor.vdev_good_morning_whole_floor_readiness_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A15", "sensor.vdev_good_morning_whole_floor_readiness_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A16", "sensor.vdev_good_morning_whole_floor_readiness_local_lane", file_rel="hue/v2/group.py", integration="hue"),
                "overall": write_action("A17", "sensor.vdev_good_morning_whole_floor_readiness_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs(
                {"ble": [{"action_id": f"A{i}"} for i in range(1, 7)]}
            ),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_bedtime_lockdown_routine_01",
            name="Bedtime Lockdown Routine",
            group=monitoring_group,
            story="Before everyone goes to sleep, the routine checks lights, curtains, plugs, climate, and door or window sensors, then publishes a bedtime lockdown summary.",
            strengths=[
                "Long aggregation chain with natural room-by-room semantics.",
                "Mixes cloud lights, switches, and climate in one night routine.",
                "Local plugs and one Hue group keep the local lane meaningful.",
            ],
            focus_areas=[
                "Cloud grouping across lights and switches",
                "BLE curtain and safety-read ordering",
                "Local lane should stay inexpensive",
                "Night summary should preserve a clean writeback tail",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_master_lockdown"),
                    switchbot_cover("A2", "ble:switchbot:curtain_living_lockdown"),
                    xiaomi_sensor("A3", "ble:xiaomi_ble:window_sensor_master_lockdown", domain="event", file_rel="xiaomi_ble/event.py"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:window_sensor_guest_lockdown", domain="event", file_rel="xiaomi_ble/event.py"),
                    xiaomi_status("A5", "ble:xiaomi_ble:bedside_lamp_left_lockdown", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_status("A6", "ble:xiaomi_ble:bedside_lamp_right_lockdown", domain="device", file_rel="xiaomi_ble/device.py"),
                ],
                "cloud": [
                    tuya_status("A7", "tuya:light.bedroom_lockdown.status", domain="light", endpoint_group_key="bedtime_lights"),
                    tuya_status("A8", "tuya:light.hallway_lockdown.status", domain="light", endpoint_group_key="bedtime_lights"),
                    tuya_status("A9", "tuya:light.living_lockdown.status", domain="light", endpoint_group_key="bedtime_lights"),
                    tuya_status("A10", "tuya:switch.tv_lockdown.status", domain="switch", endpoint_group_key="bedtime_switches"),
                    tuya_status("A11", "tuya:switch.heater_lockdown.status", domain="switch", endpoint_group_key="bedtime_switches"),
                    tuya_status("A12", "tuya:climate.master_lockdown.status", domain="climate", endpoint_group_key="bedtime_hvac"),
                ],
                "local": [
                    tplink_state("A13", "tplink:plug.bedside_lockdown_left", endpoint_group_key="bedtime_tplink"),
                    tplink_state("A14", "tplink:plug.bedside_lockdown_right", endpoint_group_key="bedtime_tplink"),
                    hue_state("A15", "hue:bridge_1:hallway_group_lockdown", file_rel="hue/v2/group.py"),
                ],
            },
            writebacks={
                "ble": write_action("A16", "sensor.vdev_bedtime_lockdown_routine_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A17", "sensor.vdev_bedtime_lockdown_routine_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A18", "sensor.vdev_bedtime_lockdown_routine_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A19", "sensor.vdev_bedtime_lockdown_routine_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs(
                {"ble": [{"action_id": f"A{i}"} for i in range(1, 7)]}
            ),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_rain_coming_indoor_adjustment_01",
            name="Rain-Coming Indoor Adjustment",
            group=context_group,
            story="When rain starts, the routine checks window-side curtains, nearby lights, indoor climate, air quality, and one comfort thermostat to publish a rainy-day indoor adjustment suggestion.",
            strengths=[
                "Weather trigger is natural but still uses only existing benchmark action families.",
                "Balanced mixed case with modest BLE, cloud, and local work.",
                "MQTT air quality keeps the local lane grounded in a real monitoring source.",
            ],
            focus_areas=[
                "Cloud light plus climate grouping",
                "BLE curtain refresh ordering under a short weather corridor",
                "Local Hue and MQTT reads should stay cheap",
                "Overall recommendation should depend only on lane summaries",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_window_left_rain"),
                    switchbot_cover("A2", "ble:switchbot:curtain_window_right_rain"),
                    xiaomi_sensor("A3", "ble:xiaomi_ble:temp_sensor_window_rain"),
                ],
                "cloud": [
                    tuya_status("A4", "tuya:light.window_accent_left.status", domain="light", endpoint_group_key="rain_window_lights"),
                    tuya_status("A5", "tuya:light.window_accent_right.status", domain="light", endpoint_group_key="rain_window_lights"),
                    tuya_status("A6", "tuya:climate.window_room.status", domain="climate", endpoint_group_key="rain_window_hvac"),
                    ecobee_runtime("A7", "ecobee:thermostat.rain_home_1", endpoint_group_key="rain_window_ecobee"),
                ],
                "local": [
                    hue_state("A8", "hue:bridge_1:window_light_left"),
                    hue_state("A9", "hue:bridge_1:window_light_right"),
                    mqtt_last("A10", "mqtt:air_quality_node_window_side"),
                ],
            },
            writebacks={
                "ble": write_action("A11", "sensor.vdev_rain_coming_indoor_adjustment_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A12", "sensor.vdev_rain_coming_indoor_adjustment_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A13", "sensor.vdev_rain_coming_indoor_adjustment_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A14", "sensor.vdev_rain_coming_indoor_adjustment_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": "A1"}, {"action_id": "A2"}, {"action_id": "A3"}]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_weekend_whole_home_snapshot_extended_01",
            name="Weekend Whole-Home Snapshot Extended",
            group=survey_group,
            story="On a weekend morning, the routine produces a larger whole-home snapshot of curtains, temperatures, air quality, lights, plugs, and climate to give the household a quick status overview.",
            strengths=[
                "Larger mixed baseline than the original weekend snapshot.",
                "Contains BLE connect plus subscribe in addition to many read actions.",
                "Includes local plugs, MQTT power, and multiple cloud buckets in one survey.",
            ],
            focus_areas=[
                "Large mixed-lane batching and overlap",
                "BLE transport setup inside a long read-heavy corridor",
                "Local lane should stay cheap despite more devices",
                "Whole-home summary should remain lane-first then overall",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_living_weekend_ext"),
                    switchbot_cover("A2", "ble:switchbot:curtain_master_weekend_ext"),
                    switchbot_cover("A3", "ble:switchbot:curtain_study_weekend_ext"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:temp_sensor_living_weekend_ext"),
                    xiaomi_sensor("A5", "ble:xiaomi_ble:temp_sensor_bedroom_weekend_ext"),
                    xiaomi_sensor("A6", "ble:xiaomi_ble:temp_sensor_study_weekend_ext"),
                    esphome_connect("A7", "ble:esphome:air_node_weekend_ext"),
                    esphome_subscribe("A8", "ble:esphome:relay_node_weekend_ext"),
                ],
                "cloud": [
                    tuya_status("A9", "tuya:light.living_weekend_ext.status", domain="light", endpoint_group_key="weekend_ext_lights"),
                    tuya_status("A10", "tuya:light.hallway_weekend_ext.status", domain="light", endpoint_group_key="weekend_ext_lights"),
                    tuya_status("A11", "tuya:light.study_weekend_ext.status", domain="light", endpoint_group_key="weekend_ext_lights"),
                    tuya_status("A12", "tuya:climate.master_weekend_ext.status", domain="climate", endpoint_group_key="weekend_ext_hvac"),
                    tuya_status("A13", "tuya:climate.guest_weekend_ext.status", domain="climate", endpoint_group_key="weekend_ext_hvac"),
                    tuya_status("A14", "tuya:switch.energy_strip_weekend_ext_1.status", domain="switch", endpoint_group_key="weekend_ext_energy"),
                    tuya_status("A15", "tuya:switch.energy_strip_weekend_ext_2.status", domain="switch", endpoint_group_key="weekend_ext_energy"),
                ],
                "local": [
                    hue_state("A16", "hue:bridge_1:living_group_weekend_ext", file_rel="hue/v2/group.py"),
                    hue_state("A17", "hue:bridge_1:bedroom_group_weekend_ext", file_rel="hue/v2/group.py"),
                    tplink_state("A18", "tplink:plug.server_corner_weekend_ext", endpoint_group_key="weekend_ext_tplink"),
                    tplink_state("A19", "tplink:plug.media_corner_weekend_ext", endpoint_group_key="weekend_ext_tplink"),
                    mqtt_last("A20", "mqtt:power_meter_whole_home_weekend_ext"),
                ],
            },
            writebacks={
                "ble": write_action("A21", "sensor.vdev_weekend_whole_home_snapshot_extended_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A22", "sensor.vdev_weekend_whole_home_snapshot_extended_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A23", "sensor.vdev_weekend_whole_home_snapshot_extended_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A24", "sensor.vdev_weekend_whole_home_snapshot_extended_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            connect_before_subscribe=[("A7", "A8")],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": f"A{i}"} for i in range(1, 9)]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_dinner_preparation_readiness_01",
            name="Dinner Preparation Readiness",
            group=comfort_group,
            story="Before dinner, the routine checks dining lights, kitchen lights, dining climate, a kitchen plug, curtains, and indoor air quality to decide whether dinner mode is ready.",
            strengths=[
                "Natural dinner scenario with modest but meaningful three-lane work.",
                "Cloud lane has enough lights to exercise batching.",
                "MQTT power and one plug keep the local lane realistic.",
            ],
            focus_areas=[
                "Cloud light burst batching",
                "BLE read ordering under a shorter evening routine",
                "Local API plus MQTT should stay cheap",
                "Writeback chain should remain short and explicit",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_dining_prep"),
                    xiaomi_sensor("A2", "ble:xiaomi_ble:motion_sensor_kitchen_prep", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A3", "ble:xiaomi_ble:temp_sensor_dining_prep"),
                ],
                "cloud": [
                    tuya_status("A4", "tuya:light.dining_main_prep.status", domain="light", endpoint_group_key="dinner_prep_lights"),
                    tuya_status("A5", "tuya:light.kitchen_main_prep.status", domain="light", endpoint_group_key="dinner_prep_lights"),
                    tuya_status("A6", "tuya:light.kitchen_counter_prep.status", domain="light", endpoint_group_key="dinner_prep_lights"),
                    tuya_status("A7", "tuya:climate.dining_prep.status", domain="climate", endpoint_group_key="dinner_prep_hvac"),
                    tuya_status("A8", "tuya:switch.kitchen_strip_prep.status", domain="switch", endpoint_group_key="dinner_prep_switches"),
                ],
                "local": [
                    hue_state("A9", "hue:bridge_1:dining_group_prep", file_rel="hue/v2/group.py"),
                    tplink_state("A10", "tplink:plug.rice_cooker_prep", endpoint_group_key="dinner_prep_tplink"),
                    mqtt_last("A11", "mqtt:kitchen_power_meter_prep"),
                ],
            },
            writebacks={
                "ble": write_action("A12", "sensor.vdev_dinner_preparation_readiness_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A13", "sensor.vdev_dinner_preparation_readiness_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A14", "sensor.vdev_dinner_preparation_readiness_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A15", "sensor.vdev_dinner_preparation_readiness_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": "A1"}, {"action_id": "A2"}, {"action_id": "A3"}]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_party_preparation_ambience_check_01",
            name="Party Preparation and Ambience Check",
            group=comfort_group,
            story="Before a gathering, the routine checks room lights, color ambience, curtains, climate, speaker plugs, and purifier state to decide whether the party setup is ready.",
            strengths=[
                "Local Hue lane is intentionally larger than many other cases.",
                "BLE lane is short but semantically meaningful.",
                "Cloud lane mixes lights, switches, and climate in one ambience routine.",
            ],
            focus_areas=[
                "Local API lane should remain cheap even with several lights",
                "Cloud burst across lights and switches",
                "Short BLE lane should not dominate overall latency",
                "Lane summaries should stay clean and easy to reason about",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_party_left"),
                    switchbot_cover("A2", "ble:switchbot:curtain_party_right"),
                    switchbot_status("A3", "ble:switchbot:air_purifier_party", domain="fan", file_rel="switchbot/fan.py"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:motion_sensor_party", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                ],
                "cloud": [
                    tuya_status("A5", "tuya:light.party_main_1.status", domain="light", endpoint_group_key="party_ambience_lights"),
                    tuya_status("A6", "tuya:light.party_main_2.status", domain="light", endpoint_group_key="party_ambience_lights"),
                    tuya_status("A7", "tuya:light.party_aux.status", domain="light", endpoint_group_key="party_ambience_lights"),
                    tuya_status("A8", "tuya:switch.party_speakers.status", domain="switch", endpoint_group_key="party_ambience_switches"),
                    tuya_status("A9", "tuya:switch.party_tv.status", domain="switch", endpoint_group_key="party_ambience_switches"),
                    tuya_status("A10", "tuya:climate.party_room.status", domain="climate", endpoint_group_key="party_ambience_hvac"),
                ],
                "local": [
                    hue_state("A11", "hue:bridge_1:party_room_light_1"),
                    hue_state("A12", "hue:bridge_1:party_room_light_2"),
                    hue_state("A13", "hue:bridge_1:party_room_light_3"),
                    hue_state("A14", "hue:bridge_1:party_room_light_4"),
                ],
            },
            writebacks={
                "ble": write_action("A15", "sensor.vdev_party_preparation_ambience_check_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A16", "sensor.vdev_party_preparation_ambience_check_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A17", "sensor.vdev_party_preparation_ambience_check_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A18", "sensor.vdev_party_preparation_ambience_check_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": f"A{i}"} for i in range(1, 5)]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_workday_departure_office_zone_shutdown_01",
            name="Workday Departure Office-Zone Shutdown",
            group=morning_group,
            story="After leaving for work, the routine does one compact office-zone sweep across curtains, desk lights, monitor plugs, printer plug, and study climate.",
            strengths=[
                "Small but realistic mixed routine rather than a synthetic toy.",
                "Good lower-bound case for the scheduler on short mixed workloads.",
                "Lets the benchmark suite include a believable office-only zone routine.",
            ],
            focus_areas=[
                "Small mixed-case overheads should remain low",
                "Local API should stay cheap",
                "Cloud lane should not dominate a compact routine",
                "Short writeback tail should stay intact",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_study_departure"),
                    xiaomi_sensor("A2", "ble:xiaomi_ble:temp_sensor_study_departure"),
                ],
                "cloud": [
                    tuya_status("A3", "tuya:switch.printer_departure.status", domain="switch", endpoint_group_key="office_departure_switches"),
                    tuya_status("A4", "tuya:climate.study_departure.status", domain="climate", endpoint_group_key="office_departure_hvac"),
                ],
                "local": [
                    tplink_state("A5", "tplink:plug.desk_lamp_departure", endpoint_group_key="office_departure_tplink"),
                    tplink_state("A6", "tplink:plug.monitor_departure", endpoint_group_key="office_departure_tplink"),
                    hue_state("A7", "hue:bridge_1:desk_light_left_departure"),
                    hue_state("A8", "hue:bridge_1:desk_light_right_departure"),
                ],
            },
            writebacks={
                "ble": write_action("A9", "sensor.vdev_workday_departure_office_zone_shutdown_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A10", "sensor.vdev_workday_departure_office_zone_shutdown_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A11", "sensor.vdev_workday_departure_office_zone_shutdown_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A12", "sensor.vdev_workday_departure_office_zone_shutdown_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": "A1"}, {"action_id": "A2"}]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_kids_room_comfort_safety_snapshot_01",
            name="Kids' Room Comfort and Safety Snapshot",
            group=family_group,
            story="Parents trigger a quick children’s-room snapshot covering temperature, lights, curtains, climate, door or window safety, and air quality.",
            strengths=[
                "Lightweight room-level case with a very understandable story.",
                "BLE lane is read-heavy and appropriate for child-room monitoring.",
                "MQTT keeps local monitoring realistic without making the case synthetic.",
            ],
            focus_areas=[
                "BLE read-heavy scheduling",
                "Cloud and local lanes should remain inexpensive",
                "Cheap local plus MQTT behavior",
                "Conservative but short writeback chain",
            ],
            lanes={
                "ble": [
                    xiaomi_sensor("A1", "ble:xiaomi_ble:temp_sensor_kids_left"),
                    xiaomi_sensor("A2", "ble:xiaomi_ble:temp_sensor_kids_right"),
                    xiaomi_sensor("A3", "ble:xiaomi_ble:door_sensor_kids_window", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:window_sensor_kids_balcony", domain="event", file_rel="xiaomi_ble/event.py"),
                    switchbot_cover("A5", "ble:switchbot:curtain_kids_room"),
                ],
                "cloud": [
                    tuya_status("A6", "tuya:climate.kids_room.status", domain="climate", endpoint_group_key="kids_room_hvac"),
                    tuya_status("A7", "tuya:light.kids_room.status", domain="light", endpoint_group_key="kids_room_lights"),
                ],
                "local": [
                    hue_state("A8", "hue:bridge_1:kids_room_light_left"),
                    hue_state("A9", "hue:bridge_1:kids_room_light_right"),
                    mqtt_last("A10", "mqtt:air_quality_node_kids_room"),
                ],
            },
            writebacks={
                "ble": write_action("A11", "sensor.vdev_kids_room_comfort_safety_snapshot_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A12", "sensor.vdev_kids_room_comfort_safety_snapshot_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A13", "sensor.vdev_kids_room_comfort_safety_snapshot_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A14", "sensor.vdev_kids_room_comfort_safety_snapshot_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": f"A{i}"} for i in range(1, 6)]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_elderly_care_daily_check_01",
            name="Elderly Care Daily Check",
            group=family_group,
            story="At a fixed time each day, the system checks one elder room’s climate, lighting, temperature, curtain, motion, and air quality state and writes a care-oriented daily summary.",
            strengths=[
                "Strong real-world care narrative makes the benchmark easy to interpret.",
                "Balanced across BLE, cloud, local, and MQTT without being oversized.",
                "Still uses the current action vocabulary, so it stays compatible with the suite.",
            ],
            focus_areas=[
                "BLE sensor plus curtain ordering",
                "Cloud plus local comfort checks",
                "Cheap MQTT and local reads should remain cheap",
                "Conservative daily-summary writeback structure",
            ],
            lanes={
                "ble": [
                    xiaomi_sensor("A1", "ble:xiaomi_ble:motion_sensor_elder_room", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A2", "ble:xiaomi_ble:temp_sensor_elder_room"),
                    switchbot_cover("A3", "ble:switchbot:curtain_elder_room"),
                ],
                "cloud": [
                    ecobee_runtime("A4", "ecobee:thermostat.elder_room", endpoint_group_key="elder_room_ecobee"),
                    tuya_status("A5", "tuya:light.elder_room.status", domain="light", endpoint_group_key="elder_room_lights"),
                    tuya_status("A6", "tuya:switch.elder_room_heater.status", domain="switch", endpoint_group_key="elder_room_switches"),
                ],
                "local": [
                    hue_state("A7", "hue:bridge_1:elder_bedside_left"),
                    hue_state("A8", "hue:bridge_1:elder_bedside_right"),
                    mqtt_last("A9", "mqtt:air_quality_node_elder_room"),
                ],
            },
            writebacks={
                "ble": write_action("A10", "sensor.vdev_elderly_care_daily_check_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A11", "sensor.vdev_elderly_care_daily_check_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A12", "sensor.vdev_elderly_care_daily_check_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A13", "sensor.vdev_elderly_care_daily_check_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": "A1"}, {"action_id": "A2"}, {"action_id": "A3"}]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_laundry_utility_room_sweep_01",
            name="Laundry and Utility Room Sweep",
            group=family_group,
            story="On a utility-room schedule, the system checks washer and dryer plugs, ventilation, light, door sensor, and temperature to produce one laundry-area health summary.",
            strengths=[
                "Practical room-level monitoring case with one small BLE lane.",
                "Good fit for local plugs and one MQTT-style utility metric if needed later.",
                "Compact enough to catch small-schedule overheads.",
            ],
            focus_areas=[
                "Small mixed-case scheduling overhead",
                "Local plug checks should stay cheap",
                "Cloud vent and utility light should not dominate",
                "Summary writeback should stay compact",
            ],
            lanes={
                "ble": [
                    xiaomi_sensor("A1", "ble:xiaomi_ble:temp_sensor_utility_room"),
                    xiaomi_sensor("A2", "ble:xiaomi_ble:door_sensor_utility_room", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                ],
                "cloud": [
                    tuya_status("A3", "tuya:switch.utility_vent.status", domain="switch", endpoint_group_key="utility_room_switches"),
                    tuya_status("A4", "tuya:light.utility_room.status", domain="light", endpoint_group_key="utility_room_lights"),
                ],
                "local": [
                    tplink_state("A5", "tplink:plug.washer_utility", endpoint_group_key="utility_room_tplink"),
                    tplink_state("A6", "tplink:plug.dryer_utility", endpoint_group_key="utility_room_tplink"),
                    mqtt_last("A7", "mqtt:utility_power_meter"),
                ],
            },
            writebacks={
                "ble": write_action("A8", "sensor.vdev_laundry_utility_room_sweep_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A9", "sensor.vdev_laundry_utility_room_sweep_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A10", "sensor.vdev_laundry_utility_room_sweep_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A11", "sensor.vdev_laundry_utility_room_sweep_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": "A1"}, {"action_id": "A2"}]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_air_quality_recovery_routine_01",
            name="Air Quality Recovery Routine",
            group=family_group,
            story="After indoor air quality drops, the routine checks purifier state, nearby temperature, climate, switches, lights, and air-quality feeds to decide whether recovery is progressing normally.",
            strengths=[
                "Good case for local and MQTT lanes being treated as cheap.",
                "BLE lane is small but semantically strong.",
                "Cloud lane mixes climate and switches without becoming synthetic.",
            ],
            focus_areas=[
                "MQTT and local-lane cheapness",
                "Cloud climate plus switch grouping",
                "Short BLE lane should not dominate",
                "Conservative summary writeback after one recovery sweep",
            ],
            lanes={
                "ble": [
                    switchbot_status("A1", "ble:switchbot:air_purifier_recovery", domain="fan", file_rel="switchbot/fan.py"),
                    xiaomi_sensor("A2", "ble:xiaomi_ble:temp_sensor_recovery_zone"),
                ],
                "cloud": [
                    tuya_status("A3", "tuya:climate.recovery_zone.status", domain="climate", endpoint_group_key="air_recovery_hvac"),
                    tuya_status("A4", "tuya:switch.recovery_fan.status", domain="switch", endpoint_group_key="air_recovery_switches"),
                    tuya_status("A5", "tuya:switch.recovery_window_actuator.status", domain="switch", endpoint_group_key="air_recovery_switches"),
                ],
                "local": [
                    hue_state("A6", "hue:bridge_1:recovery_zone_light_left"),
                    hue_state("A7", "hue:bridge_1:recovery_zone_light_right"),
                    mqtt_last("A8", "mqtt:air_quality_node_recovery_1"),
                    mqtt_last("A9", "mqtt:air_quality_node_recovery_2"),
                ],
            },
            writebacks={
                "ble": write_action("A10", "sensor.vdev_air_quality_recovery_routine_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A11", "sensor.vdev_air_quality_recovery_routine_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A12", "sensor.vdev_air_quality_recovery_routine_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A13", "sensor.vdev_air_quality_recovery_routine_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": "A1"}, {"action_id": "A2"}]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_vacation_mode_house_sweep_01",
            name="Vacation-Mode House Sweep",
            group=survey_group,
            story="Before a longer trip, the routine runs one final whole-home sweep across curtains, sensors, lights, plugs, climate, and thermostat runtime to validate vacation-mode readiness.",
            strengths=[
                "Large realistic stress case rather than a synthetic transport-only stress.",
                "Contains enough devices to expose batching and long-tail issues.",
                "Still keeps a very understandable household routine story.",
            ],
            focus_areas=[
                "Large mixed-lane batching and aggregation",
                "Long BLE sweep ordering",
                "Cloud grouping across multiple resource families",
                "Local groups and plugs should stay cheaper than cloud",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_living_vacation"),
                    switchbot_cover("A2", "ble:switchbot:curtain_master_vacation"),
                    switchbot_cover("A3", "ble:switchbot:curtain_study_vacation"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:door_sensor_entry_vacation", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A5", "ble:xiaomi_ble:window_sensor_kitchen_vacation", domain="event", file_rel="xiaomi_ble/event.py"),
                    xiaomi_sensor("A6", "ble:xiaomi_ble:window_sensor_bedroom_vacation", domain="event", file_rel="xiaomi_ble/event.py"),
                    xiaomi_sensor("A7", "ble:xiaomi_ble:temp_sensor_living_vacation"),
                    xiaomi_sensor("A8", "ble:xiaomi_ble:temp_sensor_study_vacation"),
                ],
                "cloud": [
                    tuya_status("A9", "tuya:light.living_vacation.status", domain="light", endpoint_group_key="vacation_lights"),
                    tuya_status("A10", "tuya:light.hallway_vacation.status", domain="light", endpoint_group_key="vacation_lights"),
                    tuya_status("A11", "tuya:light.bedroom_vacation.status", domain="light", endpoint_group_key="vacation_lights"),
                    tuya_status("A12", "tuya:switch.tv_vacation.status", domain="switch", endpoint_group_key="vacation_switches"),
                    tuya_status("A13", "tuya:switch.kitchen_vacation.status", domain="switch", endpoint_group_key="vacation_switches"),
                    tuya_status("A14", "tuya:switch.study_vacation.status", domain="switch", endpoint_group_key="vacation_switches"),
                    tuya_status("A15", "tuya:climate.master_vacation.status", domain="climate", endpoint_group_key="vacation_hvac"),
                    tuya_status("A16", "tuya:climate.guest_vacation.status", domain="climate", endpoint_group_key="vacation_hvac"),
                    ecobee_runtime("A17", "ecobee:thermostat.vacation_home_1", endpoint_group_key="vacation_ecobee"),
                ],
                "local": [
                    hue_state("A18", "hue:bridge_1:living_group_vacation", file_rel="hue/v2/group.py"),
                    hue_state("A19", "hue:bridge_1:bedroom_group_vacation", file_rel="hue/v2/group.py"),
                    tplink_state("A20", "tplink:plug.router_backup_vacation", endpoint_group_key="vacation_tplink"),
                    tplink_state("A21", "tplink:plug.media_backup_vacation", endpoint_group_key="vacation_tplink"),
                ],
            },
            writebacks={
                "ble": write_action("A22", "sensor.vdev_vacation_mode_house_sweep_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A23", "sensor.vdev_vacation_mode_house_sweep_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A24", "sensor.vdev_vacation_mode_house_sweep_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A25", "sensor.vdev_vacation_mode_house_sweep_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": f"A{i}"} for i in range(1, 9)]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_homecoming_security_ambience_merge_01",
            name="Homecoming Security and Ambience Merge",
            group=control_group,
            story="At arrival time, the routine merges a small security reassurance sweep with lighting and comfort checks to decide whether the home is ready for a safe, pleasant arrival.",
            strengths=[
                "Good merged arrival scenario rather than a synthetic cross-lane blend.",
                "Cloud climate and ecobee runtime naturally sit beside entry lighting.",
                "Smaller mixed case is useful as a medium-complexity benchmark.",
            ],
            focus_areas=[
                "Mixed arrival semantics with a short BLE lane",
                "Cloud comfort checks should batch cleanly",
                "Hue entry lights should remain cheap",
                "Overall summary should stay short and explainable",
            ],
            lanes={
                "ble": [
                    xiaomi_sensor("A1", "ble:xiaomi_ble:motion_sensor_homecoming", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    switchbot_cover("A2", "ble:switchbot:curtain_entry_homecoming"),
                ],
                "cloud": [
                    tuya_status("A3", "tuya:light.entry_homecoming.status", domain="light", endpoint_group_key="homecoming_lights"),
                    tuya_status("A4", "tuya:light.hallway_homecoming.status", domain="light", endpoint_group_key="homecoming_lights"),
                    tuya_status("A5", "tuya:climate.living_homecoming.status", domain="climate", endpoint_group_key="homecoming_hvac"),
                    ecobee_runtime("A6", "ecobee:thermostat.homecoming_1", endpoint_group_key="homecoming_ecobee"),
                ],
                "local": [
                    hue_state("A7", "hue:bridge_1:entry_light_homecoming"),
                    hue_state("A8", "hue:bridge_1:hallway_light_left_homecoming"),
                    hue_state("A9", "hue:bridge_1:hallway_light_right_homecoming"),
                ],
            },
            writebacks={
                "ble": write_action("A10", "sensor.vdev_homecoming_security_ambience_merge_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A11", "sensor.vdev_homecoming_security_ambience_merge_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A12", "sensor.vdev_homecoming_security_ambience_merge_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A13", "sensor.vdev_homecoming_security_ambience_merge_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": "A1"}, {"action_id": "A2"}]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_school_night_quiet_hours_01",
            name="School-Night Quiet Hours Routine",
            group=monitoring_group,
            story="At a fixed school-night quiet-hours time, the routine checks curtains, bedside lights, hallway lights, heater plug, window state, and climate to confirm the house is in a quieter night state.",
            strengths=[
                "Natural bedtime variant with a slightly different device mix.",
                "Includes both local lights and one local heater plug.",
                "Mid-sized case with easy-to-understand semantics.",
            ],
            focus_areas=[
                "Mid-sized night routine scheduling",
                "BLE lamps and curtain ordering",
                "Cloud and local checks should remain compact",
                "Conservative writeback tail",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_school_night_left"),
                    switchbot_cover("A2", "ble:switchbot:curtain_school_night_right"),
                    xiaomi_status("A3", "ble:xiaomi_ble:bedside_lamp_school_night_left", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_status("A4", "ble:xiaomi_ble:bedside_lamp_school_night_right", domain="device", file_rel="xiaomi_ble/device.py"),
                    xiaomi_sensor("A5", "ble:xiaomi_ble:window_sensor_school_night", domain="event", file_rel="xiaomi_ble/event.py"),
                ],
                "cloud": [
                    tuya_status("A6", "tuya:climate.school_night.status", domain="climate", endpoint_group_key="school_night_hvac"),
                    tuya_status("A7", "tuya:switch.school_night_heater.status", domain="switch", endpoint_group_key="school_night_switches"),
                    tuya_status("A8", "tuya:light.school_night_room.status", domain="light", endpoint_group_key="school_night_lights"),
                ],
                "local": [
                    hue_state("A9", "hue:bridge_1:hallway_school_night_left"),
                    hue_state("A10", "hue:bridge_1:hallway_school_night_right"),
                    tplink_state("A11", "tplink:plug.heater_school_night", endpoint_group_key="school_night_tplink"),
                ],
            },
            writebacks={
                "ble": write_action("A12", "sensor.vdev_school_night_quiet_hours_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A13", "sensor.vdev_school_night_quiet_hours_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A14", "sensor.vdev_school_night_quiet_hours_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A15", "sensor.vdev_school_night_quiet_hours_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": f"A{i}"} for i in range(1, 6)]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_rainy_commute_preparation_01",
            name="Rainy Commute Preparation",
            group=context_group,
            story="When rain overlaps with the morning commute window, the routine checks entry lights, curtain, door state, and a small comfort set to decide whether rainy-commute preparation is needed.",
            strengths=[
                "Small weather-triggered case with a strong story.",
                "Good for observing scheduler overhead on short mixed routines.",
                "Uses only current benchmark action families and integrations.",
            ],
            focus_areas=[
                "Small mixed-case scheduling overhead",
                "BLE lane should remain inexpensive",
                "Cloud and local entry lighting should not over-serialize",
                "Short overall summary path",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_entry_commute_rain"),
                    xiaomi_sensor("A2", "ble:xiaomi_ble:door_sensor_commute_rain", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                ],
                "cloud": [
                    tuya_status("A3", "tuya:climate.entry_commute_rain.status", domain="climate", endpoint_group_key="commute_rain_hvac"),
                    tuya_status("A4", "tuya:light.entry_commute_rain.status", domain="light", endpoint_group_key="commute_rain_lights"),
                ],
                "local": [
                    hue_state("A5", "hue:bridge_1:entry_commute_rain_left"),
                    hue_state("A6", "hue:bridge_1:entry_commute_rain_right"),
                ],
            },
            writebacks={
                "ble": write_action("A7", "sensor.vdev_rainy_commute_preparation_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "cloud": write_action("A8", "sensor.vdev_rainy_commute_preparation_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A9", "sensor.vdev_rainy_commute_preparation_local_lane", file_rel="hue/v2/light.py", integration="hue"),
                "overall": write_action("A10", "sensor.vdev_rainy_commute_preparation_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE", "CLOUD", "LOCAL"],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": "A1"}, {"action_id": "A2"}]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_energy_hvac_audit_expanded_01",
            name="Energy and HVAC Audit Expanded",
            group=survey_group,
            story="At a fixed audit time, the routine collects whole-home lights, plugs, climates, thermostats, and two local smart-plug checks to produce one expanded energy and HVAC audit.",
            strengths=[
                "Cloud-heavy case with a little local confirmation mixed in.",
                "Good benchmark for cross-provider cloud parallelism plus a small local tail.",
                "Larger than the original cloud audit while staying very realistic.",
            ],
            focus_areas=[
                "Tuya bucket grouping across lights, switches, and climates",
                "Cross-provider Ecobee overlap",
                "Local plug checks should stay cheap",
                "Cloud and local writeback chain should remain short",
            ],
            lanes={
                "cloud": [
                    tuya_status("A1", "tuya:light.energy_audit_1.status", domain="light", endpoint_group_key="energy_expanded_lights"),
                    tuya_status("A2", "tuya:light.energy_audit_2.status", domain="light", endpoint_group_key="energy_expanded_lights"),
                    tuya_status("A3", "tuya:light.energy_audit_3.status", domain="light", endpoint_group_key="energy_expanded_lights"),
                    tuya_status("A4", "tuya:switch.energy_audit_1.status", domain="switch", endpoint_group_key="energy_expanded_switches"),
                    tuya_status("A5", "tuya:switch.energy_audit_2.status", domain="switch", endpoint_group_key="energy_expanded_switches"),
                    tuya_status("A6", "tuya:switch.energy_audit_3.status", domain="switch", endpoint_group_key="energy_expanded_switches"),
                    tuya_status("A7", "tuya:climate.energy_audit_master.status", domain="climate", endpoint_group_key="energy_expanded_hvac"),
                    tuya_status("A8", "tuya:climate.energy_audit_guest.status", domain="climate", endpoint_group_key="energy_expanded_hvac"),
                    ecobee_runtime("A9", "ecobee:thermostat.energy_audit_1", endpoint_group_key="energy_expanded_ecobee"),
                    ecobee_runtime("A10", "ecobee:thermostat.energy_audit_2", endpoint_group_key="energy_expanded_ecobee"),
                ],
                "local": [
                    tplink_state("A11", "tplink:plug.energy_audit_local_1", endpoint_group_key="energy_expanded_tplink"),
                    tplink_state("A12", "tplink:plug.energy_audit_local_2", endpoint_group_key="energy_expanded_tplink"),
                ],
            },
            writebacks={
                "cloud": write_action("A13", "sensor.vdev_energy_hvac_audit_expanded_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "local": write_action("A14", "sensor.vdev_energy_hvac_audit_expanded_local_lane", file_rel="tplink/entity.py", integration="tplink"),
                "overall": write_action("A15", "sensor.vdev_energy_hvac_audit_expanded_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["CLOUD", "LOCAL"],
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_whole_home_ble_safety_sweep_01",
            name="Whole-Home BLE Safety Sweep",
            group=stress_group,
            story="At a fixed time, the routine performs one realistic whole-home BLE sweep over curtains, door or window sensors, motion sensors, temperatures, and one ESPHome transport pair.",
            strengths=[
                "BLE-heavy case is realistic rather than purely synthetic.",
                "Includes both status-style reads and a connect plus subscribe pair.",
                "Useful upper-bound case for BLE lane conservatism and future micro refinements.",
            ],
            focus_areas=[
                "BLE corridor length and min-gap behavior",
                "Connect-before-subscribe under a larger BLE sweep",
                "Avoiding hidden lane inflation from non-BLE work",
                "Very short writeback tail after a long BLE lane",
            ],
            lanes={
                "ble": [
                    switchbot_cover("A1", "ble:switchbot:curtain_ble_sweep_living"),
                    switchbot_cover("A2", "ble:switchbot:curtain_ble_sweep_master"),
                    switchbot_cover("A3", "ble:switchbot:curtain_ble_sweep_study"),
                    xiaomi_sensor("A4", "ble:xiaomi_ble:door_sensor_ble_sweep_entry", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A5", "ble:xiaomi_ble:window_sensor_ble_sweep_kitchen", domain="event", file_rel="xiaomi_ble/event.py"),
                    xiaomi_sensor("A6", "ble:xiaomi_ble:window_sensor_ble_sweep_bedroom", domain="event", file_rel="xiaomi_ble/event.py"),
                    xiaomi_sensor("A7", "ble:xiaomi_ble:door_sensor_ble_sweep_balcony", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A8", "ble:xiaomi_ble:motion_sensor_ble_sweep_living", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A9", "ble:xiaomi_ble:motion_sensor_ble_sweep_hall", domain="binary_sensor", file_rel="xiaomi_ble/binary_sensor.py"),
                    xiaomi_sensor("A10", "ble:xiaomi_ble:temp_sensor_ble_sweep_1"),
                    xiaomi_sensor("A11", "ble:xiaomi_ble:temp_sensor_ble_sweep_2"),
                    esphome_connect("A12", "ble:esphome:air_node_ble_sweep"),
                    esphome_subscribe("A13", "ble:esphome:relay_node_ble_sweep"),
                ],
            },
            writebacks={
                "ble": write_action("A14", "sensor.vdev_whole_home_ble_safety_sweep_ble_lane", file_rel="switchbot/fan.py", integration="switchbot"),
                "overall": write_action("A15", "sensor.vdev_whole_home_ble_safety_sweep_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["BLE"],
            connect_before_subscribe=[("A12", "A13")],
            ble_soft_pairs=soft_ble_pairs({"ble": [{"action_id": f"A{i}"} for i in range(1, 14)]}),
        )
    )

    cases.append(
        case_target(
            vdev_id="vdev_cloud_burst_living_conditions_snapshot_01",
            name="Cloud Burst Living-Conditions Snapshot",
            group=survey_group,
            story="At a scheduled mode-change checkpoint, the routine bursts through lighting, switch, and HVAC endpoints to build one cloud-only living-conditions snapshot.",
            strengths=[
                "Pure cloud burst case without synthetic protocol noise.",
                "Useful for testing same-provider Tuya batching plus Ecobee overlap.",
                "Small writeback chain keeps the final observable semantics easy to review.",
            ],
            focus_areas=[
                "Tuya batching on a larger cloud burst",
                "Cross-provider cloud parallelism",
                "Host grouping and session reuse",
                "Short cloud-lane to overall writeback chain",
            ],
            lanes={
                "cloud": [
                    tuya_status("A1", "tuya:light.cloud_snapshot_1.status", domain="light", endpoint_group_key="cloud_snapshot_lights"),
                    tuya_status("A2", "tuya:light.cloud_snapshot_2.status", domain="light", endpoint_group_key="cloud_snapshot_lights"),
                    tuya_status("A3", "tuya:light.cloud_snapshot_3.status", domain="light", endpoint_group_key="cloud_snapshot_lights"),
                    tuya_status("A4", "tuya:light.cloud_snapshot_4.status", domain="light", endpoint_group_key="cloud_snapshot_lights"),
                    tuya_status("A5", "tuya:switch.cloud_snapshot_1.status", domain="switch", endpoint_group_key="cloud_snapshot_switches"),
                    tuya_status("A6", "tuya:switch.cloud_snapshot_2.status", domain="switch", endpoint_group_key="cloud_snapshot_switches"),
                    tuya_status("A7", "tuya:switch.cloud_snapshot_3.status", domain="switch", endpoint_group_key="cloud_snapshot_switches"),
                    tuya_status("A8", "tuya:switch.cloud_snapshot_4.status", domain="switch", endpoint_group_key="cloud_snapshot_switches"),
                    tuya_status("A9", "tuya:climate.cloud_snapshot_1.status", domain="climate", endpoint_group_key="cloud_snapshot_hvac"),
                    tuya_status("A10", "tuya:climate.cloud_snapshot_2.status", domain="climate", endpoint_group_key="cloud_snapshot_hvac"),
                    ecobee_runtime("A11", "ecobee:thermostat.cloud_snapshot_1", endpoint_group_key="cloud_snapshot_ecobee"),
                    ecobee_runtime("A12", "ecobee:thermostat.cloud_snapshot_2", endpoint_group_key="cloud_snapshot_ecobee"),
                ],
            },
            writebacks={
                "cloud": write_action("A13", "sensor.vdev_cloud_burst_living_conditions_snapshot_cloud_lane", file_rel="tuya/entity.py", integration="tuya"),
                "overall": write_action("A14", "sensor.vdev_cloud_burst_living_conditions_snapshot_overall", file_rel="esphome/update.py", integration="esphome"),
            },
            mixed_source_protocols=["CLOUD"],
        )
    )

    return cases


def build_profile_coverage_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    morning_group = "Profile Coverage - Morning Routines"
    transition_group = "Profile Coverage - Arrival and Departure Routines"
    evening_group = "Profile Coverage - Evening and Overnight Routines"
    audit_group = "Profile Coverage - Monitoring and Audit Routines"
    stress_group = "Profile Coverage - Realistic Stress Routines"

    def case_slug(vdev_id: str) -> str:
        raw = vdev_id.removeprefix("vdev_")
        return "".join(ch if ch.isalnum() else "_" for ch in raw).strip("_").lower()

    def switchbot_cover(action_id: str, device_id: str) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="refresh_cover",
            file_rel="switchbot/cover.py",
            integration="switchbot",
            hints=BLE_STATUS_HINTS,
            domain="cover",
            action_type="refresh_cover",
        )

    def switchbot_status(action_id: str, device_id: str) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="read_status",
            file_rel="switchbot/fan.py",
            integration="switchbot",
            hints=BLE_STATUS_HINTS,
            domain="fan",
            action_type="read_status",
        )

    def xiaomi_sensor(action_id: str, device_id: str, *, domain: str = "sensor", file_rel: str = "xiaomi_ble/sensor.py") -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="read_sensor",
            file_rel=file_rel,
            integration="xiaomi_ble",
            hints=BLE_STATUS_HINTS,
            domain=domain,
            action_type="read_sensor",
        )

    def xiaomi_status(action_id: str, device_id: str) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="read_status",
            file_rel="xiaomi_ble/device.py",
            integration="xiaomi_ble",
            hints=BLE_STATUS_HINTS,
            domain="device",
            action_type="read_status",
        )

    def ble_sensor(action_id: str, integration: str, device_id: str, *, domain: str = "sensor", file_rel: str | None = None) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="read_sensor",
            file_rel=file_rel or f"{integration}/sensor.py",
            integration=integration,
            hints=BLE_STATUS_HINTS,
            domain=domain,
            action_type="read_sensor",
        )

    def esphome_connect(action_id: str, device_id: str) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="connect",
            file_rel="esphome/__init__.py",
            integration="esphome",
            hints=BLE_CONNECT_HINTS,
            domain="esphome",
            action_type="connect",
        )

    def esphome_subscribe(action_id: str, device_id: str) -> Dict[str, Any]:
        return ble_action(
            action_id,
            device_id,
            service="subscribe",
            file_rel="esphome/manager.py",
            integration="esphome",
            hints=BLE_SUBSCRIBE_HINTS,
            domain="manager",
            action_type="subscribe",
        )

    def local_state(action_id: str, endpoint: str, *, integration: str, file_rel: str, domain: str, provider: str, endpoint_group_key: str, host_group_key: str) -> Dict[str, Any]:
        return local_action(
            action_id,
            endpoint,
            service="get_state",
            file_rel=file_rel,
            integration=integration,
            domain=domain,
            marker_hints=LOCAL_API_HINTS,
            provider=provider,
            endpoint_group_key=endpoint_group_key,
            host_group_key=host_group_key,
            action_type="get_state",
        )

    def tuya_status(action_id: str, endpoint: str, *, domain: str, endpoint_group_key: str) -> Dict[str, Any]:
        return cloud_action(
            action_id,
            endpoint,
            service="status",
            file_rel={"light": "tuya/light.py", "switch": "tuya/switch.py", "climate": "tuya/climate.py"}[domain],
            integration="tuya",
            domain=domain,
            endpoint_group_key=endpoint_group_key,
            host_group_key="tuya",
            action_type="status",
        )

    def cloud_runtime(action_id: str, endpoint: str, *, integration: str, file_rel: str, domain: str, endpoint_group_key: str) -> Dict[str, Any]:
        return cloud_action(
            action_id,
            endpoint,
            service="read_runtime",
            file_rel=file_rel,
            integration=integration,
            domain=domain,
            provider=integration,
            endpoint_group_key=endpoint_group_key,
            host_group_key=integration,
            action_type="read_runtime",
            marker_hints=["CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"],
        )

    def make_ble_action(action_id: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        kind = str(spec["kind"])
        integration = str(spec.get("integration") or "switchbot")
        device_id = str(spec.get("device_id") or f"ble:{integration}:{spec['id']}")
        if kind == "switchbot_cover":
            return switchbot_cover(action_id, device_id)
        if kind == "switchbot_status":
            return switchbot_status(action_id, device_id)
        if kind == "xiaomi_sensor":
            return xiaomi_sensor(
                action_id,
                device_id,
                domain=str(spec.get("domain") or "sensor"),
                file_rel=str(spec.get("file_rel") or "xiaomi_ble/sensor.py"),
            )
        if kind == "xiaomi_status":
            return xiaomi_status(action_id, device_id)
        if kind == "ble_sensor":
            return ble_sensor(
                action_id,
                integration,
                device_id,
                domain=str(spec.get("domain") or "sensor"),
                file_rel=str(spec["file_rel"]) if spec.get("file_rel") else None,
            )
        if kind == "esphome_connect":
            return esphome_connect(action_id, device_id)
        if kind == "esphome_subscribe":
            return esphome_subscribe(action_id, device_id)
        raise ValueError(f"Unsupported BLE benchmark action kind: {kind}")

    def make_local_action(action_id: str, spec: Dict[str, Any], slug: str) -> Dict[str, Any]:
        integration = str(spec["integration"])
        defaults = {
            "hue": ("hue/v2/light.py", "light", "hue_local", "bridge_1", "hue_bridge_1"),
            "tplink": ("tplink/entity.py", "switch", "tplink_local", f"{slug}_tplink", "tplink_local"),
            "nanoleaf": ("nanoleaf/light.py", "light", "nanoleaf_local", f"{slug}_nanoleaf", "nanoleaf_local"),
            "philips_js": ("philips_js/media_player.py", "media_player", "philips_js_local", f"{slug}_philips_js", "philips_js_local"),
            "roku": ("roku/media_player.py", "media_player", "roku_local", f"{slug}_roku", "roku_local"),
            "denonavr": ("denonavr/media_player.py", "media_player", "denonavr_local", f"{slug}_denonavr", "denonavr_local"),
            "webostv": ("webostv/media_player.py", "media_player", "webostv_local", f"{slug}_webostv", "webostv_local"),
        }
        file_rel, domain, provider, endpoint_group_key, host_group_key = defaults[integration]
        endpoint = str(spec.get("endpoint") or f"{integration}:{spec['id']}")
        return local_state(
            action_id,
            endpoint,
            integration=integration,
            file_rel=str(spec.get("file_rel") or file_rel),
            domain=str(spec.get("domain") or domain),
            provider=str(spec.get("provider") or provider),
            endpoint_group_key=str(spec.get("endpoint_group_key") or endpoint_group_key),
            host_group_key=str(spec.get("host_group_key") or host_group_key),
        )

    def make_cloud_action(action_id: str, spec: Dict[str, Any], slug: str) -> Dict[str, Any]:
        integration = str(spec["integration"])
        if integration == "tuya":
            domain = str(spec["domain"])
            endpoint = str(spec.get("endpoint") or f"tuya:{domain}.{spec['id']}.status")
            return tuya_status(
                action_id,
                endpoint,
                domain=domain,
                endpoint_group_key=str(spec.get("endpoint_group_key") or f"{slug}_tuya_{domain}"),
            )
        defaults = {
            "ecobee": ("ecobee/climate.py", "climate"),
            "netatmo": ("netatmo/sensor.py", "sensor"),
            "smartthings": ("smartthings/entity.py", "sensor"),
            "blink": ("blink/sensor.py", "sensor"),
        }
        file_rel, domain = defaults[integration]
        endpoint = str(spec.get("endpoint") or f"{integration}:{spec['id']}")
        return cloud_runtime(
            action_id,
            endpoint,
            integration=integration,
            file_rel=str(spec.get("file_rel") or file_rel),
            domain=str(spec.get("domain") or domain),
            endpoint_group_key=str(spec.get("endpoint_group_key") or f"{slug}_{integration}"),
        )

    def writebacks_for(slug: str, lanes: Dict[str, List[Dict[str, Any]]], next_index: int) -> Dict[str, Dict[str, Any]]:
        writebacks: Dict[str, Dict[str, Any]] = {}
        if lanes.get("ble"):
            writebacks["ble"] = write_action(
                f"A{next_index}",
                f"sensor.vdev_{slug}_ble_lane",
                file_rel="switchbot/fan.py",
                integration="switchbot",
            )
            next_index += 1
        if lanes.get("cloud"):
            writebacks["cloud"] = write_action(
                f"A{next_index}",
                f"sensor.vdev_{slug}_cloud_lane",
                file_rel="tuya/entity.py",
                integration="tuya",
            )
            next_index += 1
        if lanes.get("local"):
            writebacks["local"] = write_action(
                f"A{next_index}",
                f"sensor.vdev_{slug}_local_lane",
                file_rel="tplink/entity.py",
                integration="tplink",
            )
            next_index += 1
        writebacks["overall"] = write_action(
            f"A{next_index}",
            f"sensor.vdev_{slug}_overall",
            file_rel="esphome/update.py",
            integration="esphome",
        )
        return writebacks

    def mixed_protocols(lanes: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        protocols: List[str] = []
        if lanes.get("ble"):
            protocols.append("BLE")
        if lanes.get("cloud"):
            protocols.append("CLOUD")
        if lanes.get("local"):
            protocols.append("LOCAL")
        return protocols

    def add_case(spec: Dict[str, Any]) -> None:
        slug = case_slug(str(spec["vdev_id"]))
        lanes: Dict[str, List[Dict[str, Any]]] = {}
        action_index = 1
        id_by_key: Dict[str, str] = {}
        for lane_name in ("ble", "cloud", "local"):
            lane_specs = list(spec.get(lane_name, []))
            if not lane_specs:
                continue
            lane_actions: List[Dict[str, Any]] = []
            for lane_spec in lane_specs:
                action_id = f"A{action_index}"
                action_index += 1
                if lane_spec.get("key"):
                    id_by_key[str(lane_spec["key"])] = action_id
                if lane_name == "ble":
                    lane_actions.append(make_ble_action(action_id, lane_spec))
                elif lane_name == "cloud":
                    lane_actions.append(make_cloud_action(action_id, lane_spec, slug))
                else:
                    lane_actions.append(make_local_action(action_id, lane_spec, slug))
            lanes[lane_name] = lane_actions

        writebacks = writebacks_for(slug, lanes, action_index)
        connect_pairs = [
            (id_by_key[str(before)], id_by_key[str(after)])
            for before, after in spec.get("connect_pairs", [])
        ]
        cases.append(
            case_target(
                vdev_id=str(spec["vdev_id"]),
                name=str(spec["name"]),
                group=str(spec["group"]),
                story=str(spec["story"]),
                strengths=list(spec["strengths"]),
                focus_areas=list(spec["focus_areas"]),
                lanes=lanes,
                writebacks=writebacks,
                mixed_source_protocols=mixed_protocols(lanes),
                connect_before_subscribe=connect_pairs,
                ble_soft_pairs=ble_budget_pairs([str(action["action_id"]) for action in lanes.get("ble", [])]),
                objectives={
                    "primary": str(spec.get("objective") or "minimize_tail_latency_for_profile_coverage_routine"),
                    "metrics": {"e2e_latency_ms": {"p95": int(spec.get("p95_ms") or 2800)}},
                },
            )
        )

    case_specs: List[Dict[str, Any]] = [
        {
            "vdev_id": "vdev_morning_wakeup_readiness_profile_01",
            "name": "Morning Wake-Up Readiness Profile Coverage",
            "group": morning_group,
            "story": "After residents wake up, the routine quickly checks bedroom and hallway readiness across curtains, bedside lamps, environmental sensors, local lights, local TV state, cloud climate, and thermostat runtime.",
            "strengths": ["Long BLE lane with connect-before-subscribe semantics.", "Cloud has two providers while the local lane stays cheap.", "Lane-level publishes and one overall publish mirror the requested aggregation structure."],
            "focus_areas": ["BLE chain with connect before subscribe", "Cheap local API packing", "Cloud provider separation", "Lane-first writeback semantics"],
            "ble": [
                {"kind": "switchbot_cover", "id": "morning_curtain_left"},
                {"kind": "switchbot_cover", "id": "morning_curtain_right"},
                {"kind": "xiaomi_status", "id": "morning_bedside_lamp_left"},
                {"kind": "xiaomi_status", "id": "morning_bedside_lamp_right"},
                {"kind": "ble_sensor", "integration": "qingping", "id": "bedroom_temp_humidity_left"},
                {"kind": "ble_sensor", "integration": "sensorpush", "id": "bedroom_temp_humidity_right"},
                {"kind": "esphome_connect", "id": "morning_air_node", "key": "esp_air_connect"},
                {"kind": "esphome_subscribe", "id": "morning_relay_node", "key": "esp_relay_subscribe"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:bedroom_group", "file_rel": "hue/v2/group.py"},
                {"integration": "philips_js", "id": "tv.bedroom"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "climate", "id": "bedroom_ac"},
                {"integration": "ecobee", "id": "thermostat.master_bedroom"},
            ],
            "connect_pairs": [("esp_air_connect", "esp_relay_subscribe")],
        },
        {
            "vdev_id": "vdev_whole_family_morning_comfort_snapshot_01",
            "name": "Whole-Family Morning Comfort Snapshot",
            "group": morning_group,
            "story": "Before the whole family wakes up, the routine snapshots comfort state across multiple rooms, including BLE environment sensors, SwitchBot curtains, local lighting systems, Tuya climate or lights, and Netatmo runtime.",
            "strengths": ["Read-heavy mixed snapshot with no artificial hard action dependency.", "BLE sensor count is high enough to expose radio ordering pressure.", "Cloud and local lanes are naturally separable."],
            "focus_areas": ["BLE read-heavy ordering", "Cloud/local frontier completeness", "Local Hue and Nanoleaf packing", "Single comfort summary tail"],
            "ble": [
                {"kind": "ble_sensor", "integration": "airthings_ble", "id": "living_room_air_quality"},
                {"kind": "ble_sensor", "integration": "ruuvitag_ble", "id": "bedroom_environment"},
                {"kind": "ble_sensor", "integration": "ruuvitag_ble", "id": "kids_room_environment"},
                {"kind": "ble_sensor", "integration": "thermobeacon", "id": "hallway_environment"},
                {"kind": "switchbot_cover", "id": "living_room_curtain_left"},
                {"kind": "switchbot_cover", "id": "living_room_curtain_right"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:living_room_group", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:dining_room_group", "file_rel": "hue/v2/group.py"},
                {"integration": "nanoleaf", "id": "panel.family_room"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "living_room_morning_1"},
                {"integration": "tuya", "domain": "light", "id": "living_room_morning_2"},
                {"integration": "tuya", "domain": "climate", "id": "kids_room_ac"},
                {"integration": "netatmo", "id": "station.indoor_environment"},
            ],
        },
        {
            "vdev_id": "vdev_school_day_quiet_start_check_01",
            "name": "School-Day Quiet Start Check",
            "group": morning_group,
            "story": "On school-day mornings, the routine checks hallway, kids-room, and study state to avoid noisy or incorrect wake-up behavior.",
            "strengths": ["Medium-size realistic mixed case.", "Cross-provider cloud reads can run independently.", "Local media state is present but cheap."],
            "focus_areas": ["Cross-provider cloud readiness", "BLE plus local lightweight overlap", "No unnecessary hard dependency injection"],
            "ble": [
                {"kind": "xiaomi_sensor", "id": "entry_motion_quiet_start", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "ble_sensor", "integration": "qingping", "id": "kids_room_temp_humidity"},
                {"kind": "switchbot_cover", "id": "kids_room_curtain"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:hallway_quiet_light_left"},
                {"integration": "hue", "id": "bridge_1:hallway_quiet_light_right"},
                {"integration": "webostv", "id": "tv.living_room"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "study_quiet_start"},
                {"integration": "smartthings", "id": "kids_room_device_snapshot"},
                {"integration": "ecobee", "id": "thermostat.school_day"},
            ],
        },
        {
            "vdev_id": "vdev_bad_air_morning_recovery_01",
            "name": "Bad-Air Morning Recovery",
            "group": morning_group,
            "story": "When indoor air quality is poor in the morning, the routine checks purifier state, curtains, climate, local ambience lights, and Netatmo environment state before recommending recovery actions.",
            "strengths": ["Natural air-quality recovery scenario.", "BLE status reads mix with curtain refresh.", "Cloud climate endpoints are grouped but still provider separated from Netatmo."],
            "focus_areas": ["BLE status versus cover refresh ordering", "Cloud climate grouping", "Local Nanoleaf and Hue cheap reads", "Overall recommendation writeback"],
            "ble": [
                {"kind": "ble_sensor", "integration": "airthings_ble", "id": "bad_air_morning_sensor"},
                {"kind": "switchbot_status", "id": "air_purifier_living_room"},
                {"kind": "switchbot_cover", "id": "bad_air_curtain_left"},
                {"kind": "switchbot_cover", "id": "bad_air_curtain_right"},
            ],
            "local": [
                {"integration": "nanoleaf", "id": "panel.bad_air_ambience"},
                {"integration": "hue", "id": "bridge_1:living_room_bad_air_group", "file_rel": "hue/v2/group.py"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "climate", "id": "living_room_bad_air_ac"},
                {"integration": "tuya", "domain": "climate", "id": "bedroom_bad_air_ac"},
                {"integration": "netatmo", "id": "station.bad_air_runtime"},
            ],
        },
        {
            "vdev_id": "vdev_leave_home_safety_sweep_profile_01",
            "name": "Leave-Home Safety Sweep Profile Coverage",
            "group": transition_group,
            "story": "After residents leave, the routine checks lights, plugs, curtains, door or window sensors, climate, and entertainment devices to confirm the home is safe and energy efficient.",
            "strengths": ["Large mixed departure routine with many realistic device families.", "Cloud burst and local media or plug reads are both significant.", "BLE safety sensors and curtains stress the BLE lane without synthetic padding."],
            "focus_areas": ["Cloud burst grouping", "Cheap local frontier packing", "BLE safety sensor sweep", "Short final safety summary tail"],
            "p95_ms": 3600,
            "ble": [
                {"kind": "xiaomi_sensor", "id": "front_door_departure", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "side_door_departure", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "kitchen_window_departure", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "bedroom_window_departure", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "switchbot_cover", "id": "departure_curtain_living"},
                {"kind": "switchbot_cover", "id": "departure_curtain_bedroom"},
                {"kind": "switchbot_cover", "id": "departure_curtain_study"},
            ],
            "local": [
                {"integration": "tplink", "id": "plug.desk_left_departure"},
                {"integration": "tplink", "id": "plug.desk_right_departure"},
                {"integration": "hue", "id": "bridge_1:living_room_departure_group", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:dining_departure_group", "file_rel": "hue/v2/group.py"},
                {"integration": "roku", "id": "media_player.family_room"},
                {"integration": "denonavr", "id": "media_player.main_avr"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "departure_light_1"},
                {"integration": "tuya", "domain": "light", "id": "departure_light_2"},
                {"integration": "tuya", "domain": "light", "id": "departure_light_3"},
                {"integration": "tuya", "domain": "switch", "id": "departure_strip_1"},
                {"integration": "tuya", "domain": "switch", "id": "departure_strip_2"},
                {"integration": "tuya", "domain": "switch", "id": "departure_strip_3"},
                {"integration": "ecobee", "id": "thermostat.departure"},
            ],
        },
        {
            "vdev_id": "vdev_arrival_home_preparation_profile_01",
            "name": "Arrival Home Preparation Profile Coverage",
            "group": transition_group,
            "story": "When a family member is near home, the routine checks entry lighting, living-room ambience, climate, curtains, and air-node state before preparing arrival context.",
            "strengths": ["Realistic arrival routine with BLE connect-before-subscribe.", "Cloud scene aggregation is separate from local Hue and Nanoleaf reads.", "The final summary can validate lane-first aggregation."],
            "focus_areas": ["BLE connect-before-subscribe", "Cloud light and climate status grouping", "Local Hue and Nanoleaf packing"],
            "ble": [
                {"kind": "xiaomi_sensor", "id": "entry_motion_arrival", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "switchbot_cover", "id": "arrival_curtain_left"},
                {"kind": "switchbot_cover", "id": "arrival_curtain_right"},
                {"kind": "esphome_connect", "id": "arrival_air_node", "key": "esp_air_connect"},
                {"kind": "esphome_subscribe", "id": "arrival_relay_node", "key": "esp_relay_subscribe"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:entry_hall_group", "file_rel": "hue/v2/group.py"},
                {"integration": "nanoleaf", "id": "panel.living_room_arrival"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "arrival_living_light_1"},
                {"integration": "tuya", "domain": "light", "id": "arrival_living_light_2"},
                {"integration": "tuya", "domain": "climate", "id": "arrival_living_ac"},
                {"integration": "smartthings", "id": "arrival_scene_devices"},
            ],
            "connect_pairs": [("esp_air_connect", "esp_relay_subscribe")],
        },
        {
            "vdev_id": "vdev_vacation_departure_final_audit_01",
            "name": "Vacation Departure Final Audit",
            "group": transition_group,
            "story": "Before a long trip, the routine performs a final whole-home audit across curtains, door or window sensors, temperature sensors, local lights or plugs, media devices, cloud lights or switches, thermostat, and security state.",
            "strengths": ["Large realistic stress case for departure.", "Cloud burst and local frontier are both non-trivial.", "BLE lane is long but still semantically natural."],
            "focus_areas": ["Whole-home BLE sweep", "Cloud same-provider grouping", "Local plug and media packing", "Vacation-mode writeback chain"],
            "p95_ms": 4300,
            "ble": [
                {"kind": "switchbot_cover", "id": "vacation_curtain_living"},
                {"kind": "switchbot_cover", "id": "vacation_curtain_bedroom"},
                {"kind": "switchbot_cover", "id": "vacation_curtain_study"},
                {"kind": "switchbot_cover", "id": "vacation_curtain_guest"},
                {"kind": "xiaomi_sensor", "id": "vacation_front_door", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "vacation_back_door", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "vacation_kitchen_window", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "vacation_bedroom_window", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "ble_sensor", "integration": "sensorpush", "id": "vacation_temp_basement"},
                {"kind": "ble_sensor", "integration": "ruuvitag_ble", "id": "vacation_temp_attic"},
            ],
            "local": [
                {"integration": "tplink", "id": "plug.vacation_router"},
                {"integration": "tplink", "id": "plug.vacation_desk"},
                {"integration": "tplink", "id": "plug.vacation_kitchen"},
                {"integration": "hue", "id": "bridge_1:vacation_living_group", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:vacation_hall_group", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:vacation_bedroom_group", "file_rel": "hue/v2/group.py"},
                {"integration": "webostv", "id": "media_player.vacation_living_tv"},
                {"integration": "roku", "id": "media_player.vacation_guest_roku"},
                {"integration": "denonavr", "id": "media_player.vacation_avr"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "vacation_light_1"},
                {"integration": "tuya", "domain": "light", "id": "vacation_light_2"},
                {"integration": "tuya", "domain": "light", "id": "vacation_light_3"},
                {"integration": "tuya", "domain": "light", "id": "vacation_light_4"},
                {"integration": "tuya", "domain": "switch", "id": "vacation_strip_1"},
                {"integration": "tuya", "domain": "switch", "id": "vacation_strip_2"},
                {"integration": "tuya", "domain": "switch", "id": "vacation_strip_3"},
                {"integration": "tuya", "domain": "switch", "id": "vacation_strip_4"},
                {"integration": "ecobee", "id": "thermostat.vacation"},
                {"integration": "blink", "id": "security.vacation_system"},
            ],
        },
        {
            "vdev_id": "vdev_come_home_security_comfort_merge_01",
            "name": "Come-Home Security and Comfort Merge",
            "group": transition_group,
            "story": "When residents come home, the routine merges security, lighting, and comfort state into one concise arrival summary.",
            "strengths": ["Small but realistic arrival/security benchmark.", "Cloud security plus thermostat state is separated from local Hue and TV state.", "Useful sanity case for mixed schedule overhead."],
            "focus_areas": ["Small mixed-lane schedule quality", "Security and comfort provider separation", "Short publish tail"],
            "ble": [
                {"kind": "xiaomi_sensor", "id": "come_home_entry_motion", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "switchbot_cover", "id": "come_home_entry_curtain"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:entry_light"},
                {"integration": "hue", "id": "bridge_1:hallway_light_left"},
                {"integration": "hue", "id": "bridge_1:hallway_light_right"},
                {"integration": "philips_js", "id": "tv.entry_area"},
            ],
            "cloud": [
                {"integration": "blink", "id": "security.come_home"},
                {"integration": "tuya", "domain": "light", "id": "come_home_living_1"},
                {"integration": "tuya", "domain": "light", "id": "come_home_living_2"},
                {"integration": "ecobee", "id": "thermostat.come_home"},
            ],
        },
        {
            "vdev_id": "vdev_bedtime_lockdown_profile_01",
            "name": "Bedtime Lockdown Profile Coverage",
            "group": evening_group,
            "story": "Before sleep, the routine checks bedroom, hallway, living-room, door or window, plug, and climate state before publishing a night lockdown summary.",
            "strengths": ["Very natural bedtime case for paper readers.", "BLE lane combines curtains, bedside lamps, and door or window sensors.", "Cloud and local lanes are both non-trivial."],
            "focus_areas": ["BLE read/status chain", "Cloud light and climate grouping", "Local Hue and TP-Link packing", "Night summary writeback"],
            "ble": [
                {"kind": "switchbot_cover", "id": "bedtime_curtain_left"},
                {"kind": "switchbot_cover", "id": "bedtime_curtain_right"},
                {"kind": "xiaomi_status", "id": "bedtime_lamp_left"},
                {"kind": "xiaomi_status", "id": "bedtime_lamp_right"},
                {"kind": "xiaomi_sensor", "id": "bedtime_front_door", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "bedtime_kitchen_window", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "bedtime_bedroom_window", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:hallway_bedtime_group", "file_rel": "hue/v2/group.py"},
                {"integration": "tplink", "id": "plug.bedtime_heater"},
                {"integration": "tplink", "id": "plug.bedside"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "bedtime_light_1"},
                {"integration": "tuya", "domain": "light", "id": "bedtime_light_2"},
                {"integration": "tuya", "domain": "light", "id": "bedtime_light_3"},
                {"integration": "tuya", "domain": "climate", "id": "bedtime_ac"},
                {"integration": "ecobee", "id": "thermostat.bedtime"},
            ],
        },
        {
            "vdev_id": "vdev_kids_room_night_safety_check_01",
            "name": "Kids' Room Night Safety Check",
            "group": evening_group,
            "story": "Before sleep, the routine checks a kids-room temperature, humidity, lighting, curtain, AC, and window state.",
            "strengths": ["Small daily safety routine.", "BLE sensor mix covers Qingping, SensorPush, Xiaomi, and SwitchBot.", "Cloud SmartThings aggregation tests non-Tuya provider handling."],
            "focus_areas": ["Small mixed case quality", "BLE read-heavy path", "Cloud provider separation"],
            "ble": [
                {"kind": "ble_sensor", "integration": "qingping", "id": "kids_room_night_temp_left"},
                {"kind": "ble_sensor", "integration": "sensorpush", "id": "kids_room_night_temp_right"},
                {"kind": "switchbot_cover", "id": "kids_room_night_curtain"},
                {"kind": "xiaomi_sensor", "id": "kids_room_window_night", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:kids_room_night_group", "file_rel": "hue/v2/group.py"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "climate", "id": "kids_room_night_ac"},
                {"integration": "tuya", "domain": "light", "id": "kids_room_night_light"},
                {"integration": "smartthings", "id": "kids_room_night_devices"},
            ],
        },
        {
            "vdev_id": "vdev_late_night_entertainment_shutdown_01",
            "name": "Late-Night Entertainment Shutdown",
            "group": evening_group,
            "story": "After watching TV at night, the routine checks whether the living-room entertainment area is fully shut down.",
            "strengths": ["Local API heavy case with AV integrations.", "BLE and cloud lanes remain present but smaller.", "Good target for cheap local lane packing."],
            "focus_areas": ["Local AV and plug packing", "Cloud light and switch grouping", "Small BLE context reads"],
            "ble": [
                {"kind": "switchbot_cover", "id": "entertainment_shutdown_curtain"},
                {"kind": "xiaomi_sensor", "id": "entertainment_shutdown_environment"},
            ],
            "local": [
                {"integration": "denonavr", "id": "media_player.shutdown_avr"},
                {"integration": "roku", "id": "media_player.shutdown_roku"},
                {"integration": "webostv", "id": "media_player.shutdown_tv"},
                {"integration": "hue", "id": "bridge_1:shutdown_living_light_left"},
                {"integration": "hue", "id": "bridge_1:shutdown_living_light_right"},
                {"integration": "tplink", "id": "plug.shutdown_speaker"},
                {"integration": "tplink", "id": "plug.shutdown_tv"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "shutdown_living_light_1"},
                {"integration": "tuya", "domain": "light", "id": "shutdown_living_light_2"},
                {"integration": "tuya", "domain": "switch", "id": "shutdown_entertainment_strip"},
            ],
        },
        {
            "vdev_id": "vdev_overnight_quiet_hours_snapshot_01",
            "name": "Overnight Quiet-Hours Snapshot",
            "group": evening_group,
            "story": "At a fixed overnight time, the routine snapshots the family's quiet-hours state across environmental sensors, door or window sensors, Hue groups, thermostats, power strips, and Netatmo environment runtime.",
            "strengths": ["Read-heavy overnight monitoring case.", "Cloud lane mixes two Ecobee thermostats, Tuya switches, and Netatmo.", "BLE environment and safety sensors stay realistic."],
            "focus_areas": ["Read-heavy cloud grouping", "BLE environmental sensor sweep", "Short overnight writeback tail"],
            "ble": [
                {"kind": "ble_sensor", "integration": "airthings_ble", "id": "overnight_air_bedroom"},
                {"kind": "ble_sensor", "integration": "ruuvitag_ble", "id": "overnight_environment_bedroom"},
                {"kind": "ble_sensor", "integration": "ruuvitag_ble", "id": "overnight_environment_kids_room"},
                {"kind": "xiaomi_sensor", "id": "overnight_front_door", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "overnight_bedroom_window", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:overnight_bedroom_group", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:overnight_hallway_group", "file_rel": "hue/v2/group.py"},
            ],
            "cloud": [
                {"integration": "ecobee", "id": "thermostat.overnight_1"},
                {"integration": "ecobee", "id": "thermostat.overnight_2"},
                {"integration": "tuya", "domain": "switch", "id": "overnight_strip_1"},
                {"integration": "tuya", "domain": "switch", "id": "overnight_strip_2"},
                {"integration": "netatmo", "id": "station.overnight_environment"},
            ],
        },
        {
            "vdev_id": "vdev_weekend_whole_home_snapshot_profile_01",
            "name": "Weekend Whole-Home Snapshot Profile Coverage",
            "group": audit_group,
            "story": "On a weekend, the routine builds a whole-home snapshot of lights, curtains, temperature, energy, air quality, local media, and climate state.",
            "strengths": ["Flagship whole-home mixed benchmark.", "Contains BLE connect-before-subscribe plus many ordinary BLE reads.", "Cloud and local frontiers are both large enough to show packing quality."],
            "focus_areas": ["Large BLE lane with connect-before-subscribe", "Cloud burst grouping", "Cheap local frontier completeness", "Whole-home summary writeback"],
            "p95_ms": 4300,
            "ble": [
                {"kind": "switchbot_cover", "id": "weekend_profile_curtain_living"},
                {"kind": "switchbot_cover", "id": "weekend_profile_curtain_bedroom"},
                {"kind": "switchbot_cover", "id": "weekend_profile_curtain_study"},
                {"kind": "xiaomi_sensor", "id": "weekend_profile_temp_living"},
                {"kind": "xiaomi_sensor", "id": "weekend_profile_temp_bedroom"},
                {"kind": "xiaomi_sensor", "id": "weekend_profile_temp_kids"},
                {"kind": "esphome_connect", "id": "weekend_profile_air_node", "key": "esp_air_connect"},
                {"kind": "esphome_subscribe", "id": "weekend_profile_relay_node", "key": "esp_relay_subscribe"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:weekend_living_group", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:weekend_dining_group", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:weekend_bedroom_group", "file_rel": "hue/v2/group.py"},
                {"integration": "tplink", "id": "plug.weekend_kitchen"},
                {"integration": "tplink", "id": "plug.weekend_study"},
                {"integration": "nanoleaf", "id": "panel.weekend_family_room"},
                {"integration": "roku", "id": "media_player.weekend_family_room"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "weekend_profile_light_1"},
                {"integration": "tuya", "domain": "light", "id": "weekend_profile_light_2"},
                {"integration": "tuya", "domain": "light", "id": "weekend_profile_light_3"},
                {"integration": "tuya", "domain": "light", "id": "weekend_profile_light_4"},
                {"integration": "tuya", "domain": "climate", "id": "weekend_profile_ac_1"},
                {"integration": "tuya", "domain": "climate", "id": "weekend_profile_ac_2"},
                {"integration": "tuya", "domain": "switch", "id": "weekend_profile_strip_1"},
                {"integration": "tuya", "domain": "switch", "id": "weekend_profile_strip_2"},
                {"integration": "netatmo", "id": "station.weekend_environment"},
            ],
            "connect_pairs": [("esp_air_connect", "esp_relay_subscribe")],
        },
        {
            "vdev_id": "vdev_whole_home_energy_hvac_audit_profile_01",
            "name": "Whole-Home Energy and HVAC Audit Profile Coverage",
            "group": audit_group,
            "story": "At a fixed time, the routine audits lights, plug strips, climates, thermostats, local plugs, and local entertainment devices for energy and HVAC state.",
            "strengths": ["Cloud-heavy and local-heavy case without BLE.", "Useful to test cloud frontier completeness independently from BLE constraints.", "Local media state should not block cloud burst grouping."],
            "focus_areas": ["Cloud heavy scheduling", "Local heavy packing", "Provider separation without BLE", "Energy audit writeback"],
            "p95_ms": 4000,
            "local": [
                {"integration": "tplink", "id": "plug.energy_audit_1"},
                {"integration": "tplink", "id": "plug.energy_audit_2"},
                {"integration": "tplink", "id": "plug.energy_audit_3"},
                {"integration": "denonavr", "id": "media_player.energy_audit_avr"},
                {"integration": "webostv", "id": "media_player.energy_audit_tv"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "energy_audit_light_1"},
                {"integration": "tuya", "domain": "light", "id": "energy_audit_light_2"},
                {"integration": "tuya", "domain": "light", "id": "energy_audit_light_3"},
                {"integration": "tuya", "domain": "light", "id": "energy_audit_light_4"},
                {"integration": "tuya", "domain": "switch", "id": "energy_audit_strip_1"},
                {"integration": "tuya", "domain": "switch", "id": "energy_audit_strip_2"},
                {"integration": "tuya", "domain": "switch", "id": "energy_audit_strip_3"},
                {"integration": "tuya", "domain": "switch", "id": "energy_audit_strip_4"},
                {"integration": "tuya", "domain": "climate", "id": "energy_audit_ac_1"},
                {"integration": "tuya", "domain": "climate", "id": "energy_audit_ac_2"},
                {"integration": "ecobee", "id": "thermostat.energy_audit_1"},
                {"integration": "ecobee", "id": "thermostat.energy_audit_2"},
                {"integration": "smartthings", "id": "platform.energy_snapshot"},
            ],
        },
        {
            "vdev_id": "vdev_indoor_air_climate_audit_01",
            "name": "Indoor Air and Climate Audit",
            "group": audit_group,
            "story": "The routine audits air quality and climate state across BLE environmental sensors, local ambience lights, Tuya climates, Ecobee thermostats, and Netatmo station runtime.",
            "strengths": ["Realistic environment and climate daily audit.", "BLE environmental families exercise the expanded profile coverage.", "Cloud climate grouping remains conservative."],
            "focus_areas": ["BLE environmental sensor coverage", "Cloud climate grouping", "Local Nanoleaf cheap lane"],
            "ble": [
                {"kind": "ble_sensor", "integration": "airthings_ble", "id": "climate_audit_airthings"},
                {"kind": "ble_sensor", "integration": "sensorpush", "id": "climate_audit_sensorpush_1"},
                {"kind": "ble_sensor", "integration": "sensorpush", "id": "climate_audit_sensorpush_2"},
                {"kind": "ble_sensor", "integration": "qingping", "id": "climate_audit_qingping_1"},
                {"kind": "ble_sensor", "integration": "qingping", "id": "climate_audit_qingping_2"},
            ],
            "local": [
                {"integration": "nanoleaf", "id": "panel.climate_audit"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "climate", "id": "climate_audit_ac_1"},
                {"integration": "tuya", "domain": "climate", "id": "climate_audit_ac_2"},
                {"integration": "tuya", "domain": "climate", "id": "climate_audit_ac_3"},
                {"integration": "ecobee", "id": "thermostat.climate_audit_1"},
                {"integration": "ecobee", "id": "thermostat.climate_audit_2"},
                {"integration": "netatmo", "id": "station.climate_audit"},
            ],
        },
        {
            "vdev_id": "vdev_security_presence_fabric_snapshot_01",
            "name": "Security and Presence Fabric Snapshot",
            "group": audit_group,
            "story": "At a fixed time, the routine checks whole-home presence, doors, motion, curtains, security platform state, and essential lights.",
            "strengths": ["Security-focused benchmark that remains easy to explain.", "BLE safety sensors dominate but cloud security and presence aggregation also matter.", "Local lane is deliberately small and cheap."],
            "focus_areas": ["BLE safety sensor sweep", "Cloud security and presence providers", "Minimal local packing", "Security summary writeback"],
            "ble": [
                {"kind": "xiaomi_sensor", "id": "presence_motion_entry", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "presence_motion_hallway", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "presence_front_door", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "presence_back_door", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "presence_kitchen_window", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "presence_bedroom_window", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "switchbot_cover", "id": "presence_curtain_living"},
                {"kind": "switchbot_cover", "id": "presence_curtain_bedroom"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:security_entry_group", "file_rel": "hue/v2/group.py"},
            ],
            "cloud": [
                {"integration": "blink", "id": "security.presence_fabric"},
                {"integration": "smartthings", "id": "presence.fabric_snapshot"},
                {"integration": "tuya", "domain": "light", "id": "presence_light_1"},
                {"integration": "tuya", "domain": "light", "id": "presence_light_2"},
            ],
        },
        {
            "vdev_id": "vdev_party_preparation_full_sweep_01",
            "name": "Party Preparation Full Sweep",
            "group": stress_group,
            "story": "Before a party, the routine checks living-room and dining-room lighting, curtains, climate, entertainment devices, and air quality.",
            "strengths": ["Large but realistic party preparation benchmark.", "Local lane includes Hue, Nanoleaf, Denon AVR, Roku, and webOS TV.", "Cloud and BLE lanes remain significant enough for mixed optimization."],
            "focus_areas": ["Local API frontier packing", "Cloud light/switch/climate grouping", "BLE curtain and air-quality reads", "Party-readiness writeback"],
            "p95_ms": 3900,
            "ble": [
                {"kind": "switchbot_cover", "id": "party_full_curtain_living"},
                {"kind": "switchbot_cover", "id": "party_full_curtain_dining"},
                {"kind": "xiaomi_sensor", "id": "party_full_motion", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "ble_sensor", "integration": "airthings_ble", "id": "party_full_air_quality"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:party_light_1"},
                {"integration": "hue", "id": "bridge_1:party_light_2"},
                {"integration": "hue", "id": "bridge_1:party_light_3"},
                {"integration": "hue", "id": "bridge_1:party_light_4"},
                {"integration": "nanoleaf", "id": "panel.party_full"},
                {"integration": "denonavr", "id": "media_player.party_avr"},
                {"integration": "roku", "id": "media_player.party_roku"},
                {"integration": "webostv", "id": "media_player.party_tv"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "party_full_light_1"},
                {"integration": "tuya", "domain": "light", "id": "party_full_light_2"},
                {"integration": "tuya", "domain": "light", "id": "party_full_light_3"},
                {"integration": "tuya", "domain": "switch", "id": "party_full_strip_1"},
                {"integration": "tuya", "domain": "switch", "id": "party_full_strip_2"},
                {"integration": "tuya", "domain": "climate", "id": "party_full_ac"},
            ],
        },
        {
            "vdev_id": "vdev_holiday_vacation_mode_full_audit_01",
            "name": "Holiday Vacation Mode Full Audit",
            "group": stress_group,
            "story": "Before a holiday trip, the routine performs the largest whole-home audit across curtains, doors, windows, environmental sensors, ESPHome transport, local lights, plugs, TVs, and cloud HVAC or security systems.",
            "strengths": ["Large realistic stress benchmark with all three lanes.", "BLE connect-before-subscribe is embedded in a long BLE safety sweep.", "Cloud and local frontiers are both dense enough to reveal scheduler weaknesses."],
            "focus_areas": ["Large BLE safety and environment sweep", "Cloud burst grouping with security state", "Local media and plug packing", "Holiday audit summary"],
            "p95_ms": 5200,
            "ble": [
                {"kind": "switchbot_cover", "id": "holiday_curtain_1"},
                {"kind": "switchbot_cover", "id": "holiday_curtain_2"},
                {"kind": "switchbot_cover", "id": "holiday_curtain_3"},
                {"kind": "switchbot_cover", "id": "holiday_curtain_4"},
                {"kind": "xiaomi_sensor", "id": "holiday_door_window_1", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "holiday_door_window_2", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "holiday_door_window_3", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "holiday_door_window_4", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "holiday_door_window_5", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "ble_sensor", "integration": "qingping", "id": "holiday_temp_1"},
                {"kind": "ble_sensor", "integration": "sensorpush", "id": "holiday_temp_2"},
                {"kind": "ble_sensor", "integration": "sensorpush", "id": "holiday_temp_3"},
                {"kind": "esphome_connect", "id": "holiday_esphome_connect", "key": "esp_air_connect"},
                {"kind": "esphome_subscribe", "id": "holiday_esphome_subscribe", "key": "esp_relay_subscribe"},
            ],
            "local": [
                {"integration": "hue", "id": "bridge_1:holiday_light_group_1", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:holiday_light_group_2", "file_rel": "hue/v2/group.py"},
                {"integration": "hue", "id": "bridge_1:holiday_light_group_3", "file_rel": "hue/v2/group.py"},
                {"integration": "tplink", "id": "plug.holiday_1"},
                {"integration": "tplink", "id": "plug.holiday_2"},
                {"integration": "tplink", "id": "plug.holiday_3"},
                {"integration": "webostv", "id": "media_player.holiday_tv"},
                {"integration": "roku", "id": "media_player.holiday_roku"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "holiday_light_1"},
                {"integration": "tuya", "domain": "light", "id": "holiday_light_2"},
                {"integration": "tuya", "domain": "light", "id": "holiday_light_3"},
                {"integration": "tuya", "domain": "light", "id": "holiday_light_4"},
                {"integration": "tuya", "domain": "switch", "id": "holiday_strip_1"},
                {"integration": "tuya", "domain": "switch", "id": "holiday_strip_2"},
                {"integration": "tuya", "domain": "switch", "id": "holiday_strip_3"},
                {"integration": "tuya", "domain": "switch", "id": "holiday_strip_4"},
                {"integration": "tuya", "domain": "climate", "id": "holiday_ac_1"},
                {"integration": "tuya", "domain": "climate", "id": "holiday_ac_2"},
                {"integration": "ecobee", "id": "thermostat.holiday"},
                {"integration": "blink", "id": "security.holiday"},
            ],
            "connect_pairs": [("esp_air_connect", "esp_relay_subscribe")],
        },
        {
            "vdev_id": "vdev_ble_safety_sweep_routine_01",
            "name": "BLE Safety Sweep Routine",
            "group": stress_group,
            "story": "At a fixed time, the routine performs a whole-home BLE safety sweep over curtains, doors, windows, motion sensors, bedside lamps, environmental sensors, and ESPHome transport state.",
            "strengths": ["BLE-heavy but still realistic safety scenario.", "Useful to test atomic BLE schedule behavior before any micro refinement.", "Only BLE lane and overall writeback keep the proof surface focused."],
            "focus_areas": ["BLE-heavy atomic schedule", "Connect-before-subscribe constraint", "BLE lane publish plus overall publish"],
            "p95_ms": 4200,
            "ble": [
                {"kind": "switchbot_cover", "id": "ble_safety_curtain_1"},
                {"kind": "switchbot_cover", "id": "ble_safety_curtain_2"},
                {"kind": "switchbot_cover", "id": "ble_safety_curtain_3"},
                {"kind": "xiaomi_sensor", "id": "ble_safety_door_window_1", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "ble_safety_door_window_2", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "ble_safety_door_window_3", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "ble_safety_door_window_4", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "ble_safety_motion_1", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_sensor", "id": "ble_safety_motion_2", "domain": "binary_sensor", "file_rel": "xiaomi_ble/binary_sensor.py"},
                {"kind": "xiaomi_status", "id": "ble_safety_lamp_1"},
                {"kind": "xiaomi_status", "id": "ble_safety_lamp_2"},
                {"kind": "ble_sensor", "integration": "airthings_ble", "id": "ble_safety_airthings"},
                {"kind": "ble_sensor", "integration": "ruuvitag_ble", "id": "ble_safety_ruuvitag"},
                {"kind": "esphome_connect", "id": "ble_safety_esphome_connect", "key": "esp_air_connect"},
                {"kind": "esphome_subscribe", "id": "ble_safety_esphome_subscribe", "key": "esp_relay_subscribe"},
            ],
            "connect_pairs": [("esp_air_connect", "esp_relay_subscribe")],
        },
        {
            "vdev_id": "vdev_cloud_burst_living_conditions_snapshot_profile_01",
            "name": "Cloud Burst Living Conditions Snapshot Profile Coverage",
            "group": stress_group,
            "story": "During a weather change or scheduled snapshot, the routine performs a burst read over whole-home lights, plug strips, climates, thermostats, Netatmo runtime, SmartThings aggregation, and a small local plug lane.",
            "strengths": ["Cloud-heavy flagship benchmark.", "Provider separation and same-provider grouping are both visible.", "Small local TP-Link lane tests that cloud burst does not swallow cheap local work."],
            "focus_areas": ["Cloud burst batching", "Provider separation", "Backoff-safe same-bucket grouping", "Small local lane packing"],
            "p95_ms": 4300,
            "local": [
                {"integration": "tplink", "id": "plug.cloud_burst_local_1"},
                {"integration": "tplink", "id": "plug.cloud_burst_local_2"},
            ],
            "cloud": [
                {"integration": "tuya", "domain": "light", "id": "cloud_burst_light_1"},
                {"integration": "tuya", "domain": "light", "id": "cloud_burst_light_2"},
                {"integration": "tuya", "domain": "light", "id": "cloud_burst_light_3"},
                {"integration": "tuya", "domain": "light", "id": "cloud_burst_light_4"},
                {"integration": "tuya", "domain": "light", "id": "cloud_burst_light_5"},
                {"integration": "tuya", "domain": "switch", "id": "cloud_burst_strip_1"},
                {"integration": "tuya", "domain": "switch", "id": "cloud_burst_strip_2"},
                {"integration": "tuya", "domain": "switch", "id": "cloud_burst_strip_3"},
                {"integration": "tuya", "domain": "switch", "id": "cloud_burst_strip_4"},
                {"integration": "tuya", "domain": "switch", "id": "cloud_burst_strip_5"},
                {"integration": "tuya", "domain": "climate", "id": "cloud_burst_ac_1"},
                {"integration": "tuya", "domain": "climate", "id": "cloud_burst_ac_2"},
                {"integration": "tuya", "domain": "climate", "id": "cloud_burst_ac_3"},
                {"integration": "ecobee", "id": "thermostat.cloud_burst_1"},
                {"integration": "ecobee", "id": "thermostat.cloud_burst_2"},
                {"integration": "netatmo", "id": "station.cloud_burst"},
                {"integration": "smartthings", "id": "platform.cloud_burst_snapshot"},
            ],
        },
    ]

    for spec in case_specs:
        add_case(spec)
    return cases


def _action_label(action: Dict[str, Any]) -> str:
    target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
    if str(action.get("protocol", "")).upper() == "HA":
        return str(target.get("entity_id") or target.get("id") or "")
    return str(target.get("device_id") or target.get("endpoint") or target.get("id") or "")


def _lane_actions(target: Dict[str, Any], lane_name: str) -> List[Dict[str, Any]]:
    if lane_name == "writeback":
        return [action for action in target["vdev_actions"] if str(action.get("protocol", "")).upper() == "HA"]
    protocol = {"ble": "BLE", "cloud": "CLOUD", "local": "LOCAL"}[lane_name]
    return [action for action in target["vdev_actions"] if str(action.get("protocol", "")).upper() == protocol]


def _build_readme(cases: List[Dict[str, Any]]) -> str:
    groups = list(
        dict.fromkeys(
            str(case["meta"]["benchmark"]["group"])
            for case in cases
        )
    )
    lines: List[str] = [
        "# vDev Benchmark Suite v2",
        "",
        "This suite organizes benchmark cases around realistic household routines instead of abstract transport-only scenarios.",
        "",
        "## Groups",
    ]
    for group in groups:
        members = [case for case in cases if case["meta"]["benchmark"]["group"] == group]
        lines.append(f"- **{group}**: {len(members)} cases")
    lines.extend(
        [
            "",
            "## Case Index",
            "",
            "| Case | vdev_id | Group | Source actions | Writebacks |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for idx, case in enumerate(cases, start=1):
        actions = [action for action in case["vdev_actions"] if str(action.get("protocol", "")).upper() != "HA"]
        writebacks = [action for action in case["vdev_actions"] if str(action.get("protocol", "")).upper() == "HA"]
        lines.append(
            f"| {idx}. {case['meta']['name']} | `{case['meta']['vdev_id']}` | {case['meta']['benchmark']['group']} | {len(actions)} | {len(writebacks)} |"
        )

    for idx, case in enumerate(cases, start=1):
        meta = case["meta"]
        benchmark = meta["benchmark"]
        lines.extend(
            [
                "",
                f"## Case {idx}. {meta['name']}",
                "",
                f"- `vdev_id`: `{meta['vdev_id']}`",
                f"- Group: {benchmark['group']}",
                f"- Scenario: {benchmark['story']}",
                "",
                "### Composition",
            ]
        )
        for lane_name, title in (("ble", "BLE lane"), ("cloud", "Cloud lane"), ("local", "Local lane"), ("writeback", "Writeback")):
            lane_rows = _lane_actions(case, lane_name)
            if not lane_rows:
                continue
            lines.append(f"- {title}:")
            for action in lane_rows:
                lines.append(
                    f"  - `{action['action_id']}`: `{_action_label(action)}` -> `{action['exec']['service']}` (`{action['exec']['domain']}`)"
                )
        lines.extend(
            [
                "",
                "### Why It Is Useful",
            ]
        )
        for item in benchmark["strengths"]:
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "### Main Optimization Focus",
            ]
        )
        for item in benchmark["focus_areas"]:
            lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The generated `manifest.json` is the active source of truth for the current suite.",
            f"- The benchmark generator script is `{REPO_ROOT / 'scripts' / 'run_vdev_benchmarks.py'}`.",
            f"- Targets are written under `{TARGET_ROOT}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _seed_llm_cache_from_existing_run(out_dir: Path) -> None:
    report_path = out_dir / "m1_unresolved_grounding_report.json"
    llm_path = out_dir / "m1_detector_profile_draft_llm.json"
    if not report_path.exists() or not llm_path.exists():
        return
    try:
        unresolved_report = json.loads(report_path.read_text(encoding="utf-8"))
        llm_draft = json.loads(llm_path.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(unresolved_report, dict) or not isinstance(llm_draft, dict):
        return
    source_hash = str(unresolved_report.get("source_report_sha256", "")).strip() or _sha256_json(unresolved_report)
    if not source_hash:
        return
    llm_draft = dict(llm_draft)
    llm_draft["source_report_sha256"] = source_hash
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(CACHE_ROOT / f"{source_hash}.json", llm_draft)


def _default_worker_count(case_count: int) -> int:
    env_value = str(os.environ.get("FLOWEAVER_BENCHMARK_WORKERS", "")).strip()
    if env_value.isdigit():
        return max(1, min(case_count, int(env_value)))
    return max(1, min(case_count, 6))


def _write_suite_targets(cases: List[Dict[str, Any]]) -> None:
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    keep_files = set()
    manifest: List[Dict[str, Any]] = []
    for target in cases:
        vdev_id = target["meta"]["vdev_id"]
        target_path = TARGET_ROOT / f"{vdev_id}.json"
        write_json(target_path, target)
        keep_files.add(target_path.name)
        manifest.append(
            {
                "vdev_id": vdev_id,
                "name": target["meta"]["name"],
                "group": target["meta"]["benchmark"]["group"],
                "target_path": str(target_path.resolve()),
            }
        )
    write_json(TARGET_ROOT / "manifest.json", {"cases": manifest})
    keep_files.add("manifest.json")
    README_PATH.write_text(_build_readme(cases), encoding="utf-8")

    for stale in TARGET_ROOT.glob("vdev_*.json"):
        if stale.name not in keep_files:
            stale.unlink()


def summarize_run(run_dir: Path, target: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "vdev_id": target["meta"]["vdev_id"],
        "name": target["meta"]["name"],
        "group": target["meta"]["benchmark"]["group"],
        "target_path": str((TARGET_ROOT / f"{target['meta']['vdev_id']}.json").resolve()),
        "run_dir": str(run_dir.resolve()),
    }
    cert_path = run_dir / "execution_certificate.json"
    plan_path = run_dir / "m5_execution_plan.json"
    if cert_path.exists():
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
        diff = cert.get("differential_summary", {})
        summary.update(
            {
                "strict_pass": diff.get("strict_pass"),
                "tolerant_pass": diff.get("tolerant_pass"),
                "counterexample_count": diff.get("counterexample_count"),
            }
        )
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        batches = plan.get("ordered_batches", [])
        triggered = plan.get("meta", {}).get("derived_policy", {}).get("triggered_fallbacks", [])
        summary.update(
            {
                "batch_count": len(batches),
                "parallel_groups": {batch["batch_id"]: batch.get("parallel_groups", []) for batch in batches},
                "batching_buckets": {
                    batch["batch_id"]: batch.get("rate_policy", {}).get("batching_buckets", [])
                    for batch in batches
                },
                "triggered_fallbacks": triggered,
                "unknown_protocol_actions": plan.get("meta", {}).get("unknown_protocol_actions", []),
            }
        )
    return summary


def _load_json_if_exists(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _target_protocol_counts(target: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for action in target.get("vdev_actions", []):
        protocol = str(action.get("protocol", "UNKNOWN")).strip().upper() or "UNKNOWN"
        counts[protocol] = counts.get(protocol, 0) + 1
    return counts


def _action_type_counts(target: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for action in target.get("vdev_actions", []):
        action_type = str(action.get("type", "unknown")).strip() or "unknown"
        counts[action_type] = counts.get(action_type, 0) + 1
    return counts


def _ground_truth_binding_summary(target: Dict[str, Any]) -> Dict[str, Any]:
    integrations: Dict[str, int] = {}
    files: List[str] = []
    seen_files: set[str] = set()
    source_scope = target.get("source_scope", {}) if isinstance(target.get("source_scope", {}), dict) else {}
    file_bindings = source_scope.get("file_bindings", []) if isinstance(source_scope.get("file_bindings", []), list) else []
    if not file_bindings:
        for action in target.get("vdev_actions", []):
            binding = action.get("_binding", {}) if isinstance(action.get("_binding", {}), dict) else {}
            if binding:
                file_bindings.append(binding)
    for binding in file_bindings:
        if not isinstance(binding, dict):
            continue
        integration = str(binding.get("integration", "")).strip() or "unknown"
        file_path = str(binding.get("file_path", "")).strip()
        integrations[integration] = integrations.get(integration, 0) + 1
        if file_path and file_path not in seen_files:
            files.append(file_path)
            seen_files.add(file_path)
    return {
        "integrations": integrations,
        "files": files,
    }


def _find_generated_component_dir(run_dir: Path) -> Path | None:
    reassembly_dir = run_dir / "reassembly"
    if not reassembly_dir.exists():
        return None
    for plan_path in reassembly_dir.glob("**/custom_components/*/plan.json"):
        return plan_path.parent
    return None


def _generated_component_summary(run_dir: Path) -> Dict[str, Any]:
    component_dir = _find_generated_component_dir(run_dir)
    if component_dir is None:
        return {
            "component_dir": "",
            "files": [],
        }
    preferred = [
        "__init__.py",
        "const.py",
        "entities.py",
        "executor.py",
        "manifest.json",
        "plan.json",
        "services.yaml",
        "target.json",
    ]
    files = [str((component_dir / name).resolve()) for name in preferred if (component_dir / name).exists()]
    return {
        "component_dir": str(component_dir.resolve()),
        "files": files,
    }


def _max_parallel_groups(plan: Dict[str, Any]) -> int:
    batches = plan.get("ordered_batches", [])
    max_groups = 0
    for batch in batches:
        groups = batch.get("parallel_groups", [])
        if isinstance(groups, list):
            max_groups = max(max_groups, len(groups))
    return max_groups


def _tail_writeback_batches(target: Dict[str, Any], plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    action_by_id = {str(action.get("action_id")): action for action in target.get("vdev_actions", [])}
    batches = plan.get("ordered_batches", [])
    tail: List[Dict[str, Any]] = []
    for batch in reversed(batches):
        flat_ids = [str(action_id) for group in batch.get("parallel_groups", []) for action_id in group]
        if not flat_ids:
            break
        if all(str(action_by_id.get(action_id, {}).get("protocol", "")).upper() == "HA" for action_id in flat_ids):
            tail.append(batch)
            continue
        break
    return list(reversed(tail))


def _format_protocol_counts(counts: Dict[str, int]) -> str:
    if not counts:
        return "None"
    order = ["BLE", "CLOUD", "LOCAL", "HA", "UNKNOWN"]
    parts: List[str] = []
    for key in order:
        if counts.get(key):
            parts.append(f"{key} {counts[key]}")
    for key in sorted(counts):
        if key not in order:
            parts.append(f"{key} {counts[key]}")
    return " / ".join(parts)


def _format_top_action_types(counts: Dict[str, int], limit: int = 5) -> str:
    if not counts:
        return "None"
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name} x{count}" for name, count in ordered[:limit])


def _schedule_plain_language(target: Dict[str, Any], plan: Dict[str, Any], status: Dict[str, Any]) -> str:
    batches = plan.get("ordered_batches", [])
    if not batches:
        return "No execution batches are available."
    action_by_id = {str(action.get("action_id")): action for action in target.get("vdev_actions", [])}
    protocol_counts = _target_protocol_counts(target)
    ble_prefix = 0
    for batch in batches:
        groups = batch.get("parallel_groups", [])
        if len(groups) != 1 or len(groups[0]) != 1:
            break
        action_id = str(groups[0][0])
        if str(action_by_id.get(action_id, {}).get("protocol", "")).upper() != "BLE":
            break
        ble_prefix += 1
    cloud_bucket_lines: List[str] = []
    for batch in batches:
        for bucket in batch.get("rate_policy", {}).get("batching_buckets", []) or []:
            members = bucket.get("members", []) or []
            if len(members) >= 2:
                cloud_bucket_lines.append(
                    f"{bucket.get('bucket', 'bucket')} groups {len(members)} actions into {bucket.get('chunks', 1)} chunks"
                )
    local_overlap_batches: List[str] = []
    for batch in batches:
        groups = batch.get("parallel_groups", [])
        flat_ids = [str(action_id) for group in groups for action_id in group]
        protocols = {str(action_by_id.get(action_id, {}).get('protocol', '')).upper() for action_id in flat_ids}
        if "LOCAL" in protocols and len(flat_ids) >= 2:
            local_overlap_batches.append(batch.get("batch_id", "batch"))
    tail_batches = _tail_writeback_batches(target, plan)
    tail_desc = " -> ".join(batch.get("batch_id", "?") for batch in tail_batches) if tail_batches else "no distinct writeback tail"
    lines: List[str] = []
    if protocol_counts.get("BLE"):
        lines.append(f"The first {ble_prefix} BLE actions run serially to avoid shared-radio conflicts.")
    if cloud_bucket_lines:
        lines.append("Cloud reads are grouped by provider and endpoint: " + "; ".join(cloud_bucket_lines[:3]) + ".")
    if local_overlap_batches:
        lines.append(f"Local reads overlap other reads in {', '.join(local_overlap_batches[:3])}.")
    lines.append(f"Writeback follows lane updates and then the overall update: {tail_desc}.")
    if status.get("counterexample_count") == 0 and status.get("strict_pass"):
        lines.append("M6 found no counterexamples in the evaluated replay scenarios.")
    return " ".join(lines)


def _refactor_characteristics(target: Dict[str, Any], run_dir: Path) -> List[str]:
    binding_summary = _ground_truth_binding_summary(target)
    component_summary = _generated_component_summary(run_dir)
    integrations = binding_summary["integrations"]
    files = binding_summary["files"]
    generated_files = component_summary["files"]
    integration_count = len(integrations)
    file_count = len(files)
    lines = [
        f"The source spans {integration_count} integrations and approximately {file_count} files, assembled into one `custom_components/vdev_*` component.",
        "State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.",
        "Batching, session, and fallback policies are recorded explicitly in the generated plan.",
    ]
    if generated_files:
        lines.append("The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.")
    return lines


def _build_run_report(cases: List[Dict[str, Any]], statuses: List[Dict[str, Any]], run_id: str) -> str:
    case_by_id = {str(case["meta"]["vdev_id"]): case for case in cases}
    lines: List[str] = [
        "# VDev Benchmark Run Report",
        "",
        f"- Run ID: `{run_id}`",
        f"- Case Count: `{len(cases)}`",
        "",
        "## Overview",
        "",
        "| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for status in statuses:
        run_dir = Path(str(status.get("run_dir", "")))
        has_reassembly = "yes" if (run_dir / "reassembly").exists() else "no"
        lines.append(
            "| {case} | {group} | {status_text} | {batches} | {strict_pass} | {counterexamples} | {reassembly} |".format(
                case=str(status.get("vdev_id", "")),
                group=str(status.get("group", "")),
                status_text=str(status.get("status", "")),
                batches=status.get("batch_count", "-"),
                strict_pass=status.get("strict_pass", "-"),
                counterexamples=status.get("counterexample_count", "-"),
                reassembly=has_reassembly,
            )
        )
    lines.extend(
        [
            "",
            "## Case Details",
            "",
        ]
    )
    for status in statuses:
        vdev_id = str(status.get("vdev_id", ""))
        target = case_by_id.get(vdev_id)
        if target is None:
            continue
        persisted_target = _load_json_if_exists(TARGET_ROOT / f"{vdev_id}.json") or target
        run_dir = Path(str(status.get("run_dir", "")))
        plan = _load_json_if_exists(run_dir / "m5_execution_plan.json") or {}
        cert = _load_json_if_exists(run_dir / "execution_certificate.json") or {}
        binding_summary = _ground_truth_binding_summary(persisted_target)
        component_summary = _generated_component_summary(run_dir)
        protocol_counts = _target_protocol_counts(persisted_target)
        action_type_counts = _action_type_counts(persisted_target)
        benchmark_meta = persisted_target.get("meta", {}).get("benchmark", {}) if isinstance(persisted_target.get("meta", {}).get("benchmark", {}), dict) else {}
        component_dir = component_summary.get("component_dir", "")
        cert_summary = cert.get("differential_summary", {}) if isinstance(cert.get("differential_summary", {}), dict) else {}
        lines.extend(
            [
                f"### {target['meta']['name']} (`{vdev_id}`)",
                "",
                f"- Story: {benchmark_meta.get('story', '')}",
                f"- Protocol Mix: {_format_protocol_counts(protocol_counts)}",
                f"- Main Action Types: {_format_top_action_types(action_type_counts)}",
                f"- Final Schedule: `{status.get('batch_count', '-')}` batches, max `{_max_parallel_groups(plan)}` parallel groups in one batch",
                f"- M6 Evidence: strict `{status.get('strict_pass', '-')}`, tolerant `{status.get('tolerant_pass', '-')}`, counterexamples `{status.get('counterexample_count', '-')}`",
                f"- Run Dir: `{run_dir.resolve()}`",
                f"- M7 Component Dir: `{component_dir or 'missing'}`",
                "",
                "**Schedule Interpretation**",
                "",
                _schedule_plain_language(persisted_target, plan, status),
                "",
                "**Ground-Truth vs Generated Code**",
                "",
                "| Dimension | Ground-Truth | Generated vDev |",
                "| --- | --- | --- |",
                f"| Source Shape | `{len(binding_summary['integrations'])}` integrations / `{len(binding_summary['files'])}` files | `1` generated custom component |",
                f"| Main Source Integrations | `{', '.join(f'{name}:{count}' for name, count in sorted(binding_summary['integrations'].items())) or 'none'}` | `vdev_{vdev_id}` |",
                f"| Main Source Files | `{'; '.join(binding_summary['files'][:4])}`{' ...' if len(binding_summary['files']) > 4 else ''} | `{'; '.join(component_summary['files'][:6])}`{' ...' if len(component_summary['files']) > 6 else ''} |",
                "",
                "**Refactor Characteristics**",
                "",
            ]
        )
        for item in _refactor_characteristics(persisted_target, run_dir):
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "**Key Evidence Files**",
                "",
                f"- Target: `{(TARGET_ROOT / f'{vdev_id}.json').resolve()}`",
                f"- M5 Plan: `{(run_dir / 'm5_execution_plan.json').resolve()}`",
                f"- M6 Certificate: `{(run_dir / 'execution_certificate.json').resolve()}`",
                f"- Counterexamples: `{(run_dir / 'counterexamples.json').resolve()}`",
                f"- Generated Component: `{component_dir or 'missing'}`",
                "",
            ]
        )
        if cert_summary:
            lines.extend(
                [
                    "**M6 Proof Summary**",
                    "",
                    f"- Strict pass scenarios: `{cert_summary.get('strict_pass', '-')}`",
                    f"- Tolerant pass scenarios: `{cert_summary.get('tolerant_pass', '-')}`",
                    f"- Counterexample count: `{cert_summary.get('counterexample_count', '-')}`",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _write_markdown_report(cases: List[Dict[str, Any]], completed: Dict[str, Dict[str, Any]], run_id: str) -> None:
    merged: Dict[str, Dict[str, Any]] = {}
    merged.update(_recover_completed_statuses(cases, run_id=run_id if run_id != "consolidated" else None))
    merged.update(completed)
    ordered_statuses: List[Dict[str, Any]] = []
    for target in cases:
        vdev_id = str(target["meta"]["vdev_id"])
        status = merged.get(vdev_id)
        if status is None:
            ordered_statuses.append(
                {
                    "vdev_id": vdev_id,
                    "name": target["meta"]["name"],
                    "group": target["meta"]["benchmark"]["group"],
                    "target_path": str((TARGET_ROOT / f"{vdev_id}.json").resolve()),
                    "run_dir": str((RUN_ROOT / vdev_id).resolve()),
                    "status": "pending",
                }
            )
        else:
            ordered_statuses.append(status)
    report = _build_run_report(cases, ordered_statuses, run_id)
    report_path = TARGET_ROOT / f"benchmark_run_{run_id}.md"
    report_path.write_text(report, encoding="utf-8")
    LATEST_RUN_REPORT_PATH.write_text(report, encoding="utf-8")


def _recover_completed_statuses(cases: List[Dict[str, Any]], run_id: str | None = None) -> Dict[str, Dict[str, Any]]:
    recovered: Dict[str, Dict[str, Any]] = {}
    for target in cases:
        vdev_id = str(target["meta"]["vdev_id"])
        case_status_path = RUN_ROOT / vdev_id / "case_status.json"
        if not case_status_path.exists():
            continue
        try:
            payload = json.loads(case_status_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict) or payload.get("status") not in {"ok", "error"}:
            continue
        if run_id is not None and str(payload.get("run_id", "")).strip() != str(run_id).strip():
            continue
        if isinstance(payload, dict):
            recovered[vdev_id] = payload
    return recovered


def _run_case(target: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    vdev_id = target["meta"]["vdev_id"]
    target_path = TARGET_ROOT / f"{vdev_id}.json"
    out_dir = RUN_ROOT / vdev_id
    if out_dir.exists():
        _seed_llm_cache_from_existing_run(out_dir)
        shutil.rmtree(out_dir)
    optimizer = FloWeaverOptimizer(
        integration_name=vdev_id,
        profile_path=PROFILE_PATH,
        optimization_target_path=target_path,
        out_dir=out_dir,
    )
    try:
        optimizer.run()
        status = summarize_run(out_dir, target)
        status["status"] = "ok"
    except Exception as exc:
        status = {
            "vdev_id": vdev_id,
            "name": target["meta"]["name"],
            "group": target["meta"]["benchmark"]["group"],
            "target_path": str(target_path.resolve()),
            "run_dir": str(out_dir.resolve()),
            "status": "error",
            "error": repr(exc),
        }
    status["run_id"] = str(run_id)
    write_json(out_dir / "case_status.json", status)
    return status


def _write_incremental_summary(cases: List[Dict[str, Any]], completed: Dict[str, Dict[str, Any]], run_id: str) -> None:
    merged: Dict[str, Dict[str, Any]] = {}
    merged.update(_recover_completed_statuses(cases, run_id=run_id))
    merged.update(completed)
    ordered_statuses: List[Dict[str, Any]] = []
    for target in cases:
        vdev_id = target["meta"]["vdev_id"]
        status = merged.get(vdev_id)
        if status is None:
            ordered_statuses.append(
                {
                    "vdev_id": vdev_id,
                    "name": target["meta"]["name"],
                    "group": target["meta"]["benchmark"]["group"],
                    "target_path": str((TARGET_ROOT / f"{vdev_id}.json").resolve()),
                    "run_dir": str((RUN_ROOT / vdev_id).resolve()),
                    "status": "pending",
                }
            )
        else:
            ordered_statuses.append(status)
    write_json(
        RUN_ROOT / "summary.json",
        {
            "profile_path": str(PROFILE_PATH.resolve()),
            "run_id": str(run_id),
            "completed_case_count": len(merged),
            "total_case_count": len(cases),
            "cases": ordered_statuses,
        },
    )
    _write_markdown_report(cases, completed, run_id)


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate and optionally run the vDev benchmark suite.")
    parser.add_argument(
        "--targets-only",
        action="store_true",
        help="Only regenerate target JSON, manifest, and README without running the optimizer.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of benchmark cases to run in parallel. Defaults to min(case_count, 6) or FLOWEAVER_BENCHMARK_WORKERS.",
    )
    parser.add_argument(
        "--cases",
        nargs="*",
        default=None,
        help="Optional list of vdev_ids to run. Comma-separated values are also accepted.",
    )
    parser.add_argument(
        "--report-from-existing",
        action="store_true",
        help="Generate a markdown report from existing benchmark outputs without running the optimizer.",
    )
    args = parser.parse_args(argv)

    cases = build_cases()
    _write_suite_targets(cases)

    if args.cases:
        requested: List[str] = []
        for token in args.cases:
            for item in str(token).split(","):
                value = item.strip()
                if value:
                    requested.append(value)
        requested_set = set(requested)
        cases = [case for case in cases if str(case["meta"]["vdev_id"]) in requested_set]

    if args.targets_only:
        return

    if args.report_from_existing:
        _write_markdown_report(cases, completed={}, run_id="consolidated")
        return

    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    completed: Dict[str, Dict[str, Any]] = {}
    _write_incremental_summary(cases, completed, run_id)

    worker_count = max(1, int(args.workers or _default_worker_count(len(cases))))
    try:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_vdev = {
                executor.submit(_run_case, target, run_id): target["meta"]["vdev_id"]
                for target in cases
            }
            for future in as_completed(future_to_vdev):
                status = future.result()
                completed[str(status["vdev_id"])] = status
                _write_incremental_summary(cases, completed, run_id)
    finally:
        _write_incremental_summary(cases, completed, run_id)


if __name__ == "__main__":
    main()
