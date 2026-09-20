from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re
from typing import Dict, List, Set, Tuple

from dsl.contracts import GraphEdge, HAPProfile, MSSU, Marker, MarkerStrength, OptimizationTarget, Phase, ReducedGraph


MARKER_TO_MSSU_TYPE = {
    "ENTRY_SETUP": "INIT",
    "ENTRY_UNLOAD": "CLEANUP",
    "ENTRY_REMOVE": "CLEANUP",
    "COORD_REFRESH": "SYNC",
    "COORD_FIRST_REFRESH": "SYNC",
    "STATE_WRITE": "UPDATE",
    "SUBSCRIBE": "PREPARE",
    "UNSUBSCRIBE": "CLEANUP",
    "BLE_OP": "ACT",
    "CLOUD_OP": "ACT",
    "BLE_CONNECT": "PREPARE",
    "BLE_DISCONNECT": "CLEANUP",
    "BLE_GATT_OP": "ACT",
    "BLE_SCAN": "PREPARE",
    "BLE_RETRY_OR_TIMEOUT": "FALLBACK",
    "CLOUD_TOKEN_REFRESH": "PREPARE",
    "CLOUD_HTTP_CALL": "ACT",
    "CLOUD_429_CHECK": "CHECK",
    "CLOUD_BACKOFF_SLEEP": "FALLBACK",
    "CLOUD_RETRY_OR_TIMEOUT": "FALLBACK",
    "RETRY_OR_TIMEOUT": "FALLBACK",
}


@dataclass
class MSSUBuildResult:
    mssus: List[MSSU]
    mssu_internal_edges: Dict[str, List[GraphEdge]]
    dependency_candidates: List[Tuple[str, str, str]]
    build_status: str = "OK"
    summary: Dict[str, object] | None = None


class MSSUBuilder:
    _MERGEABLE_EFFECT_FAMILIES: Set[str] = {
        "ble_op",
        "cloud_http_call",
        "state_write",
    }

    def __init__(self, profile: HAPProfile, closure_depth: int = 2, max_nodes_per_mssu: int = 48) -> None:
        self.profile = profile
        self.closure_depth = closure_depth
        self.max_nodes_per_mssu = max(8, int(max_nodes_per_mssu))

    @staticmethod
    def _overlap_borrow_depth(marker: Marker) -> int:
        marker_type = str(marker.marker_type).strip().upper()
        if marker_type in {"UNSUBSCRIBE", "ENTRY_UNLOAD", "ENTRY_REMOVE", "BLE_DISCONNECT", "DISCONNECT"}:
            return 2
        mssu_phase = str(marker.phase).strip().upper()
        if mssu_phase == Phase.TEARDOWN.value:
            return 2
        return 1

    @staticmethod
    def _closure_depth_for_marker(marker: Marker, default_depth: int) -> int:
        marker_type = str(marker.marker_type).strip().upper()
        depth = max(1, int(default_depth))
        if marker_type in {"CLOUD_HTTP_CALL", "CLOUD_OP", "STATE_WRITE"}:
            return 1
        if marker_type in {"BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT"}:
            return min(depth, 2)
        if marker_type in {"ENTRY_SETUP", "ENTRY_UNLOAD", "ENTRY_REMOVE"}:
            return min(depth, 2)
        return depth

    @staticmethod
    def _closure_edge_types(marker: Marker) -> tuple[Set[str], Set[str]]:
        marker_type = str(marker.marker_type).strip().upper()
        if marker_type in {"CLOUD_HTTP_CALL", "CLOUD_OP"}:
            return {"DATA_DEP", "EXCEPTION_DEP"}, {"EXCEPTION_DEP"}
        if marker_type == "STATE_WRITE":
            return {"DATA_DEP", "EXCEPTION_DEP"}, {"EXCEPTION_DEP"}
        return (
            {"DATA_DEP", "CONTROL_DEP", "LIFECYCLE_DEP", "EXCEPTION_DEP"},
            {"LIFECYCLE_DEP", "EXCEPTION_DEP"},
        )

    @staticmethod
    def _max_nodes_for_marker(marker: Marker, default_cap: int) -> int:
        marker_type = str(marker.marker_type).strip().upper()
        default_cap = max(8, int(default_cap))
        if marker_type in {"CLOUD_HTTP_CALL", "CLOUD_OP"}:
            return min(default_cap, 12)
        if marker_type == "STATE_WRITE":
            return min(default_cap, 8)
        if marker_type == "BLE_GATT_OP":
            return min(default_cap, 16)
        if marker_type in {"ENTRY_SETUP", "ENTRY_UNLOAD", "ENTRY_REMOVE"}:
            return min(default_cap, 24)
        return default_cap

    @staticmethod
    def _mssu_type_for_marker(marker_type: str) -> str:
        marker = str(marker_type).strip().upper()
        if marker in MARKER_TO_MSSU_TYPE:
            return MARKER_TO_MSSU_TYPE[marker]
        if marker.startswith("BLE_"):
            return "ACT"
        if marker.startswith("CLOUD_"):
            return "ACT"
        return "ACT"

    def _build_adj(self, graph: ReducedGraph) -> tuple[Dict[str, List[GraphEdge]], Dict[str, List[GraphEdge]]]:
        forward: Dict[str, List[GraphEdge]] = {}
        backward: Dict[str, List[GraphEdge]] = {}
        for edge in graph.edges:
            forward.setdefault(edge.src, []).append(edge)
            backward.setdefault(edge.dst, []).append(edge)
        return forward, backward

    @staticmethod
    def _edge_index_by_node(graph: ReducedGraph) -> Dict[str, List[GraphEdge]]:
        by_node: Dict[str, List[GraphEdge]] = {}
        for edge in graph.edges:
            by_node.setdefault(edge.src, []).append(edge)
            by_node.setdefault(edge.dst, []).append(edge)
        return by_node

    def _seed_nodes(self, markers: List[Marker], marker_to_nodes: Dict[str, List[str]]) -> List[Tuple[Marker, Set[str]]]:
        seeds: List[Tuple[Marker, Set[str]]] = []
        for marker in markers:
            if marker.strength not in {MarkerStrength.STRONG.value, MarkerStrength.MEDIUM.value}:
                continue
            node_ids = set(marker_to_nodes.get(marker.marker_id, []))
            if not node_ids:
                continue
            seeds.append((marker, node_ids))
        seeds.sort(
            key=lambda item: (
                0 if "target_anchor_seed" in item[0].evidence or "target_anchor_op" in item[0].evidence else 1,
                0 if item[0].strength == MarkerStrength.STRONG.value else 1,
                item[0].line_start,
                item[0].marker_type,
            )
        )
        return seeds

    def _expand_closure(
        self,
        marker: Marker,
        seed_nodes: Set[str],
        backward: Dict[str, List[GraphEdge]],
        forward: Dict[str, List[GraphEdge]],
    ) -> Set[str]:

        depth_limit = self._closure_depth_for_marker(marker, self.closure_depth)
        if marker.strength == MarkerStrength.MEDIUM.value:
            depth_limit = max(1, depth_limit - 1)

        backward_edge_types, forward_edge_types = self._closure_edge_types(marker)

        keep = set(seed_nodes)
        frontier = set(seed_nodes)
        depth = 0
        max_expansion = self._max_nodes_for_marker(marker, self.max_nodes_per_mssu) * 2
        while frontier and depth < depth_limit and len(keep) < max_expansion:
            next_frontier: Set[str] = set()
            for node_id in frontier:
                for edge in backward.get(node_id, []):
                    if edge.edge_type in backward_edge_types and edge.src not in keep:
                        keep.add(edge.src)
                        next_frontier.add(edge.src)
                for edge in forward.get(node_id, []):
                    if edge.edge_type in forward_edge_types and edge.dst not in keep:
                        keep.add(edge.dst)
                        next_frontier.add(edge.dst)
            frontier = next_frontier
            depth += 1
        return keep

    @staticmethod
    def _claim_nodes(
        closed_nodes: Set[str],
        seed_nodes: Set[str],
        assigned_nodes: Set[str],
    ) -> Set[str]:

        return {node_id for node_id in closed_nodes if node_id not in assigned_nodes or node_id in seed_nodes}

    @staticmethod
    def _borrow_overlap_context(
        marker: Marker,
        closed_nodes: Set[str],
        overlap_seed_nodes: Set[str],
        backward: Dict[str, List[GraphEdge]],
        assigned_nodes: Set[str],
    ) -> Set[str]:
        if not overlap_seed_nodes:
            return closed_nodes
        marker_type = str(marker.marker_type).strip().upper()
        if marker_type in {"CLOUD_HTTP_CALL", "CLOUD_OP", "STATE_WRITE"}:
            return closed_nodes
        borrowed = set(closed_nodes)
        frontier = set(overlap_seed_nodes)
        depth = 0
        depth_limit = MSSUBuilder._overlap_borrow_depth(marker)
        allowed_edge_types = {"DATA_DEP", "EXCEPTION_DEP"}
        seen = set(overlap_seed_nodes)
        while frontier and depth < depth_limit:
            next_frontier: Set[str] = set()
            for node_id in frontier:
                for edge in backward.get(node_id, []):
                    if edge.edge_type not in allowed_edge_types:
                        continue
                    if edge.src in assigned_nodes or edge.src in seen:
                        continue
                    borrowed.add(edge.src)
                    seen.add(edge.src)
                    next_frontier.add(edge.src)
            frontier = next_frontier
            depth += 1
        return borrowed

    @classmethod
    def _filter_action_local_nodes(
        cls,
        marker: Marker,
        node_ids: Set[str],
        seed_nodes: Set[str],
        graph: ReducedGraph,
        markers_by_id: Dict[str, Marker],
        target: OptimizationTarget | None,
    ) -> Set[str]:
        seed_action = str(getattr(marker, "primary_action_id", "")).strip()
        if not seed_action or cls._marker_is_shared_infra(marker):
            return node_ids

        action_index = cls._action_index(target)
        action_row = action_index.get(seed_action, {})
        protocol = str(action_row.get("protocol", "")).strip().upper()
        scope_tokens = cls._action_scope_tokens(action_row)

        filtered: Set[str] = set()
        for node_id in node_ids:
            if node_id in seed_nodes:
                filtered.add(node_id)
                continue
            node = graph.nodes.get(node_id)
            if node is None or not node.marker_refs:
                filtered.add(node_id)
                continue
            conflicting = False
            for marker_id in node.marker_refs:
                neighbor = markers_by_id.get(str(marker_id))
                if neighbor is None:
                    continue
                neighbor_primary = str(getattr(neighbor, "primary_action_id", "")).strip()
                if not neighbor_primary:
                    continue
                if neighbor_primary == seed_action:
                    continue
                if cls._marker_is_shared_infra(neighbor):
                    continue
                conflicting = True
                break
            if conflicting:
                continue
            if protocol in {"CLOUD", "HA"} and scope_tokens:
                if node.marker_refs:
                    filtered.add(node_id)
                    continue
                node_tokens = cls._node_scope_tokens(node)
                if not node_tokens.intersection(scope_tokens):
                    continue
            filtered.add(node_id)
        return filtered

    @staticmethod
    def _action_scope_tokens(action: Dict[str, object] | None) -> Set[str]:
        if not isinstance(action, dict):
            return set()
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        raw_values = [
            action.get("action_id", ""),
            target.get("id", ""),
            target.get("entity_id", ""),
            target.get("device_id", ""),
            target.get("endpoint", ""),
            exec_cfg.get("domain", ""),
            exec_cfg.get("service", ""),
        ]
        generic = {"sensor", "light", "switch", "cloud", "status", "device", "entity"}
        tokens: Set[str] = set()
        for raw in raw_values:
            for token in re.split(r"[^a-zA-Z0-9_]+", str(raw).lower()):
                if len(token) >= 4 and token not in generic:
                    tokens.add(token)
        return tokens

    @staticmethod
    def _node_scope_tokens(node: object) -> Set[str]:
        raw_text = " ".join(
            [
                str(getattr(node, "raw_repr", "") or ""),
                str(getattr(node, "function_name", "") or ""),
                " ".join(sorted(getattr(node, "defs", set()) or set())),
                " ".join(sorted(getattr(node, "uses", set()) or set())),
            ]
        ).lower()
        return {
            token
            for token in re.split(r"[^a-zA-Z0-9_]+", raw_text)
            if len(token) >= 4
        }

    @staticmethod
    def _overlap_dep_kinds(
        overlap_seed_nodes: Set[str],
        backward: Dict[str, List[GraphEdge]],
    ) -> Set[str]:
        kinds: Set[str] = set()
        for node_id in overlap_seed_nodes:
            for edge in backward.get(node_id, []):
                if edge.edge_type in {"DATA_DEP", "LIFECYCLE_DEP", "EXCEPTION_DEP"}:
                    kinds.add(edge.edge_type)
        return kinds or {"CONTROL_DEP"}

    def _prune_to_cap(
        self,
        marker: Marker,
        node_ids: Set[str],
        seed_nodes: Set[str],
        graph: ReducedGraph,
        backward: Dict[str, List[GraphEdge]],
        forward: Dict[str, List[GraphEdge]],
        extra_required: Set[str] | None = None,
    ) -> Set[str]:
        cap_limit = self._max_nodes_for_marker(marker, self.max_nodes_per_mssu)
        if len(node_ids) <= cap_limit:
            return node_ids

        required = set(seed_nodes)
        if extra_required:
            required |= {node_id for node_id in extra_required if node_id in node_ids}
        for node_id in node_ids:
            node = graph.nodes[node_id]
            if node.effects or node.marker_refs:
                required.add(node_id)
            for edge in backward.get(node_id, []):
                if edge.edge_type == "CONTROL_DEP" and edge.src in node_ids:
                    required.add(edge.src)


        distance: Dict[str, int] = {node_id: 0 for node_id in seed_nodes}
        queue = deque(seed_nodes)
        while queue:
            current = queue.popleft()
            current_distance = distance[current]
            for edge in backward.get(current, []):
                if edge.src in node_ids and edge.src not in distance:
                    distance[edge.src] = current_distance + 1
                    queue.append(edge.src)
            for edge in forward.get(current, []):
                if edge.dst in node_ids and edge.dst not in distance:
                    distance[edge.dst] = current_distance + 1
                    queue.append(edge.dst)

        ranked = sorted(
            node_ids,
            key=lambda node_id: (
                0 if node_id in required else 1,
                distance.get(node_id, 10_000),
                graph.nodes[node_id].line_start,
                node_id,
            ),
        )
        selected = set(ranked[:cap_limit])
        selected |= seed_nodes
        return selected

    def _phase_for_marker(self, marker: Marker) -> str:
        if marker.phase in {Phase.SETUP.value, Phase.RUNTIME.value, Phase.TEARDOWN.value}:
            return marker.phase
        return Phase.RUNTIME.value

    @classmethod
    def _marker_is_shared_infra(cls, marker: Marker) -> bool:
        has_secondary_refs = bool(getattr(marker, "secondary_action_ids", []))
        return bool(
            (has_secondary_refs and not cls._marker_supports_generalized_secondary_binding(marker))
            or str(marker.marker_type).strip().upper()
            in {
                "SUBSCRIBE",
                "UNSUBSCRIBE",
                "BLE_CONNECT",
                "BLE_DISCONNECT",
                "CLOUD_BATCH_CALL",
                "CLOUD_SESSION_REUSE",
                "ENTRY_SETUP",
                "ENTRY_UNLOAD",
                "ENTRY_REMOVE",
            }
            or "shared_infra_secondary_binding" in getattr(marker, "binding_reason", [])
        )

    @staticmethod
    def _is_policy_only_shared_marker(marker_type: str) -> bool:
        return str(marker_type).strip().upper() in {
            "ENTRY_SETUP",
            "ENTRY_UNLOAD",
            "ENTRY_REMOVE",
            "COORD_REFRESH",
            "COORD_FIRST_REFRESH",
        }

    @staticmethod
    def _is_generic_protocol_marker(marker_type: str) -> bool:
        return str(marker_type).strip().upper() in {"BLE_OP", "CLOUD_OP"}

    @staticmethod
    def _marker_has_specific_action_signal(marker: Marker) -> bool:
        evidence = {str(item).strip() for item in getattr(marker, "evidence", []) if str(item).strip()}
        reasons = {str(item).strip() for item in getattr(marker, "binding_reason", []) if str(item).strip()}
        return "target_anchor_seed" in evidence or bool({"literal_overlap", "scope_token_match"} & reasons)

    @classmethod
    def _has_more_specific_protocol_peer(
        cls,
        marker: Marker,
        action_id: str,
        markers_by_id: Dict[str, Marker],
    ) -> bool:
        marker_type = str(marker.marker_type).strip().upper()
        if marker_type == "CLOUD_OP":
            specific_types = {"CLOUD_HTTP_CALL", "CLOUD_429_CHECK", "CLOUD_BACKOFF_SLEEP", "CLOUD_TOKEN_REFRESH"}
        elif marker_type == "BLE_OP":
            specific_types = {"BLE_GATT_OP", "BLE_CONNECT", "BLE_DISCONNECT"}
        else:
            return False
        marker_file = str(getattr(marker, "file_path", "")).strip()
        for peer in markers_by_id.values():
            if peer.marker_id == marker.marker_id:
                continue
            if str(getattr(peer, "file_path", "")).strip() != marker_file:
                continue
            if str(getattr(peer, "primary_action_id", "") or "").strip() != action_id:
                continue
            if str(peer.marker_type).strip().upper() in specific_types:
                if cls._marker_supports_generalized_secondary_binding(marker):
                    marker_refs = cls._effective_marker_action_ref_set(marker)
                    peer_refs = cls._effective_marker_action_ref_set(peer)
                    if marker_refs and not marker_refs <= peer_refs:
                        continue
                return True
        return False

    @staticmethod
    def _clear_action_binding(refined: Dict[str, object], *, mark_shared_infra: bool = False) -> None:
        refined["primary_action_ref"] = None
        refined["secondary_action_refs"] = []
        refined["action_refs"] = []
        refined["lane_tag"] = None
        refined["resource_instance_tag"] = None
        if mark_shared_infra:
            refined["is_shared_infra"] = True

    @staticmethod
    def _action_index(target: OptimizationTarget | None) -> Dict[str, Dict[str, object]]:
        if target is None:
            return {}
        rows: Dict[str, Dict[str, object]] = {}
        for action in target.vdev_actions:
            action_id = str(action.get("action_id", "")).strip()
            if action_id:
                rows[action_id] = action
        return rows

    @classmethod
    def _lane_tag_for_action(cls, action: Dict[str, object]) -> str | None:
        protocol = str(action.get("protocol", "")).strip().upper()
        if protocol == "BLE":
            return "BLE_LOCAL"
        if protocol == "CLOUD":
            return "CLOUD"
        if protocol == "HA":
            target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
            entity = str(target.get("entity_id") or target.get("id") or "").lower()
            if "overall" in entity:
                return "WRITEBACK_OVERALL"
            if "ble_lane" in entity:
                return "WRITEBACK_BLE"
            if "cloud_lane" in entity:
                return "WRITEBACK_CLOUD"
            return "WRITEBACK"
        return None

    @staticmethod
    def _resource_instance_tag(action: Dict[str, object]) -> str | None:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        for key in ("device_id", "endpoint", "entity_id", "id"):
            value = str(target.get(key, "")).strip()
            if value:
                return value
        return None

    @classmethod
    def _is_aggregate_sink_action(cls, action: Dict[str, object] | None) -> bool:
        if not isinstance(action, dict):
            return False
        protocol = str(action.get("protocol", "")).strip().upper()
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        entity = str(target.get("entity_id") or target.get("id") or "").lower()
        return protocol == "HA" and "overall" in entity

    @classmethod
    def _effective_marker_action_refs(cls, marker: Marker) -> tuple[str | None, List[str], bool]:
        raw_primary = getattr(marker, "primary_action_id", "")
        primary = "" if raw_primary is None else str(raw_primary).strip()
        primary = primary or None
        legacy_refs = [
            str(action_id).strip()
            for action_id in getattr(marker, "related_action_ids", [])
            if str(action_id).strip()
        ]
        if primary is None and legacy_refs:
            primary = legacy_refs[0]
        secondary = [
            str(action_id).strip()
            for action_id in getattr(marker, "secondary_action_ids", [])
            if str(action_id).strip()
        ]
        if not secondary and len(legacy_refs) > 1:
            secondary = legacy_refs[1:]
        is_shared = cls._marker_is_shared_infra(marker)
        return primary, sorted(set(secondary)), is_shared

    @classmethod
    def _effective_marker_action_ref_set(cls, marker: Marker) -> Set[str]:
        primary, secondary, is_shared = cls._effective_marker_action_refs(marker)
        refs = {primary} if primary else set()
        if is_shared or cls._marker_supports_generalized_secondary_binding(marker):
            refs.update(secondary)
        return {str(action_id).strip() for action_id in refs if str(action_id).strip()}

    @staticmethod
    def _marker_supports_generalized_secondary_binding(marker: Marker) -> bool:
        evidence = {
            str(item or "").strip()
            for item in getattr(marker, "evidence", [])
            if str(item or "").strip()
        }
        if "action_match:generalized_profile_secondary_binding" in evidence:
            return True
        has_profile_rule = any(item.startswith("grounding_profile_rule:") for item in evidence)
        secondary = [
            str(action_id).strip()
            for action_id in getattr(marker, "secondary_action_ids", [])
            if str(action_id).strip()
        ]
        return bool(has_profile_rule and secondary)

    @staticmethod
    def _supports_multi_action_binding(binding: Dict[str, object]) -> bool:
        return bool(binding.get("is_shared_infra")) or bool(binding.get("supports_generalized_secondary_binding"))

    @staticmethod
    def _preserve_explicit_profile_binding(marker: Marker, binding: Dict[str, object]) -> bool:
        explicit_primary = str(binding.get("primary_action_ref") or "").strip()
        if not explicit_primary:
            return False
        if MSSUBuilder._is_policy_only_shared_marker(str(getattr(marker, "marker_type", "") or "").strip().upper()):
            return False
        evidence = {
            str(item or "").strip()
            for item in getattr(marker, "evidence", [])
            if str(item or "").strip()
        }
        return any(item.startswith("grounding_profile_rule:") for item in evidence)

    @staticmethod
    def _is_generalized_cluster_bound_mssu(mssu: MSSU) -> bool:
        return (
            not bool(getattr(mssu, "is_shared_infra", False))
            and bool(str(getattr(mssu, "primary_action_ref", "") or "").strip())
            and bool([aid for aid in getattr(mssu, "secondary_action_refs", []) if str(aid).strip()])
            and len([aid for aid in getattr(mssu, "action_refs", []) if str(aid).strip()]) > 1
        )

    @staticmethod
    def _exception_labels(node_raw_repr: str, stmt_kind: str) -> Set[str]:
        text = node_raw_repr.lower()
        labels: Set[str] = set()
        if "configentryauthfailed" in text or "authfailed" in text:
            labels.add("AuthFailed")
        if "updatefailed" in text:
            labels.add("UpdateFailed")
        if "timeout" in text:
            labels.add("TimeoutError")
        if "ratelimit" in text or "toomanyrequests" in text:
            labels.add("RateLimitError")
        if stmt_kind == "Try" and not labels and any(
            token in text
            for token in {
                "raise(",
                "excepthandler(",
                "return(",
                "retry",
                "backoff",
                "sleep",
            }
        ):
            labels.add("Exception")
        return labels

    @staticmethod
    def _marker_matches_action_hint(marker_type: str, action_hints: Set[str]) -> bool:
        marker = marker_type.upper()
        if marker in action_hints:
            return True
        if marker.startswith("BLE_") and "BLE_OP" in action_hints:
            return True
        if marker.startswith("CLOUD_") and "CLOUD_OP" in action_hints:
            return True
        if marker in {"COORD_REFRESH", "COORD_FIRST_REFRESH"} and (
            "COORD_REFRESH" in action_hints or "COORD_FIRST_REFRESH" in action_hints
        ):
            return True
        return False

    @classmethod
    def _action_binding_for_marker(cls, marker: Marker, target: OptimizationTarget | None) -> Dict[str, object]:
        if target is None:
            return {
                "action_refs": [],
                "primary_action_ref": None,
                "secondary_action_refs": [],
                "critical": False,
                "is_shared_infra": False,
                "is_aggregate_sink": False,
                "lane_tag": None,
                "resource_instance_tag": None,
            }

        action_index = cls._action_index(target)
        primary, secondary, is_shared_infra = cls._effective_marker_action_refs(marker)
        supports_generalized_secondary_binding = cls._marker_supports_generalized_secondary_binding(marker)

        refs: List[str] = []
        if primary and primary in action_index:
            refs.append(primary)
        if is_shared_infra or supports_generalized_secondary_binding:
            refs.extend(action_id for action_id in secondary if action_id in action_index)
        refs = sorted(set(refs))

        if not refs and (is_shared_infra or target is not None):
            for action in target.vdev_actions:
                action_id = str(action.get("action_id", "")).strip()
                marker_hints = {str(item).upper() for item in action.get("marker_hints", [])}
                if action_id and cls._marker_matches_action_hint(marker.marker_type, marker_hints):
                    refs.append(action_id)
            refs = sorted(set(refs))
            if refs and (is_shared_infra or supports_generalized_secondary_binding or len(refs) == 1):
                primary = refs[0]
                secondary = refs[1:]
            elif not is_shared_infra and len(refs) > 1:
                refs = []
                secondary = []

        critical = any(
            bool(action_index[action_id].get("critical", False))
            or action_id in set(target.critical_action_ids)
            for action_id in refs
            if action_id in action_index
        )
        if "target_anchor_seed" in marker.evidence or "target_anchor_op" in marker.evidence:
            critical = True

        action_row = action_index.get(primary or "")
        is_aggregate_sink = cls._is_aggregate_sink_action(action_row)
        return {
            "action_refs": refs,
            "primary_action_ref": primary if primary in action_index else None,
            "secondary_action_refs": [
                action_id for action_id in secondary if action_id in action_index
            ] if (is_shared_infra or supports_generalized_secondary_binding) else [],
            "critical": critical,
            "is_shared_infra": is_shared_infra,
            "supports_generalized_secondary_binding": supports_generalized_secondary_binding,
            "is_aggregate_sink": is_aggregate_sink,
            "lane_tag": cls._lane_tag_for_action(action_row) if action_row else None,
            "resource_instance_tag": cls._resource_instance_tag(action_row) if action_row else None,
        }

    @classmethod
    def _action_refs_for_marker(cls, marker: Marker, target: OptimizationTarget | None) -> tuple[List[str], bool]:
        binding = cls._action_binding_for_marker(marker, target)
        return list(binding["action_refs"]), bool(binding["critical"])

    @staticmethod
    def _writeback_lanes() -> Set[str]:
        return {"WRITEBACK", "WRITEBACK_BLE", "WRITEBACK_CLOUD", "WRITEBACK_OVERALL"}

    @classmethod
    def _action_ownership_score(
        cls,
        node_ids: Set[str],
        graph: ReducedGraph,
        markers_by_id: Dict[str, Marker],
    ) -> Dict[str, float]:
        score: Dict[str, float] = {}
        for node_id in node_ids:
            node = graph.nodes.get(node_id)
            if node is None:
                continue
            for marker_id in node.marker_refs:
                marker = markers_by_id.get(str(marker_id))
                if marker is None:
                    continue
                marker_type = str(marker.marker_type).strip().upper()
                weight = 1.0
                if marker_type in {"ENTRY_SETUP", "ENTRY_UNLOAD", "ENTRY_REMOVE", "SUBSCRIBE", "UNSUBSCRIBE", "COORD_REFRESH", "COORD_FIRST_REFRESH"}:
                    weight = 0.25
                primary, secondary, is_shared = cls._effective_marker_action_refs(marker)
                supports_generalized = cls._marker_supports_generalized_secondary_binding(marker)
                if primary:
                    score[primary] = score.get(primary, 0.0) + weight
                if is_shared or supports_generalized:
                    secondary_weight = weight * 0.8
                    for action_id in secondary:
                        score[action_id] = score.get(action_id, 0.0) + secondary_weight
        return score

    @classmethod
    def _refine_binding_from_closure(
        cls,
        marker: Marker,
        node_ids: Set[str],
        graph: ReducedGraph,
        markers_by_id: Dict[str, Marker],
        target: OptimizationTarget | None,
        binding: Dict[str, object],
    ) -> Dict[str, object]:
        refined = dict(binding)
        action_index = cls._action_index(target)
        marker_type = str(marker.marker_type).strip().upper()
        explicit_primary = str(binding.get("primary_action_ref") or "").strip()
        explicit_action_row = action_index.get(explicit_primary, {}) if explicit_primary else {}
        explicit_lane = cls._lane_tag_for_action(explicit_action_row) if explicit_action_row else None
        explicit_protocol = str(explicit_action_row.get("protocol", "")).strip().upper() if explicit_action_row else ""
        preserve_explicit_writeback_primary = (
            marker_type == "STATE_WRITE"
            and bool(explicit_primary)
            and (explicit_protocol == "HA" or str(explicit_lane or "") in cls._writeback_lanes())
        )
        explicit_refs = [
            action_id
            for action_id in [
                str(binding.get("primary_action_ref") or "").strip(),
                *[
                    str(action_id).strip()
                    for action_id in binding.get("secondary_action_refs", [])
                    if str(action_id).strip()
                ],
            ]
            if action_id and action_id in action_index
        ]
        preserve_explicit_profile_binding = cls._preserve_explicit_profile_binding(marker, binding)
        ownership = cls._action_ownership_score(node_ids, graph, markers_by_id)
        if preserve_explicit_profile_binding:
            refined["primary_action_ref"] = explicit_primary if explicit_primary in action_index else None
            if cls._supports_multi_action_binding(refined):
                refined["secondary_action_refs"] = [
                    action_id
                    for action_id in explicit_refs
                    if action_id and action_id in action_index and action_id != refined["primary_action_ref"]
                ]
            else:
                refined["secondary_action_refs"] = []
            refined["action_refs"] = [
                action_id
                for action_id in [refined.get("primary_action_ref"), *refined.get("secondary_action_refs", [])]
                if action_id and action_id in action_index
            ]
        elif ownership and not cls._is_policy_only_shared_marker(marker_type) and not preserve_explicit_writeback_primary:
            ranked = sorted(ownership.items(), key=lambda item: (-item[1], item[0]))
            primary_action = ranked[0][0]
            refined["primary_action_ref"] = primary_action if primary_action in action_index else None
            if cls._supports_multi_action_binding(refined):
                max_score = ranked[0][1]
                ownership_secondary = [
                    action_id
                    for action_id, score in ranked[1:]
                    if action_id in action_index and score >= max_score - 0.25
                ]
                preferred_secondary = [action_id for action_id in explicit_refs if action_id != primary_action]
                refined["secondary_action_refs"] = sorted(
                    {
                        action_id
                        for action_id in [*preferred_secondary, *ownership_secondary]
                        if action_id and action_id in action_index and action_id != primary_action
                    }
                )
            else:
                refined["secondary_action_refs"] = []
            refined["action_refs"] = [
                action_id
                for action_id in [refined["primary_action_ref"], *refined.get("secondary_action_refs", [])]
                if action_id
            ]
        elif preserve_explicit_writeback_primary:
            refined["primary_action_ref"] = explicit_primary if explicit_primary in action_index else None
            if not cls._supports_multi_action_binding(refined):
                refined["secondary_action_refs"] = []
            refined["action_refs"] = [
                action_id
                for action_id in [refined.get("primary_action_ref"), *refined.get("secondary_action_refs", [])]
                if action_id and action_id in action_index
            ]

        if cls._is_policy_only_shared_marker(marker_type):
            cls._clear_action_binding(refined, mark_shared_infra=True)

        primary_action = str(refined.get("primary_action_ref") or "").strip()
        if (
            primary_action
            and cls._is_generic_protocol_marker(marker_type)
            and not cls._marker_has_specific_action_signal(marker)
            and cls._has_more_specific_protocol_peer(marker, primary_action, markers_by_id)
        ):
            cls._clear_action_binding(refined, mark_shared_infra=True)

        if marker_type == "STATE_WRITE":
            lane = str(refined.get("lane_tag") or "")
            action_row = action_index.get(str(refined.get("primary_action_ref") or "").strip(), {})
            protocol = str(action_row.get("protocol", "")).strip().upper()
            if (lane and lane not in cls._writeback_lanes()) or protocol in {"BLE", "CLOUD"}:
                cls._clear_action_binding(refined, mark_shared_infra=True)

        if bool(refined.get("is_shared_infra", False)) and not refined.get("primary_action_ref"):
            cls._clear_action_binding(refined, mark_shared_infra=True)

        primary_action = str(refined.get("primary_action_ref") or "").strip()
        if primary_action:
            action_row = action_index.get(primary_action)
            refined["is_aggregate_sink"] = cls._is_aggregate_sink_action(action_row)
            refined["lane_tag"] = cls._lane_tag_for_action(action_row) if action_row else None
            refined["resource_instance_tag"] = cls._resource_instance_tag(action_row) if action_row else None

        return refined

    @classmethod
    def _same_lane_or_writeback(cls, src_mssu: MSSU, dst_mssu: MSSU) -> bool:
        src_action = str(getattr(src_mssu, "primary_action_ref", "") or "").strip()
        dst_action = str(getattr(dst_mssu, "primary_action_ref", "") or "").strip()
        if src_action and src_action == dst_action:
            return True
        src_lane = str(getattr(src_mssu, "lane_tag", "") or "").strip()
        dst_lane = str(getattr(dst_mssu, "lane_tag", "") or "").strip()
        if not src_action and not dst_action and not src_lane and not dst_lane:
            return True
        if src_lane and src_lane == dst_lane:
            return True
        writeback = cls._writeback_lanes()
        if src_lane in writeback or dst_lane in writeback:
            return True
        return False

    @classmethod
    def summarize_grounding(cls, mssus: List[MSSU], optimization_target: OptimizationTarget | None) -> Dict[str, object]:
        if optimization_target is None:
            return {
                "build_status": "OK",
                "resolved_action_refs": [],
                "resolved_runtime_action_refs": [],
                "critical_action_ids": [],
                "missing_critical_action_ids": [],
                "resolved_runtime_action_count": 0,
            }

        critical_ids = sorted({str(item) for item in optimization_target.critical_action_ids if str(item).strip()})
        if not critical_ids:
            critical_ids = sorted(
                {
                    str(action.get("action_id", "")).strip()
                    for action in optimization_target.vdev_actions
                    if str(action.get("action_id", "")).strip() and bool(action.get("critical", False))
                }
            )

        resolved_action_refs = sorted(
            {
                str(action_id)
                for mssu in mssus
                for action_id in getattr(mssu, "action_refs", [])
                if str(action_id).strip()
            }
        )
        resolved_runtime_action_refs = sorted(
            {
                str(action_id)
                for mssu in mssus
                if str(getattr(mssu, "phase", "")).upper() == "RUNTIME"
                for action_id in getattr(mssu, "action_refs", [])
                if str(action_id).strip()
            }
        )
        multi_bound_nonshared = sorted(
            mssu.mssu_id
            for mssu in mssus
            if mssu.mssu_type in {"ACT", "UPDATE"}
            and len([action_id for action_id in getattr(mssu, "action_refs", []) if str(action_id).strip()]) > 1
            and not bool(getattr(mssu, "is_shared_infra", False))
            and not bool(getattr(mssu, "is_aggregate_sink", False))
            and not cls._is_generalized_cluster_bound_mssu(mssu)
        )
        missing_critical = sorted(set(critical_ids) - set(resolved_action_refs))
        return {
            "build_status": "OK" if not missing_critical and not multi_bound_nonshared else "PARTIAL_GROUNDING",
            "resolved_action_refs": resolved_action_refs,
            "resolved_runtime_action_refs": resolved_runtime_action_refs,
            "critical_action_ids": critical_ids,
            "missing_critical_action_ids": missing_critical,
            "resolved_runtime_action_count": len(resolved_runtime_action_refs),
            "multi_bound_nonshared_mssu_ids": multi_bound_nonshared,
        }

    def _derive_io(
        self,
        node_ids: Set[str],
        graph: ReducedGraph,
        forward: Dict[str, List[GraphEdge]],
    ) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
        defs_in: Set[str] = set()
        uses_in: Set[str] = set()
        effects: Set[str] = set()
        exceptions: Set[str] = set()

        for node_id in node_ids:
            node = graph.nodes[node_id]
            defs_in |= set(node.defs)
            uses_in |= set(node.uses)
            effects |= set(node.effects)
            exceptions |= self._exception_labels(node.raw_repr, node.stmt_kind)

        inputs = uses_in - defs_in
        outputs = set()
        for node_id in node_ids:
            node = graph.nodes[node_id]
            if not node.defs:
                continue
            escaped = False
            for edge in forward.get(node_id, []):
                if edge.dst not in node_ids and edge.edge_type in {"DATA_DEP", "LIFECYCLE_DEP"}:
                    escaped = True
                    break
            if escaped:
                outputs |= set(node.defs)

        return inputs, outputs, effects, exceptions

    @staticmethod
    def _mssu_file_scope(mssu: MSSU, graph: ReducedGraph) -> Tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(graph.nodes[node_id].file_path)
                    for node_id in mssu.node_ids
                    if node_id in graph.nodes and str(graph.nodes[node_id].file_path).strip()
                }
            )
        )

    @staticmethod
    def _primary_effect_family(mssu: MSSU) -> str:
        effects = {str(item).strip().lower() for item in getattr(mssu, "side_effect_sig", set()) if str(item).strip()}
        if "ble_op" in effects:
            return "ble_op"
        if "cloud_http_call" in effects:
            return "cloud_http_call"
        if "state_write" in effects:
            return "state_write"
        if "subscribe" in effects:
            return "subscribe"
        if "unsubscribe" in effects:
            return "unsubscribe"
        if "ble_connect" in effects:
            return "ble_connect"
        if "ble_disconnect" in effects:
            return "ble_disconnect"
        if "entry_setup" in effects:
            return "entry_setup"
        if "entry_unload" in effects:
            return "entry_unload"
        return "|".join(sorted(effects))

    @classmethod
    def _drop_teardown_unowned_ble_ops(cls, mssu: MSSU) -> bool:
        effects = {str(item).strip().lower() for item in getattr(mssu, "side_effect_sig", set()) if str(item).strip()}
        return (
            str(getattr(mssu, "phase", "")).upper() == Phase.TEARDOWN.value
            and not [action_id for action_id in getattr(mssu, "action_refs", []) if str(action_id).strip()]
            and bool(getattr(mssu, "is_shared_infra", False))
            and effects.issubset({"ble_op", "external_call_ble"})
        )

    @classmethod
    def _drop_teardown_connect_mssu(cls, mssu: MSSU) -> bool:
        effects = {str(item).strip().lower() for item in getattr(mssu, "side_effect_sig", set()) if str(item).strip()}
        return (
            str(getattr(mssu, "phase", "")).upper() == Phase.TEARDOWN.value
            and str(getattr(mssu, "primary_action_ref", "") or "").strip() == "A2"
            and "ble_connect" in effects
            and bool(getattr(mssu, "is_shared_infra", False))
        )

    @classmethod
    def _normalize_teardown_connect_mssu(cls, mssu: MSSU, peers: List[MSSU]) -> MSSU:
        if not cls._drop_teardown_connect_mssu(mssu):
            return mssu
        has_alternative_owner = any(
            peer.mssu_id != mssu.mssu_id
            and str(getattr(peer, "primary_action_ref", "") or "").strip() == "A2"
            and str(getattr(peer, "phase", "")).strip().upper() != Phase.TEARDOWN.value
            for peer in peers
        )
        if has_alternative_owner:
            mssu.primary_action_ref = None
            mssu.secondary_action_refs = []
            mssu.action_refs = []
            mssu.is_shared_infra = True
            mssu.is_aggregate_sink = False
            mssu.lane_tag = None
            mssu.resource_instance_tag = None
            mssu.critical = False
            return mssu
        mssu.phase = Phase.SETUP.value
        return mssu

    @classmethod
    def _propagate_shared_cleanup_resource_tags(cls, mssus: List[MSSU], graph: ReducedGraph) -> List[MSSU]:
        subscribe_tags_by_file: Dict[Tuple[str, ...], Set[str]] = {}
        subscribe_lanes_by_file: Dict[Tuple[str, ...], Set[str]] = {}
        global_subscribe_tags: Set[str] = set()
        global_subscribe_lanes: Set[str] = set()
        for mssu in mssus:
            family = cls._primary_effect_family(mssu)
            if family != "subscribe":
                continue
            file_scope = cls._mssu_file_scope(mssu, graph)
            tag = str(getattr(mssu, "resource_instance_tag", "") or "").strip()
            lane = str(getattr(mssu, "lane_tag", "") or "").strip()
            if tag:
                subscribe_tags_by_file.setdefault(file_scope, set()).add(tag)
                global_subscribe_tags.add(tag)
            if lane:
                subscribe_lanes_by_file.setdefault(file_scope, set()).add(lane)
                global_subscribe_lanes.add(lane)

        for mssu in mssus:
            if cls._primary_effect_family(mssu) != "unsubscribe":
                continue
            if str(getattr(mssu, "resource_instance_tag", "") or "").strip():
                continue
            file_scope = cls._mssu_file_scope(mssu, graph)
            tags = subscribe_tags_by_file.get(file_scope, set())
            if not tags and len(global_subscribe_tags) == 1:
                tags = set(global_subscribe_tags)
            if len(tags) == 1:
                mssu.resource_instance_tag = next(iter(tags))
            if not str(getattr(mssu, "lane_tag", "") or "").strip():
                lanes = subscribe_lanes_by_file.get(file_scope, set())
                if not lanes and len(global_subscribe_lanes) == 1:
                    lanes = set(global_subscribe_lanes)
                if len(lanes) == 1:
                    mssu.lane_tag = next(iter(lanes))
        return mssus

    @staticmethod
    def _merged_phase(bucket: List[MSSU]) -> str:
        phases = {str(getattr(mssu, "phase", "")).strip().upper() for mssu in bucket}
        for phase in (Phase.RUNTIME.value, Phase.SETUP.value, Phase.TEARDOWN.value):
            if phase in phases:
                return phase
        return str(getattr(bucket[0], "phase", "")).strip().upper()

    def _merge_key(self, mssu: MSSU, graph: ReducedGraph) -> Tuple[object, ...] | None:
        if not str(getattr(mssu, "primary_action_ref", "") or "").strip():
            return None
        if bool(getattr(mssu, "is_shared_infra", False)) or bool(getattr(mssu, "is_aggregate_sink", False)):
            return None
        if str(getattr(mssu, "mssu_type", "")).upper() not in {"ACT", "UPDATE"}:
            return None
        family = self._primary_effect_family(mssu)
        if family in self._MERGEABLE_EFFECT_FAMILIES:
            return (
                str(getattr(mssu, "primary_action_ref", "") or "").strip(),
                str(getattr(mssu, "lane_tag", "") or "").strip(),
                str(mssu.mssu_type).strip().upper(),
                family,
                str(getattr(mssu, "resource_instance_tag", "") or "").strip(),
            )
        if str(getattr(mssu, "phase", "")).upper() != Phase.RUNTIME.value:
            return None
        return (
            str(mssu.primary_action_ref),
            str(mssu.mssu_type),
            str(mssu.phase),
            str(mssu.lane_tag or ""),
            str(mssu.resource_instance_tag or ""),
            tuple(sorted(mssu.required_guards)),
            family,
            self._mssu_file_scope(mssu, graph),
        )

    def _merge_bucket(self, bucket: List[MSSU], graph: ReducedGraph) -> MSSU:
        base = bucket[0]
        node_ids = sorted({node_id for mssu in bucket for node_id in mssu.node_ids})
        return MSSU(
            mssu_id=base.mssu_id,
            mssu_type=base.mssu_type,
            phase=self._merged_phase(bucket),
            node_ids=node_ids,
            inputs=set().union(*(mssu.inputs for mssu in bucket)),
            outputs=set().union(*(mssu.outputs for mssu in bucket)),
            side_effect_sig=set().union(*(mssu.side_effect_sig for mssu in bucket)),
            exceptions=set().union(*(mssu.exceptions for mssu in bucket)),
            required_guards=sorted({guard for mssu in bucket for guard in mssu.required_guards}),
            critical=any(bool(mssu.critical) for mssu in bucket),
            primary_action_ref=base.primary_action_ref,
            secondary_action_refs=sorted({aid for mssu in bucket for aid in mssu.secondary_action_refs}),
            action_refs=sorted({aid for mssu in bucket for aid in mssu.action_refs}),
            is_shared_infra=any(bool(mssu.is_shared_infra) for mssu in bucket),
            is_aggregate_sink=any(bool(mssu.is_aggregate_sink) for mssu in bucket),
            lane_tag=base.lane_tag,
            resource_instance_tag=base.resource_instance_tag,
        )

    @classmethod
    def _forbid_candidate_pair(cls, src_row: MSSU, dst_row: MSSU) -> bool:
        src_type = str(getattr(src_row, "mssu_type", "")).strip().upper()
        dst_type = str(getattr(dst_row, "mssu_type", "")).strip().upper()
        src_phase = str(getattr(src_row, "phase", "")).strip().upper()
        dst_phase = str(getattr(dst_row, "phase", "")).strip().upper()
        if src_type == "ACT" and dst_type == "INIT":
            return True
        if src_phase == Phase.RUNTIME.value and dst_phase == Phase.SETUP.value:
            return True

        src_family = cls._primary_effect_family(src_row)
        dst_family = cls._primary_effect_family(dst_row)
        if src_type == "ACT" and dst_type == "ACT":
            if src_family == "cloud_http_call" and dst_family == "cloud_op":
                return True

        src_effects = {str(item).strip().lower() for item in getattr(src_row, "side_effect_sig", set()) if str(item).strip()}
        dst_effects = {str(item).strip().lower() for item in getattr(dst_row, "side_effect_sig", set()) if str(item).strip()}
        if "entry_setup" in src_effects and "unsubscribe" in dst_effects:
            return True

        return False

    @staticmethod
    def _skip_candidate_source_or_target(mssu: MSSU) -> bool:
        effects = {
            str(item).strip().lower()
            for item in getattr(mssu, "side_effect_sig", set())
            if str(item).strip()
        }
        return (
            not str(getattr(mssu, "primary_action_ref", "") or "").strip()
            and not str(getattr(mssu, "lane_tag", "") or "").strip()
            and effects == {"cloud_op", "external_call_cloud"}
        )

    def _compact_mssus(
        self,
        mssus: List[MSSU],
        mssu_internal_edges: Dict[str, List[GraphEdge]],
        dependency_candidates: Set[Tuple[str, str, str]],
        graph: ReducedGraph,
    ) -> Tuple[List[MSSU], Dict[str, List[GraphEdge]], Set[Tuple[str, str, str]]]:
        groups: Dict[Tuple[object, ...], List[MSSU]] = {}
        passthrough: List[MSSU] = []
        for mssu in mssus:
            key = self._merge_key(mssu, graph)
            if key is None:
                passthrough.append(mssu)
                continue
            groups.setdefault(key, []).append(mssu)

        merged_mssus: List[MSSU] = []
        id_map: Dict[str, str] = {}

        for mssu in passthrough:
            merged_mssus.append(mssu)
            id_map[mssu.mssu_id] = mssu.mssu_id

        for group in groups.values():
            if len(group) == 1:
                mssu = group[0]
                merged_mssus.append(mssu)
                id_map[mssu.mssu_id] = mssu.mssu_id
                continue

            merged = self._merge_bucket(group, graph)
            merged_mssus.append(merged)
            for mssu in group:
                id_map[mssu.mssu_id] = merged.mssu_id

        merged_internal_edges: Dict[str, List[GraphEdge]] = {}
        node_owner: Dict[str, str] = {}
        for mssu in merged_mssus:
            for node_id in mssu.node_ids:
                node_owner[node_id] = mssu.mssu_id

        for mssu in merged_mssus:
            internal: Dict[Tuple[str, str, str], GraphEdge] = {}
            for edge in mssu_internal_edges.get(mssu.mssu_id, []):
                if edge.src in set(mssu.node_ids) and edge.dst in set(mssu.node_ids):
                    internal[(edge.src, edge.dst, edge.edge_type)] = edge
            for edge in graph.edges:
                if edge.src in node_owner and edge.dst in node_owner and node_owner[edge.src] == mssu.mssu_id and node_owner[edge.dst] == mssu.mssu_id:
                    internal[(edge.src, edge.dst, edge.edge_type)] = edge
            merged_internal_edges[mssu.mssu_id] = list(internal.values())

        by_id = {mssu.mssu_id: mssu for mssu in merged_mssus}
        inter_mssu_edge_types = {"DATA_DEP", "LIFECYCLE_DEP", "CONTROL_DEP", "EXCEPTION_DEP"}
        merged_deps: Set[Tuple[str, str, str]] = set()
        for edge in graph.edges:
            if edge.edge_type not in inter_mssu_edge_types:
                continue
            src_mssu = node_owner.get(edge.src)
            dst_mssu = node_owner.get(edge.dst)
            if not src_mssu or not dst_mssu or src_mssu == dst_mssu:
                continue
            src_row = by_id.get(src_mssu)
            dst_row = by_id.get(dst_mssu)
            if src_row is None or dst_row is None:
                continue
            if self._skip_candidate_source_or_target(src_row) or self._skip_candidate_source_or_target(dst_row):
                continue
            if self._forbid_candidate_pair(src_row, dst_row):
                continue
            if not self._same_lane_or_writeback(src_row, dst_row):
                continue
            merged_deps.add((src_mssu, dst_mssu, edge.edge_type))

        for src, dst, kind in dependency_candidates:
            src_mssu = id_map.get(src, src)
            dst_mssu = id_map.get(dst, dst)
            if not src_mssu or not dst_mssu or src_mssu == dst_mssu:
                continue
            src_row = by_id.get(src_mssu)
            dst_row = by_id.get(dst_mssu)
            if src_row is None or dst_row is None:
                continue
            if self._skip_candidate_source_or_target(src_row) or self._skip_candidate_source_or_target(dst_row):
                continue
            if self._forbid_candidate_pair(src_row, dst_row):
                continue
            merged_deps.add((src_mssu, dst_mssu, kind))

        filtered_mssus = [mssu for mssu in merged_mssus if not self._drop_teardown_unowned_ble_ops(mssu)]
        filtered_mssus = [self._normalize_teardown_connect_mssu(mssu, filtered_mssus) for mssu in filtered_mssus]
        filtered_mssus = self._propagate_shared_cleanup_resource_tags(filtered_mssus, graph)
        if len(filtered_mssus) != len(merged_mssus):
            kept_ids = {mssu.mssu_id for mssu in filtered_mssus}
            merged_internal_edges = {
                mssu_id: rows
                for mssu_id, rows in merged_internal_edges.items()
                if mssu_id in kept_ids
            }
            merged_deps = {
                (src, dst, kind)
                for src, dst, kind in merged_deps
                if src in kept_ids and dst in kept_ids
            }

        filtered_mssus.sort(key=lambda mssu: mssu.mssu_id)
        return filtered_mssus, merged_internal_edges, merged_deps

    def build(
        self,
        graph: ReducedGraph,
        markers: List[Marker],
        marker_to_nodes: Dict[str, List[str]],
        optimization_target: OptimizationTarget | None = None,
        mssu_id_prefix: str = "mssu",
    ) -> MSSUBuildResult:
        forward, backward = self._build_adj(graph)
        edges_by_node = self._edge_index_by_node(graph)
        seeds = self._seed_nodes(markers, marker_to_nodes)
        markers_by_id = {marker.marker_id: marker for marker in markers}

        mssus: List[MSSU] = []
        mssu_internal_edges: Dict[str, List[GraphEdge]] = {}
        node_owner: Dict[str, str] = {}
        assigned_nodes: Set[str] = set()
        overlap_dep_candidates: Set[Tuple[str, str, str]] = set()

        for idx, (marker, seed_nodes) in enumerate(seeds):
            closed_nodes = self._expand_closure(marker, seed_nodes, backward, forward)
            overlap_seed_nodes = {node_id for node_id in seed_nodes if node_id in assigned_nodes}
            closed_nodes = self._claim_nodes(closed_nodes, seed_nodes, assigned_nodes)
            closed_nodes = self._borrow_overlap_context(marker, closed_nodes, overlap_seed_nodes, backward, assigned_nodes)
            closed_nodes = self._filter_action_local_nodes(
                marker,
                closed_nodes,
                seed_nodes,
                graph,
                markers_by_id,
                optimization_target,
            )
            mssu_id = f"{mssu_id_prefix}_{idx:03d}_{marker.marker_type.lower()}"
            for node_id in sorted(overlap_seed_nodes):
                prior_owner = node_owner.get(node_id)
                if prior_owner and prior_owner != mssu_id:
                    for kind in self._overlap_dep_kinds({node_id}, backward):
                        overlap_dep_candidates.add((prior_owner, mssu_id, kind))
            closed_nodes = self._prune_to_cap(
                marker,
                closed_nodes,
                seed_nodes,
                graph,
                backward,
                forward,
                extra_required=overlap_seed_nodes,
            )
            mssu_type = self._mssu_type_for_marker(marker.marker_type)
            phase = self._phase_for_marker(marker)
            inputs, outputs, effects, exceptions = self._derive_io(closed_nodes, graph, forward)
            required_guards: List[str] = []
            marker_type = str(marker.marker_type).strip().upper()
            if marker_type.startswith("BLE_"):
                required_guards.append("resource_available")
            if marker_type.startswith("CLOUD_"):
                required_guards.append("rate_limit_budget_ok")
            if marker_type == "STATE_WRITE":
                required_guards.append("state_write_contract_ok")
            binding = self._action_binding_for_marker(marker, optimization_target)
            binding = self._refine_binding_from_closure(
                marker,
                closed_nodes,
                graph,
                markers_by_id,
                optimization_target,
                binding,
            )

            mssu = MSSU(
                mssu_id=mssu_id,
                mssu_type=mssu_type,
                phase=phase,
                node_ids=sorted(closed_nodes),
                inputs=inputs,
                outputs=outputs,
                side_effect_sig=effects | {marker.marker_type.lower()},
                exceptions=exceptions,
                required_guards=sorted(set(required_guards)),
                critical=bool(binding["critical"]),
                primary_action_ref=binding["primary_action_ref"],
                secondary_action_refs=list(binding["secondary_action_refs"]),
                action_refs=list(binding["action_refs"]),
                is_shared_infra=bool(binding["is_shared_infra"]),
                is_aggregate_sink=bool(binding["is_aggregate_sink"]),
                lane_tag=str(binding["lane_tag"]) if binding["lane_tag"] else None,
                resource_instance_tag=str(binding["resource_instance_tag"]) if binding["resource_instance_tag"] else None,
            )
            mssus.append(mssu)

            for node_id in sorted(closed_nodes):
                if node_id not in node_owner:
                    node_owner[node_id] = mssu_id
                    assigned_nodes.add(node_id)

            internal_edges: Dict[Tuple[str, str, str], GraphEdge] = {}
            for node_id in closed_nodes:
                for edge in edges_by_node.get(node_id, []):
                    if edge.src in closed_nodes and edge.dst in closed_nodes:
                        internal_edges[(edge.src, edge.dst, edge.edge_type)] = edge
            mssu_internal_edges[mssu_id] = list(internal_edges.values())

        dep_candidates: Set[Tuple[str, str, str]] = set()
        inter_mssu_edge_types = {"DATA_DEP", "LIFECYCLE_DEP", "CONTROL_DEP", "EXCEPTION_DEP"}
        for edge in graph.edges:
            if edge.edge_type not in inter_mssu_edge_types:
                continue
            src_mssu = node_owner.get(edge.src)
            dst_mssu = node_owner.get(edge.dst)
            if not src_mssu or not dst_mssu or src_mssu == dst_mssu:
                continue
            src_row = next((mssu for mssu in mssus if mssu.mssu_id == src_mssu), None)
            dst_row = next((mssu for mssu in mssus if mssu.mssu_id == dst_mssu), None)
            if src_row is None or dst_row is None:
                continue
            if self._skip_candidate_source_or_target(src_row) or self._skip_candidate_source_or_target(dst_row):
                continue
            if self._forbid_candidate_pair(src_row, dst_row):
                continue
            if not self._same_lane_or_writeback(src_row, dst_row):
                continue
            dep_candidates.add((src_mssu, dst_mssu, edge.edge_type))
        dep_candidates |= overlap_dep_candidates

        mssus, mssu_internal_edges, dep_candidates = self._compact_mssus(
            mssus,
            mssu_internal_edges,
            dep_candidates,
            graph,
        )

        summary = self.summarize_grounding(mssus, optimization_target)
        return MSSUBuildResult(
            mssus=mssus,
            mssu_internal_edges=mssu_internal_edges,
            dependency_candidates=sorted(dep_candidates),
            build_status=str(summary["build_status"]),
            summary=summary,
        )
