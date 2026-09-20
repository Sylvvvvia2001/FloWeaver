from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "generate_counterexample",
    "generate_counterexample_from_traces",
    "CounterexampleWitness",
    "CounterexampleVerdict",
    "ViolatedProperty",
]


def __getattr__(name: str) -> Any:
    if name in {"generate_counterexample", "generate_counterexample_from_traces"}:
        module = import_module("counterexample_layer.api.generate_counterexample")
        return getattr(module, name)
    if name in {"CounterexampleWitness", "CounterexampleVerdict", "ViolatedProperty"}:
        module = import_module("counterexample_layer.witness.witness")
        return getattr(module, name)
    raise AttributeError(f"module 'counterexample_layer' has no attribute {name!r}")
