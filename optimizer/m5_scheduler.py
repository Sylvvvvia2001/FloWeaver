from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Set, Tuple

from dsl.contracts import Batch, ExecutionPlan, MSSU, OptimizationTarget, SoftConstraintKind, TypedDAG


@dataclass
class SchedulerPolicy:
    max_parallel: int = 4
    ble_parallel: int = 1
    cloud_parallel: int = 3
    local_parallel: int = 4
    default_qps: float = 5.0


@dataclass
class DerivedConstraintPolicy:
    total_limit: int
    ble_limit: int
    cloud_limit: int
    local_limit: int
    unknown_limit: int
    max_qps: float
    rate_limit_burst: int
    rate_limit_window_ms: int
    reuse_enabled: bool
    reuse_window_ms: int
    latency_budget_ms: int
    budget_rules: List[Dict[str, Any]]
    batch_rules: List[Dict[str, Any]]
    session_rules: List[Dict[str, Any]]
    no_overlap_scopes: List[Set[str]]
    min_gap_pairs: Dict[Tuple[str, str], int]
    soft_order_pairs: Set[Tuple[str, str]]
    active_constraints: List[Dict[str, Any]]
    triggered_fallbacks: List[Dict[str, Any]]


@dataclass
class BatchBuildState:
    selected: List[str] = field(default_factory=list)
    total_occupancy: int = 0
    ble_count: int = 0
    cloud_count: int = 0
    cloud_request_counts: Dict[str, int] = field(default_factory=dict)
    local_count: int = 0
    unknown_count: int = 0
    budget_counts: Dict[int, int] = field(default_factory=dict)
    no_overlap_counts: Dict[int, int] = field(default_factory=dict)
    selected_group_counts: Dict[Tuple[int, str], int] = field(default_factory=dict)


@dataclass
class CorridorSearchState:
    done: Set[str]
    indegree: Dict[str, int]
    ready: Set[str]
    scheduled_batches: List[List[str]]
    score: float


class CrossProtocolScheduler:
    def __init__(self, policy: SchedulerPolicy | None = None) -> None:
        self.policy = policy or SchedulerPolicy()

    @staticmethod
    def _policy_from_target(base: SchedulerPolicy, optimization_target: OptimizationTarget | None) -> SchedulerPolicy:
        policy = SchedulerPolicy(**base.__dict__)
        if optimization_target is None:
            return policy

        knobs = (
            optimization_target.constraints.get("optimization_knobs", {})
            if isinstance(optimization_target.constraints, dict)
            else {}
        )
        if knobs.get("allow_concurrency") is False:
            policy.max_parallel = 1
            policy.ble_parallel = 1
            policy.cloud_parallel = 1
            policy.local_parallel = 1

        max_concurrency = knobs.get("max_concurrency", {}) if isinstance(knobs.get("max_concurrency", {}), dict) else {}
        if isinstance(max_concurrency.get("ble"), (int, float)):
            policy.ble_parallel = max(1, int(max_concurrency["ble"]))
        if isinstance(max_concurrency.get("cloud"), (int, float)):
            policy.cloud_parallel = max(1, int(max_concurrency["cloud"]))
        if isinstance(max_concurrency.get("local"), (int, float)):
            policy.local_parallel = max(1, int(max_concurrency["local"]))
        if isinstance(max_concurrency.get("total"), (int, float)):
            policy.max_parallel = max(1, int(max_concurrency["total"]))
        if isinstance(knobs.get("max_qps"), (int, float)):
            policy.default_qps = float(knobs["max_qps"])

        return policy

    @staticmethod
    def _policy_from_metrics(base: SchedulerPolicy, runtime_metrics: Dict[str, Any] | None) -> SchedulerPolicy:
        policy = SchedulerPolicy(**base.__dict__)
        runtime_metrics = runtime_metrics or {}
        overrides = runtime_metrics.get("offline_policy_overrides", {})
        if isinstance(overrides, dict):
            if isinstance(overrides.get("max_parallel"), (int, float)):
                policy.max_parallel = max(1, int(overrides["max_parallel"]))
            if isinstance(overrides.get("ble_parallel"), (int, float)):
                policy.ble_parallel = max(1, int(overrides["ble_parallel"]))
            if isinstance(overrides.get("cloud_parallel"), (int, float)):
                policy.cloud_parallel = max(1, int(overrides["cloud_parallel"]))
            if isinstance(overrides.get("local_parallel"), (int, float)):
                policy.local_parallel = max(1, int(overrides["local_parallel"]))
            if isinstance(overrides.get("max_qps"), (int, float)):
                policy.default_qps = max(0.1, float(overrides["max_qps"]))

        risks = runtime_metrics.get("risk_indicators", {})
        if isinstance(risks, dict):
            if float(risks.get("ble_timeout_rate", 0.0)) >= 0.2:
                policy.ble_parallel = 1
            if float(risks.get("recent_429_rate", 0.0)) >= 0.1:
                policy.cloud_parallel = min(policy.cloud_parallel, 1)
                policy.default_qps = min(policy.default_qps, 1.0)
            if float(risks.get("ha_loop_load", 0.0)) >= 0.8:
                policy.max_parallel = min(policy.max_parallel, 1)
        return policy

    @staticmethod
    def _action_index(optimization_target: OptimizationTarget | None) -> Dict[str, Dict[str, Any]]:
        if optimization_target is None:
            return {}
        index: Dict[str, Dict[str, Any]] = {}
        for action in optimization_target.vdev_actions:
            action_id = str(action.get("action_id", "")).strip()
            if action_id:
                index[action_id] = action
        return index

    @staticmethod
    def _mssu_action_refs(mssu: MSSU) -> Set[str]:
        refs = {
            str(action_id).strip()
            for action_id in getattr(mssu, "action_refs", [])
            if action_id is not None and str(action_id).strip()
        }
        primary = str(getattr(mssu, "primary_action_ref", "") or "").strip()
        if primary:
            refs.add(primary)
        refs.update(
            str(action_id).strip()
            for action_id in getattr(mssu, "secondary_action_refs", [])
            if action_id is not None and str(action_id).strip()
        )
        return refs

    @classmethod
    def _mssu_to_actions(cls, dag: TypedDAG) -> Dict[str, Set[str]]:
        mapping: Dict[str, Set[str]] = {}
        for mssu_id, mssu in dag.nodes.items():
            mapping[mssu_id] = cls._mssu_action_refs(mssu)
        return mapping

    @staticmethod
    def _action_target_kind(action: Dict[str, Any]) -> str:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        return str(target.get("kind", "")).strip().lower()

    @classmethod
    def _action_lane(cls, action: Dict[str, Any]) -> str:
        protocol = cls._action_protocol(action)
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        entity = str(target.get("entity_id") or target.get("id") or "").lower()
        if protocol == "BLE":
            return "BLE_LOCAL"
        if protocol == "CLOUD":
            return "CLOUD"
        if protocol == "LOCAL":
            return "LOCAL"
        if protocol == "HA":
            if "overall" in entity:
                return "WRITEBACK_OVERALL"
            if "ble_lane" in entity:
                return "WRITEBACK_BLE"
            if "cloud_lane" in entity:
                return "WRITEBACK_CLOUD"
            if "local_lane" in entity or "mqtt_lane" in entity:
                return "WRITEBACK_LOCAL"
            return "WRITEBACK"
        return "UNKNOWN"

    @classmethod
    def _action_is_writeback(cls, action: Dict[str, Any]) -> bool:
        return cls._action_lane(action).startswith("WRITEBACK")

    @staticmethod
    def _mssu_effect_tokens(mssu: Any) -> Set[str]:
        tokens: Set[str] = set()
        for effect in getattr(mssu, "side_effect_sig", set()) or set():
            normalized = str(effect).strip().lower().replace("-", "_").replace(" ", "_")
            if not normalized:
                continue
            tokens.add(normalized)
            if normalized == "ble_gatt_op":
                tokens.add("ble_op")
            if normalized == "cloud_http_call":
                tokens.add("cloud_op")
            if normalized == "state_write":
                tokens.add("ha_state_write")
        return tokens

    @staticmethod
    def _baseline_trace_hints(optimization_target: OptimizationTarget | None) -> Dict[str, Any]:
        validation = optimization_target.validation if optimization_target and isinstance(optimization_target.validation, dict) else {}
        observation = validation.get("observation", {}) if isinstance(validation.get("observation", {}), dict) else {}
        return observation.get("baseline_order_hints", {}) if isinstance(observation.get("baseline_order_hints", {}), dict) else {}

    @classmethod
    def _observable_anchor_priority(
        cls,
        action_id: str,
        action_to_mssus: Dict[str, List[str]],
        typed_dag: TypedDAG,
        baseline_trace_hints: Dict[str, Any] | None,
        action_index: Dict[str, Dict[str, Any]],
    ) -> int:
        explicit = baseline_trace_hints.get("action_order", {}) if isinstance((baseline_trace_hints or {}).get("action_order", {}), dict) else {}
        if action_id in explicit and isinstance(explicit[action_id], int):
            return int(explicit[action_id])

        declared_order = {item: idx for idx, item in enumerate(action_index.keys())}
        if action_id in declared_order:
            return declared_order[action_id]

        action = action_index.get(action_id, {})
        lane = cls._action_lane(action)
        if lane == "WRITEBACK_OVERALL":
            return 50
        if lane.startswith("WRITEBACK"):
            return 30

        effects: Set[str] = set()
        for mssu_id in action_to_mssus.get(action_id, []):
            mssu = typed_dag.nodes.get(mssu_id)
            if mssu is None:
                continue
            effects |= cls._mssu_effect_tokens(mssu)

        if "cloud_http_call" in effects or "cloud_op" in effects or lane == "CLOUD":
            return 0
        if "ble_gatt_op" in effects or "ble_op" in effects or lane == "BLE_LOCAL":
            return 10
        if "ble_connect" in effects or "subscribe" in effects or "coord_refresh" in effects:
            return 15
        if "local_api_read" in effects or lane == "LOCAL":
            return 20
        if "state_write" in effects or "ha_state_write" in effects:
            return 30
        return 40

    @staticmethod
    def _is_fat_action(action_id: str, action_to_mssus: Dict[str, List[str]], threshold: int = 24) -> bool:
        return len(action_to_mssus.get(action_id, [])) > max(1, int(threshold))

    @classmethod
    def _writeback_precedence_constraints(
        cls,
        action_index: Dict[str, Dict[str, Any]],
        optimization_target: OptimizationTarget | None,
    ) -> List[Tuple[str, str]]:
        del optimization_target
        pairs: Set[Tuple[str, str]] = set()
        lanes = {action_id: cls._action_lane(action) for action_id, action in action_index.items()}
        acquisition = [action_id for action_id, lane in lanes.items() if not lane.startswith("WRITEBACK")]
        writebacks = [action_id for action_id, lane in lanes.items() if lane.startswith("WRITEBACK")]

        for writeback in writebacks:
            lane = lanes.get(writeback, "")
            if lane == "WRITEBACK_BLE":
                for action_id in acquisition:
                    if lanes.get(action_id) == "BLE_LOCAL":
                        pairs.add((action_id, writeback))
            elif lane == "WRITEBACK_CLOUD":
                for action_id in acquisition:
                    if lanes.get(action_id) == "CLOUD":
                        pairs.add((action_id, writeback))
            elif lane == "WRITEBACK_LOCAL":
                for action_id in acquisition:
                    if lanes.get(action_id) == "LOCAL":
                        pairs.add((action_id, writeback))
            elif lane == "WRITEBACK_OVERALL":
                for action_id in writebacks:
                    if action_id != writeback and lanes.get(action_id) != "WRITEBACK_OVERALL":
                        pairs.add((action_id, writeback))
            elif lane.startswith("WRITEBACK"):
                for action_id in acquisition:
                    pairs.add((action_id, writeback))

        return sorted(pairs)

    @staticmethod
    def _add_edge(
        src: str,
        dst: str,
        kind: str,
        out: Dict[str, Set[str]],
        indegree: Dict[str, int],
        edge_kinds: Dict[Tuple[str, str], Set[str]],
    ) -> None:
        if src == dst:
            return
        if dst not in out.setdefault(src, set()):
            out[src].add(dst)
            indegree[dst] = indegree.get(dst, 0) + 1
        edge_kinds.setdefault((src, dst), set()).add(kind)

    def _project_hard_graph(
        self,
        dag: TypedDAG,
        action_index: Dict[str, Dict[str, Any]],
        optimization_target: OptimizationTarget | None,
    ) -> tuple[Dict[str, Set[str]], Dict[str, int], Dict[Tuple[str, str], Set[str]], Dict[str, List[str]]]:
        actions = list(action_index.keys())
        out: Dict[str, Set[str]] = {action_id: set() for action_id in actions}
        indegree: Dict[str, int] = {action_id: 0 for action_id in actions}
        edge_kinds: Dict[Tuple[str, str], Set[str]] = {}

        mssu_to_actions = self._mssu_to_actions(dag)
        action_to_mssus: Dict[str, List[str]] = {action_id: [] for action_id in actions}
        for mssu_id, refs in mssu_to_actions.items():
            for action_id in refs:
                if action_id in action_to_mssus:
                    action_to_mssus[action_id].append(mssu_id)

        for edge in dag.hard_edges:
            src_actions = mssu_to_actions.get(edge.src_mssu, set())
            dst_actions = mssu_to_actions.get(edge.dst_mssu, set())
            for src, dst in sorted(self._edge_action_pairs(src_actions, dst_actions, edge.justification, action_index)):
                self._add_edge(src, dst, edge.kind, out, indegree, edge_kinds)

        if optimization_target is not None:
            for dep in optimization_target.hard_dependencies:
                before = str(dep.get("before", ""))
                after = str(dep.get("after", ""))
                if before in action_index and after in action_index:
                    self._add_edge(before, after, "HARD_CONTROL", out, indegree, edge_kinds)

            for before, after in self._writeback_precedence_constraints(action_index, optimization_target):
                if before in action_index and after in action_index:
                    self._add_edge(before, after, "HARD_CONTROL", out, indegree, edge_kinds)

            for action_id, action in action_index.items():
                for nxt in action.get("must_happen_before", []):
                    nxt_id = str(nxt)
                    if nxt_id in action_index:
                        self._add_edge(action_id, nxt_id, "HARD_CONTROL", out, indegree, edge_kinds)

        return out, indegree, edge_kinds, action_to_mssus

    @staticmethod
    def _topological_order(nodes: List[str], out: Dict[str, Set[str]], indegree: Dict[str, int]) -> List[str]:
        queue = [node for node in nodes if indegree.get(node, 0) == 0]
        order: List[str] = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for nxt in out.get(node, set()):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        return order

    @staticmethod
    def _resolve_cycles(
        action_ids: List[str],
        out: Dict[str, Set[str]],
        indegree: Dict[str, int],
        edge_kinds: Dict[Tuple[str, str], Set[str]],
    ) -> List[Dict[str, Any]]:
        del indegree

        index = 0
        stack: List[str] = []
        on_stack: Set[str] = set()
        indices: Dict[str, int] = {}
        lowlink: Dict[str, int] = {}
        reports: List[Dict[str, Any]] = []

        def strongconnect(node: str) -> None:
            nonlocal index
            indices[node] = index
            lowlink[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for nxt in sorted(out.get(node, set())):
                if nxt not in indices:
                    strongconnect(nxt)
                    lowlink[node] = min(lowlink[node], lowlink[nxt])
                elif nxt in on_stack:
                    lowlink[node] = min(lowlink[node], indices[nxt])

            if lowlink[node] != indices[node]:
                return

            component: List[str] = []
            while stack:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break

            if len(component) <= 1:
                only = component[0]
                if only not in out.get(only, set()):
                    return

            component_set = set(component)
            edges: List[Dict[str, Any]] = []
            kinds: Set[str] = set()
            for src in sorted(component_set):
                for dst in sorted(out.get(src, set())):
                    if dst not in component_set:
                        continue
                    edge_kind_values = sorted(edge_kinds.get((src, dst), set()))
                    edges.append({"src": src, "dst": dst, "kinds": edge_kind_values})
                    kinds.update(edge_kind_values)

            reports.append(
                {
                    "kind": "hard_cycle",
                    "nodes": sorted(component_set),
                    "edge_kinds": sorted(kinds),
                    "edges": edges,
                }
            )

        for node in sorted(action_ids):
            if node not in indices:
                strongconnect(node)

        return reports

    def _critical_path_score(
        self,
        action_ids: List[str],
        out: Dict[str, Set[str]],
        indegree: Dict[str, int],
        latency_weights: Dict[str, float],
    ) -> Dict[str, float]:
        topo = self._topological_order(action_ids, out, dict(indegree))
        score = {action_id: latency_weights.get(action_id, 1.0) for action_id in action_ids}
        for action_id in reversed(topo):
            successors = out.get(action_id, set())
            if successors:
                score[action_id] = latency_weights.get(action_id, 1.0) + max(score[s] for s in successors)
        return score

    @staticmethod
    def _action_protocol(action: Dict[str, Any]) -> str:
        token = action.get("protocol")
        if not token and isinstance(action.get("io"), dict):
            token = action["io"].get("protocol")
        value = str(token or "").strip().upper()
        if value in {"BLE", "CLOUD", "HA", "LOCAL"}:
            return value
        if value == "MQTT":
            return "LOCAL"
        return "UNKNOWN"

    @staticmethod
    def _action_resource(action: Dict[str, Any]) -> str:
        protocol = CrossProtocolScheduler._action_protocol(action)
        if protocol == "BLE":
            return "BLE"
        if protocol == "CLOUD":
            return "CLOUD"
        if protocol == "LOCAL":
            return "LOCAL"
        if protocol == "HA":
            return "HA"
        return "UNKNOWN"

    @staticmethod
    def _action_group_value(action: Dict[str, Any], group_key: str) -> str:
        key = str(group_key).strip().lower()
        if not key:
            return ""
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        data_template = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
        if key == "endpoint":
            return str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or data_template.get("endpoint") or "")
        if key == "device_id":
            return str(target.get("device_id") or target.get("id") or exec_cfg.get("device_id") or data_template.get("device_id") or "")
        if key == "host":
            explicit = (
                action.get("host_group_key")
                or target.get("host_group_key")
                or exec_cfg.get("host_group_key")
                or data_template.get("host_group_key")
            )
            if str(explicit or "").strip():
                return str(explicit)
            endpoint = str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or data_template.get("endpoint") or "")
            if endpoint.startswith("http://") or endpoint.startswith("https://"):
                return endpoint.split("//", 1)[-1].split("/", 1)[0]
            if ":" in endpoint:
                return endpoint.split(":", 1)[0]
            return endpoint
        return str(action.get(key) or target.get(key) or exec_cfg.get(key) or "")

    @staticmethod
    def _action_provider(action: Dict[str, Any]) -> str:
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

    @staticmethod
    def _action_marker_hints(action: Dict[str, Any]) -> Set[str]:
        hints = action.get("marker_hints", [])
        if not isinstance(hints, list):
            return set()
        tokens: Set[str] = set()
        for item in hints:
            token = str(item).strip().lower().replace("-", "_").replace(" ", "_")
            if token:
                tokens.add(token)
        return tokens

    @classmethod
    def _action_is_subscribe_like(cls, action: Dict[str, Any]) -> bool:
        hints = cls._action_marker_hints(action)
        if any(token in hints for token in {"subscribe", "subscribe_pairing", "unsubscribe"}):
            return True

        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        fields = [
            action.get("action_kind"),
            action.get("kind"),
            exec_cfg.get("kind"),
            exec_cfg.get("service"),
            target.get("kind"),
            target.get("id"),
            target.get("entity_id"),
        ]
        text = " ".join(str(value).strip().lower() for value in fields if str(value).strip())
        return "subscribe" in text

    @classmethod
    def _needs_ble_min_gap(cls, action_a: Dict[str, Any], action_b: Dict[str, Any]) -> bool:
        if cls._action_is_subscribe_like(action_a) or cls._action_is_subscribe_like(action_b):
            return False
        return True

    @staticmethod
    def _action_is_batch_safe(action: Dict[str, Any]) -> bool:
        strings = CrossProtocolScheduler._action_semantic_strings(action)
        tokens = CrossProtocolScheduler._action_semantic_tokens(strings)
        read_markers = {
            "status",
            "get",
            "get_state",
            "read",
            "read_runtime",
            "read_sensor",
            "read_status",
            "read_last_message",
            "fetch",
            "list",
            "refresh",
            "refresh_cover",
        }
        if any(value in read_markers for value in strings):
            return True
        if any(value.endswith(".status") for value in strings):
            return True
        return bool(tokens & read_markers)

    @staticmethod
    def _action_is_idempotent(action: Dict[str, Any]) -> bool:
        return str(action.get("idempotent", "")).strip().lower() in {"yes", "true"}

    @classmethod
    def _action_is_read_like(cls, action: Dict[str, Any]) -> bool:
        return not cls._action_is_writeback(action) and cls._action_is_batch_safe(action)

    @staticmethod
    def _action_semantic_strings(action: Dict[str, Any]) -> List[str]:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        fields = [
            action.get("type"),
            action.get("action_kind"),
            action.get("kind"),
            exec_cfg.get("service"),
            exec_cfg.get("kind"),
            target.get("kind"),
            target.get("id"),
            target.get("entity_id"),
            target.get("endpoint"),
        ]
        values: List[str] = []
        for field in fields:
            token = str(field).strip().lower()
            if token:
                values.append(token)
        return values

    @staticmethod
    def _action_semantic_tokens(strings: List[str]) -> Set[str]:
        tokens: Set[str] = set(strings)
        for value in strings:
            for token in re.split(r"[^a-z0-9]+", value):
                normalized = str(token).strip().lower()
                if normalized:
                    tokens.add(normalized)
        return tokens

    @classmethod
    def _action_is_control_like(cls, action: Dict[str, Any]) -> bool:
        if cls._action_is_writeback(action) or cls._action_is_read_like(action):
            return False
        strings = cls._action_semantic_strings(action)
        control_tokens = (
            "turn_on",
            "turn_off",
            "toggle",
            "set_",
            "open",
            "close",
            "play_media",
            "media_play",
            "media_pause",
            "volume",
            "brightness",
            "color_temp",
            "hs_color",
            "rgb_color",
            "cover_position",
            "cover_tilt",
            "hvac_mode",
            "temperature",
            "fan_mode",
            "percentage",
            "preset_mode",
            "swing_mode",
            "source",
        )
        return any(token in value for value in strings for token in control_tokens)

    @classmethod
    def _action_phase_map(
        cls,
        action_index: Dict[str, Dict[str, Any]],
    ) -> Dict[str, str]:
        phases: Dict[str, str] = {}
        ordered_actions = list(action_index.items())
        last_control_idx = -1
        for idx, (_, action) in enumerate(ordered_actions):
            if cls._action_is_writeback(action):
                continue
            if cls._action_is_control_like(action):
                last_control_idx = idx

        for idx, (action_id, action) in enumerate(ordered_actions):
            if cls._action_is_writeback(action):
                phases[action_id] = "writeback"
                continue
            if cls._action_is_control_like(action):
                phases[action_id] = "control"
                continue
            if last_control_idx >= 0 and idx > last_control_idx:
                phases[action_id] = "post_control_verification"
                continue
            phases[action_id] = "pre_control_acquisition"
        return phases

    @staticmethod
    def _canonical_bucket_token(value: str) -> str:
        token = str(value or "").strip().lower()
        if token.startswith("http://") or token.startswith("https://"):
            prefix, rest = token.split("//", 1)
            rest = rest.rstrip("/")
            return f"{prefix}//{rest}"
        return token.rstrip("/")

    def _batch_bucket_key(self, action: Dict[str, Any], group_key: str) -> str:
        group = self._canonical_bucket_token(self._action_group_value(action, group_key))
        host = self._canonical_bucket_token(self._action_group_value(action, "host"))
        provider = self._canonical_bucket_token(self._action_provider(action))
        if str(group_key).strip().lower() == "endpoint":
            parts = [part for part in (provider, host, group) if part]
            return "|".join(parts)
        return group

    def _action_batch_group_value(self, action: Dict[str, Any], group_key: str) -> str:
        key = str(group_key).strip().lower()
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        data_template = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
        if key == "endpoint":
            explicit = (
                action.get("endpoint_group_key")
                or target.get("endpoint_group_key")
                or exec_cfg.get("endpoint_group_key")
                or data_template.get("endpoint_group_key")
                or data_template.get("device_group")
            )
            if str(explicit or "").strip():
                host = self._canonical_bucket_token(self._action_group_value(action, "host"))
                endpoint_group = self._canonical_bucket_token(str(explicit))
                return "|".join([part for part in (host, endpoint_group) if part])
            return self._batch_bucket_key(action, group_key)
        return self._canonical_bucket_token(self._action_group_value(action, group_key))

    def _inferred_cloud_group_scope(
        self,
        optimization_target: OptimizationTarget,
        *,
        group_key: str,
        batch_only: bool,
    ) -> List[str]:
        grouped: Dict[str, List[str]] = {}
        for action in optimization_target.vdev_actions:
            action_id = str(action.get("action_id", "")).strip()
            if not action_id:
                continue
            if self._action_protocol(action) != "CLOUD":
                continue
            if self._action_is_writeback(action):
                continue
            if batch_only and not self._action_is_batch_safe(action):
                continue
            target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
            exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
            data_template = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
            if batch_only:
                explicit_group = (
                    action.get("endpoint_group_key")
                    or target.get("endpoint_group_key")
                    or exec_cfg.get("endpoint_group_key")
                    or data_template.get("endpoint_group_key")
                    or data_template.get("device_group")
                )
                if not str(explicit_group or "").strip():
                    continue
            else:
                explicit_group = (
                    action.get("host_group_key")
                    or target.get("host_group_key")
                    or exec_cfg.get("host_group_key")
                    or data_template.get("host_group_key")
                )
                if not str(explicit_group or "").strip():
                    continue
            bucket_key = (
                self._action_batch_group_value(action, group_key)
                if batch_only
                else self._canonical_bucket_token(self._action_group_value(action, group_key))
            )
            if not str(bucket_key or "").strip():
                continue
            grouped.setdefault(str(bucket_key), []).append(action_id)
        return sorted(
            {
                action_id
                for members in grouped.values()
                if len(members) >= 2
                for action_id in members
            }
        )

    @staticmethod
    def _apply_execution_batch_cap(rule: Dict[str, Any]) -> Dict[str, Any]:
        capped = dict(rule)


        capped["max_batch_size"] = min(int(capped.get("max_batch_size", 20)), 3)
        capped["max_wait_ms"] = min(int(capped.get("max_wait_ms", 80)), 40)
        return capped

    @staticmethod
    def _guard_flag(name: str, runtime_metrics: Dict[str, Any]) -> bool:
        token = str(name).strip().lower()
        if token in {"", "true"}:
            return True
        if token == "false":
            return False

        guard_flags = runtime_metrics.get("guard_flags", {}) if isinstance(runtime_metrics.get("guard_flags", {}), dict) else {}
        if token in guard_flags:
            return bool(guard_flags[token])

        risks = runtime_metrics.get("risk_indicators", {}) if isinstance(runtime_metrics.get("risk_indicators", {}), dict) else {}
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
            "latency_budget_allows_batching": bool(runtime_metrics.get("latency_budget_allows_batching", True)),
            "runtime_metrics_available": bool(runtime_metrics),
            "rollback_safe_mode": bool(runtime_metrics.get("rollback_safe_mode", False)),
        }
        if token in mapping:
            return mapping[token]
        return bool(runtime_metrics.get(token, False))

    def _guard_active(self, guard: str, runtime_metrics: Dict[str, Any]) -> bool:
        expr = str(guard or "true").strip()
        upper = expr.upper()
        if " OR " in upper:
            parts = re.split(r"\s+OR\s+", expr, flags=re.IGNORECASE)
            return any(self._guard_active(part, runtime_metrics) for part in parts)
        if " AND " in upper:
            parts = re.split(r"\s+AND\s+", expr, flags=re.IGNORECASE)
            return all(self._guard_active(part, runtime_metrics) for part in parts)
        return self._guard_flag(expr, runtime_metrics)

    @staticmethod
    def _fallback_triggers_on_inactive_guard(kind: str, guard: str, fallback: str) -> bool:
        kind_u = str(kind or "").strip().upper()
        guard_l = str(guard or "").strip().lower()
        fallback_l = str(fallback or "").strip().lower()
        if guard_l in {"", "true"}:
            return False
        if kind_u in {SoftConstraintKind.BATCH_GROUP.value, SoftConstraintKind.SAME_SESSION_GROUP.value}:
            return True
        if kind_u == SoftConstraintKind.MIN_GAP.value and "disable_ble_reuse" in fallback_l:
            return True
        if any(token in guard_l for token in ("_low", "_ok", "allows_batching", "latency_budget_allows", "success_rate_ok")):
            return True
        return False

    @staticmethod
    def _high_batching_risk(runtime_metrics: Dict[str, Any]) -> bool:
        risks = runtime_metrics.get("risk_indicators", {}) if isinstance(runtime_metrics.get("risk_indicators", {}), dict) else {}
        guard_flags = runtime_metrics.get("guard_flags", {}) if isinstance(runtime_metrics.get("guard_flags", {}), dict) else {}
        recent_429 = float(risks.get("recent_429_rate", 0.0))
        return bool(
            recent_429 >= 0.1
            or runtime_metrics.get("trust_mismatch_on_batching")
            or runtime_metrics.get("replay_error_on_batching")
            or guard_flags.get("trust_mismatch_on_batching")
            or guard_flags.get("replay_error_on_batching")
        )

    @staticmethod
    def _apply_batch_shrink_params(params: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(params)
        out["max_batch_size"] = min(int(out.get("max_batch_size", 20)), 4)
        out["max_wait_ms"] = min(int(out.get("max_wait_ms", 80)), 40)
        return out

    @classmethod
    def _normalized_fallback_mode(
        cls,
        kind: str,
        fallback: str,
        runtime_metrics: Dict[str, Any],
    ) -> str:
        mode = str(fallback or "").strip()
        kind_u = str(kind or "").strip().upper()
        if not mode:
            return mode
        if (
            kind_u in {SoftConstraintKind.BATCH_GROUP.value, SoftConstraintKind.SAME_SESSION_GROUP.value}
            and "disable_batching" in mode
            and not cls._high_batching_risk(runtime_metrics)
        ):
            return "shrink_batch_not_disable"
        return mode

    @staticmethod
    def _constraint_scope_set(constraint: Dict[str, Any]) -> Set[str]:
        return {str(item) for item in constraint.get("scope", []) if str(item)}

    def _derive_policy_from_constraints(
        self,
        policy: SchedulerPolicy,
        soft_constraints: List[Dict[str, Any]],
        runtime_metrics: Dict[str, Any],
        optimization_target: OptimizationTarget | None = None,
    ) -> DerivedConstraintPolicy:
        latency_budget_ms = 0
        if isinstance(runtime_metrics.get("latency_budget_ms"), (int, float)):
            latency_budget_ms = max(0, int(runtime_metrics["latency_budget_ms"]))
        elif optimization_target is not None and isinstance(optimization_target.objectives, dict):
            metrics = optimization_target.objectives.get("metrics", {})
            if isinstance(metrics, dict):
                e2e_latency = metrics.get("e2e_latency_ms", {})
                if isinstance(e2e_latency, dict):
                    for key in ("p95", "p99", "target", "max"):
                        if isinstance(e2e_latency.get(key), (int, float)):
                            latency_budget_ms = max(0, int(e2e_latency[key]))
                            break

        derived = DerivedConstraintPolicy(
            total_limit=max(1, int(policy.max_parallel)),
            ble_limit=max(1, int(policy.ble_parallel)),
            cloud_limit=max(1, int(policy.cloud_parallel)),
            local_limit=max(1, int(policy.local_parallel)),
            unknown_limit=1,
            max_qps=max(0.1, float(policy.default_qps)),
            rate_limit_burst=max(1, int(policy.max_parallel)),
            rate_limit_window_ms=1000,
            reuse_enabled=True,
            reuse_window_ms=20_000,
            latency_budget_ms=latency_budget_ms,
            budget_rules=[],
            batch_rules=[],
            session_rules=[],
            no_overlap_scopes=[],
            min_gap_pairs={},
            soft_order_pairs=set(),
            active_constraints=[],
            triggered_fallbacks=[],
        )

        def apply_fallback(fallback_mode: str, scope: Set[str], params: Dict[str, Any], kind: str) -> None:
            mode = str(fallback_mode)
            mode_l = mode.lower()
            effective_params = dict(params)
            if "shrink_batch" in mode_l and kind in {
                SoftConstraintKind.BATCH_GROUP.value,
                SoftConstraintKind.SAME_SESSION_GROUP.value,
            }:
                effective_params = self._apply_batch_shrink_params(effective_params)
            derived.triggered_fallbacks.append(
                {
                    "kind": kind,
                    "scope": sorted(scope),
                    "fallback": mode,
                    "params": effective_params,
                }
            )
            if "disable_reuse" in mode_l:
                derived.reuse_enabled = False
            if "reduce_qps" in mode_l:
                derived.max_qps = min(derived.max_qps, 1.0)
            if "serialize_local_api_reads" in mode_l:
                derived.local_limit = 1
            elif "reduce_parallelism" in mode_l or "serialize" in mode_l:
                derived.total_limit = 1
            if "set_ble_parallelism_to_1" in mode_l:
                derived.ble_limit = 1
            if "set_cloud_parallelism_to_1" in mode_l:
                derived.cloud_limit = 1
            if "set_local_parallelism_to_1" in mode_l:
                derived.local_limit = 1
            if "serial_unknown" in mode_l:
                derived.unknown_limit = 1
            if "disable_batching" in mode_l:
                derived.batch_rules = []
            if "shrink_batch" in mode_l:
                for row in derived.batch_rules:
                    row["max_batch_size"] = min(int(row.get("max_batch_size", 20)), 4)
                    row["max_wait_ms"] = min(int(row.get("max_wait_ms", 80)), 40)

        for constraint in soft_constraints:
            kind = str(constraint.get("kind", ""))
            params = dict(constraint.get("params", {})) if isinstance(constraint.get("params", {}), dict) else {}
            guard = str(constraint.get("guard", "true"))
            fallback = str(constraint.get("fallback", "fallback_to_sequential"))
            normalized_fallback = self._normalized_fallback_mode(kind, fallback, runtime_metrics)
            scope_set = self._constraint_scope_set(constraint)
            guard_active = self._guard_active(guard, runtime_metrics)
            always_active = guard.strip().lower() in {"", "true"}
            enforced = always_active or guard_active

            fallback_on_inactive = self._fallback_triggers_on_inactive_guard(kind, guard, fallback)
            if not enforced:
                if fallback and not always_active and fallback_on_inactive:
                    if "shrink_batch" in normalized_fallback and kind in {
                        SoftConstraintKind.BATCH_GROUP.value,
                        SoftConstraintKind.SAME_SESSION_GROUP.value,
                    }:
                        params = self._apply_batch_shrink_params(params)
                    constraint_row = {
                        "kind": kind,
                        "scope": sorted(scope_set),
                        "params": dict(params),
                        "guard": guard,
                        "fallback": normalized_fallback,
                        "enforced": enforced,
                    }
                    derived.active_constraints.append(constraint_row)
                    apply_fallback(normalized_fallback, scope_set, params, kind)
                    if not (
                        "shrink_batch" in normalized_fallback
                        and kind in {SoftConstraintKind.BATCH_GROUP.value, SoftConstraintKind.SAME_SESSION_GROUP.value}
                    ):
                        continue
                else:
                    constraint_row = {
                        "kind": kind,
                        "scope": sorted(scope_set),
                        "params": dict(params),
                        "guard": guard,
                        "fallback": normalized_fallback,
                        "enforced": enforced,
                    }
                    derived.active_constraints.append(constraint_row)
                    continue
            else:
                constraint_row = {
                    "kind": kind,
                    "scope": sorted(scope_set),
                    "params": dict(params),
                    "guard": guard,
                    "fallback": normalized_fallback,
                    "enforced": enforced,
                }
                derived.active_constraints.append(constraint_row)

            if kind == SoftConstraintKind.BUDGET_K.value:
                resource = str(params.get("resource", "")).upper()
                limit = int(params.get("limit", 1))
                if scope_set and resource in {"BLE", "BLE_PARALLEL", "CLOUD", "CLOUD_PARALLEL", "LOCAL", "LOCAL_PARALLEL", "HA", "TOTAL", "TOTAL_PARALLEL"}:
                    derived.budget_rules.append(
                        {
                            "resource": resource,
                            "scope": sorted(scope_set),
                            "scope_set": set(scope_set),
                            "limit": max(1, limit),
                        }
                    )
                elif resource in {"BLE", "BLE_PARALLEL"}:
                    derived.ble_limit = max(1, min(derived.ble_limit, limit))
                elif resource in {"CLOUD", "CLOUD_PARALLEL"}:
                    derived.cloud_limit = max(1, min(derived.cloud_limit, limit))
                elif resource in {"LOCAL", "LOCAL_PARALLEL"}:
                    derived.local_limit = max(1, min(derived.local_limit, limit))
                elif resource in {"TOTAL", "TOTAL_PARALLEL"}:
                    derived.total_limit = max(1, min(derived.total_limit, limit))
            elif kind == SoftConstraintKind.NO_OVERLAP.value:
                resource = str(params.get("resource", "")).upper()
                if resource.startswith("BLE"):
                    derived.ble_limit = 1
                derived.no_overlap_scopes.append(set(scope_set))
            elif kind == SoftConstraintKind.RATE_LIMIT.value:
                max_qps = params.get("max_qps")
                if isinstance(max_qps, (int, float)):
                    derived.max_qps = min(derived.max_qps, float(max_qps))
                burst = params.get("burst")
                if isinstance(burst, (int, float)):
                    derived.rate_limit_burst = max(1, min(derived.rate_limit_burst, int(burst)))
                window_ms = params.get("window_ms")
                if isinstance(window_ms, (int, float)):
                    derived.rate_limit_window_ms = max(1, min(derived.rate_limit_window_ms, int(window_ms)))
            elif kind == SoftConstraintKind.BACKOFF_WINDOW.value:
                if guard_active:
                    factor = float(params.get("factor", 2.0))
                    derived.max_qps = min(derived.max_qps, max(0.1, derived.max_qps / max(1.0, factor)))
                    derived.cloud_limit = max(1, min(derived.cloud_limit, 1))
            elif kind == SoftConstraintKind.BATCH_GROUP.value:
                max_wait_ms = int(params.get("max_wait_ms", 80))
                if derived.latency_budget_ms > 0:
                    max_wait_ms = min(max_wait_ms, max(0, int(derived.latency_budget_ms / 4)))
                row = {
                    "scope": sorted(scope_set),
                    "scope_set": set(scope_set),
                    "group_key": str(params.get("group_key", "endpoint")),
                    "max_batch_size": int(params.get("max_batch_size", 20)),
                    "max_wait_ms": max_wait_ms,
                    "idempotent_only": bool(params.get("idempotent_only", False)),
                }
                if row["max_batch_size"] > 1 and row["max_wait_ms"] >= 0:
                    derived.batch_rules.append(row)
            elif kind == SoftConstraintKind.SAME_SESSION_GROUP.value:
                row = {
                    "scope": sorted(scope_set),
                    "scope_set": set(scope_set),
                    "group_key": str(params.get("group_key", "host")),
                    "reuse_window_ms": int(params.get("reuse_window_ms", 10_000)),
                }
                derived.reuse_window_ms = max(derived.reuse_window_ms, row["reuse_window_ms"])
                derived.session_rules.append(row)
            elif kind == SoftConstraintKind.MIN_GAP.value:
                gap_ms = int(params.get("gap_ms", params.get("min_gap_ms", 0)) or 0)
                ordered_scope = [str(item) for item in constraint.get("scope", []) if str(item)]
                for idx in range(len(ordered_scope) - 1):
                    pair = (ordered_scope[idx], ordered_scope[idx + 1])
                    derived.min_gap_pairs[pair] = max(derived.min_gap_pairs.get(pair, 0), gap_ms)
                    derived.soft_order_pairs.add(pair)
            elif kind == SoftConstraintKind.SOFT_ORDER.value:
                ordered_scope = [str(item) for item in constraint.get("scope", []) if str(item)]
                for idx in range(len(ordered_scope) - 1):
                    derived.soft_order_pairs.add((ordered_scope[idx], ordered_scope[idx + 1]))

            if fallback:
                if always_active:
                    apply_fallback(normalized_fallback, scope_set, params, kind)
                elif not fallback_on_inactive and guard_active:
                    apply_fallback(normalized_fallback, scope_set, params, kind)

        has_batch_rule = any(str(row.get("kind", "")).strip().upper() == SoftConstraintKind.BATCH_GROUP.value for row in derived.active_constraints)
        has_session_rule = any(str(row.get("kind", "")).strip().upper() == SoftConstraintKind.SAME_SESSION_GROUP.value for row in derived.active_constraints)
        if optimization_target is not None:
            auto_constraints: List[Dict[str, Any]] = []
            if not has_batch_rule and not derived.batch_rules:
                batch_scope = self._inferred_cloud_group_scope(
                    optimization_target,
                    group_key="endpoint",
                    batch_only=True,
                )
                if len(batch_scope) >= 2:
                    auto_constraints.append(
                        {
                            "kind": SoftConstraintKind.BATCH_GROUP.value,
                            "scope": batch_scope,
                            "params": {
                                "group_key": "endpoint",
                                "max_batch_size": 20,
                                "max_wait_ms": 80,
                                "idempotent_only": True,
                            },
                            "guard": "latency_budget_allows_batching AND 429_rate_low",
                            "fallback": "disable_batching_use_singleton_calls",
                        }
                    )
            if not has_session_rule and not derived.session_rules:
                session_scope = self._inferred_cloud_group_scope(
                    optimization_target,
                    group_key="host",
                    batch_only=False,
                )
                if len(session_scope) >= 2:
                    auto_constraints.append(
                        {
                            "kind": SoftConstraintKind.SAME_SESSION_GROUP.value,
                            "scope": session_scope,
                            "params": {
                                "group_key": "host",
                                "reuse_window_ms": 10000,
                            },
                            "guard": "latency_budget_allows_batching AND 429_rate_low",
                            "fallback": "disable_batching_use_singleton_calls",
                        }
                    )

            for constraint in auto_constraints:
                kind = str(constraint.get("kind", ""))
                params = dict(constraint.get("params", {})) if isinstance(constraint.get("params", {}), dict) else {}
                guard = str(constraint.get("guard", "true"))
                fallback = str(constraint.get("fallback", "fallback_to_sequential"))
                normalized_fallback = self._normalized_fallback_mode(kind, fallback, runtime_metrics)
                scope_set = self._constraint_scope_set(constraint)
                guard_active = self._guard_active(guard, runtime_metrics)
                always_active = guard.strip().lower() in {"", "true"}
                enforced = always_active or guard_active
                fallback_on_inactive = self._fallback_triggers_on_inactive_guard(kind, guard, fallback)

                if not enforced and fallback and not always_active and fallback_on_inactive:
                    if "shrink_batch" in normalized_fallback:
                        params = self._apply_batch_shrink_params(params)
                derived.active_constraints.append(
                    {
                        "kind": kind,
                        "scope": sorted(scope_set),
                        "params": dict(params),
                        "guard": guard,
                        "fallback": normalized_fallback,
                        "enforced": enforced,
                    }
                )

                if kind == SoftConstraintKind.BATCH_GROUP.value:
                    max_wait_ms = int(params.get("max_wait_ms", 80))
                    if derived.latency_budget_ms > 0:
                        max_wait_ms = min(max_wait_ms, max(0, int(derived.latency_budget_ms / 4)))
                    row = {
                        "scope": sorted(scope_set),
                        "scope_set": set(scope_set),
                        "group_key": str(params.get("group_key", "endpoint")),
                        "max_batch_size": int(params.get("max_batch_size", 20)),
                        "max_wait_ms": max_wait_ms,
                        "idempotent_only": bool(params.get("idempotent_only", False)),
                    }
                    if row["max_batch_size"] > 1 and row["max_wait_ms"] >= 0:
                        derived.batch_rules.append(row)
                elif kind == SoftConstraintKind.SAME_SESSION_GROUP.value:
                    row = {
                        "scope": sorted(scope_set),
                        "scope_set": set(scope_set),
                        "group_key": str(params.get("group_key", "host")),
                        "reuse_window_ms": int(params.get("reuse_window_ms", 10_000)),
                    }
                    derived.reuse_window_ms = max(derived.reuse_window_ms, row["reuse_window_ms"])
                    derived.session_rules.append(row)

                if fallback:
                    if always_active:
                        apply_fallback(normalized_fallback, scope_set, params, kind)
                    elif not fallback_on_inactive and guard_active:
                        apply_fallback(normalized_fallback, scope_set, params, kind)

        derived.total_limit = max(1, min(derived.total_limit, policy.max_parallel))
        derived.ble_limit = max(1, min(derived.ble_limit, derived.total_limit))
        derived.cloud_limit = max(1, min(derived.cloud_limit, derived.total_limit))
        derived.local_limit = max(1, min(derived.local_limit, derived.total_limit))
        derived.unknown_limit = max(1, min(derived.unknown_limit, derived.total_limit))
        derived.rate_limit_burst = max(1, derived.rate_limit_burst)
        derived.rate_limit_window_ms = max(1, derived.rate_limit_window_ms)
        derived.max_qps = max(0.1, derived.max_qps)
        return derived

    @staticmethod
    def _group_affinity(
        action_id: str,
        affinity_rules_by_action: Dict[str, List[Tuple[int, str]]],
        selected_group_counts: Dict[Tuple[int, str], int],
    ) -> int:
        affinity = 0
        for token in affinity_rules_by_action.get(action_id, []):
            affinity += selected_group_counts.get(token, 0)
        return affinity

    @staticmethod
    def _min_gap_conflict(candidate: str, selected: List[str], min_gap_pairs: Dict[Tuple[str, str], int]) -> bool:
        for src in selected:
            if (src, candidate) in min_gap_pairs:
                return True
        return False

    @staticmethod
    def _soft_order_blocked(
        candidate: str,
        selected: List[str],
        done: Set[str],
        soft_order_pairs: Set[Tuple[str, str]],
    ) -> bool:
        del candidate, selected, done, soft_order_pairs
        return False

    @staticmethod
    def _soft_order_predecessor_pressure(
        candidate: str,
        selected: List[str],
        done: Set[str],
        soft_order_pairs: Set[Tuple[str, str]],
    ) -> int:
        pressure = 0
        selected_set = set(selected)
        for src, dst in soft_order_pairs:
            if dst != candidate:
                continue
            if src in done or src in selected_set:
                continue
            pressure += 1
        return pressure

    @staticmethod
    def _overlap_conflict(
        candidate: str,
        no_overlap_scope_ids_by_action: Dict[str, List[int]],
        no_overlap_counts: Dict[int, int],
    ) -> bool:
        for scope_id in no_overlap_scope_ids_by_action.get(candidate, []):
            if no_overlap_counts.get(scope_id, 0) > 0:
                return True
        return False

    def _group_selected_actions(
        self,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        derived: DerivedConstraintPolicy,
    ) -> tuple[List[List[str]], List[Dict[str, Any]]]:
        if not selected:
            return [], []
        if not derived.batch_rules and not derived.session_rules:
            return [selected], []

        buckets = self._build_batching_buckets(selected, action_index, derived)
        groups: List[List[str]] = []
        assigned: Set[str] = set()
        for bucket in buckets:
            members = [str(action_id) for action_id in bucket.get("members", []) if str(action_id)]
            chunk_size = max(1, int(bucket.get("max_batch_size", len(members) or 1)))
            for idx in range(0, len(members), chunk_size):
                chunk = members[idx : idx + chunk_size]
                groups.append(chunk)
                assigned.update(chunk)

        def append_unassigned_groups(action_ids: List[str]) -> None:
            local_group: List[str] = []
            for action_id in action_ids:
                if action_id in assigned:
                    if local_group:
                        groups.append(list(local_group))
                        local_group = []
                    continue
                action = action_index[action_id]
                if (
                    self._action_protocol(action) == "LOCAL"
                    and not self._action_is_writeback(action)
                    and self._action_is_batch_safe(action)
                ):
                    local_group.append(action_id)
                    continue
                if local_group:
                    groups.append(list(local_group))
                    local_group = []
                groups.append([action_id])
            if local_group:
                groups.append(list(local_group))

        if not buckets:
            append_unassigned_groups(selected)
            return groups or [[action_id] for action_id in selected], []

        append_unassigned_groups(selected)

        return groups or [[action_id] for action_id in selected], buckets

    @staticmethod
    def _writeback_target_id(action: Dict[str, Any]) -> str:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        data_template = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
        return str(
            target.get("entity_id")
            or target.get("id")
            or exec_cfg.get("entity_id")
            or data_template.get("entity_id")
            or ""
        ).strip()

    @classmethod
    def _conservative_local_parallel_compatible(
        cls,
        candidate: str,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
    ) -> bool:
        candidate_action = action_index[candidate]
        if cls._action_protocol(candidate_action) != "LOCAL" or cls._action_is_writeback(candidate_action):
            return False
        if not cls._action_is_batch_safe(candidate_action):
            return False

        for action_id in selected:
            action = action_index[action_id]
            if cls._action_protocol(action) != "LOCAL" or cls._action_is_writeback(action):
                return False
            if not cls._action_is_batch_safe(action):
                return False
        return True

    @classmethod
    def _conservative_cloud_read_parallel_compatible(
        cls,
        candidate: str,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        soft_order_pairs: Set[Tuple[str, str]],
        ready: Set[str],
        action_rank: Dict[str, int],
        action_phase_by_action: Dict[str, str],
    ) -> bool:
        candidate_action = action_index[candidate]
        if cls._action_protocol(candidate_action) != "CLOUD":
            return False
        if cls._action_is_writeback(candidate_action) or not cls._action_is_read_like(candidate_action):
            return False

        candidate_phase = str(action_phase_by_action.get(candidate, "pre_control_acquisition"))
        if candidate_phase not in {"pre_control_acquisition", "post_control_verification"}:
            return False

        selected_cloud_count = 0
        for action_id in selected:
            action = action_index[action_id]
            if cls._action_protocol(action) != "CLOUD":
                return False
            if cls._action_is_writeback(action) or not cls._action_is_read_like(action):
                return False
            if cls._action_lane(action) != cls._action_lane(candidate_action):
                return False
            if str(action_phase_by_action.get(action_id, "pre_control_acquisition")) != candidate_phase:
                return False
            if (action_id, candidate) in soft_order_pairs or (candidate, action_id) in soft_order_pairs:
                return False
            selected_cloud_count += 1


        if selected_cloud_count < 2:
            return False

        candidate_rank = int(action_rank.get(candidate, 10_000))
        for action_id in ready:
            if action_id == candidate or action_id in selected:
                continue
            action = action_index[action_id]
            if cls._action_protocol(action) != "CLOUD":
                continue
            if cls._action_is_writeback(action) or not cls._action_is_read_like(action):
                continue
            if str(action_phase_by_action.get(action_id, "pre_control_acquisition")) != candidate_phase:
                continue
            if int(action_rank.get(action_id, 10_000)) < candidate_rank:
                return False
        return True

    @classmethod
    def _conservative_writeback_parallel_compatible(
        cls,
        candidate: str,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
    ) -> bool:
        candidate_action = action_index[candidate]
        candidate_lane = cls._action_lane(candidate_action)
        if not candidate_lane.startswith("WRITEBACK") or candidate_lane == "WRITEBACK_OVERALL":
            return False

        candidate_target = cls._writeback_target_id(candidate_action)
        if not candidate_target:
            return False

        for action_id in selected:
            action = action_index[action_id]
            lane = cls._action_lane(action)
            if not lane.startswith("WRITEBACK") or lane == "WRITEBACK_OVERALL":
                return False
            if cls._writeback_target_id(action) == candidate_target:
                return False
        return True

    @classmethod
    def _conservative_cross_protocol_read_parallel_compatible(
        cls,
        candidate: str,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        soft_order_pairs: Set[Tuple[str, str]],
        ready: Set[str],
        action_rank: Dict[str, int],
        action_phase_by_action: Dict[str, str],
    ) -> bool:
        if not selected:
            return True
        candidate_action = action_index[candidate]
        candidate_protocol = cls._action_protocol(candidate_action)
        if candidate_protocol not in {"CLOUD", "LOCAL"}:
            return False
        if cls._action_is_writeback(candidate_action) or not cls._action_is_batch_safe(candidate_action):
            return False
        candidate_phase = str(action_phase_by_action.get(candidate, "pre_control_acquisition"))
        if candidate_phase not in {"pre_control_acquisition", "post_control_verification"}:
            return False

        selected_phases = {
            str(action_phase_by_action.get(action_id, "pre_control_acquisition"))
            for action_id in selected
            if action_id in action_index
            and cls._action_protocol(action_index[action_id]) in {"CLOUD", "LOCAL"}
            and not cls._action_is_writeback(action_index[action_id])
            and cls._action_is_batch_safe(action_index[action_id])
        }
        if any(phase != candidate_phase for phase in selected_phases):
            return False

        if candidate_phase == "post_control_verification":
            candidate_rank = int(action_rank.get(candidate, 10_000))
            for action_id in ready:
                if action_id == candidate or action_id in selected:
                    continue
                action = action_index[action_id]
                if cls._action_is_writeback(action) or not cls._action_is_batch_safe(action):
                    continue
                if str(action_phase_by_action.get(action_id, "pre_control_acquisition")) != "post_control_verification":
                    continue
                if int(action_rank.get(action_id, 10_000)) < candidate_rank:
                    return False


        candidate_rank = int(action_rank.get(candidate, 10_000))
        for action_id in ready:
            if action_id == candidate or action_id in selected:
                continue
            action = action_index[action_id]
            if cls._action_protocol(action) != candidate_protocol:
                continue
            if cls._action_is_writeback(action) or not cls._action_is_batch_safe(action):
                continue
            if int(action_rank.get(action_id, 10_000)) < candidate_rank:
                return False

        selected_protocols = [
            cls._action_protocol(action_index[action_id])
            for action_id in selected
            if action_id in action_index
            and cls._action_protocol(action_index[action_id]) in {"CLOUD", "LOCAL"}
            and not cls._action_is_writeback(action_index[action_id])
            and cls._action_is_batch_safe(action_index[action_id])
        ]
        leading_protocol = selected_protocols[0] if selected_protocols else ""
        if leading_protocol and candidate_protocol != leading_protocol:
            leading_selected = [
                action_id
                for action_id in selected
                if action_id in action_index
                and cls._action_protocol(action_index[action_id]) == leading_protocol
            ]


            for action_id in ready:
                if action_id == candidate or action_id in selected:
                    continue
                action = action_index[action_id]
                if cls._action_protocol(action) != leading_protocol:
                    continue
                if cls._action_is_writeback(action) or not cls._action_is_batch_safe(action):
                    continue
                if leading_protocol == "LOCAL":
                    if cls._conservative_local_parallel_compatible(action_id, leading_selected, action_index):
                        return False
                    continue
                if all(
                    cls._action_protocol(action_index[selected_id]) == leading_protocol
                    and cls._action_lane(action_index[selected_id]) == cls._action_lane(action)
                    for selected_id in leading_selected
                ) and cls._shares_affinity_token(action_id, leading_selected, affinity_tokens_by_action):
                    return False

        saw_different_protocol = False
        for action_id in selected:
            action = action_index[action_id]
            protocol = cls._action_protocol(action)
            if protocol not in {"CLOUD", "LOCAL"}:
                return False
            if cls._action_is_writeback(action) or not cls._action_is_batch_safe(action):
                return False
            if (action_id, candidate) in soft_order_pairs or (candidate, action_id) in soft_order_pairs:
                return False
            if protocol != candidate_protocol:
                saw_different_protocol = True
        return saw_different_protocol

    @classmethod
    def _snapshot_frontier_blocks_candidate(
        cls,
        candidate: str,
        selected: List[str],
        ready: Set[str],
        action_index: Dict[str, Dict[str, Any]],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        soft_order_pairs: Set[Tuple[str, str]],
        action_rank: Dict[str, int],
        action_phase_by_action: Dict[str, str],
    ) -> bool:
        if not selected:
            return False
        if any(
            str(phase) in {"control", "post_control_verification"}
            for phase in action_phase_by_action.values()
        ):
            return False

        candidate_action = action_index[candidate]
        if cls._action_protocol(candidate_action) not in {"CLOUD", "LOCAL"}:
            return False
        if cls._action_is_writeback(candidate_action) or not cls._action_is_batch_safe(candidate_action):
            return False
        if str(action_phase_by_action.get(candidate, "pre_control_acquisition")) != "pre_control_acquisition":
            return False

        candidate_rank = int(action_rank.get(candidate, 10_000))
        for action_id in ready:
            if action_id == candidate or action_id in selected:
                continue
            action = action_index[action_id]
            if cls._action_protocol(action) not in {"CLOUD", "LOCAL"}:
                continue
            if cls._action_is_writeback(action) or not cls._action_is_batch_safe(action):
                continue
            if str(action_phase_by_action.get(action_id, "pre_control_acquisition")) != "pre_control_acquisition":
                continue
            if int(action_rank.get(action_id, 10_000)) < candidate_rank:
                if cls._conservative_batch_compatible(
                    action_id,
                    selected,
                    action_index,
                    affinity_tokens_by_action,
                    soft_order_pairs,
                    ready,
                    action_rank,
                    action_phase_by_action,
                ):
                    return True
        return False

    def _prepare_cloud_request_slots(
        self,
        action_index: Dict[str, Dict[str, Any]],
        derived: DerivedConstraintPolicy,
    ) -> Dict[str, Tuple[str, int]]:
        slots: Dict[str, Tuple[str, int]] = {}
        for rule in derived.batch_rules:
            scope_set = set(rule.get("scope_set", set()))
            if not scope_set:
                scope_set = {str(item) for item in rule.get("scope", []) if str(item)}
                rule["scope_set"] = scope_set
            group_key = str(rule.get("group_key", "endpoint"))
            max_batch_size = max(1, int(rule.get("max_batch_size", 1)))
            for action_id in sorted(scope_set):
                action = action_index.get(action_id)
                if action is None:
                    continue
                if self._action_protocol(action) != "CLOUD":
                    continue
                if self._action_is_writeback(action) or not self._action_is_read_like(action):
                    continue
                bucket = self._action_batch_group_value(action, group_key)
                if not bucket:
                    continue
                slots[action_id] = (f"bucket:{bucket}", max_batch_size)
        return slots

    @staticmethod
    def _cloud_request_increment(
        action_id: str,
        cloud_request_slots: Dict[str, Tuple[str, int]],
        cloud_request_counts: Dict[str, int],
    ) -> int:
        bucket, max_batch_size = cloud_request_slots.get(action_id, (f"single:{action_id}", 1))
        current = int(cloud_request_counts.get(bucket, 0))
        return 1 if current % max(1, max_batch_size) == 0 else 0

    @classmethod
    def _local_frontier_increment(
        cls,
        candidate: str,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        soft_order_pairs: Set[Tuple[str, str]],
        action_phase_by_action: Dict[str, str],
    ) -> int:
        candidate_action = action_index[candidate]
        if cls._action_protocol(candidate_action) != "LOCAL":
            return 1
        if cls._action_is_writeback(candidate_action) or not cls._action_is_batch_safe(candidate_action):
            return 1

        candidate_phase = str(action_phase_by_action.get(candidate, "pre_control_acquisition"))
        compatible_local_seen = False
        for action_id in selected:
            action = action_index[action_id]
            if cls._action_protocol(action) != "LOCAL":
                continue
            if cls._action_is_writeback(action) or not cls._action_is_batch_safe(action):
                return 1
            if str(action_phase_by_action.get(action_id, "pre_control_acquisition")) != candidate_phase:
                return 1
            if (action_id, candidate) in soft_order_pairs or (candidate, action_id) in soft_order_pairs:
                return 1
            compatible_local_seen = True
        return 0 if compatible_local_seen else 1

    @classmethod
    def _candidate_occupancy_increment(
        cls,
        candidate: str,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        cloud_request_slots: Dict[str, Tuple[str, int]],
        cloud_request_counts: Dict[str, int],
        soft_order_pairs: Set[Tuple[str, str]],
        action_phase_by_action: Dict[str, str],
    ) -> int:
        resource = cls._action_resource(action_index[candidate])
        if resource == "CLOUD":
            return cls._cloud_request_increment(candidate, cloud_request_slots, cloud_request_counts)
        if resource == "LOCAL":
            return cls._local_frontier_increment(
                candidate,
                selected,
                action_index,
                soft_order_pairs,
                action_phase_by_action,
            )
        return 1

    def _candidate_sort_key(
        self,
        node: str,
        selected: List[str],
        done: Set[str],
        conservative_grouping: bool,
        action_to_mssus: Dict[str, List[str]],
        dag: TypedDAG,
        baseline_trace_hints: Dict[str, Any],
        action_index: Dict[str, Dict[str, Any]],
        derived: DerivedConstraintPolicy,
        critical_boost: Dict[str, int],
        critical_score: Dict[str, float],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        selected_group_counts: Dict[Tuple[int, str], int],
        action_rank: Dict[str, int],
    ) -> Tuple[Any, ...]:
        return (
            action_rank.get(node, 10_000)
            if conservative_grouping
            else self._observable_anchor_priority(
                node,
                action_to_mssus,
                dag,
                baseline_trace_hints,
                action_index,
            ),
            self._observable_anchor_priority(
                node,
                action_to_mssus,
                dag,
                baseline_trace_hints,
                action_index,
            )
            if conservative_grouping
            else 0,
            self._soft_order_predecessor_pressure(
                node,
                selected,
                done,
                derived.soft_order_pairs,
            ),
            -critical_boost.get(node, 0),
            -critical_score.get(node, 0.0),
            -self._group_affinity(node, affinity_tokens_by_action, selected_group_counts),
            action_rank.get(node, 10_000),
            node,
        )

    @staticmethod
    def _protocol_priority(action: Dict[str, Any]) -> int:
        protocol = CrossProtocolScheduler._action_protocol(action)
        if protocol == "CLOUD":
            return 0
        if protocol == "LOCAL":
            return 1
        if protocol == "BLE":
            return 2
        if protocol == "HA":
            return 3
        return 4

    @staticmethod
    def _batch_protocol_signature(selected: List[str], action_index: Dict[str, Dict[str, Any]]) -> Tuple[str, ...]:
        return tuple(
            sorted(
                {
                    CrossProtocolScheduler._action_protocol(action_index[action_id])
                    for action_id in selected
                    if action_id in action_index
                }
            )
        )

    def _candidate_allowed_in_batch(
        self,
        action_id: str,
        build_state: BatchBuildState,
        ready: Set[str],
        done: Set[str],
        action_index: Dict[str, Dict[str, Any]],
        derived: DerivedConstraintPolicy,
        conservative_grouping: bool,
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        action_rank: Dict[str, int],
        action_phase_by_action: Dict[str, str],
        cloud_request_slots: Dict[str, Tuple[str, int]],
        budget_rule_ids_by_action: Dict[str, List[int]],
        no_overlap_scope_ids_by_action: Dict[str, List[int]],
        fat_actions: Set[str],
        allow_ble_api_frontier: bool = False,
    ) -> bool:
        selected = build_state.selected
        if build_state.unknown_count >= derived.unknown_limit and selected:
            return False
        if selected and any(node in fat_actions for node in selected):
            return False

        resource = self._action_resource(action_index[action_id])
        occupancy_increment = self._candidate_occupancy_increment(
            action_id,
            selected,
            action_index,
            cloud_request_slots,
            build_state.cloud_request_counts,
            derived.soft_order_pairs,
            action_phase_by_action,
        )
        candidate_is_writeback = self._action_is_writeback(action_index[action_id])
        selected_has_writeback = any(self._action_is_writeback(action_index[node]) for node in selected)

        if (
            conservative_grouping
            and len(selected) >= derived.total_limit
            and occupancy_increment > 0
        ):
            if resource != "CLOUD" or not self._conservative_cloud_read_parallel_compatible(
                action_id,
                selected,
                action_index,
                derived.soft_order_pairs,
                ready,
                action_rank,
                action_phase_by_action,
            ):
                return False
        if self._phase_barrier_blocks(
            action_id,
            selected,
            done,
            action_phase_by_action,
        ):
            return False
        if self._snapshot_frontier_blocks_candidate(
            action_id,
            selected,
            ready,
            action_index,
            affinity_tokens_by_action,
            derived.soft_order_pairs,
            action_rank,
            action_phase_by_action,
        ):
            return False
        if conservative_grouping and not self._conservative_batch_compatible(
            action_id,
            selected,
            action_index,
            affinity_tokens_by_action,
            derived.soft_order_pairs,
            ready,
            action_rank,
            action_phase_by_action,
            allow_ble_api_frontier=allow_ble_api_frontier,
        ):
            return False
        if action_id in fat_actions and selected:
            return False
        if candidate_is_writeback and any(item in fat_actions for item in selected):
            return False
        if action_id in fat_actions and selected_has_writeback:
            return False
        if build_state.total_occupancy + occupancy_increment > derived.total_limit:
            return False
        if resource == "BLE" and build_state.ble_count >= derived.ble_limit:
            return False
        if resource == "CLOUD" and build_state.cloud_count + occupancy_increment > derived.cloud_limit:
            return False
        if resource == "LOCAL" and build_state.local_count >= derived.local_limit:
            return False
        if resource == "UNKNOWN" and (build_state.unknown_count >= derived.unknown_limit or selected):
            return False
        if self._budget_conflict(action_id, budget_rule_ids_by_action, build_state.budget_counts, derived.budget_rules):
            return False
        if self._overlap_conflict(action_id, no_overlap_scope_ids_by_action, build_state.no_overlap_counts):
            return False
        if self._min_gap_conflict(action_id, selected, derived.min_gap_pairs):
            return False
        return True

    def _apply_pick_to_batch_state(
        self,
        picked: str,
        build_state: BatchBuildState,
        action_index: Dict[str, Dict[str, Any]],
        budget_rule_ids_by_action: Dict[str, List[int]],
        no_overlap_scope_ids_by_action: Dict[str, List[int]],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        cloud_request_slots: Dict[str, Tuple[str, int]],
        derived: DerivedConstraintPolicy,
        action_phase_by_action: Dict[str, str],
    ) -> None:
        build_state.selected.append(picked)
        resource = self._action_resource(action_index[picked])
        occupancy_increment = self._candidate_occupancy_increment(
            picked,
            build_state.selected[:-1],
            action_index,
            cloud_request_slots,
            build_state.cloud_request_counts,
            derived.soft_order_pairs,
            action_phase_by_action,
        )
        if resource == "BLE":
            build_state.ble_count += 1
        if resource == "CLOUD":
            build_state.cloud_count += occupancy_increment
            bucket, _ = cloud_request_slots.get(picked, (f"single:{picked}", 1))
            build_state.cloud_request_counts[bucket] = build_state.cloud_request_counts.get(bucket, 0) + 1
        if resource == "LOCAL":
            build_state.local_count += 1
        if resource == "UNKNOWN":
            build_state.unknown_count += 1
        build_state.total_occupancy += occupancy_increment
        for rule_id in budget_rule_ids_by_action.get(picked, []):
            build_state.budget_counts[rule_id] = build_state.budget_counts.get(rule_id, 0) + 1
        for scope_id in no_overlap_scope_ids_by_action.get(picked, []):
            build_state.no_overlap_counts[scope_id] = build_state.no_overlap_counts.get(scope_id, 0) + 1
        for token in affinity_tokens_by_action.get(picked, []):
            build_state.selected_group_counts[token] = build_state.selected_group_counts.get(token, 0) + 1

    def _build_batch_from_order(
        self,
        ordered_candidates: List[str],
        stop_on_protocol_switch: bool,
        ready: Set[str],
        done: Set[str],
        action_index: Dict[str, Dict[str, Any]],
        derived: DerivedConstraintPolicy,
        conservative_grouping: bool,
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        action_rank: Dict[str, int],
        action_phase_by_action: Dict[str, str],
        cloud_request_slots: Dict[str, Tuple[str, int]],
        budget_rule_ids_by_action: Dict[str, List[int]],
        no_overlap_scope_ids_by_action: Dict[str, List[int]],
        fat_actions: Set[str],
        allow_ble_api_frontier: bool = False,
    ) -> BatchBuildState:
        build_state = BatchBuildState()
        while True:
            remaining = [node for node in ordered_candidates if node in ready and node not in build_state.selected]
            if not remaining:
                break
            picked = None
            for action_id in remaining:
                if stop_on_protocol_switch and build_state.selected:
                    leading_protocol = self._action_protocol(action_index[build_state.selected[0]])
                    if self._action_protocol(action_index[action_id]) != leading_protocol:
                        continue
                if self._candidate_allowed_in_batch(
                    action_id,
                    build_state,
                    ready,
                    done,
                    action_index,
                    derived,
                    conservative_grouping,
                    affinity_tokens_by_action,
                    action_rank,
                    action_phase_by_action,
                    cloud_request_slots,
                    budget_rule_ids_by_action,
                    no_overlap_scope_ids_by_action,
                    fat_actions,
                    allow_ble_api_frontier=allow_ble_api_frontier,
                ):
                    picked = action_id
                    break
            if picked is None:
                break
            self._apply_pick_to_batch_state(
                picked,
                build_state,
                action_index,
                budget_rule_ids_by_action,
                no_overlap_scope_ids_by_action,
                affinity_tokens_by_action,
                cloud_request_slots,
                derived,
                action_phase_by_action,
            )
        return build_state

    def _build_batching_buckets(
        self,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        derived: DerivedConstraintPolicy,
    ) -> List[Dict[str, Any]]:
        buckets: List[Dict[str, Any]] = []
        selected_order = {action_id: idx for idx, action_id in enumerate(selected)}

        def extend_buckets(
            *,
            rule_kind: str,
            scope_actions: List[str],
            group_key: str,
            max_batch_size: int,
            max_wait_ms: int,
            idempotent_only: bool,
            bucket_value_fn,
        ) -> None:
            grouped: Dict[str, List[str]] = {}
            for action_id in scope_actions:
                action = action_index[action_id]
                if self._action_protocol(action) != "CLOUD":
                    continue
                if self._action_is_writeback(action):
                    continue
                if idempotent_only and not self._action_is_idempotent(action):
                    continue
                bucket_key = str(bucket_value_fn(action, group_key) or "").strip()
                if not bucket_key:
                    continue
                grouped.setdefault(bucket_key, []).append(action_id)

            ordered_groups = sorted(
                grouped.items(),
                key=lambda item: min(selected_order.get(action_id, 10_000) for action_id in item[1]),
            )
            for bucket_key, members in ordered_groups:
                if len(members) < 2:
                    continue
                members = sorted(members, key=lambda action_id: selected_order.get(action_id, 10_000))
                buckets.append(
                    {
                        "rule_kind": rule_kind,
                        "group_key": group_key,
                        "bucket": bucket_key,
                        "members": members,
                        "size": len(members),
                        "chunks": max(1, (len(members) + max(1, max_batch_size) - 1) // max(1, max_batch_size)),
                        "max_batch_size": max(1, max_batch_size),
                        "max_wait_ms": max(0, max_wait_ms),
                    }
                )

        for rule in derived.batch_rules:
            scope = set(rule.get("scope", []))
            scoped_actions = [action_id for action_id in selected if action_id in scope]
            if len(scoped_actions) < 2:
                continue
            extend_buckets(
                rule_kind=SoftConstraintKind.BATCH_GROUP.value,
                scope_actions=scoped_actions,
                group_key=str(rule.get("group_key", "endpoint")),
                max_batch_size=max(1, int(rule.get("max_batch_size", 20))),
                max_wait_ms=max(0, int(rule.get("max_wait_ms", 80))),
                idempotent_only=bool(rule.get("idempotent_only", False)),
                bucket_value_fn=lambda action, key: self._action_batch_group_value(action, key),
            )

        if buckets:
            return buckets

        for rule in derived.session_rules:
            scope = set(rule.get("scope", []))
            scoped_actions = [action_id for action_id in selected if action_id in scope]
            if len(scoped_actions) < 2:
                continue
            overlapping_batch_rules = [
                row for row in derived.batch_rules if set(row.get("scope", [])) & set(scoped_actions)
            ]
            max_batch_size = min(
                [max(1, int(row.get("max_batch_size", 20))) for row in overlapping_batch_rules] or [4]
            )
            max_wait_ms = min(
                [max(0, int(row.get("max_wait_ms", 40))) for row in overlapping_batch_rules] or [40]
            )
            extend_buckets(
                rule_kind=SoftConstraintKind.SAME_SESSION_GROUP.value,
                scope_actions=scoped_actions,
                group_key=str(rule.get("group_key", "host")),
                max_batch_size=max_batch_size,
                max_wait_ms=max_wait_ms,
                idempotent_only=False,
                bucket_value_fn=lambda action, key: self._action_group_value(action, key),
            )
        return buckets

    @classmethod
    def _corridor_action_eligible(
        cls,
        action_id: str,
        action_index: Dict[str, Dict[str, Any]],
        action_phase_by_action: Dict[str, str],
    ) -> bool:
        action = action_index[action_id]
        if str(action_phase_by_action.get(action_id, "pre_control_acquisition")) != "pre_control_acquisition":
            return False
        if cls._action_protocol(action) not in {"CLOUD", "LOCAL"}:
            return False
        if cls._action_is_writeback(action):
            return False
        return cls._action_is_batch_safe(action)

    @classmethod
    def _ble_frontier_anchor_eligible(
        cls,
        action_id: str,
        action_index: Dict[str, Dict[str, Any]],
        action_phase_by_action: Dict[str, str],
    ) -> bool:
        action = action_index[action_id]
        if cls._action_protocol(action) != "BLE":
            return False
        if cls._action_is_writeback(action):
            return False
        return str(action_phase_by_action.get(action_id, "pre_control_acquisition")) == "pre_control_acquisition"

    @classmethod
    def _api_frontier_action_eligible(
        cls,
        action_id: str,
        action_index: Dict[str, Dict[str, Any]],
        action_phase_by_action: Dict[str, str],
    ) -> bool:
        return cls._corridor_action_eligible(action_id, action_index, action_phase_by_action)

    @staticmethod
    def _action_has_explicit_group_metadata(action: Dict[str, Any]) -> bool:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        data_template = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}
        for container in (action, target, exec_cfg, data_template):
            if any(
                str(container.get(key, "")).strip()
                for key in ("endpoint_group_key", "host_group_key", "session_group_key", "bucket")
            ):
                return True
        return False

    @classmethod
    def _extract_optimizable_corridor(
        cls,
        action_ids: List[str],
        done: Set[str],
        action_index: Dict[str, Dict[str, Any]],
        action_phase_by_action: Dict[str, str],
    ) -> List[str]:
        unscheduled = [action_id for action_id in action_ids if action_id not in done]
        if not unscheduled:
            return []
        first = unscheduled[0]
        if not cls._corridor_action_eligible(first, action_index, action_phase_by_action):
            return []

        corridor: List[str] = []
        for action_id in unscheduled:
            if not cls._corridor_action_eligible(action_id, action_index, action_phase_by_action):
                break
            corridor.append(action_id)

        if len(corridor) < 6:
            return []
        cloud_count = sum(1 for action_id in corridor if cls._action_protocol(action_index[action_id]) == "CLOUD")
        local_count = sum(1 for action_id in corridor if cls._action_protocol(action_index[action_id]) == "LOCAL")
        if cloud_count < 3 or local_count < 2:
            return []
        return corridor

    @classmethod
    def _extract_frontier_window(
        cls,
        action_ids: List[str],
        ready: Set[str],
        done: Set[str],
        action_index: Dict[str, Dict[str, Any]],
        action_phase_by_action: Dict[str, str],
        *,
        max_window: int = 16,
    ) -> List[str]:


        unscheduled = [action_id for action_id in action_ids if action_id not in done]
        if not unscheduled:
            return []

        start_idx = -1
        for idx, action_id in enumerate(unscheduled):
            action = action_index[action_id]
            if action_id in ready:
                if cls._corridor_action_eligible(action_id, action_index, action_phase_by_action):
                    start_idx = idx
                    break
                return []
            if cls._action_is_writeback(action):
                return []
            if str(action_phase_by_action.get(action_id, "pre_control_acquisition")) != "pre_control_acquisition":
                return []

        if start_idx < 0:
            return []

        window: List[str] = []
        for action_id in unscheduled[start_idx:]:
            if len(window) >= max_window:
                break
            action = action_index[action_id]
            if cls._corridor_action_eligible(action_id, action_index, action_phase_by_action):
                window.append(action_id)
                continue
            if action_id in ready:
                break
            if cls._action_is_writeback(action):
                break
            if str(action_phase_by_action.get(action_id, "pre_control_acquisition")) != "pre_control_acquisition":
                break
            break

        initial_ready = [
            action_id
            for action_id in window
            if action_id in ready and cls._corridor_action_eligible(action_id, action_index, action_phase_by_action)
        ]
        if len(initial_ready) < 2:
            return []

        cloud_count = sum(1 for action_id in window if cls._action_protocol(action_index[action_id]) == "CLOUD")
        local_count = sum(1 for action_id in window if cls._action_protocol(action_index[action_id]) == "LOCAL")
        if cloud_count + local_count < 3:
            return []
        if cloud_count >= 4 or local_count >= 3:
            return window
        if cloud_count >= 2 and local_count >= 2:
            return window
        return []

    @classmethod
    def _extract_ble_api_frontier_window(
        cls,
        action_ids: List[str],
        ready: Set[str],
        done: Set[str],
        action_index: Dict[str, Dict[str, Any]],
        action_phase_by_action: Dict[str, str],
        *,
        max_window: int = 20,
    ) -> List[str]:


        unscheduled = [action_id for action_id in action_ids if action_id not in done]
        if not unscheduled:
            return []

        anchor = unscheduled[0]
        if anchor not in ready or not cls._ble_frontier_anchor_eligible(anchor, action_index, action_phase_by_action):
            return []

        window: List[str] = [anchor]
        api_count = 0
        cloud_count = 0
        local_count = 0
        scanned = 0
        for action_id in unscheduled[1:]:
            if len(window) >= max_window or scanned >= max_window:
                break
            scanned += 1
            action = action_index[action_id]
            phase = str(action_phase_by_action.get(action_id, "pre_control_acquisition"))
            if cls._action_is_writeback(action) or phase != "pre_control_acquisition":
                break

            protocol = cls._action_protocol(action)
            if protocol == "BLE":


                break

            if not cls._api_frontier_action_eligible(action_id, action_index, action_phase_by_action):
                break
            if action_id not in ready:
                break
            if protocol == "CLOUD" and not cls._action_has_explicit_group_metadata(action):
                break

            window.append(action_id)
            api_count += 1
            if protocol == "CLOUD":
                cloud_count += 1
            elif protocol == "LOCAL":
                local_count += 1

        if api_count < 2:
            return []
        if cloud_count >= 2 or local_count >= 2:
            return window
        if cloud_count >= 1 and local_count >= 1:
            return window
        return []

    def _corridor_candidate_orders(
        self,
        ready: Set[str],
        done: Set[str],
        action_index: Dict[str, Dict[str, Any]],
        action_to_mssus: Dict[str, List[str]],
        dag: TypedDAG,
        baseline_trace_hints: Dict[str, Any],
        derived: DerivedConstraintPolicy,
        critical_boost: Dict[str, int],
        critical_score: Dict[str, float],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        action_rank: Dict[str, int],
        conservative_grouping: bool,
    ) -> List[Tuple[List[str], bool]]:
        ready_list = list(ready)
        default_order = sorted(
            ready_list,
            key=lambda node: self._candidate_sort_key(
                node,
                [],
                done,
                conservative_grouping,
                action_to_mssus,
                dag,
                baseline_trace_hints,
                action_index,
                derived,
                critical_boost,
                critical_score,
                affinity_tokens_by_action,
                {},
                action_rank,
            ),
        )

        def stable_protocol_order(primary: str) -> List[str]:
            return sorted(
                ready_list,
                key=lambda node: (
                    0 if self._action_protocol(action_index[node]) == primary else 1,
                    self._candidate_sort_key(
                        node,
                        [],
                        done,
                        conservative_grouping,
                        action_to_mssus,
                        dag,
                        baseline_trace_hints,
                        action_index,
                        derived,
                        critical_boost,
                        critical_score,
                        affinity_tokens_by_action,
                        {},
                        action_rank,
                    ),
                ),
            )

        orders: List[Tuple[List[str], bool]] = [
            (default_order, False),
            (stable_protocol_order("CLOUD"), True),
            (stable_protocol_order("LOCAL"), True),
        ]
        focus_actions = default_order[: min(4, len(default_order))]
        for focus in focus_actions:
            protocol = self._action_protocol(action_index[focus])
            ordered = [focus]
            for node in default_order:
                if node == focus:
                    continue
                if self._action_protocol(action_index[node]) == protocol:
                    ordered.append(node)
            for node in default_order:
                if node != focus and node not in ordered:
                    ordered.append(node)
            orders.append((ordered, protocol in {"CLOUD", "LOCAL"}))

        unique: List[Tuple[List[str], bool]] = []
        seen: Set[Tuple[Tuple[str, ...], bool]] = set()
        for order, stop_on_protocol_switch in orders:
            key = (tuple(order), stop_on_protocol_switch)
            if key in seen:
                continue
            seen.add(key)
            unique.append((order, stop_on_protocol_switch))
        return unique[:6]

    def _corridor_remaining_lower_bound(
        self,
        remaining: Set[str],
        action_index: Dict[str, Dict[str, Any]],
        cloud_request_slots: Dict[str, Tuple[str, int]],
    ) -> float:
        if not remaining:
            return 0.0
        cloud_buckets: Dict[str, int] = {}
        has_local = False
        ble_count = 0
        for action_id in remaining:
            action = action_index[action_id]
            protocol = self._action_protocol(action)
            if protocol == "CLOUD":
                bucket, max_batch_size = cloud_request_slots.get(action_id, (f"single:{action_id}", 1))
                bucket_key = f"{bucket}|{max(1, max_batch_size)}"
                cloud_buckets[bucket_key] = cloud_buckets.get(bucket_key, 0) + 1
            elif protocol == "LOCAL":
                has_local = True
            elif protocol == "BLE":
                ble_count += 1
        cloud_lb = 0.0
        for key, count in cloud_buckets.items():
            max_batch_size = int(key.rsplit("|", 1)[-1])
            cloud_lb += max(1, (count + max(1, max_batch_size) - 1) // max(1, max_batch_size))
        local_lb = 0.35 if has_local else 0.0
        return cloud_lb + local_lb + float(ble_count)

    def _corridor_batch_cost(
        self,
        batch_state: BatchBuildState,
        remaining_after: Set[str],
        ready_before: Set[str],
        previous_signature: Tuple[str, ...],
        action_index: Dict[str, Dict[str, Any]],
        action_rank: Dict[str, int],
        *,
        cheap_local_overlap: bool = False,
    ) -> float:
        selected = batch_state.selected
        if not selected:
            return 10_000.0

        has_cloud = batch_state.cloud_count > 0
        has_local = batch_state.local_count > 0
        has_ble = batch_state.ble_count > 0
        batch_cost = 0.0
        if has_ble:
            batch_cost += 1.0
        if has_cloud:
            batch_cost += 1.0 + max(0, batch_state.cloud_count - 1) * 0.35
        if has_local and not has_cloud:
            batch_cost += 0.35
        elif has_local and has_cloud:
            batch_cost += 0.05 if cheap_local_overlap else 0.9

        remaining_cloud = sum(
            1 for action_id in remaining_after if self._action_protocol(action_index[action_id]) == "CLOUD"
        )
        remaining_local = sum(
            1 for action_id in remaining_after if self._action_protocol(action_index[action_id]) == "LOCAL"
        )
        signature = self._batch_protocol_signature(selected, action_index)

        if has_local and remaining_cloud > 0:
            batch_cost += 4.0
        if has_cloud and has_local and remaining_cloud > 0:
            batch_cost += 6.0
        if has_local and not has_cloud and remaining_local > 0:
            batch_cost += 1.5
        if "LOCAL" in previous_signature and has_cloud:
            batch_cost += 3.0
        if has_ble and (has_cloud or has_local):
            batch_cost -= 0.8

        unused_ready_cloud = [
            action_id
            for action_id in ready_before
            if action_id not in selected and self._action_protocol(action_index[action_id]) == "CLOUD"
        ]
        if has_local and unused_ready_cloud:
            batch_cost += 3.0

        for protocol in ("CLOUD", "LOCAL"):
            selected_protocol_ranks = [
                int(action_rank.get(action_id, 10_000))
                for action_id in selected
                if self._action_protocol(action_index[action_id]) == protocol
            ]
            if not selected_protocol_ranks:
                continue
            latest_selected_rank = max(selected_protocol_ranks)
            if any(
                self._action_protocol(action_index[action_id]) == protocol
                and int(action_rank.get(action_id, 10_000)) < latest_selected_rank
                for action_id in remaining_after
            ):
                batch_cost += 5.0
        return batch_cost

    def _corridor_search_first_batch(
        self,
        corridor: List[str],
        ready: Set[str],
        done: Set[str],
        out: Dict[str, Set[str]],
        indegree: Dict[str, int],
        action_index: Dict[str, Dict[str, Any]],
        action_to_mssus: Dict[str, List[str]],
        dag: TypedDAG,
        baseline_trace_hints: Dict[str, Any],
        derived: DerivedConstraintPolicy,
        critical_boost: Dict[str, int],
        critical_score: Dict[str, float],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        action_rank: Dict[str, int],
        action_phase_by_action: Dict[str, str],
        cloud_request_slots: Dict[str, Tuple[str, int]],
        budget_rule_ids_by_action: Dict[str, List[int]],
        no_overlap_scope_ids_by_action: Dict[str, List[int]],
        fat_actions: Set[str],
        conservative_grouping: bool,
        *,
        beam_width: int = 4,
        lookahead_depth: int = 3,
        cheap_local_overlap: bool = False,
        required_first_batch_actions: Set[str] | None = None,
        min_first_batch_size: int = 1,
        allow_ble_api_frontier: bool = False,
    ) -> List[str]:
        corridor_set = set(corridor)
        initial_indegree = {action_id: int(indegree.get(action_id, 0)) for action_id in corridor}
        initial_ready = {action_id for action_id in corridor if action_id in ready and initial_indegree.get(action_id, 0) == 0}
        if len(initial_ready) < 2:
            return []
        required_first_batch_actions = required_first_batch_actions or set()

        initial_state = CorridorSearchState(
            done=set(done),
            indegree=initial_indegree,
            ready=initial_ready,
            scheduled_batches=[],
            score=0.0,
        )
        beam: List[CorridorSearchState] = [initial_state]

        for _ in range(lookahead_depth):
            expanded: List[Tuple[float, CorridorSearchState]] = []
            for state in beam:
                remaining = corridor_set - state.done
                if not remaining or not state.ready:
                    expanded.append((state.score, state))
                    continue

                candidate_orders = self._corridor_candidate_orders(
                    state.ready,
                    state.done,
                    action_index,
                    action_to_mssus,
                    dag,
                    baseline_trace_hints,
                    derived,
                    critical_boost,
                    critical_score,
                    affinity_tokens_by_action,
                    action_rank,
                    conservative_grouping,
                )

                previous_signature = ()
                if state.scheduled_batches:
                    previous_signature = self._batch_protocol_signature(state.scheduled_batches[-1], action_index)

                seen_batches: Set[Tuple[str, ...]] = set()
                for ordered_candidates, stop_on_protocol_switch in candidate_orders:
                    batch_state = self._build_batch_from_order(
                        ordered_candidates,
                        stop_on_protocol_switch,
                        state.ready,
                        state.done,
                        action_index,
                        derived,
                        conservative_grouping,
                        affinity_tokens_by_action,
                        action_rank,
                        action_phase_by_action,
                        cloud_request_slots,
                        budget_rule_ids_by_action,
                        no_overlap_scope_ids_by_action,
                        fat_actions,
                        allow_ble_api_frontier=allow_ble_api_frontier,
                    )
                    batch = batch_state.selected
                    if not batch:
                        continue
                    if not state.scheduled_batches:
                        if required_first_batch_actions and not required_first_batch_actions.issubset(set(batch)):
                            continue
                        if len(batch) < min_first_batch_size:
                            continue
                    batch_key = tuple(batch)
                    if batch_key in seen_batches:
                        continue
                    seen_batches.add(batch_key)

                    next_done = set(state.done)
                    next_indegree = dict(state.indegree)
                    next_ready = set(state.ready)
                    for action_id in batch:
                        next_done.add(action_id)
                        next_ready.discard(action_id)
                        for nxt in out.get(action_id, set()):
                            if nxt not in corridor_set:
                                continue
                            next_indegree[nxt] = max(0, next_indegree.get(nxt, 0) - 1)
                            if next_indegree[nxt] == 0 and nxt not in next_done:
                                next_ready.add(nxt)

                    remaining_after = corridor_set - next_done
                    batch_score = self._corridor_batch_cost(
                        batch_state,
                        remaining_after,
                        state.ready,
                        previous_signature,
                        action_index,
                        action_rank,
                        cheap_local_overlap=cheap_local_overlap,
                    )
                    total_score = state.score + batch_score + self._corridor_remaining_lower_bound(
                        remaining_after,
                        action_index,
                        cloud_request_slots,
                    )
                    expanded.append(
                        (
                            total_score,
                            CorridorSearchState(
                                done=next_done,
                                indegree=next_indegree,
                                ready=next_ready,
                                scheduled_batches=state.scheduled_batches + [list(batch)],
                                score=state.score + batch_score,
                            ),
                        )
                    )

            if not expanded:
                return []
            expanded.sort(key=lambda item: (item[0], len(item[1].scheduled_batches), item[1].scheduled_batches))
            beam = [state for _, state in expanded[:beam_width]]

        best = min(
            beam,
            key=lambda state: (
                state.score + self._corridor_remaining_lower_bound(corridor_set - state.done, action_index, cloud_request_slots),
                len(state.scheduled_batches),
                state.scheduled_batches,
            ),
        )
        return list(best.scheduled_batches[0]) if best.scheduled_batches else []

    @staticmethod
    def _conservative_observable_grouping_enabled(optimization_target: OptimizationTarget | None) -> bool:
        validation = optimization_target.validation if optimization_target and isinstance(optimization_target.validation, dict) else {}
        differential = validation.get("differential_tests", {}) if isinstance(validation.get("differential_tests", {}), dict) else {}
        return bool(differential.get("enabled", False))

    @staticmethod
    def _conservative_ordered_groups(
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        observable_priority: Dict[str, int],
        action_rank: Dict[str, int],
    ) -> List[List[str]]:
        ordered = sorted(
            selected,
            key=lambda action_id: (
                int(action_rank.get(action_id, 10_000)),
                int(observable_priority.get(action_id, 20)),
                1 if CrossProtocolScheduler._action_is_writeback(action_index[action_id]) else 0,
                action_id,
            ),
        )
        return [[action_id] for action_id in ordered]

    @staticmethod
    def _shares_affinity_token(
        candidate: str,
        selected: List[str],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
    ) -> bool:
        candidate_tokens = set(affinity_tokens_by_action.get(candidate, []))
        if not candidate_tokens:
            return False
        for action_id in selected:
            if candidate_tokens & set(affinity_tokens_by_action.get(action_id, [])):
                return True
        return False

    @classmethod
    def _conservative_ble_api_frontier_compatible(
        cls,
        candidate: str,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        soft_order_pairs: Set[Tuple[str, str]],
        ready: Set[str],
        action_rank: Dict[str, int],
        action_phase_by_action: Dict[str, str],
    ) -> bool:
        prospective = list(selected) + [candidate]
        protocols = [cls._action_protocol(action_index[action_id]) for action_id in prospective]
        if "BLE" not in protocols:
            return False
        if protocols.count("BLE") != 1:
            return False
        if any(protocol not in {"BLE", "CLOUD", "LOCAL"} for protocol in protocols):
            return False

        ble_action_id = prospective[protocols.index("BLE")]
        if not cls._ble_frontier_anchor_eligible(ble_action_id, action_index, action_phase_by_action):
            return False

        for action_id in prospective:
            if action_id == ble_action_id:
                continue
            if not cls._api_frontier_action_eligible(action_id, action_index, action_phase_by_action):
                return False
            if (action_id, ble_action_id) in soft_order_pairs or (ble_action_id, action_id) in soft_order_pairs:
                return False

        for left in selected:
            if (left, candidate) in soft_order_pairs or (candidate, left) in soft_order_pairs:
                return False

        ble_tokens = set(affinity_tokens_by_action.get(ble_action_id, []))
        if ble_tokens:
            for action_id in prospective:
                if action_id != ble_action_id and ble_tokens & set(affinity_tokens_by_action.get(action_id, [])):
                    return False


        for protocol in ("CLOUD", "LOCAL"):
            selected_protocol = [
                action_id for action_id in prospective if cls._action_protocol(action_index[action_id]) == protocol
            ]
            if not selected_protocol:
                continue
            latest_rank = max(int(action_rank.get(action_id, 10_000)) for action_id in selected_protocol)
            for action_id in ready:
                if action_id in prospective:
                    continue
                action = action_index[action_id]
                if cls._action_protocol(action) != protocol:
                    continue
                if not cls._api_frontier_action_eligible(action_id, action_index, action_phase_by_action):
                    continue
                if int(action_rank.get(action_id, 10_000)) < latest_rank:
                    return False

        return True

    @classmethod
    def _conservative_batch_compatible(
        cls,
        candidate: str,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]],
        soft_order_pairs: Set[Tuple[str, str]],
        ready: Set[str],
        action_rank: Dict[str, int],
        action_phase_by_action: Dict[str, str],
        *,
        allow_ble_api_frontier: bool = False,
    ) -> bool:
        if not selected:
            return True
        candidate_action = action_index[candidate]
        if cls._action_is_writeback(candidate_action) or any(
            cls._action_is_writeback(action_index[action_id]) for action_id in selected
        ):
            return cls._conservative_writeback_parallel_compatible(candidate, selected, action_index)

        candidate_protocol = cls._action_protocol(candidate_action)
        candidate_lane = cls._action_lane(candidate_action)
        if cls._conservative_cross_protocol_read_parallel_compatible(
            candidate,
            selected,
            action_index,
            affinity_tokens_by_action,
            soft_order_pairs,
            ready,
            action_rank,
            action_phase_by_action,
        ):
            return True
        if allow_ble_api_frontier and cls._conservative_ble_api_frontier_compatible(
            candidate,
            selected,
            action_index,
            affinity_tokens_by_action,
            soft_order_pairs,
            ready,
            action_rank,
            action_phase_by_action,
        ):
            return True
        if candidate_protocol == "LOCAL":
            return cls._conservative_local_parallel_compatible(candidate, selected, action_index)
        if candidate_protocol == "CLOUD" and cls._conservative_cloud_read_parallel_compatible(
            candidate,
            selected,
            action_index,
            soft_order_pairs,
            ready,
            action_rank,
            action_phase_by_action,
        ):
            return True
        if candidate_protocol not in {"BLE", "CLOUD"}:
            return False
        for action_id in selected:
            action = action_index[action_id]
            if cls._action_protocol(action) != candidate_protocol:
                return False
            if cls._action_lane(action) != candidate_lane:
                return False
        return cls._shares_affinity_token(candidate, selected, affinity_tokens_by_action)

    @staticmethod
    def _phase_barrier_blocks(
        candidate: str,
        selected: List[str],
        done: Set[str],
        action_phase_by_action: Dict[str, str],
    ) -> bool:
        candidate_phase = str(action_phase_by_action.get(candidate, "pre_control_acquisition"))
        if candidate_phase == "post_control_verification":
            return any(
                action_id != candidate
                and str(phase) == "control"
                and action_id not in done
                for action_id, phase in action_phase_by_action.items()
            )
        if candidate_phase == "control":
            return any(
                str(action_phase_by_action.get(action_id, "pre_control_acquisition")) == "post_control_verification"
                for action_id in selected
            )
        return False

    def _build_parallel_groups(
        self,
        selected: List[str],
        action_index: Dict[str, Dict[str, Any]],
        derived: DerivedConstraintPolicy,
        observable_priority: Dict[str, int] | None = None,
        action_rank: Dict[str, int] | None = None,
        optimization_target: OptimizationTarget | None = None,
    ) -> tuple[List[List[str]], List[Dict[str, Any]]]:
        if not selected:
            return [], []

        observable_priority = observable_priority or {}
        action_rank = action_rank or {}

        if self._conservative_observable_grouping_enabled(optimization_target):
            groups, bucket_rows = self._group_selected_actions(selected, action_index, derived)
            ordered = self._conservative_ordered_groups(selected, action_index, observable_priority, action_rank)
            ordered_index = {action_id: idx for idx, group in enumerate(ordered) for action_id in group}
            groups.sort(
                key=lambda group: min(ordered_index.get(action_id, 10_000) for action_id in group)
            )
            return groups, bucket_rows

        selected_set = set(selected)
        adjacency: Dict[str, Set[str]] = {action_id: set() for action_id in selected}
        indegree: Dict[str, int] = {action_id: 0 for action_id in selected}
        for src, dst in sorted(derived.soft_order_pairs):
            if src not in selected_set or dst not in selected_set or src == dst:
                continue
            if dst not in adjacency[src]:
                adjacency[src].add(dst)
                indegree[dst] += 1

        if not any(adjacency.values()):
            return self._group_selected_actions(selected, action_index, derived)

        groups: List[List[str]] = []
        bucket_rows: List[Dict[str, Any]] = []
        remaining: Set[str] = set(selected)

        while remaining:
            ready_layer = [action_id for action_id in selected if action_id in remaining and indegree.get(action_id, 0) == 0]
            if not ready_layer:
                ready_layer = [next(action_id for action_id in selected if action_id in remaining)]

            layer_groups, layer_bucket_rows = self._group_selected_actions(ready_layer, action_index, derived)
            groups.extend(layer_groups)
            bucket_rows.extend(layer_bucket_rows)

            for action_id in ready_layer:
                remaining.discard(action_id)
                for nxt in sorted(adjacency.get(action_id, set())):
                    indegree[nxt] = max(0, indegree.get(nxt, 0) - 1)

        return groups, bucket_rows

    @staticmethod
    def _pair_key_from_justification(values: Iterable[str]) -> str:
        for item in values:
            token = str(item)
            if token.startswith("pair_key:"):
                return token.split(":", 1)[1].strip()
        return ""

    def _edge_action_pairs(
        self,
        src_actions: Set[str],
        dst_actions: Set[str],
        justifications: List[str],
        action_index: Dict[str, Dict[str, Any]],
    ) -> Set[Tuple[str, str]]:
        valid_src = sorted(action_id for action_id in src_actions if action_id in action_index)
        valid_dst = sorted(action_id for action_id in dst_actions if action_id in action_index)
        if not valid_src or not valid_dst:
            return set()
        if len(valid_src) == 1 and len(valid_dst) == 1:
            return {(valid_src[0], valid_dst[0])}

        pair_key = self._pair_key_from_justification(justifications)
        if pair_key and pair_key != "nearest":
            scoped_pairs: Set[Tuple[str, str]] = set()
            src_by_scope: Dict[str, List[str]] = {}
            dst_by_scope: Dict[str, List[str]] = {}
            for action_id in valid_src:
                value = self._action_group_value(action_index[action_id], pair_key)
                if value:
                    src_by_scope.setdefault(value, []).append(action_id)
            for action_id in valid_dst:
                value = self._action_group_value(action_index[action_id], pair_key)
                if value:
                    dst_by_scope.setdefault(value, []).append(action_id)
            for scope_value in sorted(set(src_by_scope) & set(dst_by_scope)):
                left = sorted(src_by_scope[scope_value])
                right = sorted(dst_by_scope[scope_value])
                if len(left) == 1 and len(right) == 1:
                    scoped_pairs.add((left[0], right[0]))
                    continue
                overlap = min(len(left), len(right))
                for src, dst in zip(left[:overlap], right[:overlap]):
                    if src != dst:
                        scoped_pairs.add((src, dst))
                if left and right:
                    last_left = left[min(overlap - 1, len(left) - 1)]
                    last_right = right[min(overlap - 1, len(right) - 1)]
                    for src in left[overlap:]:
                        if src != last_right:
                            scoped_pairs.add((src, last_right))
                    for dst in right[overlap:]:
                        if last_left != dst:
                            scoped_pairs.add((last_left, dst))
            if scoped_pairs:
                return scoped_pairs

        return {
            (src, dst)
            for src in valid_src
            for dst in valid_dst
            if src != dst
        }

    @staticmethod
    def _reachable_without_edge(src: str, dst: str, out: Dict[str, Set[str]], skip: Tuple[str, str]) -> bool:
        stack = [node for node in sorted(out.get(src, set())) if (src, node) != skip]
        seen: Set[str] = set()
        while stack:
            node = stack.pop()
            if node == dst:
                return True
            if node in seen:
                continue
            seen.add(node)
            for nxt in sorted(out.get(node, set())):
                if (node, nxt) == skip:
                    continue
                stack.append(nxt)
        return False

    def _transitive_reduce(
        self,
        action_ids: List[str],
        out: Dict[str, Set[str]],
        indegree: Dict[str, int],
        edge_kinds: Dict[Tuple[str, str], Set[str]],
    ) -> List[Dict[str, Any]]:
        edge_count = sum(len(values) for values in out.values())
        if edge_count > 256:
            return [
                {
                    "kind": "transitive_reduction_skipped",
                    "reason": "edge_cap",
                    "edge_count": edge_count,
                    "edge_cap": 256,
                }
            ]

        removed: List[Dict[str, Any]] = []
        for src in sorted(action_ids):
            for dst in sorted(list(out.get(src, set()))):
                if dst not in out.get(src, set()):
                    continue
                if self._reachable_without_edge(src, dst, out, (src, dst)):
                    out[src].remove(dst)
                    indegree[dst] = max(0, indegree.get(dst, 0) - 1)
                    removed.append(
                        {
                            "kind": "transitive_reduction",
                            "removed_src_action": src,
                            "removed_dst_action": dst,
                            "removed_kinds": sorted(edge_kinds.pop((src, dst), set())),
                        }
                    )
        return removed

    def _batch_rule_stats(
        self,
        action_index: Dict[str, Dict[str, Any]],
        batch_rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        stats: List[Dict[str, Any]] = []
        for rule in batch_rules:
            scope = [str(action_id) for action_id in rule.get("scope", []) if str(action_id) in action_index]
            group_key = str(rule.get("group_key", "endpoint"))
            cloud_actions = [action_id for action_id in scope if self._action_protocol(action_index[action_id]) == "CLOUD"]
            bucket_hits = 0
            for action_id in cloud_actions:
                if self._batch_bucket_key(action_index[action_id], group_key):
                    bucket_hits += 1
            stats.append(
                {
                    "group_key": group_key,
                    "scope_size": len(scope),
                    "cloud_actions": len(cloud_actions),
                    "bucket_key_hits": bucket_hits,
                    "bucket_key_hit_rate": (bucket_hits / len(cloud_actions)) if cloud_actions else 0.0,
                    "max_batch_size": int(rule.get("max_batch_size", 1)),
                    "max_wait_ms": int(rule.get("max_wait_ms", 0)),
                }
            )
        return stats

    @staticmethod
    def _public_rule_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        public: List[Dict[str, Any]] = []
        for row in rows:
            public.append({key: value for key, value in row.items() if key != "scope_set"})
        return public

    @classmethod
    def _normalize_fallback_row(
        cls,
        row: Dict[str, Any],
        action_index: Dict[str, Dict[str, Any]],
        action_field: str,
    ) -> Dict[str, Any]:
        normalized = dict(row)
        normalized["scope"] = sorted({str(token) for token in row.get("scope", []) if str(token).strip()})
        params = dict(row.get("params", {})) if isinstance(row.get("params", {}), dict) else {}
        normalized["params"] = params

        if action_field not in normalized:
            return normalized

        reason = str(params.get("reason", "")).strip()
        kind = str(normalized.get("kind", "")).strip().upper()
        action_value = str(normalized.get(action_field, "")).strip()
        scope_lanes = {
            cls._action_lane(action_index[action_id])
            for action_id in normalized["scope"]
            if action_id in action_index
        }
        if (
            kind == SoftConstraintKind.SOFT_ORDER.value
            and action_value == "preserve_action_order"
            and reason.startswith("candidate:")
            and scope_lanes == {"CLOUD"}
        ):
            normalized[action_field] = "force_topological_local_order"

        return normalized

    @classmethod
    def _dedupe_fallback_rows(
        cls,
        items: List[Dict[str, Any]],
        action_index: Dict[str, Dict[str, Any]],
        action_field: str,
    ) -> List[Dict[str, Any]]:
        seen: Set[Tuple[Any, ...]] = set()
        out: List[Dict[str, Any]] = []
        for item in items:
            normalized = cls._normalize_fallback_row(item, action_index, action_field)
            params = dict(normalized.get("params", {})) if isinstance(normalized.get("params", {}), dict) else {}
            key = (
                str(normalized.get(action_field, "")).strip(),
                str(normalized.get("kind", "")).strip(),
                tuple(sorted(str(token) for token in normalized.get("scope", []) if str(token).strip())),
                tuple(sorted((str(name), cls._freeze_value(value)) for name, value in params.items())),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(normalized)
        return out

    @staticmethod
    def _index_rows_by_action(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        index: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            for action_id in row.get("scope", []):
                token = str(action_id).strip()
                if not token:
                    continue
                index.setdefault(token, []).append(row)
        return index

    @staticmethod
    def _freeze_value(value: Any) -> Any:
        if isinstance(value, dict):
            return tuple(sorted((str(key), CrossProtocolScheduler._freeze_value(val)) for key, val in value.items()))
        if isinstance(value, list):
            return tuple(CrossProtocolScheduler._freeze_value(item) for item in value)
        if isinstance(value, set):
            return tuple(sorted(CrossProtocolScheduler._freeze_value(item) for item in value))
        return value

    @staticmethod
    def _collect_rows_for_selected(
        selected: List[str],
        index_by_action: Dict[str, List[Dict[str, Any]]],
        dedupe_fields: Tuple[str, ...],
    ) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        seen: Set[Tuple[Any, ...]] = set()
        for action_id in selected:
            for row in index_by_action.get(action_id, []):
                key_items: List[Any] = []
                for field in dedupe_fields:
                    value = row.get(field)
                    key_items.append(CrossProtocolScheduler._freeze_value(value))
                key = tuple(key_items)
                if key in seen:
                    continue
                seen.add(key)
                collected.append(row)
        return collected

    @classmethod
    def compress_plan_for_trust(cls, plan: ExecutionPlan) -> ExecutionPlan:
        compressed_batches: List[Batch] = []
        compression_summary: Dict[str, Any] = {"merged_constraints": []}
        action_lanes = {
            str(action_id): str(lane)
            for action_id, lane in (plan.meta.get("action_lanes", {}) or {}).items()
            if str(action_id).strip()
        }

        def scope_family(scope: List[str]) -> str:
            lanes = {
                action_lanes.get(str(action_id).strip(), "UNKNOWN")
                for action_id in scope
                if str(action_id).strip()
            }
            lanes.discard("")
            if not lanes:
                return "UNKNOWN"
            if len(lanes) == 1:
                return next(iter(lanes))
            if all(str(item).startswith("WRITEBACK") for item in lanes):
                return "WRITEBACK"
            return "MIXED"

        for batch in plan.ordered_batches:
            unique_constraints = sorted({str(item) for item in batch.constraints if str(item).strip()})

            guard_groups: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
            for row in batch.guards:
                scope = sorted(str(token) for token in row.get("scope", []) if str(token))
                frozen = (
                    str(row.get("kind", "")),
                    str(row.get("expr", "true")),
                    bool(row.get("enforced", False)),
                    scope_family(scope),
                )
                existing = guard_groups.get(frozen)
                if existing is None:
                    guard_groups[frozen] = {
                        "kind": str(row.get("kind", "")),
                        "scope": scope,
                        "expr": str(row.get("expr", "true")),
                        "enforced": bool(row.get("enforced", False)),
                    }
                    continue
                existing["scope"] = sorted(set(existing["scope"]) | set(scope))
            compressed_guards = list(guard_groups.values())

            fallback_groups: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
            for row in batch.fallback:
                params = dict(row.get("params", {})) if isinstance(row.get("params", {}), dict) else {}
                scope = sorted(str(token) for token in row.get("scope", []) if str(token))
                frozen = (
                    str(row.get("kind", "")),
                    str(row.get("action", "")),
                    cls._freeze_value(params),
                    scope_family(scope),
                )
                existing = fallback_groups.get(frozen)
                if existing is None:
                    fallback_groups[frozen] = {
                        "kind": str(row.get("kind", "")),
                        "scope": scope,
                        "action": str(row.get("action", "")),
                        "params": params,
                    }
                    continue
                existing["scope"] = sorted(set(existing["scope"]) | set(scope))
            compressed_fallbacks = list(fallback_groups.values())

            policy_blocks: List[Dict[str, Any]] = []
            for family in sorted({scope_family(row.get("scope", [])) for row in compressed_guards + compressed_fallbacks}):
                if family in {"UNKNOWN", "MIXED"}:
                    continue
                scope = sorted(
                    {
                        str(token)
                        for row in compressed_guards + compressed_fallbacks
                        if scope_family(row.get("scope", [])) == family
                        for token in row.get("scope", [])
                        if str(token).strip()
                    }
                )
                if not scope:
                    continue
                policy_blocks.append(
                    {
                        "policy_block": f"{family.lower()}_policy",
                        "scope": scope,
                        "guard_kinds": sorted({str(row.get("kind", "")) for row in compressed_guards if scope_family(row.get("scope", [])) == family}),
                        "fallback_actions": sorted({str(row.get("action", "")) for row in compressed_fallbacks if scope_family(row.get("scope", [])) == family}),
                    }
                )

            original_total = len(batch.constraints) + len(batch.guards) + len(batch.fallback)
            compressed_total = len(unique_constraints) + len(compressed_guards) + len(compressed_fallbacks)
            if compressed_total < original_total:
                compression_summary["merged_constraints"].append(
                    {
                        "batch_id": batch.batch_id,
                        "original_constraint_count": original_total,
                        "compressed_constraint_count": compressed_total,
                    }
                )

            compressed_rate_policy = copy.deepcopy(batch.rate_policy)
            compressed_rate_policy["trust_policy_blocks"] = policy_blocks
            compressed_batches.append(
                Batch(
                    batch_id=batch.batch_id,
                    parallel_groups=[list(group) for group in batch.parallel_groups],
                    constraints=unique_constraints,
                    session_policy=copy.deepcopy(batch.session_policy),
                    rate_policy=compressed_rate_policy,
                    guards=compressed_guards,
                    fallback=compressed_fallbacks,
                )
            )

        action_to_mssus_meta = plan.meta.get("action_to_mssus", {}) or {}
        compressed_meta = {
            "policy": copy.deepcopy(plan.meta.get("policy", {})),
            "node_kind": str(plan.meta.get("node_kind", "action_id")),
            "profile_version": plan.meta.get("profile_version"),
            "canonicalization_version": plan.meta.get("canonicalization_version"),
            "action_lanes": copy.deepcopy(plan.meta.get("action_lanes", {})),
            "trust_compression": {
                "action_to_mssu_count": {
                    action_id: len(mssu_ids)
                    for action_id, mssu_ids in action_to_mssus_meta.items()
                },
                "policy_blocks": [
                    block
                    for batch in compressed_batches
                    for block in batch.rate_policy.get("trust_policy_blocks", [])
                    if isinstance(block, dict)
                ],
                **compression_summary,
            },
        }
        if "objectives" in plan.meta:
            compressed_meta["objectives"] = copy.deepcopy(plan.meta["objectives"])

        return ExecutionPlan(ordered_batches=compressed_batches, meta=compressed_meta)

    @staticmethod
    def _budget_conflict(
        candidate: str,
        budget_rule_ids_by_action: Dict[str, List[int]],
        budget_counts: Dict[int, int],
        budget_rules: List[Dict[str, Any]],
    ) -> bool:
        for rule_id in budget_rule_ids_by_action.get(candidate, []):
            rule = budget_rules[rule_id]
            limit = max(1, int(rule.get("limit", 1)))
            if budget_counts.get(rule_id, 0) >= limit:
                return True
        return False

    def _prepare_group_affinity(
        self,
        action_index: Dict[str, Dict[str, Any]],
        derived: DerivedConstraintPolicy,
    ) -> Dict[str, List[Tuple[int, str]]]:
        affinity_rules = derived.session_rules + derived.batch_rules
        affinity_tokens_by_action: Dict[str, List[Tuple[int, str]]] = {}

        for rule_idx, rule in enumerate(affinity_rules):
            scope_set = set(rule.get("scope_set", set()))
            if not scope_set:
                scope_set = {str(item) for item in rule.get("scope", []) if str(item)}
                rule["scope_set"] = scope_set
            group_key = str(rule.get("group_key", ""))
            is_batch_rule = rule in derived.batch_rules
            for action_id in sorted(scope_set):
                action = action_index.get(action_id)
                if action is None:
                    continue
                value = self._action_batch_group_value(action, group_key) if is_batch_rule else self._action_group_value(action, group_key)
                if not value:
                    continue
                affinity_tokens_by_action.setdefault(action_id, []).append((rule_idx, value))

        return affinity_tokens_by_action

    @staticmethod
    def _prepare_budget_index(
        budget_rules: List[Dict[str, Any]],
    ) -> Dict[str, List[int]]:
        by_action: Dict[str, List[int]] = {}
        for rule_idx, rule in enumerate(budget_rules):
            scope_set = set(rule.get("scope_set", set()))
            if not scope_set:
                scope_set = {str(item) for item in rule.get("scope", []) if str(item)}
                rule["scope_set"] = scope_set
            for action_id in sorted(scope_set):
                by_action.setdefault(action_id, []).append(rule_idx)
        return by_action

    @staticmethod
    def _prepare_overlap_index(no_overlap_scopes: List[Set[str]]) -> Dict[str, List[int]]:
        by_action: Dict[str, List[int]] = {}
        for scope_idx, scope in enumerate(no_overlap_scopes):
            for action_id in sorted(scope):
                by_action.setdefault(action_id, []).append(scope_idx)
        return by_action

    @staticmethod
    def _prepare_incident_kind_index(edge_kinds: Dict[Tuple[str, str], Set[str]]) -> Dict[str, Set[str]]:
        by_action: Dict[str, Set[str]] = {}
        for (src, dst), kinds in edge_kinds.items():
            by_action.setdefault(src, set()).update(kinds)
            by_action.setdefault(dst, set()).update(kinds)
        return by_action

    @staticmethod
    def _prepare_min_gap_index(min_gap_pairs: Dict[Tuple[str, str], int]) -> Dict[str, List[Tuple[str, int]]]:
        by_after: Dict[str, List[Tuple[str, int]]] = {}
        for (before, after), gap_ms in sorted(min_gap_pairs.items()):
            by_after.setdefault(after, []).append((before, int(gap_ms)))
        return by_after

    def _candidate_soft_blockers(
        self,
        candidate: str,
        selected: List[str],
        done: Set[str],
        budget_rule_ids_by_action: Dict[str, List[int]],
        budget_counts: Dict[int, int],
        budget_rules: List[Dict[str, Any]],
        no_overlap_scope_ids_by_action: Dict[str, List[int]],
        no_overlap_scopes: List[Set[str]],
        no_overlap_counts: Dict[int, int],
        min_gap_pairs: Dict[Tuple[str, str], int],
        soft_order_pairs: Set[Tuple[str, str]],
    ) -> List[Dict[str, Any]]:
        blockers: List[Dict[str, Any]] = []

        for rule_id in budget_rule_ids_by_action.get(candidate, []):
            rule = budget_rules[rule_id]
            limit = max(1, int(rule.get("limit", 1)))
            if budget_counts.get(rule_id, 0) < limit:
                continue
            blockers.append(
                {
                    "kind": SoftConstraintKind.BUDGET_K.value,
                    "scope": sorted(str(token) for token in rule.get("scope", []) if str(token)),
                    "params": {
                        "resource": str(rule.get("resource", "")),
                        "limit": limit,
                    },
                }
            )

        for scope_id in no_overlap_scope_ids_by_action.get(candidate, []):
            if no_overlap_counts.get(scope_id, 0) <= 0:
                continue
            blockers.append(
                {
                    "kind": SoftConstraintKind.NO_OVERLAP.value,
                    "scope": sorted(str(token) for token in no_overlap_scopes[scope_id]) if scope_id < len(no_overlap_scopes) else [],
                    "params": {"scope_id": scope_id},
                }
            )

        for src in selected:
            gap_ms = min_gap_pairs.get((src, candidate))
            if gap_ms is None:
                continue
            blockers.append(
                {
                    "kind": SoftConstraintKind.MIN_GAP.value,
                    "scope": [src, candidate],
                    "params": {"gap_ms": int(gap_ms)},
                }
            )

        for src, dst in sorted(soft_order_pairs):
            if dst != candidate or src in done or src in selected:
                continue
            blockers.append(
                {
                    "kind": SoftConstraintKind.SOFT_ORDER.value,
                    "scope": [src, candidate],
                    "params": {"waiting_for": src},
                }
            )

        return blockers

    @staticmethod
    def _forced_pick_penalty(blockers: List[Dict[str, Any]]) -> Tuple[int, int, Tuple[str, ...]]:
        safety_soft_kinds = {
            SoftConstraintKind.NO_OVERLAP.value,
            SoftConstraintKind.MIN_GAP.value,
        }
        weights = {
            SoftConstraintKind.SOFT_ORDER.value: 1,
            SoftConstraintKind.BUDGET_K.value: 2,
            SoftConstraintKind.NO_OVERLAP.value: 3,
            SoftConstraintKind.MIN_GAP.value: 4,
        }
        has_safety_soft = any(str(item.get("kind", "")) in safety_soft_kinds for item in blockers)
        total = sum(weights.get(str(item.get("kind", "")), 10) for item in blockers)
        kinds = tuple(sorted(str(item.get("kind", "")) for item in blockers))
        return int(has_safety_soft), total, len(blockers), kinds

    @staticmethod
    def _forced_pick_row(action_id: str, blockers: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "kind": "FORCED_PICK",
            "scope": [action_id],
            "action": "force_pick_despite_soft_conflicts",
            "params": {
                "picked": action_id,
                "blocked_by": blockers,
            },
        }

    def _project_soft_constraints(
        self,
        dag: TypedDAG,
        action_index: Dict[str, Dict[str, Any]],
        optimization_target: OptimizationTarget | None,
    ) -> List[Dict[str, Any]]:
        mssu_to_actions = self._mssu_to_actions(dag)
        projected: List[Dict[str, Any]] = []
        action_order = {action_id: idx for idx, action_id in enumerate(action_index.keys())}

        def ordered_scope(scope_actions: Set[str]) -> List[str]:
            return sorted(
                {str(action_id) for action_id in scope_actions if str(action_id)},
                key=lambda action_id: (int(action_order.get(action_id, 10_000)), action_id),
            )

        def maybe_rewrite_control_dep_writeback_scope(
            kind: str,
            scope: List[str],
            params: Dict[str, Any],
            guard: str,
            fallback: str,
        ) -> List[Dict[str, Any]] | None:
            if str(kind).strip().upper() != SoftConstraintKind.SOFT_ORDER.value:
                return None
            if str(params.get("reason", "")).strip() != "candidate:CONTROL_DEP":
                return None

            writebacks = [
                action_id
                for action_id in scope
                if action_id in action_index and self._action_lane(action_index[action_id]) == "WRITEBACK_LOCAL"
            ]
            if len(writebacks) != 1:
                return None

            non_writebacks = [action_id for action_id in scope if action_id not in writebacks and action_id in action_index]
            if len(non_writebacks) < 2:
                return None
            if any(self._action_protocol(action_index[action_id]) != "LOCAL" for action_id in non_writebacks):
                return None
            if any(not self._action_is_read_like(action_index[action_id]) for action_id in non_writebacks):
                return None

            writeback_id = writebacks[0]
            rewritten: List[Dict[str, Any]] = []
            for action_id in non_writebacks:
                rewritten.append(
                    {
                        "kind": kind,
                        "scope": [action_id, writeback_id],
                        "params": dict(params),
                        "guard": guard,
                        "fallback": fallback,
                    }
                )
            return rewritten

        for constraint in dag.soft_constraints:
            scope_actions: Set[str] = set()
            for node_id in constraint.scope:
                if node_id in action_index:
                    scope_actions.add(node_id)
                scope_actions |= mssu_to_actions.get(node_id, set())
            if not scope_actions:
                continue
            kind = str(constraint.kind or "").strip().upper()
            params = dict(constraint.params) if isinstance(constraint.params, dict) else {}
            scope = ordered_scope(scope_actions)
            if kind == SoftConstraintKind.MIN_GAP.value and str(params.get("reason", "")) == "shared_radio_or_transport_budget":
                scoped_actions = [action_index[action_id] for action_id in scope if action_id in action_index]
                if len(scoped_actions) >= 2 and not self._needs_ble_min_gap(scoped_actions[0], scoped_actions[1]):
                    continue

            rewritten = maybe_rewrite_control_dep_writeback_scope(
                kind,
                scope,
                params,
                constraint.guard,
                constraint.fallback,
            )
            if rewritten is not None:
                projected.extend(rewritten)
                continue

            projected.append(
                {
                    "kind": constraint.kind,
                    "scope": scope,
                    "params": params,
                    "guard": constraint.guard,
                    "fallback": constraint.fallback,
                }
            )

        if optimization_target is not None:
            for dep in optimization_target.soft_dependencies:
                before = str(dep.get("before", ""))
                after = str(dep.get("after", ""))
                if before in action_index and after in action_index:
                    reason = str(dep.get("reason", "vdev_soft_dependency"))
                    if (
                        reason == "shared_radio_or_transport_budget"
                        and not self._needs_ble_min_gap(action_index[before], action_index[after])
                    ):
                        continue
                    projected.append(
                        {
                            "kind": SoftConstraintKind.MIN_GAP.value,
                            "scope": [before, after],
                            "params": {"reason": reason},
                            "guard": "true",
                            "fallback": "preserve_action_order",
                        }
                    )

        return projected

    def schedule(
        self,
        dag: TypedDAG,
        runtime_metrics: Dict[str, Any] | None = None,
        optimization_target: OptimizationTarget | None = None,
    ) -> ExecutionPlan:
        policy = self._policy_from_target(self.policy, optimization_target)
        policy = self._policy_from_metrics(policy, runtime_metrics)
        runtime_metrics = runtime_metrics or {}

        action_index = self._action_index(optimization_target)
        if not action_index:
            return ExecutionPlan(
                ordered_batches=[],
                meta={
                    "policy": policy.__dict__,
                    "objectives": optimization_target.objectives if optimization_target else {},
                    "node_kind": "action_id",
                    "warning": "No actions available for scheduling",
                },
            )

        out, indegree, edge_kinds, action_to_mssus = self._project_hard_graph(dag, action_index, optimization_target)
        action_ids = list(action_index.keys())
        cycle_report = self._resolve_cycles(action_ids, out, indegree, edge_kinds)
        if cycle_report:
            raise ValueError(f"M5 scheduling blocked by hard-edge cycle: {cycle_report}")
        transitive_reduction = self._transitive_reduce(action_ids, out, indegree, edge_kinds)
        latency_weights = runtime_metrics.get("latency_ms", {})
        critical_score = self._critical_path_score(action_ids, out, dict(indegree), latency_weights)
        critical_boost = {action_id: (1 if bool(action_index[action_id].get("critical", False)) else 0) for action_id in action_ids}
        action_rank = {action_id: idx for idx, action_id in enumerate(action_ids)}
        action_phase_by_action = self._action_phase_map(action_index)
        baseline_trace_hints = self._baseline_trace_hints(optimization_target)
        action_lanes = {action_id: self._action_lane(action) for action_id, action in action_index.items()}
        fat_actions = {action_id for action_id in action_ids if self._is_fat_action(action_id, action_to_mssus)}
        observable_priority_map = {
            action_id: self._observable_anchor_priority(
                action_id,
                action_to_mssus,
                dag,
                baseline_trace_hints,
                action_index,
            )
            for action_id in action_ids
        }

        soft_constraints = self._project_soft_constraints(dag, action_index, optimization_target)
        derived = self._derive_policy_from_constraints(policy, soft_constraints, runtime_metrics, optimization_target)
        conservative_grouping = self._conservative_observable_grouping_enabled(optimization_target)
        if conservative_grouping:
            derived.batch_rules = [self._apply_execution_batch_cap(rule) for rule in derived.batch_rules]
            for row in derived.active_constraints:
                if str(row.get("kind", "")).strip().upper() == SoftConstraintKind.BATCH_GROUP.value:
                    params = dict(row.get("params", {})) if isinstance(row.get("params", {}), dict) else {}
                    row["params"] = self._apply_execution_batch_cap(params)
        derived.triggered_fallbacks = self._dedupe_fallback_rows(
            derived.triggered_fallbacks,
            action_index,
            "fallback",
        )
        enforced_constraints = [row for row in derived.active_constraints if bool(row.get("enforced", False))]
        active_constraints_by_action = self._index_rows_by_action(enforced_constraints)
        triggered_fallbacks_by_action = self._index_rows_by_action(derived.triggered_fallbacks)
        budget_rule_ids_by_action = self._prepare_budget_index(derived.budget_rules)
        no_overlap_scope_ids_by_action = self._prepare_overlap_index(derived.no_overlap_scopes)
        cloud_request_slots = self._prepare_cloud_request_slots(action_index, derived)
        affinity_tokens_by_action = self._prepare_group_affinity(action_index, derived)
        incident_kinds_by_action = self._prepare_incident_kind_index(edge_kinds)
        min_gap_by_after = self._prepare_min_gap_index(derived.min_gap_pairs)
        ready: Set[str] = {node for node, degree in indegree.items() if degree == 0}
        done: Set[str] = set()
        batches: List[Batch] = []
        batch_idx = 0
        optimizer_decisions: List[Dict[str, Any]] = []
        unknown_actions = sorted(
            action_id for action_id, action in action_index.items() if self._action_protocol(action) == "UNKNOWN"
        )

        while len(done) < len(action_ids):
            if not ready:
                unresolved = sorted(node for node in action_ids if node not in done)
                raise ValueError(
                    "M5 scheduling blocked by unresolved hard-edge cycle: "
                    + ",".join(unresolved)
                )

            selected: List[str] = []
            total_occupancy = 0
            ble_count = 0
            cloud_count = 0
            cloud_request_counts: Dict[str, int] = {}
            local_count = 0
            unknown_count = 0
            prior_done = set(done)
            budget_counts: Dict[int, int] = {}
            no_overlap_counts: Dict[int, int] = {}
            selected_group_counts: Dict[Tuple[int, str], int] = {}
            forced_pick_rows: List[Dict[str, Any]] = []

            optimizer_selected: List[str] = []
            optimizer_mode = ""
            optimizer_window: List[str] = []
            if conservative_grouping:
                corridor = self._extract_optimizable_corridor(
                    action_ids,
                    done,
                    action_index,
                    action_phase_by_action,
                )
                if corridor:
                    optimizer_mode = "corridor"
                    optimizer_window = list(corridor)
                    optimizer_selected = self._corridor_search_first_batch(
                        corridor,
                        ready,
                        done,
                        out,
                        indegree,
                        action_index,
                        action_to_mssus,
                        dag,
                        baseline_trace_hints,
                        derived,
                        critical_boost,
                        critical_score,
                        affinity_tokens_by_action,
                        action_rank,
                        action_phase_by_action,
                        cloud_request_slots,
                        budget_rule_ids_by_action,
                        no_overlap_scope_ids_by_action,
                        fat_actions,
                        conservative_grouping,
                    )
                if not optimizer_selected:
                    frontier_window = self._extract_frontier_window(
                        action_ids,
                        ready,
                        done,
                        action_index,
                        action_phase_by_action,
                    )
                    if frontier_window:
                        optimizer_mode = "frontier_window"
                        optimizer_window = list(frontier_window)
                        optimizer_selected = self._corridor_search_first_batch(
                            frontier_window,
                            ready,
                            done,
                            out,
                            indegree,
                            action_index,
                            action_to_mssus,
                            dag,
                            baseline_trace_hints,
                            derived,
                            critical_boost,
                            critical_score,
                            affinity_tokens_by_action,
                            action_rank,
                            action_phase_by_action,
                            cloud_request_slots,
                            budget_rule_ids_by_action,
                            no_overlap_scope_ids_by_action,
                            fat_actions,
                            conservative_grouping,
                            beam_width=8,
                            lookahead_depth=4,
                            cheap_local_overlap=True,
                        )
                if not optimizer_selected:
                    ble_api_window = self._extract_ble_api_frontier_window(
                        action_ids,
                        ready,
                        done,
                        action_index,
                        action_phase_by_action,
                    )
                    if ble_api_window:
                        optimizer_mode = "ble_api_frontier"
                        optimizer_window = list(ble_api_window)
                        optimizer_selected = self._corridor_search_first_batch(
                            ble_api_window,
                            ready,
                            done,
                            out,
                            indegree,
                            action_index,
                            action_to_mssus,
                            dag,
                            baseline_trace_hints,
                            derived,
                            critical_boost,
                            critical_score,
                            affinity_tokens_by_action,
                            action_rank,
                            action_phase_by_action,
                            cloud_request_slots,
                            budget_rule_ids_by_action,
                            no_overlap_scope_ids_by_action,
                            fat_actions,
                            conservative_grouping,
                            beam_width=8,
                            lookahead_depth=4,
                            cheap_local_overlap=True,
                            required_first_batch_actions={ble_api_window[0]},
                            min_first_batch_size=2,
                            allow_ble_api_frontier=True,
                        )
                if optimizer_selected:
                    optimized_state = self._build_batch_from_order(
                        optimizer_selected,
                        False,
                        ready,
                        done,
                        action_index,
                        derived,
                        conservative_grouping,
                        affinity_tokens_by_action,
                        action_rank,
                        action_phase_by_action,
                        cloud_request_slots,
                        budget_rule_ids_by_action,
                        no_overlap_scope_ids_by_action,
                        fat_actions,
                        allow_ble_api_frontier=optimizer_mode == "ble_api_frontier",
                    )
                    selected = list(optimized_state.selected)
                    total_occupancy = optimized_state.total_occupancy
                    ble_count = optimized_state.ble_count
                    cloud_count = optimized_state.cloud_count
                    cloud_request_counts = dict(optimized_state.cloud_request_counts)
                    local_count = optimized_state.local_count
                    unknown_count = optimized_state.unknown_count
                    budget_counts = dict(optimized_state.budget_counts)
                    no_overlap_counts = dict(optimized_state.no_overlap_counts)
                    selected_group_counts = dict(optimized_state.selected_group_counts)
                    optimizer_decisions.append(
                        {
                            "batch_index": batch_idx,
                            "mode": optimizer_mode,
                            "window": optimizer_window,
                            "selected": list(selected),
                        }
                    )

            if not selected:
                while True:
                    if unknown_count >= derived.unknown_limit and selected:
                        break
                    if selected and any(action_id in fat_actions for action_id in selected):
                        break
                    remaining = [node for node in ready if node not in selected]
                    if not remaining:
                        break
                    candidates = sorted(
                        remaining,
                        key=lambda node: self._candidate_sort_key(
                            node,
                            selected,
                            done,
                            conservative_grouping,
                            action_to_mssus,
                            dag,
                            baseline_trace_hints,
                            action_index,
                            derived,
                            critical_boost,
                            critical_score,
                            affinity_tokens_by_action,
                            selected_group_counts,
                            action_rank,
                        ),
                    )

                    picked = None
                    for action_id in candidates:
                        build_state = BatchBuildState(
                            selected=list(selected),
                            total_occupancy=total_occupancy,
                            ble_count=ble_count,
                            cloud_count=cloud_count,
                            cloud_request_counts=dict(cloud_request_counts),
                            local_count=local_count,
                            unknown_count=unknown_count,
                            budget_counts=dict(budget_counts),
                            no_overlap_counts=dict(no_overlap_counts),
                            selected_group_counts=dict(selected_group_counts),
                        )
                        if self._candidate_allowed_in_batch(
                            action_id,
                            build_state,
                            ready,
                            done,
                            action_index,
                            derived,
                            conservative_grouping,
                            affinity_tokens_by_action,
                            action_rank,
                            action_phase_by_action,
                            cloud_request_slots,
                            budget_rule_ids_by_action,
                            no_overlap_scope_ids_by_action,
                            fat_actions,
                        ):
                            picked = action_id
                            break

                    if picked is None:
                        break
                    picked_state = BatchBuildState(
                        selected=list(selected),
                        total_occupancy=total_occupancy,
                        ble_count=ble_count,
                        cloud_count=cloud_count,
                        cloud_request_counts=dict(cloud_request_counts),
                        local_count=local_count,
                        unknown_count=unknown_count,
                        budget_counts=dict(budget_counts),
                        no_overlap_counts=dict(no_overlap_counts),
                        selected_group_counts=dict(selected_group_counts),
                    )
                    self._apply_pick_to_batch_state(
                        picked,
                        picked_state,
                        action_index,
                        budget_rule_ids_by_action,
                        no_overlap_scope_ids_by_action,
                        affinity_tokens_by_action,
                        cloud_request_slots,
                        derived,
                        action_phase_by_action,
                    )
                    selected = list(picked_state.selected)
                    total_occupancy = picked_state.total_occupancy
                    ble_count = picked_state.ble_count
                    cloud_count = picked_state.cloud_count
                    cloud_request_counts = dict(picked_state.cloud_request_counts)
                    local_count = picked_state.local_count
                    unknown_count = picked_state.unknown_count
                    budget_counts = dict(picked_state.budget_counts)
                    no_overlap_counts = dict(picked_state.no_overlap_counts)
                    selected_group_counts = dict(picked_state.selected_group_counts)

            if not selected:
                fallback_options: List[Tuple[Tuple[int, int, int, Tuple[str, ...]], int, float, str, List[Dict[str, Any]]]] = []
                for action_id in sorted(ready):
                    blockers = self._candidate_soft_blockers(
                        action_id,
                        selected,
                        done,
                        budget_rule_ids_by_action,
                        budget_counts,
                        derived.budget_rules,
                        no_overlap_scope_ids_by_action,
                        derived.no_overlap_scopes,
                        no_overlap_counts,
                        derived.min_gap_pairs,
                        derived.soft_order_pairs,
                    )
                    fallback_options.append(
                        (
                            self._forced_pick_penalty(blockers),
                            -critical_boost.get(action_id, 0),
                            -critical_score.get(action_id, 0.0),
                            action_id,
                            blockers,
                        )
                    )
                _, _, _, fallback_pick, fallback_blockers = sorted(fallback_options)[0]
                selected.append(fallback_pick)
                forced_pick_rows.append(self._forced_pick_row(fallback_pick, fallback_blockers))

            for action_id in selected:
                ready.discard(action_id)
                done.add(action_id)
                for nxt in out.get(action_id, set()):
                    indegree[nxt] -= 1
                    if indegree[nxt] == 0:
                        ready.add(nxt)

            selected_set = set(selected)
            batch_constraint_kinds: Set[str] = set()
            for action_id in selected:
                batch_constraint_kinds |= incident_kinds_by_action.get(action_id, set())

            active_soft = self._collect_rows_for_selected(
                selected,
                active_constraints_by_action,
                ("kind", "scope", "guard"),
            )
            guard_rows: List[Dict[str, Any]] = []
            seen_guards: Set[Tuple[str, Tuple[str, ...], str, bool]] = set()
            for item in active_soft:
                row = {
                    "kind": str(item.get("kind", "")),
                    "scope": sorted(str(token) for token in item.get("scope", []) if str(token)),
                    "expr": str(item.get("guard", "true")),
                    "enforced": True,
                }
                key = (row["kind"], tuple(row["scope"]), row["expr"], row["enforced"])
                if key not in seen_guards:
                    seen_guards.add(key)
                    guard_rows.append(row)

            fallback_rows: List[Dict[str, Any]] = []
            seen_fallbacks: Set[Tuple[str, Tuple[str, ...], str, Tuple[Tuple[str, Any], ...]]] = set()
            for item in self._collect_rows_for_selected(
                selected,
                triggered_fallbacks_by_action,
                ("kind", "scope", "fallback", "params"),
            ):
                overlap = sorted(str(token) for token in item.get("scope", []) if str(token) in selected_set)
                params = dict(item.get("params", {})) if isinstance(item.get("params", {}), dict) else {}
                row = {
                    "kind": str(item.get("kind", "")),
                    "scope": overlap,
                    "action": str(item.get("fallback", "fallback_to_sequential")),
                    "params": params,
                }
                key = (
                    row["kind"],
                    tuple(row["scope"]),
                    row["action"],
                    self._freeze_value(params),
                )
                if key not in seen_fallbacks:
                    seen_fallbacks.add(key)
                    fallback_rows.append(row)

            for row in forced_pick_rows:
                params = dict(row.get("params", {})) if isinstance(row.get("params", {}), dict) else {}
                key = (
                    row["kind"],
                    tuple(row["scope"]),
                    row["action"],
                    self._freeze_value(params),
                )
                if key not in seen_fallbacks:
                    seen_fallbacks.add(key)
                    fallback_rows.append(row)

            fallback_rows = self._dedupe_fallback_rows(fallback_rows, action_index, "action")

            parallel_groups, batching_buckets = self._build_parallel_groups(
                selected,
                action_index,
                derived,
                observable_priority=observable_priority_map,
                action_rank=action_rank,
                optimization_target=optimization_target,
            )
            min_gap_rules: List[Dict[str, Any]] = []
            for after in selected:
                for before, gap_ms in min_gap_by_after.get(after, []):
                    if before not in prior_done:
                        continue
                    min_gap_rules.append(
                        {
                            "before": before,
                            "after": str(after),
                            "gap_ms": gap_ms,
                        }
                    )
            min_gap_before_ms = max((row["gap_ms"] for row in min_gap_rules), default=0)
            forced_pick_blocked_kinds = sorted(
                {
                    str(item.get("kind", ""))
                    for row in forced_pick_rows
                    for item in row.get("params", {}).get("blocked_by", [])
                    if str(item.get("kind", ""))
                }
            )
            forced_pick_targets = [str(row.get("params", {}).get("picked", "")) for row in forced_pick_rows if str(row.get("params", {}).get("picked", ""))]
            if forced_pick_rows:
                batch_constraint_kinds.add("FORCED_PICK")

            batch = Batch(
                batch_id=f"batch_{batch_idx:03d}",
                parallel_groups=parallel_groups,
                constraints=sorted(batch_constraint_kinds),
                session_policy={
                    "reuse": derived.reuse_enabled,
                    "max_age_s": max(1, int(derived.reuse_window_ms / 1000)),
                    "session_groups": [
                        {"group_key": str(rule.get("group_key", "")), "scope": list(rule.get("scope", []))}
                        for rule in derived.session_rules
                    ],
                },
                rate_policy={
                    "max_qps": derived.max_qps,
                    "burst": derived.rate_limit_burst,
                    "window_ms": derived.rate_limit_window_ms,
                    "batch_size": len(selected),
                    "batch_rules": self._public_rule_rows(derived.batch_rules),
                    "batching_buckets": batching_buckets,
                    "min_gap_before_ms": min_gap_before_ms,
                    "min_gap_rules": min_gap_rules,
                    "forced_pick": bool(forced_pick_rows),
                    "forced_pick_target": forced_pick_targets,
                    "forced_pick_blocked_kinds": forced_pick_blocked_kinds,
                    "adaptive_controls": list(fallback_rows),
                },
                guards=guard_rows,
                fallback=fallback_rows,
            )
            batches.append(batch)
            batch_idx += 1

        soft_summary: Dict[str, List[Dict[str, Any]]] = {}
        for item in soft_constraints:
            if item["kind"] in {
                SoftConstraintKind.BACKOFF_WINDOW.value,
                SoftConstraintKind.BUDGET_K.value,
                SoftConstraintKind.NO_OVERLAP.value,
                SoftConstraintKind.MIN_GAP.value,
                SoftConstraintKind.SOFT_ORDER.value,
                SoftConstraintKind.SAME_SESSION_GROUP.value,
                SoftConstraintKind.BATCH_GROUP.value,
                SoftConstraintKind.RATE_LIMIT.value,
            }:
                soft_summary.setdefault(item["kind"], []).append(item["params"])

        validation = optimization_target.validation if optimization_target and isinstance(optimization_target.validation, dict) else {}
        observation_cfg = validation.get("observation", {}) if isinstance(validation.get("observation", {}), dict) else {}
        profile_version = (
            validation.get("profile_version")
            or validation.get("ha_profile_version")
            or validation.get("ha_profile")
            or ""
        )
        canonicalization_version = observation_cfg.get("canonicalization_version") or validation.get(
            "canonicalization_version", ""
        )

        return ExecutionPlan(
            ordered_batches=batches,
            meta={
                "policy": policy.__dict__,
                "critical_score": critical_score,
                "critical_boost": critical_boost,
                "soft_summary": soft_summary,
                "objectives": optimization_target.objectives if optimization_target else {},
                "node_kind": "action_id",
                "action_to_mssus": {action_id: sorted(mssu_ids) for action_id, mssu_ids in action_to_mssus.items()},
                "action_lanes": action_lanes,
                "observable_anchor_priority": {
                    action_id: observable_priority_map[action_id]
                    for action_id in action_ids
                },
                "action_phase": {
                    action_id: action_phase_by_action.get(action_id, "")
                    for action_id in action_ids
                },
                "fat_actions": sorted(fat_actions),
                "cycle_resolution": [],
                "cycle_report": [],
                "transitive_reduction": transitive_reduction,
                "unknown_protocol_actions": unknown_actions,
                "optimizer_decisions": optimizer_decisions,
                "derived_policy": {
                    "total_limit": derived.total_limit,
                    "ble_limit": derived.ble_limit,
                    "cloud_limit": derived.cloud_limit,
                    "local_limit": derived.local_limit,
                    "unknown_limit": derived.unknown_limit,
                    "budget_rules": self._public_rule_rows(derived.budget_rules),
                    "max_qps": derived.max_qps,
                    "rate_limit_burst": derived.rate_limit_burst,
                    "rate_limit_window_ms": derived.rate_limit_window_ms,
                    "reuse_enabled": derived.reuse_enabled,
                    "reuse_window_ms": derived.reuse_window_ms,
                    "latency_budget_ms": derived.latency_budget_ms,
                    "triggered_fallbacks": derived.triggered_fallbacks,
                },
                "policy_snapshot": {
                    "schema_version": "m5_policy_snapshot/v1",
                    "budgets": {
                        "total": derived.total_limit,
                        "ble": derived.ble_limit,
                        "cloud": derived.cloud_limit,
                        "local": derived.local_limit,
                        "unknown": derived.unknown_limit,
                    },
                    "budget_rules": self._public_rule_rows(derived.budget_rules),
                    "rate_limit": {
                        "max_qps": derived.max_qps,
                        "burst": derived.rate_limit_burst,
                        "window_ms": derived.rate_limit_window_ms,
                    },
                    "batch_policy": {
                        "latency_budget_ms": derived.latency_budget_ms,
                        "rules": self._public_rule_rows(derived.batch_rules),
                        "bucket_key_stats": self._batch_rule_stats(action_index, derived.batch_rules),
                    },
                    "reuse_policy": {
                        "enabled": derived.reuse_enabled,
                        "reuse_window_ms": derived.reuse_window_ms,
                        "session_rules": derived.session_rules,
                    },
                    "adaptive_controls": {
                        "active_constraints": derived.active_constraints,
                        "triggered_fallbacks": derived.triggered_fallbacks,
                    },
                    "versions": {
                        "profile_version": str(profile_version),
                        "canonicalization_version": str(canonicalization_version),
                    },
                },
            },
        )


MacroLevelScheduler = CrossProtocolScheduler
