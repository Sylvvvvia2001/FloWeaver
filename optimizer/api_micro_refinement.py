from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from dsl.contracts import Batch, ExecutionPlan, OptimizationTarget


COMMON_API_MICRO_PHASES = (
    "API_PREPARE",
    "API_SESSION_READY",
    "API_REQUEST_SEND",
    "API_RESPONSE_RECV",
    "API_PARSE_NORMALIZE",
    "API_AGGREGATE",
    "HA_STATE_WRITE",
)

CLOUD_MICRO_PHASES = (
    "CLOUD_AUTH_CHECK",
    "CLOUD_RATE_BUDGET_CHECK",
    "API_PREPARE",
    "API_SESSION_READY",
    "CLOUD_REQUEST_SEND",
    "API_RESPONSE_RECV",
    "CLOUD_BACKOFF_WAIT",
    "API_PARSE_NORMALIZE",
    "API_AGGREGATE",
    "CLOUD_BATCH_GROUP_COMMIT",
    "HA_STATE_WRITE",
)

LOCAL_HTTP_MICRO_PHASES = (
    "LOCAL_ENDPOINT_RESOLVE",
    "LOCAL_SESSION_READY",
    "LOCAL_REQUEST_SEND",
    "LOCAL_RESPONSE_RECV",
    "LOCAL_PARSE",
    "LOCAL_CACHE_UPDATE",
    "HA_STATE_WRITE",
)

MQTT_MICRO_PHASES = (
    "MQTT_LAST_MSG_READ",
    "MQTT_CACHE_PARSE",
    "HA_STATE_WRITE",
)

_API_DURATION_MS: Dict[str, int] = {
    "status": 350,
    "read_runtime": 450,
    "turn_on": 400,
    "turn_off": 380,
    "set_temperature": 420,
    "set_hvac_mode": 420,
    "set_fan_mode": 400,
    "set_percentage": 390,
    "get_state": 100,
    "read_last_message": 80,
}

_DEFAULT_API_DURATION_MS = 120


@dataclass(frozen=True)
class APIMicroRefinementPolicy:
    min_corridor_length: int = 2
    min_corridor_latency_ms: int = 700
    cloud_read_min_corridor_length: int = 2
    cloud_read_min_corridor_latency_ms: int = 700
    cloud_control_min_corridor_length: int = 2
    cloud_control_min_corridor_latency_ms: int = 760
    local_http_read_min_corridor_length: int = 2
    local_http_read_min_corridor_latency_ms: int = 180
    local_http_control_min_corridor_length: int = 2
    local_http_control_min_corridor_latency_ms: int = 220
    mqtt_read_min_corridor_length: int = 3
    mqtt_read_min_corridor_latency_ms: int = 220
    max_lookahead_steps: int = 1
    require_coordinator_style_fetch: bool = True
    disallow_entity_level_overlap: bool = True
    preserve_refresh_cadence: bool = True
    require_shared_web_session: bool = True
    allow_local_prepare_overlap: bool = True
    allow_cloud_prepare_overlap: bool = True
    allow_cloud_auth_budget_overlap: bool = True
    local_endpoint_concurrency_limit: int = 1
    local_session_concurrency_limit: int = 1
    cloud_host_concurrency_limit: int = 1
    cloud_bucket_concurrency_limit: int = 1
    keep_writeback_serialized: bool = True
    disallow_parse_aggregate_cross_action_overlap: bool = True
    disallow_backoff_bypass: bool = True
    parse_async_safe_max_ms: int = 220
    aggregate_async_safe_max_ms: int = 180
    availability_must_precede_write: bool = True
    require_known_session_key: bool = True
    require_known_host_key: bool = True
    require_known_endpoint_key: bool = False
    require_known_bucket_key: bool = False
    cloud_backoff_wait_ms: int = 220
    treat_mqtt_as_non_overlap_lane: bool = True

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "APIMicroRefinementPolicy":
        if not isinstance(payload, dict):
            return cls()
        fields = {name: payload[name] for name in cls.__dataclass_fields__ if name in payload}
        return cls(**fields)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class APIMicroEvent:
    step_id: str
    phase: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class APIBatchStep:
    step_id: str
    batch_id: str
    protocol: str
    phase_kind: str
    capability_class: str
    action_ids: List[str]
    latency_ms: int
    host_key: str
    bucket_key: str
    session_key: str
    endpoint_key: str
    has_backoff_wait: bool


@dataclass
class APIMicroCorridor:
    corridor_id: str
    protocol: str
    phase_kind: str
    capability_class: str
    step_ids: List[str]
    batch_ids: List[str]
    action_ids: List[str]
    original_latency_ms: int
    score: int
    overlap_candidate_pairs: int = 0


@dataclass
class APIMicroValidationResult:
    passed: bool
    coarse_completion_order_preserved: bool
    phase_order_valid: bool
    request_send_constraints_ok: bool
    lookahead_depth_ok: bool
    coordinator_constraints_ok: bool
    parallel_updates_constraints_ok: bool
    session_constraints_ok: bool
    backoff_constraints_ok: bool
    writeback_constraints_ok: bool
    event_loop_constraints_ok: bool
    cadence_constraints_ok: bool
    availability_constraints_ok: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class APIMicroCorridorResult:
    corridor: APIMicroCorridor
    serial_events: List[APIMicroEvent]
    refined_events: List[APIMicroEvent]
    refined_latency_ms: int
    latency_saved_ms: int
    validation: APIMicroValidationResult


@dataclass
class APIMicroCaseResult:
    vdev_id: str
    case_name: str
    selected_corridors: List[APIMicroCorridorResult]
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
    return str(exec_cfg.get("service", "") or "").strip().lower() or "unknown"


def _action_exec(action: Dict[str, Any]) -> Dict[str, Any]:
    return dict(action.get("exec", {})) if isinstance(action.get("exec", {}), dict) else {}


def _action_data_template(action: Dict[str, Any]) -> Dict[str, Any]:
    exec_cfg = _action_exec(action)
    return dict(exec_cfg.get("data_template", {})) if isinstance(exec_cfg.get("data_template", {}), dict) else {}


def _target_key(action: Dict[str, Any]) -> str:
    target = dict(action.get("target", {})) if isinstance(action.get("target", {}), dict) else {}
    for value in (target.get("endpoint"), target.get("device_id"), target.get("id")):
        token = str(value or "").strip()
        if token:
            return token
    data = _action_data_template(action)
    for value in (data.get("endpoint"), data.get("device_id")):
        token = str(value or "").strip()
        if token:
            return token
    return ""


def _host_key(action: Dict[str, Any]) -> str:
    data = _action_data_template(action)
    exec_cfg = _action_exec(action)
    for value in (data.get("host_group_key"), exec_cfg.get("provider")):
        token = str(value or "").strip()
        if token:
            return token
    target_key = _target_key(action)
    if ":" in target_key:
        return target_key.split(":", 1)[0]
    return ""


def _bucket_key(action: Dict[str, Any]) -> str:
    data = _action_data_template(action)
    for value in (data.get("endpoint_group_key"), data.get("bucket_key")):
        token = str(value or "").strip()
        if token:
            return token
    return _host_key(action)


def _session_key(action: Dict[str, Any]) -> str:
    data = _action_data_template(action)
    for value in (data.get("session_group_key"), data.get("host_group_key")):
        token = str(value or "").strip()
        if token:
            return token
    return _host_key(action)


def _endpoint_key(action: Dict[str, Any]) -> str:
    data = _action_data_template(action)
    for value in (data.get("endpoint"), data.get("device_id")):
        token = str(value or "").strip()
        if token:
            return token
    return _target_key(action)


def _is_control_like(action: Dict[str, Any]) -> bool:
    kind = _action_kind(action)
    return any(
        token in kind
        for token in (
            "turn_on",
            "turn_off",
            "set_",
            "open",
            "close",
            "play_media",
            "set_volume",
        )
    )


def _is_mqtt_like(action: Dict[str, Any]) -> bool:
    kind = _action_kind(action)
    exec_cfg = _action_exec(action)
    service = str(exec_cfg.get("service", "") or "").strip().lower()
    target_key = _target_key(action)
    return "read_last_message" in kind or "read_last_message" in service or target_key.startswith("mqtt:")


def _is_runtime_api_action(action: Dict[str, Any]) -> bool:
    protocol = _action_protocol(action)
    if protocol not in {"CLOUD", "LOCAL"}:
        return False
    if str(action.get("target_kind", "") or "").strip() == "state_write":
        return False
    exec_cfg = _action_exec(action)
    return str(exec_cfg.get("kind", "") or "").strip() == "ha_service_call"


def _estimated_action_latency_ms(action: Dict[str, Any]) -> int:
    protocol = _action_protocol(action)
    kind = _action_kind(action)
    if protocol == "CLOUD":
        if "runtime" in kind:
            return 450
        return 400 if _is_control_like(action) else 350
    if protocol == "LOCAL":
        return 80 if _is_mqtt_like(action) else 100
    if protocol == "HA":
        return 50
    return int(_API_DURATION_MS.get(kind, _DEFAULT_API_DURATION_MS))


def _group_latency_ms(group: Sequence[str], action_lookup: Dict[str, Dict[str, Any]]) -> int:
    if not group:
        return 0
    actions = [action_lookup[action_id] for action_id in group if action_id in action_lookup]
    if not actions:
        return 0
    protocols = {_action_protocol(action) for action in actions}
    costs = [_estimated_action_latency_ms(action) for action in actions]
    if protocols == {"LOCAL"}:
        return max(costs) + max(0, 20 * (len(costs) - 1))
    if protocols == {"CLOUD"}:
        return max(costs) + max(0, 120 * (len(costs) - 1))
    if protocols == {"HA"}:
        return max(costs) + max(0, 10 * (len(costs) - 1))
    return max(costs)


def estimate_plan_latency_ms(plan: ExecutionPlan, target: OptimizationTarget) -> int:
    action_lookup = _action_index(target)
    total = 0
    for batch in plan.ordered_batches:
        if not batch.parallel_groups:
            continue
        total += max(_group_latency_ms(group, action_lookup) for group in batch.parallel_groups)
    return int(total)


def _batch_actions(batch: Batch) -> List[str]:
    return [action_id for group in batch.parallel_groups for action_id in group]


def _batch_latency_ms(batch: Batch, action_lookup: Dict[str, Dict[str, Any]]) -> int:
    if not batch.parallel_groups:
        return 0
    return max(_group_latency_ms(group, action_lookup) for group in batch.parallel_groups)


def _batch_protocol(batch: Batch, action_lookup: Dict[str, Dict[str, Any]]) -> str:
    protocols = {_action_protocol(action_lookup[action_id]) for action_id in _batch_actions(batch) if action_id in action_lookup}
    return next(iter(protocols)) if len(protocols) == 1 else ""


def _batch_phase_kind(batch: Batch, action_lookup: Dict[str, Dict[str, Any]]) -> str:
    protocol = _batch_protocol(batch, action_lookup)
    if protocol == "CLOUD":
        return "CLOUD"
    if protocol != "LOCAL":
        return ""
    actions = [action_lookup[action_id] for action_id in _batch_actions(batch) if action_id in action_lookup]
    if not actions:
        return ""
    if all(_is_mqtt_like(action) for action in actions):
        return "MQTT"
    return "LOCAL_HTTP"


def _batch_all_runtime_api(batch: Batch, action_lookup: Dict[str, Dict[str, Any]]) -> bool:
    actions = [action_lookup[action_id] for action_id in _batch_actions(batch) if action_id in action_lookup]
    return bool(actions) and all(_is_runtime_api_action(action) for action in actions)


def _batch_backoff_barrier(batch: Batch) -> bool:
    normalized_constraints = {str(item).strip().upper() for item in batch.constraints if str(item).strip()}
    if normalized_constraints & {"BACKOFF", "BACKOFF_WAIT", "RETRY_AFTER", "RATE_LIMIT_BACKOFF"}:
        return True

    if isinstance(batch.rate_policy, dict):
        for key in ("retry_after_ms", "retry_after_s", "backoff_ms", "backoff_wait_ms"):
            value = batch.rate_policy.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return True

    for item in batch.guards + batch.fallback:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "") or "").strip().upper()
        action = str(item.get("action", "") or "").strip().upper()
        expr = str(item.get("expr", "") or "").strip().upper()
        params = dict(item.get("params", {})) if isinstance(item.get("params", {}), dict) else {}
        if kind in {"BACKOFF", "BACKOFF_WAIT", "RETRY_AFTER", "RATE_LIMIT_BACKOFF"}:
            return True
        if action in {"WAIT_BACKOFF", "HONOR_BACKOFF", "RETRY_AFTER"}:
            return True
        if any(key in params for key in ("retry_after_ms", "retry_after_s", "backoff_ms", "backoff_wait_ms")):
            return True
        if "RETRY_AFTER" in expr or "BACKOFF" in expr:
            return True
    return False


def _make_step(batch: Batch, action_lookup: Dict[str, Dict[str, Any]]) -> APIBatchStep | None:
    if not _batch_all_runtime_api(batch, action_lookup):
        return None
    protocol = _batch_protocol(batch, action_lookup)
    phase_kind = _batch_phase_kind(batch, action_lookup)
    if protocol not in {"CLOUD", "LOCAL"} or not phase_kind:
        return None
    actions = [action_lookup[action_id] for action_id in _batch_actions(batch) if action_id in action_lookup]
    host_keys = {_host_key(action) for action in actions if _host_key(action)}
    bucket_keys = {_bucket_key(action) for action in actions if _bucket_key(action)}
    session_keys = {_session_key(action) for action in actions if _session_key(action)}
    endpoint_keys = {_endpoint_key(action) for action in actions if _endpoint_key(action)}
    return APIBatchStep(
        step_id=batch.batch_id,
        batch_id=batch.batch_id,
        protocol=protocol,
        phase_kind=phase_kind,
        capability_class=_step_capability_class(protocol, phase_kind, actions),
        action_ids=[action_id for action_id in _batch_actions(batch) if action_id in action_lookup],
        latency_ms=_batch_latency_ms(batch, action_lookup),
        host_key=next(iter(host_keys), "") if len(host_keys) == 1 else "",
        bucket_key=next(iter(bucket_keys), "") if len(bucket_keys) == 1 else "",
        session_key=next(iter(session_keys), "") if len(session_keys) == 1 else "",
        endpoint_key=next(iter(endpoint_keys), "") if len(endpoint_keys) == 1 else "",
        has_backoff_wait=_batch_backoff_barrier(batch),
    )


def _step_capability_class(protocol: str, phase_kind: str, actions: Sequence[Dict[str, Any]]) -> str:
    if phase_kind == "MQTT":
        return "mqtt_read"
    if protocol == "CLOUD":
        return "cloud_control" if any(_is_control_like(action) for action in actions) else "cloud_read"
    if phase_kind == "LOCAL_HTTP":
        return "local_http_control" if any(_is_control_like(action) for action in actions) else "local_http_read"
    return "generic_api"


def _corridor_thresholds(capability_class: str, policy: APIMicroRefinementPolicy) -> Tuple[int, int]:
    mapping = {
        "cloud_read": (policy.cloud_read_min_corridor_length, policy.cloud_read_min_corridor_latency_ms),
        "cloud_control": (policy.cloud_control_min_corridor_length, policy.cloud_control_min_corridor_latency_ms),
        "local_http_read": (policy.local_http_read_min_corridor_length, policy.local_http_read_min_corridor_latency_ms),
        "local_http_control": (policy.local_http_control_min_corridor_length, policy.local_http_control_min_corridor_latency_ms),
        "mqtt_read": (policy.mqtt_read_min_corridor_length, policy.mqtt_read_min_corridor_latency_ms),
    }
    return mapping.get(capability_class, (policy.min_corridor_length, policy.min_corridor_latency_ms))


def _phase_sequence(step: APIBatchStep) -> Tuple[str, ...]:
    if step.phase_kind == "CLOUD":
        return CLOUD_MICRO_PHASES
    if step.phase_kind == "MQTT":
        return MQTT_MICRO_PHASES
    return LOCAL_HTTP_MICRO_PHASES


def _allocate_phase_durations(total_ms: int, specs: Sequence[Tuple[str, int, int]]) -> Dict[str, int]:
    if total_ms <= 0:
        return {name: 0 for name, _, _ in specs}

    min_total = sum(min_ms for _, min_ms, _ in specs)
    if min_total >= total_ms:
        durations: Dict[str, int] = {}
        scaled_total = 0
        for index, (name, min_ms, _) in enumerate(specs):
            if index == len(specs) - 1:
                dur = max(0, total_ms - scaled_total)
            else:
                dur = max(0, int(round(float(min_ms) * float(total_ms) / float(min_total))))
                scaled_total += dur
            durations[name] = dur
        drift = total_ms - sum(durations.values())
        if drift:
            tail = list(durations)[-1]
            durations[tail] += drift
        return durations

    durations = {name: min_ms for name, min_ms, _ in specs}
    remaining = total_ms - min_total
    weight_total = sum(weight for _, _, weight in specs if weight > 0)
    allocated = 0
    for index, (name, _, weight) in enumerate(specs):
        if index == len(specs) - 1:
            extra = remaining - allocated
        else:
            extra = 0 if weight_total <= 0 else int(round(float(remaining) * float(weight) / float(weight_total)))
            allocated += extra
        durations[name] += max(0, extra)
    drift = total_ms - sum(durations.values())
    if drift:
        tail = list(durations)[-1]
        durations[tail] += drift
    return durations


def _phase_durations(step: APIBatchStep, policy: APIMicroRefinementPolicy) -> Dict[str, int]:
    total_ms = step.latency_ms
    if step.phase_kind == "CLOUD":
        phases = _allocate_phase_durations(
            total_ms,
            [
                ("CLOUD_AUTH_CHECK", 10, 5),
                ("CLOUD_RATE_BUDGET_CHECK", 8, 4),
                ("API_PREPARE", 14, 8),
                ("API_SESSION_READY", 8, 4),
                ("CLOUD_REQUEST_SEND", 24, 18),
                ("API_RESPONSE_RECV", 24, 16),
                ("CLOUD_BACKOFF_WAIT", policy.cloud_backoff_wait_ms if step.has_backoff_wait else 0, 0),
                ("API_PARSE_NORMALIZE", 12, 8),
                ("API_AGGREGATE", 10, 6),
                ("CLOUD_BATCH_GROUP_COMMIT", 8, 4),
                ("HA_STATE_WRITE", 8, 3),
            ],
        )
    elif step.phase_kind == "MQTT":
        phases = _allocate_phase_durations(
            total_ms,
            [
                ("MQTT_LAST_MSG_READ", 20, 12),
                ("MQTT_CACHE_PARSE", 12, 6),
                ("HA_STATE_WRITE", 8, 2),
            ],
        )
    else:
        phases = _allocate_phase_durations(
            total_ms,
            [
                ("LOCAL_ENDPOINT_RESOLVE", 12, 8),
                ("LOCAL_SESSION_READY", 10, 6),
                ("LOCAL_REQUEST_SEND", 18, 14),
                ("LOCAL_RESPONSE_RECV", 18, 12),
                ("LOCAL_PARSE", 12, 8),
                ("LOCAL_CACHE_UPDATE", 10, 5),
                ("HA_STATE_WRITE", 8, 3),
            ],
        )
    return phases


def _serial_events_for_steps(steps: Sequence[APIBatchStep], policy: APIMicroRefinementPolicy) -> List[APIMicroEvent]:
    events: List[APIMicroEvent] = []
    cursor = 0
    for step in steps:
        durations = _phase_durations(step, policy)
        for phase in _phase_sequence(step):
            dur = durations.get(phase, 0)
            events.append(APIMicroEvent(step.step_id, phase, cursor, cursor + dur))
            cursor += dur
    return events


def _local_prepare_overlap_admission(
    left: APIBatchStep,
    right: APIBatchStep,
    policy: APIMicroRefinementPolicy,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if not policy.allow_local_prepare_overlap:
        reasons.append("local_prepare_overlap_disabled")
    if left.protocol != "LOCAL" or right.protocol != "LOCAL":
        reasons.append("local_protocol_mismatch")
    if left.phase_kind != "LOCAL_HTTP" or right.phase_kind != "LOCAL_HTTP":
        reasons.append("local_phase_kind_unsupported")
    if policy.require_shared_web_session and policy.require_known_session_key and (not left.session_key or not right.session_key):
        reasons.append("local_session_key_unresolved")
    if policy.require_known_endpoint_key and (not left.endpoint_key or not right.endpoint_key):
        reasons.append("local_endpoint_key_unresolved")
    return not reasons, reasons


def _cloud_prepare_overlap_admission(
    left: APIBatchStep,
    right: APIBatchStep,
    policy: APIMicroRefinementPolicy,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if not policy.allow_cloud_prepare_overlap:
        reasons.append("cloud_prepare_overlap_disabled")
    if left.protocol != "CLOUD" or right.protocol != "CLOUD":
        reasons.append("cloud_protocol_mismatch")
    if left.phase_kind != "CLOUD" or right.phase_kind != "CLOUD":
        reasons.append("cloud_phase_kind_unsupported")
    if policy.require_known_host_key and (not left.host_key or not right.host_key):
        reasons.append("cloud_host_key_unresolved")
    if policy.require_known_bucket_key and (not left.bucket_key or not right.bucket_key):
        reasons.append("cloud_bucket_key_unresolved")
    if left.has_backoff_wait and policy.disallow_backoff_bypass and left.host_key and right.host_key and left.host_key == right.host_key:
        reasons.append("cloud_backoff_barrier")
    return not reasons, reasons


def _completion_order(events: Sequence[APIMicroEvent]) -> List[str]:
    completion: Dict[str, int] = {}
    for event in events:
        completion[event.step_id] = max(completion.get(event.step_id, 0), event.end_ms)
    return [step_id for step_id, _ in sorted(completion.items(), key=lambda item: (item[1], item[0]))]


def _expand_refined_steps(steps: Sequence[APIBatchStep], policy: APIMicroRefinementPolicy) -> List[APIMicroEvent]:
    if not steps:
        return []

    events: List[APIMicroEvent] = []
    previous: Dict[str, APIMicroEvent] = {}

    for index, step in enumerate(steps):
        durations = _phase_durations(step, policy)
        step_events: Dict[str, APIMicroEvent] = {}
        phases = list(_phase_sequence(step))

        if index == 0:
            cursor = 0
            for phase in phases:
                dur = durations.get(phase, 0)
                step_events[phase] = APIMicroEvent(step.step_id, phase, cursor, cursor + dur)
                cursor += dur
            previous = step_events
            events.extend(step_events[phase] for phase in phases)
            continue

        previous_step = steps[index - 1]
        post_cursor = previous["HA_STATE_WRITE"].end_ms

        if step.phase_kind == "LOCAL_HTTP":
            admitted, _ = _local_prepare_overlap_admission(previous_step, step, policy)
            overlap_phases = ["LOCAL_ENDPOINT_RESOLVE", "LOCAL_SESSION_READY"] if admitted else []
            left_request = previous["LOCAL_REQUEST_SEND"]
            left_response = previous["LOCAL_RESPONSE_RECV"]
            overlap_total = sum(durations.get(phase, 0) for phase in overlap_phases)
            overlap_end = left_response.end_ms
            overlap_start = max(left_request.start_ms, overlap_end - overlap_total)
            cursor = overlap_start
            for phase in overlap_phases:
                dur = durations.get(phase, 0)
                step_events[phase] = APIMicroEvent(step.step_id, phase, cursor, cursor + dur)
                cursor += dur
        elif step.phase_kind == "CLOUD":
            admitted, _ = _cloud_prepare_overlap_admission(previous_step, step, policy)
            overlap_phases = []
            if admitted:
                if policy.allow_cloud_auth_budget_overlap:
                    overlap_phases.extend(["CLOUD_AUTH_CHECK", "CLOUD_RATE_BUDGET_CHECK"])
                overlap_phases.append("API_PREPARE")
            left_request = previous["CLOUD_REQUEST_SEND"]
            left_response = previous["API_RESPONSE_RECV"]
            overlap_total = sum(durations.get(phase, 0) for phase in overlap_phases)
            overlap_end = left_response.end_ms
            overlap_start = max(left_request.start_ms, overlap_end - overlap_total)
            cursor = overlap_start
            for phase in overlap_phases:
                dur = durations.get(phase, 0)
                step_events[phase] = APIMicroEvent(step.step_id, phase, cursor, cursor + dur)
                cursor += dur

        for phase in phases:
            if phase in step_events:
                continue
            dur = durations.get(phase, 0)
            step_events[phase] = APIMicroEvent(step.step_id, phase, post_cursor, post_cursor + dur)
            post_cursor += dur

        previous = step_events
        events.extend(step_events[phase] for phase in phases)
    return events


def validate_refined_corridor(
    corridor: APIMicroCorridor,
    steps: Sequence[APIBatchStep],
    refined_events: Sequence[APIMicroEvent],
    policy: APIMicroRefinementPolicy,
) -> APIMicroValidationResult:
    reasons: List[str] = []
    per_step: Dict[str, List[APIMicroEvent]] = {}
    for event in refined_events:
        per_step.setdefault(event.step_id, []).append(event)

    phase_order_valid = True
    request_send_constraints_ok = True
    coordinator_constraints_ok = True
    parallel_updates_constraints_ok = True
    session_constraints_ok = True
    backoff_constraints_ok = True
    writeback_constraints_ok = True
    event_loop_constraints_ok = True
    cadence_constraints_ok = True
    availability_constraints_ok = True

    for step in steps:
        step_events = sorted(per_step.get(step.step_id, []), key=lambda row: row.start_ms)
        expected = list(_phase_sequence(step))
        actual = [event.phase for event in step_events]
        if actual != expected:
            phase_order_valid = False
            reasons.append(f"{step.step_id}:invalid_phase_sequence")
            continue
        for left, right in zip(step_events, step_events[1:]):
            if left.end_ms > right.start_ms:
                phase_order_valid = False
                reasons.append(f"{step.step_id}:phase_overlap")

        phase_map = {event.phase: event for event in step_events}
        if step.phase_kind == "LOCAL_HTTP":
            parse_event = phase_map.get("LOCAL_PARSE")
            aggregate_event = phase_map.get("LOCAL_CACHE_UPDATE")
            write_event = phase_map.get("HA_STATE_WRITE")
            if parse_event and (parse_event.end_ms - parse_event.start_ms) > policy.parse_async_safe_max_ms:
                event_loop_constraints_ok = False
                reasons.append(f"{step.step_id}:local_parse_budget_exceeded")
            if aggregate_event and (aggregate_event.end_ms - aggregate_event.start_ms) > policy.aggregate_async_safe_max_ms:
                event_loop_constraints_ok = False
                reasons.append(f"{step.step_id}:local_cache_budget_exceeded")
            if policy.availability_must_precede_write and aggregate_event and write_event and aggregate_event.end_ms > write_event.start_ms:
                availability_constraints_ok = False
                reasons.append(f"{step.step_id}:local_availability_write_order_broken")
        elif step.phase_kind == "CLOUD":
            parse_event = phase_map.get("API_PARSE_NORMALIZE")
            aggregate_event = phase_map.get("API_AGGREGATE")
            commit_event = phase_map.get("CLOUD_BATCH_GROUP_COMMIT")
            write_event = phase_map.get("HA_STATE_WRITE")
            if parse_event and (parse_event.end_ms - parse_event.start_ms) > policy.parse_async_safe_max_ms:
                event_loop_constraints_ok = False
                reasons.append(f"{step.step_id}:cloud_parse_budget_exceeded")
            if aggregate_event and (aggregate_event.end_ms - aggregate_event.start_ms) > policy.aggregate_async_safe_max_ms:
                event_loop_constraints_ok = False
                reasons.append(f"{step.step_id}:cloud_aggregate_budget_exceeded")
            if policy.availability_must_precede_write and commit_event and write_event and commit_event.end_ms > write_event.start_ms:
                availability_constraints_ok = False
                reasons.append(f"{step.step_id}:cloud_availability_write_order_broken")
        else:
            parse_event = phase_map.get("MQTT_CACHE_PARSE")
            write_event = phase_map.get("HA_STATE_WRITE")
            if parse_event and (parse_event.end_ms - parse_event.start_ms) > policy.parse_async_safe_max_ms:
                event_loop_constraints_ok = False
                reasons.append(f"{step.step_id}:mqtt_parse_budget_exceeded")
            if policy.availability_must_precede_write and parse_event and write_event and parse_event.end_ms > write_event.start_ms:
                availability_constraints_ok = False
                reasons.append(f"{step.step_id}:mqtt_availability_write_order_broken")

    coarse_completion_order_preserved = _completion_order(refined_events) == corridor.step_ids
    if not coarse_completion_order_preserved:
        reasons.append("coarse_completion_order_changed")

    sweep_points = sorted({event.start_ms for event in refined_events} | {event.end_ms for event in refined_events})
    max_active_steps = 0
    for point in sweep_points:
        active = {event.step_id for event in refined_events if event.start_ms <= point < event.end_ms}
        max_active_steps = max(max_active_steps, len(active))
    lookahead_depth_ok = max_active_steps <= (policy.max_lookahead_steps + 1)
    if not lookahead_depth_ok:
        reasons.append(f"lookahead_depth_exceeded:{max_active_steps}")

    for left_step, right_step in zip(steps, steps[1:]):
        left_map = {event.phase: event for event in per_step.get(left_step.step_id, [])}
        right_map = {event.phase: event for event in per_step.get(right_step.step_id, [])}

        if left_step.phase_kind == "LOCAL_HTTP" and right_step.phase_kind == "LOCAL_HTTP":
            resolve = right_map.get("LOCAL_ENDPOINT_RESOLVE")
            session = right_map.get("LOCAL_SESSION_READY")
            left_request = left_map.get("LOCAL_REQUEST_SEND")
            left_response = left_map.get("LOCAL_RESPONSE_RECV")
            left_write = left_map.get("HA_STATE_WRITE")
            right_request = right_map.get("LOCAL_REQUEST_SEND")
            if resolve and left_request and left_response and left_write:
                overlap = resolve.start_ms < left_write.end_ms
                if overlap:
                    ok, pair_reasons = _local_prepare_overlap_admission(left_step, right_step, policy)
                    if not ok:
                        session_constraints_ok = False
                        reasons.extend(f"{left_step.step_id}->{right_step.step_id}:{reason}" for reason in pair_reasons)
                    if resolve.start_ms < left_request.start_ms:
                        request_send_constraints_ok = False
                        reasons.append(f"{left_step.step_id}->{right_step.step_id}:local_prepare_started_too_early")
                    if session and session.end_ms > left_response.end_ms:
                        request_send_constraints_ok = False
                        reasons.append(f"{left_step.step_id}->{right_step.step_id}:local_prepare_window_violation")
                if right_request and right_request.start_ms < left_write.end_ms:
                    request_send_constraints_ok = False
                    reasons.append(f"{left_step.step_id}->{right_step.step_id}:local_request_send_overlap")
                if policy.disallow_entity_level_overlap and right_request and right_request.start_ms < left_write.end_ms:
                    parallel_updates_constraints_ok = False
                    reasons.append(f"{left_step.step_id}->{right_step.step_id}:entity_level_overlap_detected")

        elif left_step.phase_kind == "CLOUD" and right_step.phase_kind == "CLOUD":
            auth = right_map.get("CLOUD_AUTH_CHECK")
            budget = right_map.get("CLOUD_RATE_BUDGET_CHECK")
            prepare = right_map.get("API_PREPARE")
            left_request = left_map.get("CLOUD_REQUEST_SEND")
            left_response = left_map.get("API_RESPONSE_RECV")
            left_backoff = left_map.get("CLOUD_BACKOFF_WAIT")
            left_write = left_map.get("HA_STATE_WRITE")
            right_request = right_map.get("CLOUD_REQUEST_SEND")
            if auth and left_request and left_response and left_write:
                overlap = auth.start_ms < left_write.end_ms
                if overlap:
                    ok, pair_reasons = _cloud_prepare_overlap_admission(left_step, right_step, policy)
                    if not ok:
                        coordinator_constraints_ok = False
                        reasons.extend(f"{left_step.step_id}->{right_step.step_id}:{reason}" for reason in pair_reasons)
                    if auth.start_ms < left_request.start_ms:
                        request_send_constraints_ok = False
                        reasons.append(f"{left_step.step_id}->{right_step.step_id}:cloud_auth_started_too_early")
                    latest_overlap_end = left_response.end_ms
                    for name, event in (("budget", budget), ("prepare", prepare)):
                        if event and event.end_ms > latest_overlap_end:
                            request_send_constraints_ok = False
                            reasons.append(f"{left_step.step_id}->{right_step.step_id}:cloud_{name}_window_violation")
                    if (
                        left_backoff
                        and left_backoff.end_ms > left_backoff.start_ms
                        and policy.disallow_backoff_bypass
                        and auth.start_ms < left_backoff.end_ms
                    ):
                        backoff_constraints_ok = False
                        reasons.append(f"{left_step.step_id}->{right_step.step_id}:backoff_bypass")
                if right_request and right_request.start_ms < left_write.end_ms:
                    request_send_constraints_ok = False
                    reasons.append(f"{left_step.step_id}->{right_step.step_id}:cloud_request_send_overlap")
                if policy.disallow_entity_level_overlap and right_request and right_request.start_ms < left_write.end_ms:
                    parallel_updates_constraints_ok = False
                    reasons.append(f"{left_step.step_id}->{right_step.step_id}:entity_level_overlap_detected")

    if not policy.preserve_refresh_cadence:
        cadence_constraints_ok = True

    passed = all(
        (
            coarse_completion_order_preserved,
            phase_order_valid,
            request_send_constraints_ok,
            lookahead_depth_ok,
            coordinator_constraints_ok,
            parallel_updates_constraints_ok,
            session_constraints_ok,
            backoff_constraints_ok,
            writeback_constraints_ok,
            event_loop_constraints_ok,
            cadence_constraints_ok,
            availability_constraints_ok,
        )
    )
    return APIMicroValidationResult(
        passed=passed,
        coarse_completion_order_preserved=coarse_completion_order_preserved,
        phase_order_valid=phase_order_valid,
        request_send_constraints_ok=request_send_constraints_ok,
        lookahead_depth_ok=lookahead_depth_ok,
        coordinator_constraints_ok=coordinator_constraints_ok,
        parallel_updates_constraints_ok=parallel_updates_constraints_ok,
        session_constraints_ok=session_constraints_ok,
        backoff_constraints_ok=backoff_constraints_ok,
        writeback_constraints_ok=writeback_constraints_ok,
        event_loop_constraints_ok=event_loop_constraints_ok,
        cadence_constraints_ok=cadence_constraints_ok,
        availability_constraints_ok=availability_constraints_ok,
        reasons=reasons,
    )


class ConservativeAPIMicroRefiner:


    def __init__(self, *, policy: APIMicroRefinementPolicy | None = None) -> None:
        self.policy = policy or APIMicroRefinementPolicy()

    def _candidate_pairs(self, steps: Sequence[APIBatchStep]) -> int:
        pairs = 0
        for left, right in zip(steps, steps[1:]):
            if left.phase_kind == "LOCAL_HTTP" and right.phase_kind == "LOCAL_HTTP":
                ok, _ = _local_prepare_overlap_admission(left, right, self.policy)
            elif left.phase_kind == "CLOUD" and right.phase_kind == "CLOUD":
                ok, _ = _cloud_prepare_overlap_admission(left, right, self.policy)
            else:
                ok = False
            if ok:
                pairs += 1
        return pairs

    def _select_corridors(self, plan: ExecutionPlan, target: OptimizationTarget) -> Tuple[List[APIBatchStep], List[APIMicroCorridor]]:
        action_lookup = _action_index(target)
        steps_by_batch: List[APIBatchStep | None] = [_make_step(batch, action_lookup) for batch in plan.ordered_batches]

        corridors: List[APIMicroCorridor] = []
        current_steps: List[APIBatchStep] = []
        current_capability_class = ""
        for step in steps_by_batch + [None]:
            if step is not None and (
                not current_steps
                or (
                    step.protocol == current_steps[-1].protocol
                    and step.phase_kind == current_steps[-1].phase_kind
                    and step.capability_class == current_capability_class
                )
            ):
                current_steps.append(step)
                current_capability_class = step.capability_class
                continue

            if current_steps:
                original_latency_ms = sum(item.latency_ms for item in current_steps)
                pair_count = self._candidate_pairs(current_steps)
                min_length, min_latency = _corridor_thresholds(current_capability_class, self.policy)
                if (
                    len(current_steps) >= min_length
                    and original_latency_ms >= min_latency
                    and pair_count > 0
                    and not (
                        self.policy.treat_mqtt_as_non_overlap_lane
                        and current_steps[0].phase_kind == "MQTT"
                    )
                ):
                    corridors.append(
                        APIMicroCorridor(
                            corridor_id=f"corridor_{len(corridors):02d}",
                            protocol=current_steps[0].protocol,
                            phase_kind=current_steps[0].phase_kind,
                            capability_class=current_capability_class or current_steps[0].capability_class,
                            step_ids=[item.step_id for item in current_steps],
                            batch_ids=[item.batch_id for item in current_steps],
                            action_ids=[action_id for item in current_steps for action_id in item.action_ids],
                            original_latency_ms=original_latency_ms,
                            score=original_latency_ms + 120 * pair_count,
                            overlap_candidate_pairs=pair_count,
                        )
                    )
            current_steps = [step] if step is not None else []
            current_capability_class = step.capability_class if step is not None else ""
        return [step for step in steps_by_batch if step is not None], corridors

    def _refine_corridor(self, corridor: APIMicroCorridor, steps_by_id: Dict[str, APIBatchStep]) -> APIMicroCorridorResult:
        steps = [steps_by_id[step_id] for step_id in corridor.step_ids if step_id in steps_by_id]
        serial_events = _serial_events_for_steps(steps, self.policy)
        refined_events = _expand_refined_steps(steps, self.policy)
        validation = validate_refined_corridor(corridor, steps, refined_events, self.policy)
        refined_latency_ms = max((event.end_ms for event in refined_events), default=0)
        latency_saved_ms = max(0, corridor.original_latency_ms - refined_latency_ms) if validation.passed else 0
        return APIMicroCorridorResult(
            corridor=corridor,
            serial_events=serial_events,
            refined_events=refined_events,
            refined_latency_ms=refined_latency_ms,
            latency_saved_ms=latency_saved_ms,
            validation=validation,
        )

    def _refined_plan_overlay(self, plan: ExecutionPlan, results: List[APIMicroCorridorResult]) -> ExecutionPlan:
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
        plan_copy.meta["api_micro_refinement"] = {
            "enabled": True,
            "strategy": "ha_conservative_api_pre_request_overlap",
            "policy": self.policy.to_dict(),
            "corridors": [
                {
                    "corridor_id": result.corridor.corridor_id,
                    "protocol": result.corridor.protocol,
                    "phase_kind": result.corridor.phase_kind,
                    "capability_class": result.corridor.capability_class,
                    "step_ids": list(result.corridor.step_ids),
                    "batch_ids": list(result.corridor.batch_ids),
                    "action_ids": list(result.corridor.action_ids),
                    "original_latency_ms": result.corridor.original_latency_ms,
                    "overlap_candidate_pairs": result.corridor.overlap_candidate_pairs,
                    "refined_latency_ms": result.refined_latency_ms,
                    "latency_saved_ms": result.latency_saved_ms,
                    "validation_passed": result.validation.passed,
                }
                for result in results
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
    ) -> APIMicroCaseResult:
        original_total_ms = estimate_plan_latency_ms(plan, target)
        steps, corridors = self._select_corridors(plan, target)
        steps_by_id = {step.step_id: step for step in steps}
        corridor_results = [self._refine_corridor(corridor, steps_by_id) for corridor in corridors]
        total_saved_ms = sum(result.latency_saved_ms for result in corridor_results if result.validation.passed)
        refined_total_ms = max(0, original_total_ms - total_saved_ms)
        refined_plan = self._refined_plan_overlay(plan, corridor_results)
        return APIMicroCaseResult(
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
    meta = dict(payload.get("meta", {})) if isinstance(payload.get("meta", {}), dict) else {}
    return ExecutionPlan(ordered_batches=batches, meta=meta)
