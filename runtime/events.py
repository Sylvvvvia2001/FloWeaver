from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional

from dsl.contracts import Event, Phase, Provider, Trace


@dataclass
class EventRecorder:
    integration: str
    scenario_id: str
    variant: str
    events: List[Event] = field(default_factory=list)
    enabled_ops: Optional[set[str]] = None

    def emit(
        self,
        provider: str,
        op: str,
        target: str,
        params_abst: Optional[Dict[str, Any]] = None,
        phase: str = Phase.RUNTIME.value,
        corr_id: Optional[str] = None,
    ) -> None:
        if self.enabled_ops is not None and op not in self.enabled_ops:
            return
        self.events.append(
            Event(
                ts=time.monotonic(),
                provider=provider,
                op=op,
                target=target,
                params_abst=params_abst or {},
                phase=phase,
                corr_id=corr_id,
            )
        )

    def as_trace(self) -> Trace:
        return Trace(
            events=list(self.events),
            meta={
                "integration": self.integration,
                "scenario_id": self.scenario_id,
                "variant": self.variant,
            },
        )

    @contextmanager
    def correlation(self, prefix: str = "corr"):
        corr_id = f"{prefix}:{uuid.uuid4().hex[:12]}"
        yield corr_id

    def instrument_async(
        self,
        provider: str,
        op: str,
        target_getter: Optional[Callable[..., str]] = None,
        phase: str = Phase.RUNTIME.value,
    ) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:


        def decorator(fn: Callable[..., Coroutine[Any, Any, Any]]):
            async def wrapped(*args: Any, **kwargs: Any) -> Any:
                target = target_getter(*args, **kwargs) if target_getter else fn.__name__
                corr_id = f"{fn.__name__}:{uuid.uuid4().hex[:10]}"
                self.emit(provider, f"{op}_BEGIN", target, phase=phase, corr_id=corr_id)
                try:
                    result = await fn(*args, **kwargs)
                except Exception as exc:
                    self.emit(
                        provider,
                        "EXCEPTION",
                        target,
                        params_abst={"type": type(exc).__name__},
                        phase=phase,
                        corr_id=corr_id,
                    )
                    raise
                self.emit(provider, f"{op}_END", target, phase=phase, corr_id=corr_id)
                return result

            return wrapped

        return decorator


class TraceCollector:


    def __init__(self, integration: str, scenario_id: str):
        self.integration = integration
        self.scenario_id = scenario_id

    async def run_variant(
        self,
        variant_name: str,
        runner: Callable[[EventRecorder], Coroutine[Any, Any, None]],
        enabled_ops: Optional[set[str]] = None,
    ) -> Trace:
        recorder = EventRecorder(
            integration=self.integration,
            scenario_id=self.scenario_id,
            variant=variant_name,
            enabled_ops=enabled_ops,
        )
        await runner(recorder)
        return recorder.as_trace()

    def run_variant_sync(
        self,
        variant_name: str,
        runner: Callable[[EventRecorder], None],
        enabled_ops: Optional[set[str]] = None,
    ) -> Trace:
        recorder = EventRecorder(
            integration=self.integration,
            scenario_id=self.scenario_id,
            variant=variant_name,
            enabled_ops=enabled_ops,
        )
        runner(recorder)
        return recorder.as_trace()


def run_maybe_async(coro_or_value: Any) -> Any:
    if asyncio.iscoroutine(coro_or_value):
        return asyncio.run(coro_or_value)
    return coro_or_value
