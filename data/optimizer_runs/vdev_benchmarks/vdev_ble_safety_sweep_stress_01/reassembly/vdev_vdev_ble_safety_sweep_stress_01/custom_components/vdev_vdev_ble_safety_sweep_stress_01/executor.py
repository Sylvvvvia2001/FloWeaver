
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event


class ActionExecutionError(RuntimeError):
    pass


class TemplateResolutionError(ActionExecutionError):
    def __init__(self, token: str) -> None:
        super().__init__(f"Missing required template token '{token}'")
        self.token = token


class ActionExecutor:
    def __init__(self, hass: HomeAssistant, target: dict[str, Any], event_trace: list[dict[str, Any]]) -> None:
        self.hass = hass
        self.target = target
        self.event_trace = event_trace

    def emit(self, provider: str, op: str, target: str, params_abst: dict[str, Any] | None = None, phase: str = "RUNTIME") -> None:
        self.event_trace.append(
            {
                "ts": time.monotonic(),
                "provider": provider,
                "op": op,
                "target": target,
                "params_abst": params_abst or {},
                "phase": phase,
            }
        )

    @staticmethod
    def _parse_default_literal(raw_default: str) -> Any:
        token = raw_default.strip()
        lowered = token.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered == "null":
            return None
        try:
            if "." in token:
                return float(token)
            return int(token)
        except ValueError:
            return token

    @classmethod
    def _parse_template_token(cls, token_expr: str) -> tuple[str, Any | None]:
        token = token_expr.strip()
        default_value: Any | None = None
        if "|default=" in token:
            token, raw_default = token.split("|default=", 1)
            default_value = cls._parse_default_literal(raw_default)
        return token.strip(), default_value

    def _resolve_value(self, value: Any, service_data: dict[str, Any], action_id: str) -> Any:
        if isinstance(value, dict):
            return {key: self._resolve_value(item, service_data, action_id) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(item, service_data, action_id) for item in value]
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            token_expr = value[2:-2].strip()
            token, default_value = self._parse_template_token(token_expr)
            if token in service_data:
                return service_data[token]
            if default_value is not None:
                return default_value
            self.emit("SYS", "TEMPLATE_MISSING", action_id, {"action_id": action_id, "missing_key": token, "token": token})
            raise TemplateResolutionError(token)
        return value

    def _resolve_template(self, data_template: dict[str, Any], service_data: dict[str, Any], action_id: str) -> dict[str, Any]:
        return {key: self._resolve_value(value, service_data, action_id) for key, value in data_template.items()}

    @staticmethod
    def _provider_for_protocol(protocol: str) -> str:
        protocol = protocol.upper()
        if protocol == "BLE":
            return "BLE"
        if protocol == "CLOUD":
            return "CLOUD"
        if protocol in {"LOCAL", "MQTT"}:
            return "LOCAL"
        return "HA"

    @staticmethod
    def _op_for_action(action: dict[str, Any]) -> str:
        hints = action.get("marker_hints", [])
        if hints:
            return str(hints[0])
        kind = action.get("exec", {}).get("kind", "action")
        return str(kind).upper()

    async def _wait_state(self, entity_id: str, expected_state: Any, timeout_s: float) -> Any:
        current_state = self.hass.states.get(entity_id)
        last_state = current_state.state if current_state is not None else None
        if current_state is not None and (
            expected_state is None or str(current_state.state) == str(expected_state)
        ):
            return current_state.state

        matched = asyncio.Event()
        result: dict[str, Any] = {"value": None, "last_state": last_state}

        def _listener(event: Any) -> None:
            new_state = None
            if isinstance(getattr(event, "data", None), dict):
                new_state = event.data.get("new_state")
            result["last_state"] = getattr(new_state, "state", result.get("last_state"))
            if new_state is None:
                return
            if expected_state is None or str(new_state.state) == str(expected_state):
                result["value"] = new_state.state
                matched.set()

        unsubscribe = async_track_state_change_event(self.hass, [entity_id], _listener)
        try:
            await asyncio.wait_for(matched.wait(), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            raise ActionExecutionError(
                f"wait_state timeout for {entity_id}; expected={expected_state!r}; last_state={result.get('last_state')!r}"
            ) from exc
        finally:
            unsubscribe()
        return result["value"]

    async def execute_action(self, action: dict[str, Any], service_data: dict[str, Any]) -> Any:
        action_id = str(action.get("action_id", "unknown"))
        protocol = str(action.get("protocol", "HA"))
        provider = self._provider_for_protocol(protocol)
        op = self._op_for_action(action)

        self.emit(provider, f"{op}_BEGIN", action_id, {"action_id": action_id})
        exec_cfg = action.get("exec", {})
        kind = str(exec_cfg.get("kind", "")).strip()

        try:
            if kind == "ha_service_call":
                domain = str(exec_cfg.get("domain"))
                service = str(exec_cfg.get("service"))
                data_template = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
                payload = self._resolve_template(data_template, service_data, action_id)
                blocking = bool(exec_cfg.get("blocking", True))
                await self.hass.services.async_call(domain, service, payload, blocking=blocking)
                result: Any = {"called": f"{domain}.{service}", "payload": payload}
            elif kind == "ha_state_read":
                entity_id = str(exec_cfg.get("entity_id"))
                attribute = str(exec_cfg.get("attribute", "state"))
                state = self.hass.states.get(entity_id)
                if state is None:
                    raise ActionExecutionError(f"State not found for entity_id={entity_id}")
                result = state.state if attribute == "state" else state.attributes.get(attribute)
            elif kind == "wait_state":
                entity_id = str(exec_cfg.get("entity_id"))
                expected_state = exec_cfg.get("expected_state")
                timeout_s = float(exec_cfg.get("timeout_s", 10))
                result = await self._wait_state(entity_id, expected_state, timeout_s)
            elif kind == "sleep":
                seconds = float(exec_cfg.get("seconds", 0.1))
                await asyncio.sleep(seconds)
                result = {"slept": seconds}
            elif kind == "retry_backoff":
                base_ms = float(exec_cfg.get("base_ms", 200))
                factor = float(exec_cfg.get("factor", 2.0))
                attempts = int(exec_cfg.get("attempts", 3))
                delays = []
                current = base_ms
                for _ in range(max(1, attempts)):
                    delays.append(current)
                    await asyncio.sleep(current / 1000.0)
                    current *= factor
                result = {"delays_ms": delays}
            else:
                raise ActionExecutionError(f"Unsupported exec.kind '{kind}' for action '{action_id}'")
        except Exception as exc:
            self.emit(provider, "EXCEPTION", action_id, {"action_id": action_id, "error": str(exc)})
            raise

        self.emit(provider, f"{op}_END", action_id, {"action_id": action_id})
        return result


class RateController:
    def __init__(
        self,
        batch_id: str,
        rate_policy: dict[str, Any],
        actions: dict[str, dict[str, Any]],
        action_executor: ActionExecutor,
    ) -> None:
        self.batch_id = batch_id
        self.rate_policy = rate_policy
        self.actions = actions
        self.action_executor = action_executor
        self.max_qps = max(0.1, float(rate_policy.get("max_qps", 5.0)))
        self.burst = max(1, int(rate_policy.get("burst", max(1, round(self.max_qps)))))
        self.window_ms = max(1, int(rate_policy.get("window_ms", 1000)))
        self._tokens_per_second = max(0.1, self.max_qps * (1000.0 / self.window_ms))
        self._base_backoff_ms = 0
        self._backoff_factor = 2.0
        self._backoff_max_ms = 2000
        self._lock = asyncio.Lock()
        self._bucket_states: dict[str, dict[str, float]] = {}
        self._load_backoff_policy(rate_policy.get("adaptive_controls", []))

    def _emit(self, op: str, target: str, params_abst: dict[str, Any] | None = None) -> None:
        self.action_executor.emit("SYS", op, target, params_abst or {})

    def _load_backoff_policy(self, rows: Any) -> None:
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            kind = str(row.get("kind", ""))
            action = str(row.get("action", "")).lower()
            params = row.get("params", {}) if isinstance(row.get("params", {}), dict) else {}
            if kind == "BACKOFF_WINDOW" or "backoff" in action or "reduce_qps" in action:
                self._base_backoff_ms = max(self._base_backoff_ms, int(params.get("base_ms", self._base_backoff_ms or 200)))
                self._backoff_factor = max(1.1, float(params.get("factor", self._backoff_factor)))
                self._backoff_max_ms = max(self._backoff_max_ms, int(params.get("max_ms", self._backoff_max_ms)))

    def _is_cloud_action(self, action_id: str) -> bool:
        action = self.actions.get(action_id, {})
        return str(action.get("protocol", "")).upper() == "CLOUD"

    @staticmethod
    def _canonical_bucket_token(value: str) -> str:
        token = str(value or "").strip().lower()
        if token.startswith("http://") or token.startswith("https://"):
            prefix, rest = token.split("//", 1)
            rest = rest.rstrip("/")
            return f"{prefix}//{rest}"
        return token.rstrip("/")

    @staticmethod
    def _action_group_value(action: dict[str, Any], group_key: str) -> str:
        key = str(group_key).strip().lower()
        if not key:
            return ""
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        if key == "endpoint":
            return str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or "")
        if key == "device_id":
            return str(target.get("device_id") or target.get("id") or exec_cfg.get("device_id") or "")
        if key == "host":
            endpoint = str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or "")
            if endpoint.startswith("http://") or endpoint.startswith("https://"):
                return endpoint.split("//", 1)[-1].split("/", 1)[0]
            if ":" in endpoint:
                return endpoint.split(":", 1)[0]
            return endpoint
        return str(action.get(key) or target.get(key) or exec_cfg.get(key) or "")

    @staticmethod
    def _action_provider(action: dict[str, Any]) -> str:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        provider = str(action.get("provider") or target.get("provider") or exec_cfg.get("provider") or "").strip()
        if provider:
            return provider
        endpoint = str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or "")
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint.split("//", 1)[-1].split("/", 1)[0]
        if ":" in endpoint:
            return endpoint.split(":", 1)[0]
        return endpoint

    def _enforced_bucket_keys(self, action_id: str) -> list[str]:
        if not self._is_cloud_action(action_id):
            return []
        action = self.actions.get(action_id, {})
        keys = ["global"]
        host = self._canonical_bucket_token(self._action_group_value(action, "host"))
        provider = self._canonical_bucket_token(self._action_provider(action))
        if host:
            keys.append(f"host:{host}")
        elif provider:
            keys.append(f"provider:{provider}")
        return keys

    def _observed_bucket_keys(self, action_id: str) -> list[str]:
        if not self._is_cloud_action(action_id):
            return []
        action = self.actions.get(action_id, {})
        keys = list(self._enforced_bucket_keys(action_id))
        endpoint = self._canonical_bucket_token(self._action_group_value(action, "endpoint"))
        host = self._canonical_bucket_token(self._action_group_value(action, "host"))
        provider = self._canonical_bucket_token(self._action_provider(action))
        if endpoint:
            keys.append(f"endpoint:{provider or host}:{endpoint}")
        deduped: list[str] = []
        for key in keys:
            if key not in deduped:
                deduped.append(key)
        return deduped

    def _bucket_state(self, key: str) -> dict[str, float]:
        state = self._bucket_states.get(key)
        if state is None:
            state = {
                "tokens": float(self.burst),
                "updated_at": time.monotonic(),
                "max_qps": self.max_qps,
                "burst": float(self.burst),
                "tokens_per_second": self._tokens_per_second,
                "backoff_until": 0.0,
                "backoff_ms": float(self._base_backoff_ms or 200),
            }
            self._bucket_states[key] = state
        return state

    async def acquire(self, action_id: str) -> None:
        if not self._is_cloud_action(action_id):
            return

        while True:
            sleep_s = 0.0
            params: dict[str, Any] = {}
            async with self._lock:
                now = time.monotonic()
                bucket_waits: list[tuple[str, float, str]] = []
                for bucket_key in self._enforced_bucket_keys(action_id):
                    state = self._bucket_state(bucket_key)
                    elapsed = max(0.0, now - state["updated_at"])
                    state["updated_at"] = now
                    state["tokens"] = min(float(state["burst"]), state["tokens"] + elapsed * state["tokens_per_second"])
                    if state["backoff_until"] > now:
                        bucket_waits.append((bucket_key, state["backoff_until"] - now, "backoff"))
                        continue
                    if state["tokens"] >= 1.0:
                        continue
                    deficit = max(0.0, 1.0 - state["tokens"])
                    wait_s = max(0.01, deficit / max(state["tokens_per_second"], 0.1))
                    bucket_waits.append((bucket_key, wait_s, "token_bucket"))
                if not bucket_waits:
                    for bucket_key in self._enforced_bucket_keys(action_id):
                        self._bucket_state(bucket_key)["tokens"] -= 1.0
                    return
                bucket_key, sleep_s, reason = max(bucket_waits, key=lambda item: item[1])
                bucket_state = self._bucket_state(bucket_key)
                params = {
                    "reason": reason,
                    "wait_ms": int(sleep_s * 1000),
                    "max_qps": bucket_state["max_qps"],
                    "bucket": bucket_key,
                    "enforced_buckets": self._enforced_bucket_keys(action_id),
                    "observed_buckets": self._observed_bucket_keys(action_id),
                }
            self._emit("RATE_WAIT", action_id, params)
            await asyncio.sleep(sleep_s)

    @staticmethod
    def is_rate_limit_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return "429" in text or "too many requests" in text or "rate limit" in text or "ratelimit" in text

    async def note_rate_limit(self, action_id: str, exc: Exception) -> None:
        if not self._is_cloud_action(action_id):
            return

        async with self._lock:
            now = time.monotonic()
            downgraded: list[dict[str, Any]] = []
            wait_ms = 0
            for bucket_key in self._enforced_bucket_keys(action_id):
                state = self._bucket_state(bucket_key)
                current_backoff = max(int(state.get("backoff_ms", self._base_backoff_ms or 200)), self._base_backoff_ms or 200)
                if bucket_key == "global":
                    new_backoff = max(50, min(self._backoff_max_ms, max(current_backoff // 2, 100)))
                    rate_scale = 0.85
                else:
                    new_backoff = min(self._backoff_max_ms, max(current_backoff, int(current_backoff * self._backoff_factor)))
                    rate_scale = 0.5
                state["backoff_ms"] = float(new_backoff)
                state["backoff_until"] = now + (new_backoff / 1000.0)
                state["max_qps"] = max(0.1, float(state.get("max_qps", self.max_qps)) * rate_scale)
                state["tokens_per_second"] = max(0.1, state["max_qps"] * (1000.0 / self.window_ms))
                state["tokens"] = min(float(state["burst"]), state["tokens"])
                wait_ms = max(wait_ms, int(new_backoff))
                downgraded.append(
                    {
                        "bucket": bucket_key,
                        "max_qps": state["max_qps"],
                        "backoff_ms": int(new_backoff),
                    }
                )
            bucket_keys = self._observed_bucket_keys(action_id)

        self._emit(
            "RATE_DOWNGRADE",
            action_id,
            {"error": str(exc), "backoff_ms": wait_ms, "batch_id": self.batch_id, "bucket_keys": bucket_keys, "downgraded_buckets": downgraded},
        )
        await asyncio.sleep(wait_ms / 1000.0)

    def snapshot(self) -> dict[str, Any]:
        buckets: list[dict[str, Any]] = []
        for bucket_key in sorted(self._bucket_states):
            state = self._bucket_states[bucket_key]
            buckets.append(
                {
                    "bucket": bucket_key,
                    "max_qps": float(state.get("max_qps", self.max_qps)),
                    "burst": float(state.get("burst", self.burst)),
                    "tokens_per_second": float(state.get("tokens_per_second", self._tokens_per_second)),
                    "backoff_ms": int(state.get("backoff_ms", self._base_backoff_ms or 0)),
                }
            )
        return {
            "batch_id": self.batch_id,
            "max_qps": self.max_qps,
            "burst": self.burst,
            "window_ms": self.window_ms,
            "buckets": buckets,
        }


class PlanRunner:
    def __init__(
        self,
        hass: HomeAssistant,
        plan: dict[str, Any],
        target: dict[str, Any],
        action_executor: ActionExecutor,
        event_trace: list[dict[str, Any]],
    ) -> None:
        self.hass = hass
        self.plan = plan
        self.target = target
        self.action_executor = action_executor
        self.event_trace = event_trace
        self.actions = {
            str(action.get("action_id")): action
            for action in target.get("vdev_actions", [])
            if action.get("action_id")
        }

    def _emit_runtime(self, op: str, target: str, params_abst: dict[str, Any] | None = None) -> None:
        self.action_executor.emit("SYS", op, target, params_abst or {})

    @staticmethod
    def _strip_parens(expr: str) -> str:
        text = expr.strip()
        while text.startswith("(") and text.endswith(")"):
            depth = 0
            balanced = True
            for idx, char in enumerate(text):
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0 and idx != len(text) - 1:
                        balanced = False
                        break
            if not balanced or depth != 0:
                break
            text = text[1:-1].strip()
        return text

    @classmethod
    def _split_bool_expr(cls, expr: str, operator: str) -> list[str]:
        parts: list[str] = []
        depth = 0
        start = 0
        token = f" {operator} "
        upper_expr = expr.upper()
        idx = 0
        while idx < len(expr):
            char = expr[idx]
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and upper_expr.startswith(token, idx):
                parts.append(expr[start:idx].strip())
                idx += len(token)
                start = idx
                continue
            idx += 1
        if start == 0:
            return [expr.strip()]
        parts.append(expr[start:].strip())
        return [part for part in parts if part]

    @staticmethod
    def _guard_flag(token: str, service_data: dict[str, Any]) -> tuple[bool, bool]:
        key = str(token or "").strip().lower()
        if key in {"", "true"}:
            return True, False
        if key == "false":
            return False, False

        runtime_metrics = service_data.get("runtime_metrics", {}) if isinstance(service_data.get("runtime_metrics", {}), dict) else {}
        guard_flags = runtime_metrics.get("guard_flags", {}) if isinstance(runtime_metrics.get("guard_flags", {}), dict) else {}
        risks = runtime_metrics.get("risk_indicators", {}) if isinstance(runtime_metrics.get("risk_indicators", {}), dict) else {}

        direct_context = {
            str(name).strip().lower(): value
            for name, value in service_data.items()
            if isinstance(name, str)
        }
        if key in direct_context:
            return bool(direct_context[key]), False
        if key in guard_flags:
            return bool(guard_flags[key]), False

        recent_429 = float(risks.get("recent_429_rate", 0.0))
        ble_timeout = float(risks.get("ble_timeout_rate", 0.0))
        ble_overlap = float(risks.get("ble_overlap_risk", 0.0))
        loop_load = float(risks.get("ha_loop_load", 0.0))
        ble_success = float(risks.get("ble_conn_success_rate", 1.0))
        mapping = {
            "recent_429_rate_high": recent_429 >= 0.1,
            "429_rate_low": recent_429 < 0.05,
            "ble_timeout_rate_high": ble_timeout >= 0.2,
            "ble_overlap_risk_high": ble_overlap >= 0.2,
            "ble_conn_success_rate_ok": ble_success >= 0.9,
            "resource_constrained": loop_load >= 0.8,
            "loop_load_high": loop_load >= 0.8,
            "latency_budget_allows_batching": bool(runtime_metrics.get("latency_budget_allows_batching", True)),
            "runtime_metrics_available": bool(runtime_metrics),
            "rollback_safe_mode": bool(runtime_metrics.get("rollback_safe_mode", False)),
        }
        if key in mapping:
            return bool(mapping[key]), False
        return False, True

    def _guard_ok(self, guard: str, service_data: dict[str, Any]) -> bool:
        expr = self._strip_parens(str(guard or "true").strip())
        upper_expr = expr.upper()

        or_parts = self._split_bool_expr(expr, "OR")
        if len(or_parts) > 1:
            return any(self._guard_ok(part, service_data) for part in or_parts)

        and_parts = self._split_bool_expr(expr, "AND")
        if len(and_parts) > 1:
            return all(self._guard_ok(part, service_data) for part in and_parts)

        if upper_expr.startswith("NOT "):
            return not self._guard_ok(expr[4:], service_data)

        value, unknown = self._guard_flag(expr, service_data)
        if unknown:
            self._emit_runtime("GUARD_UNKNOWN", expr, {"expr": expr})
            raise ActionExecutionError(f"Unknown guard token '{expr}'")
        return value

    @staticmethod
    def _rows_for_group(action_ids: list[str], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        action_set = set(str(action_id) for action_id in action_ids)
        relevant: list[dict[str, Any]] = []
        for row in rows:
            scope = [str(token) for token in row.get("scope", [])]
            if not scope or action_set.intersection(scope):
                relevant.append(row)
        return relevant

    def _serialize_targets(
        self,
        action_ids: list[str],
        failed_guards: list[dict[str, Any]],
        fallback_rows: list[dict[str, Any]],
    ) -> set[str]:
        action_set = set(action_ids)
        serialize_targets: set[str] = set()

        for row in failed_guards:
            scope = [str(token) for token in row.get("scope", []) if str(token) in action_set]
            if scope:
                serialize_targets.update(scope)
            else:
                serialize_targets.update(action_ids)

        for row in fallback_rows:
            mode = str(row.get("action", ""))
            scope = [str(token) for token in row.get("scope", []) if str(token) in action_set]
            scope_targets = set(scope) if scope else set(action_ids)
            if mode in {"preserve_action_order", "force_pick_despite_soft_conflicts"}:
                serialize_targets.update(scope_targets)
                continue
            if mode in {"reduce_parallelism", "reduce_qps_and_parallelism"}:
                serialize_targets.update(
                    action_id
                    for action_id in scope_targets
                    if str(self.actions.get(action_id, {}).get("protocol", "")).upper() == "CLOUD"
                )
                continue
            if mode in {"set_ble_parallelism_to_1", "serialize_ble_ops_and_disable_reuse"}:
                serialize_targets.update(
                    action_id
                    for action_id in scope_targets
                    if str(self.actions.get(action_id, {}).get("protocol", "")).upper() == "BLE"
                )
        return serialize_targets

    @staticmethod
    def _group_requires_order_preservation(
        action_ids: list[str],
        fallback_rows: list[dict[str, Any]],
    ) -> bool:
        action_set = set(action_ids)
        for row in fallback_rows:
            mode = str(row.get("action", ""))
            if mode not in {"preserve_action_order", "force_topological_local_order"}:
                continue
            scope = [str(token) for token in row.get("scope", []) if str(token) in action_set]
            if scope or not row.get("scope"):
                return True
        return False

    @staticmethod
    def _canonical_bucket_token(value: str) -> str:
        token = str(value or "").strip().lower()
        if token.startswith("http://") or token.startswith("https://"):
            prefix, rest = token.split("//", 1)
            rest = rest.rstrip("/")
            return f"{prefix}//{rest}"
        return token.rstrip("/")

    @staticmethod
    def _action_group_value(action: dict[str, Any], group_key: str) -> str:
        key = str(group_key).strip().lower()
        if not key:
            return ""
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        if key == "endpoint":
            return str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or "")
        if key == "device_id":
            return str(target.get("device_id") or target.get("id") or exec_cfg.get("device_id") or "")
        if key == "host":
            endpoint = str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or "")
            if endpoint.startswith("http://") or endpoint.startswith("https://"):
                return endpoint.split("//", 1)[-1].split("/", 1)[0]
            if ":" in endpoint:
                return endpoint.split(":", 1)[0]
            return endpoint
        return str(action.get(key) or target.get(key) or exec_cfg.get(key) or "")

    @staticmethod
    def _action_provider(action: dict[str, Any]) -> str:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        provider = str(action.get("provider") or target.get("provider") or exec_cfg.get("provider") or "").strip()
        if provider:
            return provider
        endpoint = str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or "")
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint.split("//", 1)[-1].split("/", 1)[0]
        if ":" in endpoint:
            return endpoint.split(":", 1)[0]
        return endpoint

    def _batch_bucket_key(self, action: dict[str, Any], group_key: str) -> str:
        group = self._canonical_bucket_token(self._action_group_value(action, group_key))
        host = self._canonical_bucket_token(self._action_group_value(action, "host"))
        provider = self._canonical_bucket_token(self._action_provider(action))
        if str(group_key).strip().lower() == "endpoint":
            parts = [part for part in (provider, host, group) if part]
            return "|".join(parts)
        return group

    def _batch_rule_for_group(self, action_ids: list[str], rate_policy: dict[str, Any]) -> dict[str, Any] | None:
        batch_rules = rate_policy.get("batch_rules", [])
        if not isinstance(batch_rules, list) or not action_ids:
            return None
        group_set = set(action_ids)
        for rule in batch_rules:
            if not isinstance(rule, dict):
                continue
            scope = {str(token) for token in rule.get("scope", [])}
            if group_set and group_set.issubset(scope):
                return rule
        return None

    def _group_bucket_info(self, action_ids: list[str], rate_policy: dict[str, Any]) -> tuple[str, int, int]:
        if not action_ids:
            return "", 0, 0
        rule = self._batch_rule_for_group(action_ids, rate_policy)
        if rule is None:
            return "", 0, 0
        group_key = str(rule.get("group_key", "endpoint"))
        first_action = self.actions.get(action_ids[0], {})
        bucket = self._batch_bucket_key(first_action, group_key)
        max_wait_ms = max(0, int(rule.get("max_wait_ms", 0)))
        max_batch_size = max(1, int(rule.get("max_batch_size", 1)))
        return bucket, max_wait_ms, max_batch_size

    def _reshape_groups_for_fallbacks(
        self,
        groups: list[list[str]],
        fallback_rows: list[dict[str, Any]],
        batch_id: str,
    ) -> list[list[str]]:
        reshaped: list[list[str]] = []
        for group in groups:
            current_segments: list[list[str]] = [list(group)]
            for row in fallback_rows:
                mode = str(row.get("action", "")).lower()
                if "disable_batch" not in mode and "shrink_batch" not in mode:
                    continue
                scope = {str(token) for token in row.get("scope", []) if str(token)}
                if not scope:
                    scope = set(group)
                next_segments: list[list[str]] = []
                applied = False
                for segment in current_segments:
                    matching = [action_id for action_id in segment if action_id in scope]
                    if len(matching) <= 1:
                        next_segments.append(segment)
                        continue
                    applied = True
                    if "disable_batch" in mode:
                        chunk_size = 1
                    else:
                        params = row.get("params", {}) if isinstance(row.get("params", {}), dict) else {}
                        chunk_size = max(1, int(params.get("new_max_batch_size", params.get("max_batch_size", 1))))
                    for action_id in segment:
                        if action_id not in scope:
                            next_segments.append([action_id])
                            continue
                        if next_segments and len(next_segments[-1]) < chunk_size and all(item in scope for item in next_segments[-1]):
                            next_segments[-1].append(action_id)
                        else:
                            next_segments.append([action_id])
                current_segments = next_segments
                if applied:
                    self._emit_runtime(
                        "BATCH_SHRINK_APPLIED",
                        batch_id,
                        {"mode": mode, "scope": sorted(scope), "group": list(group)},
                    )
            reshaped.extend(current_segments)
        return reshaped

    async def _apply_batch_coalescing_wait(
        self,
        batch_id: str,
        action_ids: list[str],
        rate_policy: dict[str, Any],
        waited_buckets: set[str],
        group_index: int,
        groups: list[list[str]],
    ) -> None:
        bucket, wait_ms, max_batch_size = self._group_bucket_info(action_ids, rate_policy)
        if not bucket or wait_ms <= 0 or bucket in waited_buckets:
            return
        if len(action_ids) >= max_batch_size:
            return
        future_has_same_bucket = False
        for future_group in groups[group_index + 1 :]:
            future_bucket, _, _ = self._group_bucket_info([str(action_id) for action_id in future_group], rate_policy)
            if future_bucket == bucket:
                future_has_same_bucket = True
                break
        if not future_has_same_bucket:
            return
        waited_buckets.add(bucket)
        self._emit_runtime(
            "BATCH_COALESCE_WAIT",
            batch_id,
            {"bucket": bucket, "wait_ms": wait_ms, "action_ids": list(action_ids)},
        )
        await asyncio.sleep(wait_ms / 1000.0)

    async def _run_parallel(
        self,
        action_ids: list[str],
        service_data: dict[str, Any],
        rate_controller: RateController,
    ) -> dict[str, Any]:
        tasks = {action_id: asyncio.create_task(self._run_action(action_id, service_data, rate_controller)) for action_id in action_ids}
        try:
            results = await asyncio.gather(*tasks.values())
        except Exception as exc:
            for task in tasks.values():
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            self._emit_runtime(
                "EXCEPTION_SUMMARY",
                ",".join(action_ids),
                {"action_ids": list(action_ids), "error": str(exc)},
            )
            raise
        return {action_id: result for action_id, result in zip(tasks.keys(), results)}

    async def _run_serial(
        self,
        action_ids: list[str],
        service_data: dict[str, Any],
        rate_controller: RateController,
    ) -> dict[str, Any]:
        results: dict[str, Any] = {}
        try:
            for action_id in action_ids:
                results[action_id] = await self._run_action(action_id, service_data, rate_controller)
        except Exception as exc:
            self._emit_runtime(
                "EXCEPTION_SUMMARY",
                ",".join(action_ids),
                {"action_ids": list(action_ids), "error": str(exc)},
            )
            raise
        return results

    async def _run_group(
        self,
        action_ids: list[str],
        guards: list[dict[str, Any]],
        fallback: list[dict[str, Any]],
        service_data: dict[str, Any],
        rate_controller: RateController,
    ) -> list[Any]:
        relevant_guards = self._rows_for_group(action_ids, guards)
        relevant_fallback = self._rows_for_group(action_ids, fallback)
        failed_guards = [row for row in relevant_guards if not self._guard_ok(str(row.get("expr", "true")), service_data)]
        if self._group_requires_order_preservation(action_ids, relevant_fallback):
            parallel_ids = []
            serial_ids = list(action_ids)
        else:
            serialize_targets = self._serialize_targets(action_ids, failed_guards, relevant_fallback)
            serial_ids = [action_id for action_id in action_ids if action_id in serialize_targets]
            parallel_ids = [action_id for action_id in action_ids if action_id not in serialize_targets]

        result_map: dict[str, Any] = {}
        if parallel_ids:
            result_map.update(await self._run_parallel(parallel_ids, service_data, rate_controller))
        if serial_ids:
            result_map.update(await self._run_serial(serial_ids, service_data, rate_controller))

        return [result_map[action_id] for action_id in action_ids]

    async def _run_action(self, action_id: str, service_data: dict[str, Any], rate_controller: RateController) -> Any:
        action = self.actions.get(action_id)
        if action is None:
            raise ActionExecutionError(f"Unknown action_id '{action_id}'")
        await rate_controller.acquire(action_id)
        try:
            return await self.action_executor.execute_action(action, service_data)
        except Exception as exc:
            if rate_controller.is_rate_limit_error(exc):
                await rate_controller.note_rate_limit(action_id, exc)
            raise

    def _trace_export_path(self, service_data: dict[str, Any]) -> Path | None:
        raw_path = str(service_data.get("trace_path", "")).strip()
        if raw_path:
            return Path(raw_path)
        if not bool(service_data.get("export_trace", False)):
            return None
        meta = self.target.get("meta", {}) if isinstance(self.target.get("meta", {}), dict) else {}
        vdev_id = str(meta.get("vdev_id", "generated")).strip() or "generated"
        filename = f"vibeaura_vdev_{vdev_id}_trace.json"
        return Path(self.hass.config.path(".storage", filename))

    async def _maybe_export_trace(self, service_data: dict[str, Any], summary: dict[str, Any]) -> str:
        path = self._trace_export_path(service_data)
        if path is None:
            return ""

        plan_meta = self.plan.get("meta", {}) if isinstance(self.plan.get("meta", {}), dict) else {}
        policy_snapshot = plan_meta.get("policy_snapshot", {}) if isinstance(plan_meta.get("policy_snapshot", {}), dict) else {}
        versions = dict(policy_snapshot.get("versions", {})) if isinstance(policy_snapshot.get("versions", {}), dict) else {}
        meta = self.target.get("meta", {}) if isinstance(self.target.get("meta", {}), dict) else {}
        vdev_id = str(meta.get("vdev_id", "generated")).strip() or "generated"
        plan_id = str(plan_meta.get("plan_id", f"{vdev_id}:{len(self.plan.get('ordered_batches', []))}"))
        payload = {
            "schema_version": "m7_trace_export/v1",
            "target_id": vdev_id,
            "vdev_id": vdev_id,
            "plan_id": plan_id,
            "profile_version": str(versions.get("profile_version", "")),
            "canonicalization_version": str(versions.get("canonicalization_version", "")),
            "policy_snapshot": policy_snapshot,
            "plan_meta": plan_meta,
            "runtime_policy_snapshot": [
                dict(batch.get("runtime_policy", {}))
                for batch in summary.get("batches", [])
                if isinstance(batch, dict) and isinstance(batch.get("runtime_policy", {}), dict)
            ],
            "forced_fallbacks_applied": [
                {
                    "batch_id": str(batch.get("batch_id", "")),
                    "fallbacks": list(batch.get("fallbacks_applied", [])),
                }
                for batch in summary.get("batches", [])
                if isinstance(batch, dict) and batch.get("fallbacks_applied")
            ],
            "event_trace": list(self.event_trace),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_text, json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._emit_runtime("TRACE_EXPORTED", str(path), {"path": str(path)})
        return str(path)

    async def run(self, service_data: dict[str, Any]) -> dict[str, Any]:
        self.event_trace.clear()
        self._emit_runtime("RUN_BEGIN", str(self.target.get("meta", {}).get("vdev_id", "vdev")))
        summary: dict[str, Any] = {
            "status": "ok",
            "batches": [],
        }
        try:
            for batch in self.plan.get("ordered_batches", []):
                batch_id = str(batch.get("batch_id", "unknown_batch"))
                batch_result: dict[str, Any] = {"batch_id": batch_id, "groups": []}
                groups = batch.get("parallel_groups", [])
                guards_raw = batch.get("guards", [])
                guards: list[dict[str, Any]] = []
                if isinstance(guards_raw, list):
                    for item in guards_raw:
                        if isinstance(item, dict):
                            guards.append(
                                {
                                    "kind": str(item.get("kind", "")),
                                    "scope": [str(token) for token in item.get("scope", [])],
                                    "expr": str(item.get("expr", "true")),
                                    "enforced": bool(item.get("enforced", True)),
                                }
                            )
                        else:
                            guards.append({"kind": "", "scope": [], "expr": str(item), "enforced": True})

                fallback_raw = batch.get("fallback", [])
                fallback: list[dict[str, Any]] = []
                if isinstance(fallback_raw, list):
                    for item in fallback_raw:
                        if not isinstance(item, dict):
                            continue
                        fallback.append(
                            {
                                "kind": str(item.get("kind", "")),
                                "scope": [str(token) for token in item.get("scope", [])],
                                "action": str(item.get("action", item.get("fallback", ""))),
                                "params": dict(item.get("params", {})) if isinstance(item.get("params", {}), dict) else {},
                            }
                        )
                elif isinstance(fallback_raw, dict):
                    for key, value in fallback_raw.items():
                        values = value if isinstance(value, list) else [value]
                        for entry in values:
                            fallback.append({"kind": str(key), "scope": [], "action": str(entry), "params": {}})

                rate_policy = batch.get("rate_policy", {}) if isinstance(batch.get("rate_policy", {}), dict) else {}
                rate_controller = RateController(batch_id, rate_policy, self.actions, self.action_executor)
                groups = self._reshape_groups_for_fallbacks(groups, fallback, batch_id)
                waited_buckets: set[str] = set()
                batch_result["fallbacks_applied"] = list(fallback)

                for group_idx, group in enumerate(groups):
                    action_ids = [str(action_id) for action_id in group]
                    await self._apply_batch_coalescing_wait(batch_id, action_ids, rate_policy, waited_buckets, group_idx, groups)
                    group_results = await self._run_group(action_ids, guards, fallback, service_data, rate_controller)
                    batch_result["groups"].append({"action_ids": action_ids, "results": group_results})

                batch_result["runtime_policy"] = rate_controller.snapshot()
                summary["batches"].append(batch_result)
        except Exception as exc:
            summary["status"] = "error"
            summary["error"] = str(exc)
            raise
        finally:
            trace_path = await self._maybe_export_trace(service_data, summary)
            if trace_path:
                summary["trace_path"] = trace_path
            self._emit_runtime("RUN_END", str(self.target.get("meta", {}).get("vdev_id", "vdev")), {"status": summary.get("status", "ok")})

        return summary
