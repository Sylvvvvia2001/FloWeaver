from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Tuple

from dsl.contracts import Batch, ExecutionPlan, OptimizationTarget


BLE_MICRO_PHASES = (
    "PREPARE_ADV_SIDE",
    "PREPARE_CONNECT_SIDE",
    "BLE_XFER",
    "BLE_SETTLE",
)

_BLE_DURATION_MS: Dict[str, int] = {
    "set_cover_position": 950,
    "refresh_cover": 850,
    "read_sensor": 750,
    "read_status": 650,
    "connect": 1200,
    "subscribe": 450,
    "set_percentage": 850,
    "turn_on": 850,
    "turn_off": 800,
}

_DEFAULT_BLE_DURATION_MS = 800


@dataclass(frozen=True)
class BLEMicroRefinementPolicy:
    min_corridor_length: int = 3
    min_corridor_latency_ms: int = 1800
    read_like_min_corridor_length: int = 2
    read_like_min_corridor_latency_ms: int = 1200
    control_like_min_corridor_length: int = 3
    control_like_min_corridor_latency_ms: int = 1800
    session_chain_min_corridor_length: int = 2
    session_chain_min_corridor_latency_ms: int = 1400
    generic_min_corridor_length: int = 3
    generic_min_corridor_latency_ms: int = 1800
    max_lookahead_actions: int = 1
    require_shared_scanner: bool = True
    assume_shared_scanner_available: bool = True
    require_source_resolution_for_adv_overlap: bool = True
    allow_unknown_source_adv_overlap: bool = False
    require_connectable_controller_for_connect_prep: bool = True
    assume_connectable_controller_available: bool = True
    enforce_connection_slot_guard: bool = True
    connectable_slot_limit: int = 1
    current_xfer_slot_cost: int = 1
    next_connect_prepare_slot_cost: int = 1
    allow_adv_prepare_overlap: bool = True
    allow_connect_prepare_overlap: bool = False
    allow_subscribe_like_adv_overlap: bool = False
    allow_same_device_adv_overlap: bool = False
    allow_same_session_adv_overlap: bool = False
    source_capability_overrides: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "switchbot": ["adv_anchor_safe"],
            "xiaomi_ble": ["adv_anchor_safe"],
            "esphome": ["subscribe_adv_overlap_safe"],
        }
    )
    kind_capability_overrides: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "refresh_cover": ["read_like_ble_op"],
            "read_sensor": ["read_like_ble_op"],
            "read_status": ["read_like_ble_op"],
            "connect": ["session_chain_ble_op"],
            "subscribe": ["session_chain_ble_op"],
            "set_cover_position": ["control_like_ble_op"],
            "set_percentage": ["control_like_ble_op"],
            "turn_on": ["control_like_ble_op"],
            "turn_off": ["control_like_ble_op"],
        }
    )
    allow_adv_prepare_during_connect_capabilities: List[str] = field(
        default_factory=lambda: ["adv_anchor_safe"]
    )
    allow_subscribe_like_adv_overlap_capabilities: List[str] = field(
        default_factory=lambda: ["subscribe_adv_overlap_safe"]
    )
    allow_adv_prepare_during_connect_for_sources: List[str] = field(
        default_factory=lambda: ["switchbot", "xiaomi_ble"]
    )
    allow_subscribe_like_adv_overlap_sources: List[str] = field(
        default_factory=lambda: ["esphome"]
    )
    prepare_adv_timeout_ms: int = 120
    prepare_connect_timeout_ms: int = 180
    prepare_must_be_side_effect_free: bool = True

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "BLEMicroRefinementPolicy":
        if not isinstance(payload, dict):
            return cls()
        fields = {field_name: payload[field_name] for field_name in cls.__dataclass_fields__ if field_name in payload}
        return cls(**fields)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BLEMicroEvent:
    action_id: str
    phase: str
    start_ms: int
    end_ms: int


@dataclass
class BLEMicroCorridor:
    corridor_id: str
    action_ids: List[str]
    batch_ids: List[str]
    profile_class: str
    original_latency_ms: int
    score: int
    overlap_candidate_pairs: int = 0


@dataclass
class BLEMicroValidationResult:
    passed: bool
    coarse_completion_order_preserved: bool
    phase_order_valid: bool
    xfer_serialized: bool
    lookahead_depth_ok: bool
    scanner_constraints_ok: bool
    connectable_constraints_ok: bool
    slot_constraints_ok: bool
    type_constraints_ok: bool
    rollback_constraints_ok: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class BLEMicroCorridorResult:
    corridor: BLEMicroCorridor
    serial_events: List[BLEMicroEvent]
    refined_events: List[BLEMicroEvent]
    refined_latency_ms: int
    latency_saved_ms: int
    validation: BLEMicroValidationResult


@dataclass
class BLEMicroCaseResult:
    vdev_id: str
    case_name: str
    selected_corridors: List[BLEMicroCorridorResult]
    original_estimated_latency_ms: int
    refined_estimated_latency_ms: int
    added_savings_ms: int
    added_savings_ratio: float
    refined_plan: ExecutionPlan


def _action_index(target: OptimizationTarget) -> Dict[str, Dict[str, Any]]:
    return {
        str(action.get("action_id", "")).strip(): action
        for action in target.vdev_actions
        if str(action.get("action_id", "")).strip()
    }


def _action_protocol(action: Dict[str, Any]) -> str:
    token = str(action.get("protocol", "") or "").strip().upper()
    if token == "MQTT":
        return "LOCAL"
    return token or "UNKNOWN"


def _action_kind(action: Dict[str, Any]) -> str:
    for key in ("action_kind", "type", "kind"):
        token = str(action.get(key, "") or "").strip().lower()
        if token:
            return token
    exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
    token = str(exec_cfg.get("service", "") or "").strip().lower()
    if token:
        return token
    return "unknown"


def _action_target(action: Dict[str, Any]) -> Dict[str, Any]:
    return dict(action.get("target", {})) if isinstance(action.get("target", {}), dict) else {}


def _normalized_device_id(action: Dict[str, Any]) -> str:
    target = _action_target(action)
    for value in (
        target.get("device_id"),
        target.get("id"),
        target.get("endpoint"),
    ):
        token = str(value or "").strip()
        if token:
            return token
    exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
    data_template = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
    for value in (
        data_template.get("device_id"),
        data_template.get("endpoint"),
    ):
        token = str(value or "").strip()
        if token:
            return token
    return ""


def _scanner_source(action: Dict[str, Any]) -> str:
    target = _action_target(action)
    for key in ("source", "scanner_source", "backend_source"):
        token = str(target.get(key, "") or "").strip()
        if token:
            return token
    device_id = _normalized_device_id(action)
    if device_id.startswith("ble:"):
        parts = device_id.split(":")
        if len(parts) >= 2:
            return parts[1]
    return ""


def _session_group(action: Dict[str, Any]) -> str:
    target = _action_target(action)
    for key in ("session_group", "connection_group", "device_session_group"):
        token = str(target.get(key, "") or "").strip()
        if token:
            return token
    kind = _action_kind(action)
    if kind in {"connect", "subscribe"}:
        return _normalized_device_id(action)
    return ""


def _adv_connect_overlap_safe_source(action: Dict[str, Any], policy: BLEMicroRefinementPolicy) -> bool:
    source = _scanner_source(action)
    if not source:
        return False
    return source in {
        str(item).strip()
        for item in policy.allow_adv_prepare_during_connect_for_sources
        if str(item).strip()
    }


def _subscribe_adv_overlap_safe_source(action: Dict[str, Any], policy: BLEMicroRefinementPolicy) -> bool:
    source = _scanner_source(action)
    if not source:
        return False
    return source in {
        str(item).strip()
        for item in policy.allow_subscribe_like_adv_overlap_sources
        if str(item).strip()
    }


def _action_is_subscribe_like(action: Dict[str, Any]) -> bool:
    kind = _action_kind(action)
    exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
    service = str(exec_cfg.get("service", "") or "").strip().lower()
    return any(token in kind or token in service for token in ("subscribe", "notification", "notify", "listen"))


def _ble_capabilities(action: Dict[str, Any], policy: BLEMicroRefinementPolicy) -> set[str]:
    capabilities: set[str] = set()
    kind = _action_kind(action)
    source = _scanner_source(action)
    for token in policy.kind_capability_overrides.get(kind, []):
        text = str(token).strip()
        if text:
            capabilities.add(text)
    for token in policy.source_capability_overrides.get(source, []):
        text = str(token).strip()
        if text:
            capabilities.add(text)
    if _action_is_subscribe_like(action):
        capabilities.add("session_chain_ble_op")
    elif kind == "connect":
        capabilities.add("session_chain_ble_op")
    elif kind in {"refresh_cover", "read_sensor", "read_status"}:
        capabilities.add("read_like_ble_op")
    elif kind in {"set_cover_position", "set_percentage", "turn_on", "turn_off"}:
        capabilities.add("control_like_ble_op")
    else:
        capabilities.add("generic_ble_op")
    return capabilities


def _ble_profile_class(action: Dict[str, Any], policy: BLEMicroRefinementPolicy) -> str:
    capabilities = _ble_capabilities(action, policy)
    if "session_chain_ble_op" in capabilities:
        return "session_chain"
    if "read_like_ble_op" in capabilities:
        return "read_like"
    if "control_like_ble_op" in capabilities:
        return "control_like"
    return "generic"


def _corridor_thresholds(profile_class: str, policy: BLEMicroRefinementPolicy) -> Tuple[int, int]:
    if profile_class == "read_like":
        return policy.read_like_min_corridor_length, policy.read_like_min_corridor_latency_ms
    if profile_class == "control_like":
        return policy.control_like_min_corridor_length, policy.control_like_min_corridor_latency_ms
    if profile_class == "session_chain":
        return policy.session_chain_min_corridor_length, policy.session_chain_min_corridor_latency_ms
    if profile_class == "generic":
        return policy.generic_min_corridor_length, policy.generic_min_corridor_latency_ms
    return policy.min_corridor_length, policy.min_corridor_latency_ms


def _has_ble_capability(action: Dict[str, Any], policy: BLEMicroRefinementPolicy, capability: str) -> bool:
    return capability in _ble_capabilities(action, policy)


def _action_requires_connectable(action: Dict[str, Any]) -> bool:
    kind = _action_kind(action)
    if kind == "connect":
        return True
    if _action_is_subscribe_like(action):
        return True
    if _action_protocol(action) != "BLE":
        return False
    return True


def _ble_action_is_runtime_transport(action: Dict[str, Any]) -> bool:
    if _action_protocol(action) != "BLE":
        return False
    kind = _action_kind(action)
    marker_hints = [str(item).strip().upper() for item in action.get("marker_hints", []) if str(item).strip()]
    if any(token in marker_hints for token in ("BLE_OP", "BLE_GATT_OP", "BLE_CONNECT")):
        return True
    if kind in {
        "refresh_cover",
        "read_sensor",
        "read_status",
        "set_cover_position",
        "connect",
        "subscribe",
        "set_percentage",
        "turn_on",
        "turn_off",
    }:
        return True
    return str(action.get("target_kind", "") or "").strip() == "ble_device"


def _estimated_action_latency_ms(action: Dict[str, Any]) -> int:
    protocol = _action_protocol(action)
    kind = _action_kind(action)
    if protocol == "BLE":
        return int(_BLE_DURATION_MS.get(kind, _DEFAULT_BLE_DURATION_MS))
    if protocol == "CLOUD":
        if "runtime" in kind:
            return 450
        return 400 if _is_control_like(action) else 350
    if protocol == "LOCAL":
        return 80 if "read_last_message" in kind else 100
    if protocol == "HA":
        return 50
    return 100


def _is_control_like(action: Dict[str, Any]) -> bool:
    kind = _action_kind(action)
    control_tokens = (
        "turn_on",
        "turn_off",
        "set_",
        "open",
        "close",
        "play_media",
        "set_volume",
        "set_cover_position",
    )
    return any(token in kind for token in control_tokens)


def _group_latency_ms(group: List[str], action_lookup: Dict[str, Dict[str, Any]]) -> int:
    if not group:
        return 0
    actions = [action_lookup[action_id] for action_id in group if action_id in action_lookup]
    if not actions:
        return 0
    protocols = {_action_protocol(action) for action in actions}
    costs = [_estimated_action_latency_ms(action) for action in actions]
    if protocols == {"BLE"}:
        return sum(costs)
    if protocols == {"LOCAL"}:
        return max(costs) + max(0, 20 * (len(costs) - 1))
    if protocols == {"HA"}:
        return max(costs) + max(0, 10 * (len(costs) - 1))
    if protocols == {"CLOUD"}:
        return max(costs) + max(0, 120 * (len(costs) - 1))
    return max(costs)


def estimate_plan_latency_ms(plan: ExecutionPlan, target: OptimizationTarget) -> int:
    action_lookup = _action_index(target)
    total = 0
    for batch in plan.ordered_batches:
        if not batch.parallel_groups:
            continue
        total += max(_group_latency_ms(group, action_lookup) for group in batch.parallel_groups)
    return int(total)


def _phase_durations(action: Dict[str, Any], policy: BLEMicroRefinementPolicy) -> Tuple[int, int, int, int]:
    total_ms = _estimated_action_latency_ms(action)
    kind = _action_kind(action)
    adv_min = 30
    connect_min = 40
    xfer_min = 120
    settle_min = 30

    if _action_is_subscribe_like(action):
        adv_target = min(policy.prepare_adv_timeout_ms, max(adv_min, int(round(total_ms * 0.08))))
        connect_target = min(policy.prepare_connect_timeout_ms, max(70, int(round(total_ms * 0.24))))
        settle_target = max(settle_min, int(round(total_ms * 0.12)))
    elif kind == "connect":
        adv_target = min(policy.prepare_adv_timeout_ms, max(adv_min, int(round(total_ms * 0.10))))
        connect_target = min(policy.prepare_connect_timeout_ms, max(75, int(round(total_ms * 0.26))))
        settle_target = max(settle_min, int(round(total_ms * 0.10)))
    else:
        adv_target = min(policy.prepare_adv_timeout_ms, max(adv_min, int(round(total_ms * 0.12))))
        connect_target = min(policy.prepare_connect_timeout_ms, max(connect_min, int(round(total_ms * 0.18))))
        settle_target = max(settle_min, int(round(total_ms * 0.10)))

    adv_ms = adv_target
    connect_ms = connect_target
    settle_ms = settle_target
    xfer_ms = total_ms - adv_ms - connect_ms - settle_ms

    for phase_name, minimum in (("xfer", xfer_min), ("connect", connect_min), ("adv", adv_min), ("settle", settle_min)):
        if xfer_ms >= xfer_min:
            break
        deficit = xfer_min - xfer_ms
        if phase_name == "connect":
            reducible = max(0, connect_ms - connect_min)
            reduction = min(deficit, reducible)
            connect_ms -= reduction
            xfer_ms += reduction
        elif phase_name == "adv":
            reducible = max(0, adv_ms - adv_min)
            reduction = min(deficit, reducible)
            adv_ms -= reduction
            xfer_ms += reduction
        elif phase_name == "settle":
            reducible = max(0, settle_ms - settle_min)
            reduction = min(deficit, reducible)
            settle_ms -= reduction
            xfer_ms += reduction
        elif phase_name == "xfer":
            continue

    if xfer_ms < xfer_min:
        xfer_ms = xfer_min
        total_other = adv_ms + connect_ms + settle_ms
        overflow = total_other + xfer_ms - total_ms
        if overflow > 0:
            settle_cut = min(overflow, max(0, settle_ms - settle_min))
            settle_ms -= settle_cut
            overflow -= settle_cut
        if overflow > 0:
            connect_cut = min(overflow, max(0, connect_ms - connect_min))
            connect_ms -= connect_cut
            overflow -= connect_cut
        if overflow > 0:
            adv_cut = min(overflow, max(0, adv_ms - adv_min))
            adv_ms -= adv_cut
            overflow -= adv_cut
        if overflow > 0:
            settle_ms = max(1, settle_ms - overflow)

    total_now = adv_ms + connect_ms + xfer_ms + settle_ms
    if total_now != total_ms:
        settle_ms += total_ms - total_now
    settle_ms = max(1, settle_ms)
    return adv_ms, connect_ms, xfer_ms, settle_ms


def _expand_serial_corridor(
    action_ids: List[str],
    action_lookup: Dict[str, Dict[str, Any]],
    policy: BLEMicroRefinementPolicy,
) -> List[BLEMicroEvent]:
    events: List[BLEMicroEvent] = []
    cursor = 0
    for action_id in action_ids:
        adv_ms, connect_ms, xfer_ms, settle_ms = _phase_durations(action_lookup[action_id], policy)
        events.append(BLEMicroEvent(action_id, "PREPARE_ADV_SIDE", cursor, cursor + adv_ms))
        cursor += adv_ms
        events.append(BLEMicroEvent(action_id, "PREPARE_CONNECT_SIDE", cursor, cursor + connect_ms))
        cursor += connect_ms
        events.append(BLEMicroEvent(action_id, "BLE_XFER", cursor, cursor + xfer_ms))
        cursor += xfer_ms
        events.append(BLEMicroEvent(action_id, "BLE_SETTLE", cursor, cursor + settle_ms))
        cursor += settle_ms
    return events


def _adv_overlap_admission(
    current_action: Dict[str, Any],
    next_action: Dict[str, Any],
    policy: BLEMicroRefinementPolicy,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if not policy.allow_adv_prepare_overlap:
        reasons.append("adv_overlap_disabled")
        return False, reasons
    if policy.require_shared_scanner and not policy.assume_shared_scanner_available:
        reasons.append("shared_scanner_unavailable")
    current_source = _scanner_source(current_action)
    next_source = _scanner_source(next_action)
    if policy.require_source_resolution_for_adv_overlap:
        if not current_source or not next_source:
            if not policy.allow_unknown_source_adv_overlap:
                reasons.append("scanner_source_unresolved")
    if (
        policy.require_connectable_controller_for_connect_prep
        and _action_requires_connectable(next_action)
        and not policy.assume_connectable_controller_available
    ):
        reasons.append("connectable_controller_unavailable")
    allow_subscribe_overlap = False
    if _action_is_subscribe_like(next_action):
        allow_subscribe_overlap = _allow_conservative_subscribe_adv_overlap(current_action, next_action, policy)
    if _action_is_subscribe_like(next_action) and not (policy.allow_subscribe_like_adv_overlap or allow_subscribe_overlap):
        reasons.append("subscribe_like_next_action")
    current_device = _normalized_device_id(current_action)
    next_device = _normalized_device_id(next_action)
    if current_device and next_device and current_device == next_device and not policy.allow_same_device_adv_overlap:
        reasons.append("same_device_overlap_blocked")
    current_session = _session_group(current_action)
    next_session = _session_group(next_action)
    if current_session and next_session and current_session == next_session and not policy.allow_same_session_adv_overlap:
        reasons.append("same_session_overlap_blocked")
    if policy.prepare_must_be_side_effect_free and _action_is_subscribe_like(next_action) and not allow_subscribe_overlap:
        reasons.append("subscribe_prepare_not_side_effect_free")
    return not reasons, reasons


def _allow_conservative_subscribe_adv_overlap(
    current_action: Dict[str, Any],
    next_action: Dict[str, Any],
    policy: BLEMicroRefinementPolicy,
) -> bool:
    if not _action_is_subscribe_like(next_action):
        return False
    if not (
        _subscribe_adv_overlap_safe_source(next_action, policy)
        or any(
            _has_ble_capability(next_action, policy, capability)
            for capability in policy.allow_subscribe_like_adv_overlap_capabilities
        )
    ):
        return False
    if _action_kind(current_action) != "connect":
        return False
    current_source = _scanner_source(current_action)
    next_source = _scanner_source(next_action)
    if not current_source or not next_source or current_source != next_source:
        return False
    current_device = _normalized_device_id(current_action)
    next_device = _normalized_device_id(next_action)
    if not current_device or not next_device or current_device == next_device:
        return False
    current_session = _session_group(current_action)
    next_session = _session_group(next_action)
    if current_session and next_session and current_session == next_session:
        return False
    if policy.require_connectable_controller_for_connect_prep and not policy.assume_connectable_controller_available:
        return False
    return True


def _allow_adv_anchor_during_connect_prepare(
    current_action: Dict[str, Any],
    next_action: Dict[str, Any],
    policy: BLEMicroRefinementPolicy,
) -> bool:
    ok, _ = _adv_overlap_admission(current_action, next_action, policy)
    if not ok:
        return False
    if _action_kind(current_action) == "connect" or _action_is_subscribe_like(current_action):
        return False
    if not (
        _adv_connect_overlap_safe_source(next_action, policy)
        or any(
            _has_ble_capability(next_action, policy, capability)
            for capability in policy.allow_adv_prepare_during_connect_capabilities
        )
    ):
        return False
    return True


def _connect_overlap_admission(
    current_action: Dict[str, Any],
    next_action: Dict[str, Any],
    policy: BLEMicroRefinementPolicy,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if not policy.allow_connect_prepare_overlap:
        reasons.append("connect_prepare_overlap_disabled")
        return False, reasons
    if policy.require_connectable_controller_for_connect_prep and not policy.assume_connectable_controller_available:
        reasons.append("connectable_controller_unavailable")
    if policy.enforce_connection_slot_guard:
        slot_usage = policy.current_xfer_slot_cost + policy.next_connect_prepare_slot_cost
        if slot_usage > policy.connectable_slot_limit:
            reasons.append("connection_slot_conflict")
    current_device = _normalized_device_id(current_action)
    next_device = _normalized_device_id(next_action)
    if current_device and next_device and current_device == next_device:
        reasons.append("same_device_connect_prepare_blocked")
    return not reasons, reasons


def _expand_conservative_overlap(
    action_ids: List[str],
    action_lookup: Dict[str, Dict[str, Any]],
    policy: BLEMicroRefinementPolicy,
) -> List[BLEMicroEvent]:
    if not action_ids:
        return []

    events: List[BLEMicroEvent] = []
    previous_xfer_start = 0
    previous_xfer_end = 0
    previous_settle_end = 0
    previous_connect_start = 0

    for idx, action_id in enumerate(action_ids):
        action = action_lookup[action_id]
        adv_ms, connect_ms, xfer_ms, settle_ms = _phase_durations(action, policy)

        if idx == 0:
            adv_start = 0
        else:
            previous_action = action_lookup[action_ids[idx - 1]]
            allow_adv, _ = _adv_overlap_admission(previous_action, action, policy)
            if allow_adv:
                if _allow_adv_anchor_during_connect_prepare(previous_action, action, policy):
                    adv_start = previous_connect_start
                else:
                    adv_start = previous_xfer_start
            else:
                adv_start = previous_settle_end
        adv_end = adv_start + adv_ms

        if idx == 0:
            connect_start = adv_end
        else:
            previous_action = action_lookup[action_ids[idx - 1]]
            allow_connect, _ = _connect_overlap_admission(previous_action, action, policy)
            if allow_connect:
                connect_start = max(adv_end, previous_xfer_start)
            else:
                connect_start = max(adv_end, previous_settle_end)
        connect_end = connect_start + connect_ms

        xfer_start = max(connect_end, previous_xfer_end)
        xfer_end = xfer_start + xfer_ms
        settle_start = xfer_end
        settle_end = settle_start + settle_ms

        events.append(BLEMicroEvent(action_id, "PREPARE_ADV_SIDE", adv_start, adv_end))
        events.append(BLEMicroEvent(action_id, "PREPARE_CONNECT_SIDE", connect_start, connect_end))
        events.append(BLEMicroEvent(action_id, "BLE_XFER", xfer_start, xfer_end))
        events.append(BLEMicroEvent(action_id, "BLE_SETTLE", settle_start, settle_end))

        previous_xfer_start = xfer_start
        previous_xfer_end = xfer_end
        previous_settle_end = settle_end
        previous_connect_start = connect_start

    return events


def _completion_order(events: List[BLEMicroEvent]) -> List[str]:
    completion: Dict[str, int] = {}
    for event in events:
        if event.phase == "BLE_SETTLE":
            completion[event.action_id] = event.end_ms
    return [action_id for action_id, _ in sorted(completion.items(), key=lambda item: (item[1], item[0]))]


def validate_refined_corridor(
    coarse_action_ids: List[str],
    refined_events: List[BLEMicroEvent],
    action_lookup: Dict[str, Dict[str, Any]],
    policy: BLEMicroRefinementPolicy,
) -> BLEMicroValidationResult:
    reasons: List[str] = []
    per_action: Dict[str, List[BLEMicroEvent]] = {}
    for event in refined_events:
        per_action.setdefault(event.action_id, []).append(event)

    phase_order_valid = True
    rollback_constraints_ok = True
    for action_id in coarse_action_ids:
        phases = sorted(per_action.get(action_id, []), key=lambda row: row.start_ms)
        names = [event.phase for event in phases]
        if names != list(BLE_MICRO_PHASES):
            phase_order_valid = False
            reasons.append(f"{action_id}:invalid_phase_sequence")
            continue
        for left, right in zip(phases, phases[1:]):
            if left.end_ms > right.start_ms:
                phase_order_valid = False
                reasons.append(f"{action_id}:phase_timing_inversion")
        adv_event, connect_event, _, _ = phases
        if (adv_event.end_ms - adv_event.start_ms) > policy.prepare_adv_timeout_ms:
            rollback_constraints_ok = False
            reasons.append(f"{action_id}:adv_prepare_timeout_exceeded")
        if (connect_event.end_ms - connect_event.start_ms) > policy.prepare_connect_timeout_ms:
            rollback_constraints_ok = False
            reasons.append(f"{action_id}:connect_prepare_timeout_exceeded")

    xfer_events = sorted((event for event in refined_events if event.phase == "BLE_XFER"), key=lambda row: row.start_ms)
    xfer_serialized = True
    for left, right in zip(xfer_events, xfer_events[1:]):
        if left.end_ms > right.start_ms:
            xfer_serialized = False
            reasons.append(f"{left.action_id}->{right.action_id}:xfer_overlap")

    coarse_completion_order_preserved = _completion_order(refined_events) == list(coarse_action_ids)
    if not coarse_completion_order_preserved:
        reasons.append("coarse_completion_order_changed")

    sweep_points = sorted({event.start_ms for event in refined_events} | {event.end_ms for event in refined_events})
    max_active_actions = 0
    for point in sweep_points:
        active = {event.action_id for event in refined_events if event.start_ms <= point < event.end_ms}
        max_active_actions = max(max_active_actions, len(active))
    lookahead_depth_ok = max_active_actions <= (policy.max_lookahead_actions + 1)
    if not lookahead_depth_ok:
        reasons.append(f"lookahead_depth_exceeded:{max_active_actions}")

    scanner_constraints_ok = True
    connectable_constraints_ok = True
    slot_constraints_ok = True
    type_constraints_ok = True

    for left_action_id, right_action_id in zip(coarse_action_ids, coarse_action_ids[1:]):
        left_action = action_lookup[left_action_id]
        right_action = action_lookup[right_action_id]
        left_events = {event.phase: event for event in per_action.get(left_action_id, [])}
        right_events = {event.phase: event for event in per_action.get(right_action_id, [])}
        left_connect = left_events.get("PREPARE_CONNECT_SIDE")
        left_xfer = left_events.get("BLE_XFER")
        left_settle = left_events.get("BLE_SETTLE")
        right_adv = right_events.get("PREPARE_ADV_SIDE")
        right_connect = right_events.get("PREPARE_CONNECT_SIDE")
        if not left_connect or not left_xfer or not left_settle or not right_adv or not right_connect:
            continue
        adv_overlaps = right_adv.start_ms < left_settle.end_ms
        connect_overlaps = right_connect.start_ms < left_settle.end_ms
        if adv_overlaps:
            ok, pair_reasons = _adv_overlap_admission(left_action, right_action, policy)
            if not ok:
                scanner_constraints_ok = False
                type_constraints_ok = False
                reasons.extend(f"{left_action_id}->{right_action_id}:{reason}" for reason in pair_reasons)
            elif right_adv.start_ms < left_xfer.start_ms:
                if not _allow_adv_anchor_during_connect_prepare(left_action, right_action, policy):
                    scanner_constraints_ok = False
                    type_constraints_ok = False
                    reasons.append(f"{left_action_id}->{right_action_id}:connect_phase_adv_anchor_not_allowed")
                if right_adv.start_ms < left_connect.start_ms:
                    scanner_constraints_ok = False
                    reasons.append(f"{left_action_id}->{right_action_id}:adv_prepare_started_before_connect_prepare")
        if connect_overlaps:
            ok, pair_reasons = _connect_overlap_admission(left_action, right_action, policy)
            if not ok:
                connectable_constraints_ok = False
                slot_constraints_ok = False
                reasons.extend(f"{left_action_id}->{right_action_id}:{reason}" for reason in pair_reasons)

    passed = (
        phase_order_valid
        and xfer_serialized
        and coarse_completion_order_preserved
        and lookahead_depth_ok
        and scanner_constraints_ok
        and connectable_constraints_ok
        and slot_constraints_ok
        and type_constraints_ok
        and rollback_constraints_ok
    )
    return BLEMicroValidationResult(
        passed=passed,
        coarse_completion_order_preserved=coarse_completion_order_preserved,
        phase_order_valid=phase_order_valid,
        xfer_serialized=xfer_serialized,
        lookahead_depth_ok=lookahead_depth_ok,
        scanner_constraints_ok=scanner_constraints_ok,
        connectable_constraints_ok=connectable_constraints_ok,
        slot_constraints_ok=slot_constraints_ok,
        type_constraints_ok=type_constraints_ok,
        rollback_constraints_ok=rollback_constraints_ok,
        reasons=reasons,
    )


class ConservativeBLEMicroRefiner:


    def __init__(self, *, policy: BLEMicroRefinementPolicy | None = None) -> None:
        self.policy = policy or BLEMicroRefinementPolicy()

    def _corridor_overlap_candidates(
        self,
        action_ids: List[str],
        action_lookup: Dict[str, Dict[str, Any]],
    ) -> int:
        pairs = 0
        for left_action_id, right_action_id in zip(action_ids, action_ids[1:]):
            ok, _ = _adv_overlap_admission(action_lookup[left_action_id], action_lookup[right_action_id], self.policy)
            if ok:
                pairs += 1
        return pairs

    def _select_corridors(self, plan: ExecutionPlan, target: OptimizationTarget) -> List[BLEMicroCorridor]:
        action_lookup = _action_index(target)
        candidate_rows: List[Tuple[str, str, str]] = []
        for batch in plan.ordered_batches:
            actions = [action_id for group in batch.parallel_groups for action_id in group]
            if len(actions) != 1:
                candidate_rows.append(("", "", ""))
                continue
            action_id = actions[0]
            action = action_lookup.get(action_id)
            if action is None or _action_protocol(action) != "BLE" or not _ble_action_is_runtime_transport(action):
                candidate_rows.append(("", "", ""))
                continue
            candidate_rows.append((batch.batch_id, action_id, _ble_profile_class(action, self.policy)))

        corridors: List[BLEMicroCorridor] = []
        current_batches: List[str] = []
        current_actions: List[str] = []
        current_profile_class = ""
        for batch_id, action_id, profile_class in candidate_rows + [("", "", "")]:
            if batch_id and action_id and (not current_actions or profile_class == current_profile_class):
                current_batches.append(batch_id)
                current_actions.append(action_id)
                current_profile_class = profile_class
                continue
            if current_actions:
                original_latency_ms = sum(_estimated_action_latency_ms(action_lookup[action_id]) for action_id in current_actions)
                overlap_candidate_pairs = self._corridor_overlap_candidates(current_actions, action_lookup)
                min_length, min_latency = _corridor_thresholds(current_profile_class, self.policy)
                if (
                    len(current_actions) >= min_length
                    and original_latency_ms >= min_latency
                    and overlap_candidate_pairs > 0
                ):
                    score = original_latency_ms + 200 * len(current_actions) + 120 * overlap_candidate_pairs
                    corridors.append(
                        BLEMicroCorridor(
                            corridor_id=f"corridor_{len(corridors):02d}",
                            action_ids=list(current_actions),
                            batch_ids=list(current_batches),
                            profile_class=current_profile_class or "generic",
                            original_latency_ms=original_latency_ms,
                            score=score,
                            overlap_candidate_pairs=overlap_candidate_pairs,
                        )
                    )
            current_batches = []
            current_actions = []
            current_profile_class = ""
            if batch_id and action_id:
                current_batches.append(batch_id)
                current_actions.append(action_id)
                current_profile_class = profile_class

        corridors.sort(key=lambda row: (-row.score, row.corridor_id))
        return corridors

    def _refine_corridor(
        self,
        corridor: BLEMicroCorridor,
        target: OptimizationTarget,
    ) -> BLEMicroCorridorResult:
        action_lookup = _action_index(target)
        serial_events = _expand_serial_corridor(corridor.action_ids, action_lookup, self.policy)
        refined_events = _expand_conservative_overlap(corridor.action_ids, action_lookup, self.policy)
        validation = validate_refined_corridor(corridor.action_ids, refined_events, action_lookup, self.policy)
        refined_latency_ms = max((event.end_ms for event in refined_events), default=0)
        latency_saved_ms = max(0, corridor.original_latency_ms - refined_latency_ms) if validation.passed else 0
        return BLEMicroCorridorResult(
            corridor=corridor,
            serial_events=serial_events,
            refined_events=refined_events,
            refined_latency_ms=refined_latency_ms,
            latency_saved_ms=latency_saved_ms,
            validation=validation,
        )

    def _refined_plan_overlay(self, plan: ExecutionPlan, results: List[BLEMicroCorridorResult]) -> ExecutionPlan:
        plan_copy = ExecutionPlan(
            ordered_batches=[
                Batch(
                    batch_id=batch.batch_id,
                    parallel_groups=[list(group) for group in batch.parallel_groups],
                    constraints=list(batch.constraints),
                    session_policy=dict(batch.session_policy),
                    rate_policy=dict(batch.rate_policy),
                    guards=[dict(item) for item in batch.guards],
                    fallback=[dict(item) for item in batch.fallback],
                )
                for batch in plan.ordered_batches
            ],
            meta=dict(plan.meta),
        )
        plan_copy.meta.setdefault("ble_micro_refinement", {})
        plan_copy.meta["ble_micro_refinement"] = {
            "enabled": True,
            "strategy": "ha_conservative_adv_prepare_overlap",
            "micro_phases": list(BLE_MICRO_PHASES),
            "policy": self.policy.to_dict(),
            "corridors": [
                {
                    "corridor_id": row.corridor.corridor_id,
                    "action_ids": list(row.corridor.action_ids),
                    "batch_ids": list(row.corridor.batch_ids),
                    "profile_class": row.corridor.profile_class,
                    "original_latency_ms": row.corridor.original_latency_ms,
                    "overlap_candidate_pairs": row.corridor.overlap_candidate_pairs,
                    "refined_latency_ms": row.refined_latency_ms,
                    "latency_saved_ms": row.latency_saved_ms,
                    "validation_passed": row.validation.passed,
                }
                for row in results
            ],
        }
        return plan_copy

    def refine_case(
        self,
        *,
        vdev_id: str,
        case_name: str,
        target: OptimizationTarget,
        plan: ExecutionPlan,
    ) -> BLEMicroCaseResult:
        original_total_ms = estimate_plan_latency_ms(plan, target)
        corridors = self._select_corridors(plan, target)
        corridor_results = [self._refine_corridor(corridor, target) for corridor in corridors]
        total_saved_ms = sum(result.latency_saved_ms for result in corridor_results if result.validation.passed)
        refined_total_ms = max(0, original_total_ms - total_saved_ms)
        refined_plan = self._refined_plan_overlay(plan, corridor_results)
        return BLEMicroCaseResult(
            vdev_id=vdev_id,
            case_name=case_name,
            selected_corridors=corridor_results,
            original_estimated_latency_ms=original_total_ms,
            refined_estimated_latency_ms=refined_total_ms,
            added_savings_ms=total_saved_ms,
            added_savings_ratio=(float(total_saved_ms) / float(original_total_ms)) if original_total_ms else 0.0,
            refined_plan=refined_plan,
        )


def execution_plan_from_dict(payload: Dict[str, Any]) -> ExecutionPlan:
    batches: List[Batch] = []
    for row in payload.get("ordered_batches", []):
        if not isinstance(row, dict):
            continue
        batches.append(
            Batch(
                batch_id=str(row.get("batch_id", "")).strip(),
                parallel_groups=[
                    [str(action_id).strip() for action_id in group if str(action_id).strip()]
                    for group in row.get("parallel_groups", [])
                    if isinstance(group, list)
                ],
                constraints=[str(item).strip() for item in row.get("constraints", []) if str(item).strip()],
                session_policy=dict(row.get("session_policy", {})) if isinstance(row.get("session_policy", {}), dict) else {},
                rate_policy=dict(row.get("rate_policy", {})) if isinstance(row.get("rate_policy", {}), dict) else {},
                guards=[dict(item) for item in row.get("guards", []) if isinstance(item, dict)],
                fallback=[dict(item) for item in row.get("fallback", []) if isinstance(item, dict)],
            )
        )
    return ExecutionPlan(ordered_batches=batches, meta=dict(payload.get("meta", {})) if isinstance(payload.get("meta", {}), dict) else {})
