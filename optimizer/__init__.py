from __future__ import annotations

__all__ = ["FloWeaverOptimizer"]


def __getattr__(name: str):
    if name == "FloWeaverOptimizer":
        from optimizer.pipeline import FloWeaverOptimizer

        return FloWeaverOptimizer
    raise AttributeError(name)
