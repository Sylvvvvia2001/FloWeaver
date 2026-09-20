from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "EventRecorder",
    "TraceCollector",
    "BLEHooks",
    "CloudHooks",
    "HAHooks",
    "replay_scenarios",
    "Scenario",
    "default_scenarios",
    "scenarios_from_config",
    "assert_trace_contract",
    "canonicalize_trace",
    "compare_traces",
]


def __getattr__(name: str) -> Any:
    if name in {"EventRecorder", "TraceCollector"}:
        module = import_module("runtime.events")
        return getattr(module, name)
    if name in {"BLEHooks", "CloudHooks", "HAHooks"}:
        module = import_module("runtime.hooks")
        return getattr(module, name)
    if name == "replay_scenarios":
        module = import_module("runtime.replay")
        return getattr(module, name)
    if name in {"Scenario", "default_scenarios", "scenarios_from_config"}:
        module = import_module("runtime.scenarios")
        return getattr(module, name)
    if name in {"assert_trace_contract", "canonicalize_trace", "compare_traces"}:
        module = import_module("runtime.trace")
        return getattr(module, name)
    raise AttributeError(f"module 'runtime' has no attribute {name!r}")
