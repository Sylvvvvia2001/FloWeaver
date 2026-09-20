from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

if __name__ == "__main__" and str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsl.contracts import Batch, ExecutionPlan, OptimizationTarget


@dataclass
class NaiveTopoPolicy:
    max_parallel: int = 4
    ble_parallel: int = 1
    cloud_parallel: int = 4
    local_parallel: int = 4


class NaiveTopoParallelScheduler:
    def __init__(self, policy: NaiveTopoPolicy | None = None) -> None:
        self.policy = policy or NaiveTopoPolicy()

    def schedule(self, target: OptimizationTarget, runtime_metrics: dict[str, Any] | None = None) -> ExecutionPlan:
        actions = self._action_index(target)
        out, indegree = self._explicit_graph(target, actions)
        ready = {aid for aid, deg in indegree.items() if deg == 0}
        done: set[str] = set()
        batches: list[Batch] = []
        latencies = self._latency_ms(actions, runtime_metrics or {})

        while len(done) < len(actions):
            if not ready:
                unresolved = sorted(aid for aid in actions if aid not in done)
                raise ValueError("NaiveTopo blocked by explicit dependency cycle: " + ",".join(unresolved))

            selected: list[str] = []
            for aid in sorted(ready, key=lambda item: (self._rank(actions, item), -latencies.get(item, 1.0), item)):
                if self._can_join(aid, selected, actions):
                    selected.append(aid)
                    continue
                if selected:
                    break
            if not selected:
                selected = [sorted(ready, key=lambda item: (self._rank(actions, item), item))[0]]

            batches.append(
                Batch(
                    batch_id=f"naive_batch_{len(batches):03d}",
                    parallel_groups=[selected],
                    constraints=[],
                    session_policy={},
                    rate_policy={},
                    guards=[],
                    fallback=[],
                )
            )
            for aid in selected:
                ready.discard(aid)
                done.add(aid)
                for nxt in sorted(out.get(aid, set()), key=lambda item: (self._rank(actions, item), item)):
                    indegree[nxt] -= 1
                    if indegree[nxt] == 0:
                        ready.add(nxt)

        return ExecutionPlan(
            ordered_batches=batches,
            meta={
                "baseline": "naive_topo_parallel",
                "node_kind": "action_id",
                "micro_applicable": False,
                "policy": self.policy.__dict__,
                "action_lanes": {aid: self._protocol(action) for aid, action in actions.items()},
            },
        )

    @staticmethod
    def _action_index(target: OptimizationTarget) -> dict[str, dict[str, Any]]:
        return {
            str(action.get("action_id")): action
            for action in target.vdev_actions
            if str(action.get("action_id", "")).strip()
        }

    @staticmethod
    def _rank(actions: dict[str, dict[str, Any]], action_id: str) -> int:
        return list(actions).index(action_id)

    @staticmethod
    def _explicit_graph(
        target: OptimizationTarget,
        actions: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, set[str]], dict[str, int]]:
        out = {aid: set() for aid in actions}
        indegree = {aid: 0 for aid in actions}

        def add(src: str, dst: str) -> None:
            if src == dst or src not in actions or dst not in actions or dst in out[src]:
                return
            out[src].add(dst)
            indegree[dst] += 1

        for dep in target.hard_dependencies:
            add(str(dep.get("before", "")), str(dep.get("after", "")))
        for aid, action in actions.items():
            for dst in action.get("must_happen_before", []) or []:
                add(aid, str(dst))
        ha_actions = [aid for aid, action in actions.items() if NaiveTopoParallelScheduler._protocol(action) == "HA"]
        non_ha_actions = [aid for aid in actions if aid not in set(ha_actions)]
        for src in non_ha_actions:
            for dst in ha_actions:
                add(src, dst)
        return out, indegree

    @classmethod
    def _latency_ms(cls, actions: dict[str, dict[str, Any]], runtime_metrics: dict[str, Any]) -> dict[str, float]:
        provided = runtime_metrics.get("latency_ms", {}) if isinstance(runtime_metrics.get("latency_ms", {}), dict) else {}
        defaults = {"BLE": 1800.0, "CLOUD": 900.0, "LOCAL": 120.0, "HA": 50.0, "UNKNOWN": 500.0}
        return {
            aid: float(provided.get(aid, defaults.get(cls._protocol(action), 500.0)))
            for aid, action in actions.items()
        }

    @staticmethod
    def _protocol(action: dict[str, Any]) -> str:
        value = str(action.get("protocol") or "").strip().upper()
        if value == "MQTT":
            return "LOCAL"
        return value if value in {"BLE", "CLOUD", "LOCAL", "HA"} else "UNKNOWN"

    @staticmethod
    def _target_key(action: dict[str, Any]) -> str:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        for key in ("entity_id", "device_id", "id", "host", "endpoint"):
            token = str(target.get(key) or exec_cfg.get(key) or "").strip().lower()
            if token:
                return token
        data = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
        for key in ("entity_id", "device_id", "host", "endpoint"):
            token = str(data.get(key) or "").strip().lower()
            if token:
                return token
        return ""

    @classmethod
    def _read_only(cls, action: dict[str, Any]) -> bool:
        if cls._protocol(action) == "HA":
            return False
        text = " ".join(str(v).lower() for v in cls._semantic_values(action))
        read_tokens = ("read", "get", "status", "refresh", "list", "sensor", "runtime")
        control_tokens = ("turn_on", "turn_off", "toggle", "set_", "open", "close", "lock", "unlock", "play", "pause")
        return any(t in text for t in read_tokens) and not any(t in text for t in control_tokens)

    @staticmethod
    def _semantic_values(action: dict[str, Any]) -> list[Any]:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        return [
            action.get("type"),
            action.get("kind"),
            action.get("action_kind"),
            exec_cfg.get("kind"),
            exec_cfg.get("service"),
            target.get("kind"),
            target.get("id"),
            target.get("entity_id"),
        ]

    def _can_join(self, aid: str, selected: list[str], actions: dict[str, dict[str, Any]]) -> bool:
        action = actions[aid]
        protocol = self._protocol(action)
        counts = {"BLE": 0, "CLOUD": 0, "LOCAL": 0, "HA": 0, "UNKNOWN": 0}
        for other_id in selected:
            other = actions[other_id]
            if self._same_device_conflict(action, other):
                return False
            counts[self._protocol(other)] = counts.get(self._protocol(other), 0) + 1
        counts[protocol] = counts.get(protocol, 0) + 1
        return (
            len(selected) + 1 <= self.policy.max_parallel
            and counts["BLE"] <= self.policy.ble_parallel
            and counts["CLOUD"] <= self.policy.cloud_parallel
            and counts["LOCAL"] <= self.policy.local_parallel
        )

    @classmethod
    def _same_device_conflict(cls, left: dict[str, Any], right: dict[str, Any]) -> bool:
        left_key = cls._target_key(left)
        right_key = cls._target_key(right)
        if not left_key or left_key != right_key:
            return False
        return not (cls._read_only(left) and cls._read_only(right))


def _demo() -> None:
    target = OptimizationTarget(
        vdev_actions=[
            {"action_id": "A1", "protocol": "CLOUD", "type": "status", "target": {"id": "cloud:lamp"}},
            {"action_id": "A2", "protocol": "LOCAL", "type": "get_state", "target": {"id": "hue:lamp"}},
            {"action_id": "A3", "protocol": "BLE", "type": "refresh_cover", "target": {"id": "ble:curtain"}},
            {"action_id": "A4", "protocol": "HA", "type": "write", "target": {"entity_id": "sensor.done"}},
        ],
        hard_dependencies=[{"before": "A1", "after": "A4"}, {"before": "A2", "after": "A4"}, {"before": "A3", "after": "A4"}],
    )
    plan = NaiveTopoParallelScheduler().schedule(target)
    assert [g for b in plan.ordered_batches for g in b.parallel_groups] == [["A1", "A2", "A3"], ["A4"]]


if __name__ == "__main__":
    _demo()
