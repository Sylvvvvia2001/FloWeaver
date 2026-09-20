
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DATA_RUNTIME, DOMAIN, SERVICE_RUN
from .executor import ActionExecutor, PlanRunner

PLATFORMS: list[str] = []


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    await _ensure_runtime(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _ensure_runtime(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = hass.data.get(DOMAIN, {}).get(DATA_RUNTIME)
    if runtime:
        hass.services.async_remove(DOMAIN, SERVICE_RUN)
    return True


async def _ensure_runtime(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_RUNTIME):
        return

    base_dir = Path(__file__).resolve().parent
    plan = json.loads((base_dir / "plan.json").read_text(encoding="utf-8"))
    target = json.loads((base_dir / "target.json").read_text(encoding="utf-8"))
    event_trace: list[dict[str, Any]] = []

    action_executor = ActionExecutor(hass=hass, target=target, event_trace=event_trace)
    runner = PlanRunner(
        hass=hass,
        plan=plan,
        target=target,
        action_executor=action_executor,
        event_trace=event_trace,
    )

    async def _handle_run(call: ServiceCall) -> dict[str, Any]:
        return await runner.run(service_data=dict(call.data))

    hass.services.async_register(DOMAIN, SERVICE_RUN, _handle_run)
    domain_data[DATA_RUNTIME] = {
        "runner": runner,
        "target": target,
        "plan": plan,
        "event_trace": event_trace,
    }
