
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

from homeassistant.core import HomeAssistant


class ActionExecutionError(RuntimeError):
    pass


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
    def _resolve_template(data_template: dict[str, Any], service_data: dict[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, value in data_template.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                token = value[2:-2].strip()
                resolved[key] = service_data.get(token)
            else:
                resolved[key] = value
        return resolved

    @staticmethod
    def _provider_for_protocol(protocol: str) -> str:
        protocol = protocol.upper()
        if protocol == "BLE":
            return "BLE"
        if protocol == "CLOUD":
            return "CLOUD"
        return "HA"

    @staticmethod
    def _op_for_action(action: dict[str, Any]) -> str:
        hints = action.get("marker_hints", [])
        if hints:
            return str(hints[0])
        kind = action.get("exec", {}).get("kind", "action")
        return str(kind).upper()

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
                payload = self._resolve_template(data_template, service_data)
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
                poll_interval_s = float(exec_cfg.get("poll_interval_s", 0.25))
                deadline = time.monotonic() + timeout_s
                result = None
                while time.monotonic() < deadline:
                    state = self.hass.states.get(entity_id)
                    if state is not None:
                        if expected_state is None or str(state.state) == str(expected_state):
                            result = state.state
                            break
                    await asyncio.sleep(poll_interval_s)
                if result is None:
                    raise ActionExecutionError(f"wait_state timeout for {entity_id}")
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

    def _guard_ok(self, guard: str, service_data: dict[str, Any]) -> bool:
        if not guard or guard == "true":
            return True
        if guard == "resource_constrained":
            return not bool(service_data.get("resource_constrained", False))
        if guard == "recent_429_rate_high":
            return not bool(service_data.get("recent_429_rate_high", False))
        if guard == "ble_timeout_rate_high":
            return not bool(service_data.get("ble_timeout_rate_high", False))

        return True

    async def _run_group(
        self,
        action_ids: list[str],
        guards: list[str],
        fallback: dict[str, str],
        service_data: dict[str, Any],
    ) -> list[Any]:
        guards_passed = all(self._guard_ok(guard, service_data) for guard in guards)
        serialize = not guards_passed or any(
            mode in {"preserve_action_order", "reduce_parallelism", "set_ble_parallelism_to_1"}
            for mode in fallback.values()
        )

        results: list[Any] = []
        if serialize:
            for action_id in action_ids:
                results.append(await self._run_action(action_id, service_data))
            return results

        tasks = [self._run_action(action_id, service_data) for action_id in action_ids]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_action(self, action_id: str, service_data: dict[str, Any]) -> Any:
        action = self.actions.get(action_id)
        if action is None:
            raise ActionExecutionError(f"Unknown action_id '{action_id}'")
        return await self.action_executor.execute_action(action, service_data)

    async def run(self, service_data: dict[str, Any]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "status": "ok",
            "batches": [],
        }

        for batch in self.plan.get("ordered_batches", []):
            batch_id = str(batch.get("batch_id", "unknown_batch"))
            batch_result: dict[str, Any] = {"batch_id": batch_id, "groups": []}
            groups = batch.get("parallel_groups", [])
            guards = [str(item) for item in batch.get("guards", [])]
            fallback = {str(k): str(v) for k, v in batch.get("fallback", {}).items()}

            for group in groups:
                action_ids = [str(action_id) for action_id in group]
                group_results = await self._run_group(action_ids, guards, fallback, service_data)
                batch_result["groups"].append({"action_ids": action_ids, "results": group_results})

            summary["batches"].append(batch_result)

        return summary
