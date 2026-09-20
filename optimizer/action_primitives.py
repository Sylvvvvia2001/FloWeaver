from __future__ import annotations

from typing import Any, Dict, List

from dsl.contracts import OptimizationTarget


SUPPORTED_ACTION_EXEC_PRIMITIVES = {
    "ha_service_call",
    "ha_state_read",
    "wait_state",
    "sleep",
    "retry_backoff",
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_action_exec_mapping(action: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    action_id = str(action.get("action_id", "<unknown_action>"))
    exec_cfg = action.get("exec")
    if not isinstance(exec_cfg, dict):
        return [f"action:{action_id}:missing_exec_mapping"]

    kind = str(exec_cfg.get("kind", "")).strip()
    if kind not in SUPPORTED_ACTION_EXEC_PRIMITIVES:
        return [f"action:{action_id}:unsupported_exec_kind:{kind}"]

    if kind == "ha_service_call":
        if not str(exec_cfg.get("domain", "")).strip():
            errors.append(f"action:{action_id}:ha_service_call_missing_domain")
        if not str(exec_cfg.get("service", "")).strip():
            errors.append(f"action:{action_id}:ha_service_call_missing_service")
        if "data_template" in exec_cfg and not isinstance(exec_cfg.get("data_template"), dict):
            errors.append(f"action:{action_id}:ha_service_call_invalid_data_template")
    elif kind == "ha_state_read":
        if not str(exec_cfg.get("entity_id", "")).strip():
            errors.append(f"action:{action_id}:ha_state_read_missing_entity_id")
    elif kind == "wait_state":
        if not str(exec_cfg.get("entity_id", "")).strip():
            errors.append(f"action:{action_id}:wait_state_missing_entity_id")
        if "timeout_s" in exec_cfg and not _is_number(exec_cfg.get("timeout_s")):
            errors.append(f"action:{action_id}:wait_state_invalid_timeout_s")
        if "poll_interval_s" in exec_cfg and not _is_number(exec_cfg.get("poll_interval_s")):
            errors.append(f"action:{action_id}:wait_state_invalid_poll_interval_s")
    elif kind == "sleep":
        if "seconds" in exec_cfg and not _is_number(exec_cfg.get("seconds")):
            errors.append(f"action:{action_id}:sleep_invalid_seconds")
    elif kind == "retry_backoff":
        if "base_ms" in exec_cfg and not _is_number(exec_cfg.get("base_ms")):
            errors.append(f"action:{action_id}:retry_backoff_invalid_base_ms")
        if "factor" in exec_cfg and not _is_number(exec_cfg.get("factor")):
            errors.append(f"action:{action_id}:retry_backoff_invalid_factor")
        if "attempts" in exec_cfg and not isinstance(exec_cfg.get("attempts"), int):
            errors.append(f"action:{action_id}:retry_backoff_invalid_attempts")

    return errors


def validate_target_action_primitives(target: OptimizationTarget) -> None:
    errors: List[str] = []
    for action in target.vdev_actions:
        if not isinstance(action, dict):
            errors.append("action:<non-dict>:invalid_action_row")
            continue
        errors.extend(validate_action_exec_mapping(action))
    if errors:
        raise ValueError("Invalid action execution mapping: " + "; ".join(errors))
