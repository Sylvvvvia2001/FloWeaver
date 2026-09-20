from __future__ import annotations

from bisect import bisect_left, bisect_right
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

from dsl.contracts import GraphEdge, GraphNode, HAPProfile, Marker, OptimizationTarget, ReducedGraph
from optimizer.ast_utils import StatementRecord, extract_statement_records


ENTITY_ID_RE = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+", re.IGNORECASE)
ENDPOINT_RE = re.compile(r"[a-z0-9_]+:[a-z0-9_.-]+", re.IGNORECASE)
MAC_RE = re.compile(r"(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}", re.IGNORECASE)
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
SHARED_INFRA_MARKER_TYPES = {
    "ENTRY_SETUP",
    "ENTRY_UNLOAD",
    "ENTRY_REMOVE",
    "SUBSCRIBE",
    "UNSUBSCRIBE",
    "COORD_REFRESH",
    "COORD_FIRST_REFRESH",
}


@dataclass
class ReductionResult:
    reduced_graph: ReducedGraph
    marker_to_nodes: Dict[str, List[str]]
    kept_node_ids: Set[str]


@dataclass
class _AnchorTerms:
    entities: Set[str]
    endpoints: Set[str]
    endpoint_prefixes: Set[str]
    macs: Set[str]
    uuids: Set[str]


class TempoSpatialReducer:
    def __init__(
        self,
        profile: HAPProfile,
        temporal_depth: int = 200,
        spatial_depth: int = 2,
        cfg_back_depth: int = 1,
        temporal_slack_lines: int = 1,
        lifecycle_spatial_depth: int | None = None,
        debug: bool = False,
    ) -> None:
        self.profile = profile
        self.temporal_depth = temporal_depth
        self.spatial_depth = spatial_depth
        self.cfg_back_depth = max(0, int(cfg_back_depth))
        self.temporal_slack_lines = max(0, int(temporal_slack_lines))
        self.lifecycle_spatial_depth = None if lifecycle_spatial_depth is None else max(0, int(lifecycle_spatial_depth))
        self.debug = bool(debug)

    @staticmethod
    def _node_ordinal(node_id: str) -> str:
        parts = node_id.split(":")
        if len(parts) < 4:
            return ""
        return parts[-2]

    @staticmethod
    def _record_ordinal(rec: StatementRecord) -> str:
        if rec.ordinal:
            return rec.ordinal
        return TempoSpatialReducer._node_ordinal(rec.node_id)

    @staticmethod
    def _is_exception_branch_descendant(
        candidate_ordinal: str,
        try_ordinal: str,
        by_ordinal: Dict[str, StatementRecord],
    ) -> bool:
        cur = candidate_ordinal
        while cur:
            rec = by_ordinal.get(cur)
            if rec is None:
                if "." not in cur:
                    return False
                cur = cur.rsplit(".", 1)[0]
                continue
            parent = rec.parent_ordinal
            if parent == try_ordinal:
                block = str(rec.parent_block).strip().lower()
                return block in {"except", "finalbody"}
            if not parent:
                return False
            cur = parent
        return False

    def _build_full_graph(self, path: str | Path) -> Tuple[ReducedGraph, Dict[str, List[StatementRecord]]]:
        records = extract_statement_records(path)
        by_fn: Dict[str, List[StatementRecord]] = {}
        for record in records:
            by_fn.setdefault(record.function_name, []).append(record)

        for fn_records in by_fn.values():
            fn_records.sort(key=lambda r: r.line_start)

        nodes: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []
        edge_keys: Set[Tuple[str, str, str]] = set()

        def add_edge(src: str, dst: str, edge_type: str) -> bool:
            key = (src, dst, edge_type)
            if src == dst or key in edge_keys:
                return False
            edge_keys.add(key)
            edges.append(GraphEdge(src=src, dst=dst, edge_type=edge_type))
            return True

        for fn, fn_records in by_fn.items():
            last_def: Dict[str, str] = {}
            by_ordinal: Dict[str, StatementRecord] = {}
            for idx, rec in enumerate(fn_records):
                if rec.ordinal:
                    by_ordinal[rec.ordinal] = rec
                nodes[rec.node_id] = GraphNode(
                    node_id=rec.node_id,
                    file_path=rec.file_path,
                    function_name=rec.function_name,
                    line_start=rec.line_start,
                    line_end=rec.line_end,
                    stmt_kind=rec.stmt_kind,
                    col_start=rec.col_start,
                    col_end=rec.col_end,
                    raw_repr=rec.raw_repr,
                    effects=set(rec.effects),
                    defs=set(rec.defs),
                    uses=set(rec.uses),
                    marker_refs=[],
                )

                if idx > 0:
                    add_edge(src=fn_records[idx - 1].node_id, dst=rec.node_id, edge_type="CFG_NEXT")

                for name in rec.uses:
                    if name in last_def:
                        add_edge(src=last_def[name], dst=rec.node_id, edge_type="DATA_DEP")

                for name in rec.defs:
                    last_def[name] = rec.node_id


            descendants_by_parent: Dict[str, List[StatementRecord]] = {}
            for rec in fn_records:
                ordinal = self._record_ordinal(rec)
                if not ordinal or "." not in ordinal:
                    continue
                cur = ordinal
                while "." in cur:
                    cur = cur.rsplit(".", 1)[0]
                    descendants_by_parent.setdefault(cur, []).append(rec)

            control_kinds = {"If", "Try", "For", "While", "With", "AsyncWith", "Match"}
            for idx, rec in enumerate(fn_records):
                if rec.stmt_kind not in control_kinds:
                    continue
                rec_ordinal = self._record_ordinal(rec)
                descendants = sorted(
                    descendants_by_parent.get(rec_ordinal, []),
                    key=lambda item: (item.line_start, item.line_end),
                )
                if descendants:
                    for child in descendants:
                        add_edge(src=rec.node_id, dst=child.node_id, edge_type="CONTROL_DEP")
                elif idx + 1 < len(fn_records):

                    add_edge(src=rec.node_id, dst=fn_records[idx + 1].node_id, edge_type="CONTROL_DEP")


            for rec in fn_records:
                if rec.stmt_kind != "Try":
                    continue
                try_ordinal = self._record_ordinal(rec)
                if not try_ordinal:
                    continue
                has_exception_branch = False
                emitted = 0
                for candidate in fn_records:
                    cand_ordinal = self._record_ordinal(candidate)
                    if not cand_ordinal or not cand_ordinal.startswith(f"{try_ordinal}."):
                        continue
                    if self._is_exception_branch_descendant(cand_ordinal, try_ordinal, by_ordinal):
                        has_exception_branch = True
                        if add_edge(src=rec.node_id, dst=candidate.node_id, edge_type="EXCEPTION_DEP"):
                            emitted += 1
                if self.debug and has_exception_branch and emitted == 0:
                    raise RuntimeError(
                        f"M2 debug: missing EXCEPTION_DEP for try node {rec.node_id} in {rec.file_path}:{rec.line_start}"
                    )

        mapping = {
            node_id: {
                "file": node.file_path,
                "function": node.function_name,
                "line_start": node.line_start,
                "line_end": node.line_end,
                "col_start": node.col_start,
                "col_end": node.col_end,
            }
            for node_id, node in nodes.items()
        }
        graph = ReducedGraph(nodes=nodes, edges=edges, mapping=mapping)
        return graph, by_fn

    @staticmethod
    def _index_fn_nodes(graph: ReducedGraph) -> Tuple[Dict[Tuple[str, str], List[GraphNode]], Dict[Tuple[str, str], List[int]]]:
        fn_index: Dict[Tuple[str, str], List[GraphNode]] = {}
        fn_starts: Dict[Tuple[str, str], List[int]] = {}

        for node in graph.nodes.values():
            key = (node.file_path, node.function_name)
            fn_index.setdefault(key, []).append(node)

        for key, rows in fn_index.items():
            rows.sort(key=lambda item: (item.line_start, item.line_end))
            fn_starts[key] = [item.line_start for item in rows]
        return fn_index, fn_starts

    @staticmethod
    def _attach_marker_refs(
        graph: ReducedGraph,
        markers: List[Marker],
        fn_index: Dict[Tuple[str, str], List[GraphNode]] | None = None,
        fn_starts: Dict[Tuple[str, str], List[int]] | None = None,
    ) -> Dict[str, List[str]]:
        marker_to_nodes: Dict[str, List[str]] = {}
        if fn_index is None or fn_starts is None:
            fn_index, fn_starts = TempoSpatialReducer._index_fn_nodes(graph)

        for marker in markers:
            attached: List[str] = []
            key = (marker.file_path, marker.function_name)
            candidates = fn_index.get(key, [])
            starts = fn_starts.get(key, [])

            if candidates and starts:
                lo = bisect_left(starts, marker.line_start)
                hi = bisect_right(starts, marker.line_end)
                scan_lo = lo
                while scan_lo > 0 and candidates[scan_lo - 1].line_end >= marker.line_start:
                    scan_lo -= 1

                for node in candidates[scan_lo:hi]:
                    line_overlap = not (node.line_end < marker.line_start or marker.line_end < node.line_start)
                    if line_overlap:
                        node.marker_refs.append(marker.marker_id)
                        attached.append(node.node_id)
            if not attached:

                if candidates:
                    nearest = min(candidates, key=lambda n: abs(n.line_start - marker.line_start))
                    nearest.marker_refs.append(marker.marker_id)
                    attached.append(nearest.node_id)
            marker_to_nodes[marker.marker_id] = attached

        return marker_to_nodes

    @staticmethod
    def _is_shared_infra_marker_type(marker_type: str) -> bool:
        return str(marker_type).strip().upper() in SHARED_INFRA_MARKER_TYPES

    @classmethod
    def _marker_expansion_allowed(cls, marker: Marker) -> bool:
        marker_type = str(getattr(marker, "marker_type", "")).strip().upper()
        if cls._is_shared_infra_marker_type(marker_type):
            return False
        return True

    @staticmethod
    def _marker_action_refs(marker: Marker) -> Set[str]:
        refs: Set[str] = set()
        primary = str(getattr(marker, "primary_action_id", "") or "").strip()
        if primary:
            refs.add(primary)
        for action_id in getattr(marker, "secondary_action_ids", []) or []:
            token = str(action_id or "").strip()
            if token:
                refs.add(token)
        for action_id in getattr(marker, "action_refs", []) or []:
            token = str(action_id or "").strip()
            if token:
                refs.add(token)
        return refs

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
    def _closure_depth_for_marker(marker: Marker, default_depth: int) -> int:
        marker_type = str(marker.marker_type).strip().upper()
        if not TempoSpatialReducer._marker_action_refs(marker):
            return 0
        if marker_type in {"CLOUD_HTTP_CALL", "CLOUD_OP", "STATE_WRITE"}:
            return 1
        if marker_type in {"BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT", "BLE_OP"}:
            return min(max(1, int(default_depth)), 1)
        if marker_type in {"ENTRY_SETUP", "ENTRY_UNLOAD", "ENTRY_REMOVE", "SUBSCRIBE", "UNSUBSCRIBE"}:
            return 1
        return max(1, int(default_depth))

    @staticmethod
    def _allowed_edge_types_for_marker(marker: Marker) -> Set[str]:
        marker_type = str(marker.marker_type).strip().upper()
        if marker_type in {
            "CLOUD_HTTP_CALL",
            "CLOUD_OP",
            "BLE_OP",
            "BLE_GATT_OP",
            "STATE_WRITE",
            "BLE_CONNECT",
            "BLE_DISCONNECT",
            "SUBSCRIBE",
            "UNSUBSCRIBE",
        }:
            return {"DATA_DEP", "EXCEPTION_DEP"}
        return {"DATA_DEP", "CONTROL_DEP", "LIFECYCLE_DEP", "EXCEPTION_DEP"}

    @staticmethod
    def _cfg_chain_limit_for_marker(marker_type: str) -> int:
        mt = str(marker_type).strip().upper()
        if mt in {
            "BLE_OP",
            "BLE_GATT_OP",
            "BLE_CONNECT",
            "BLE_DISCONNECT",
            "CLOUD_HTTP_CALL",
            "CLOUD_OP",
            "STATE_WRITE",
            "SUBSCRIBE",
            "UNSUBSCRIBE",
        }:
            return 1
        return 2

    def _expand_try_related_nodes(self, keep: Set[str], fn_nodes: List[GraphNode]) -> Set[str]:
        if not keep or not fn_nodes:
            return keep

        ordinal_map: Dict[str, GraphNode] = {
            self._node_ordinal(node.node_id): node
            for node in fn_nodes
        }
        fn_node_ids = {node.node_id for node in fn_nodes}
        kept_ordinals = {
            self._node_ordinal(node_id)
            for node_id in keep
            if node_id in fn_node_ids
        }
        try_roots: Set[str] = set()

        for ordinal in kept_ordinals:
            if not ordinal:
                continue
            cur = ordinal
            while cur:
                parent_node = ordinal_map.get(cur)
                if parent_node and parent_node.stmt_kind == "Try":
                    try_roots.add(cur)
                if "." not in cur:
                    break
                cur = cur.rsplit(".", 1)[0]

        if not try_roots:
            return keep

        for node in fn_nodes:
            ordinal = self._node_ordinal(node.node_id)
            if any(ordinal == root or ordinal.startswith(f"{root}.") for root in try_roots):
                keep.add(node.node_id)
        return keep

    def _temporal_keep(
        self,
        graph: ReducedGraph,
        markers: List[Marker],
        marker_to_nodes: Dict[str, List[str]],
        fn_index: Dict[Tuple[str, str], List[GraphNode]] | None = None,
        fn_starts: Dict[Tuple[str, str], List[int]] | None = None,
    ) -> Set[str]:
        keep: Set[str] = set()
        markers_by_fn: Dict[Tuple[str, str], List[Marker]] = {}
        for marker in markers:
            key = (marker.file_path, marker.function_name)
            markers_by_fn.setdefault(key, []).append(marker)

        if fn_index is None or fn_starts is None:
            fn_index, fn_starts = self._index_fn_nodes(graph)

        for (file_path, fn_name), fn_markers in markers_by_fn.items():
            fn_markers.sort(key=lambda m: m.line_start)
            key = (file_path, fn_name)
            fn_nodes = fn_index.get(key, [])
            fn_start_rows = fn_starts.get(key, [])
            if not fn_nodes or not fn_start_rows:
                continue


            for marker in fn_markers:
                keep.update(marker_to_nodes.get(marker.marker_id, []))

            for idx in range(len(fn_markers) - 1):
                left = fn_markers[idx].line_start
                right = fn_markers[idx + 1].line_start + self.temporal_slack_lines
                lo = bisect_left(fn_start_rows, left)
                hi = bisect_right(fn_start_rows, right)
                scan_lo = lo
                while scan_lo > 0 and fn_nodes[scan_lo - 1].line_end >= left:
                    scan_lo -= 1
                for node in fn_nodes[scan_lo:hi]:
                    if left <= node.line_start <= right:
                        keep.add(node.node_id)

            keep = self._expand_try_related_nodes(keep, fn_nodes)

        return keep

    def _spatial_keep(
        self,
        graph: ReducedGraph,
        markers: List[Marker],
        marker_to_nodes: Dict[str, List[str]],
        marker_strengths: Dict[str, str] | None = None,
        respect_binding_policy: bool = False,
    ) -> Set[str]:
        marker_by_id = {marker.marker_id: marker for marker in markers}
        strong_seed_map: Dict[str, List[str]] = {}
        non_strong_seed_map: Dict[str, List[str]] = {}
        grouped_allowed_types: Dict[str, Set[str]] = {}
        grouped_depths: Dict[str, int] = {}
        grouped_cfg_limits: Dict[str, int] = {}
        for marker_id, node_ids in marker_to_nodes.items():
            if not node_ids:
                continue
            marker = marker_by_id.get(marker_id)
            if marker is None:
                continue
            if respect_binding_policy and not self._marker_expansion_allowed(marker):
                continue
            strength = str(marker_strengths.get(marker_id, "")).strip().upper()
            depth_limit = self._closure_depth_for_marker(marker, self.spatial_depth) if respect_binding_policy else self.spatial_depth
            if depth_limit <= 0:
                continue
            grouped_allowed_types[marker_id] = self._allowed_edge_types_for_marker(marker)
            grouped_depths[marker_id] = depth_limit
            grouped_cfg_limits[marker_id] = self._cfg_chain_limit_for_marker(getattr(marker, "marker_type", ""))
            if strength == "STRONG":
                strong_seed_map[marker_id] = node_ids
            else:
                non_strong_seed_map[marker_id] = node_ids

        keep: Set[str] = set()
        if strong_seed_map:
            keep |= self._spatial_keep_with_policy(
                graph=graph,
                marker_to_nodes=strong_seed_map,
                allowed_edge_types_by_marker=grouped_allowed_types,
                depth_by_marker=grouped_depths,
                cfg_limit_by_marker=grouped_cfg_limits,
                cfg_back_depth=self.cfg_back_depth,
            )
        if non_strong_seed_map:
            keep |= self._spatial_keep_with_policy(
                graph=graph,
                marker_to_nodes=non_strong_seed_map,
                allowed_edge_types_by_marker=grouped_allowed_types,
                depth_by_marker=grouped_depths,
                cfg_limit_by_marker=grouped_cfg_limits,
                cfg_back_depth=0,
            )
        return keep

    @staticmethod
    def _spatial_keep_with_policy(
        graph: ReducedGraph,
        marker_to_nodes: Dict[str, List[str]],
        allowed_edge_types_by_marker: Dict[str, Set[str]],
        depth_by_marker: Dict[str, int],
        cfg_limit_by_marker: Dict[str, int],
        cfg_back_depth: int,
    ) -> Set[str]:
        backward_adj: Dict[str, List[GraphEdge]] = {}
        for edge in graph.edges:
            backward_adj.setdefault(edge.dst, []).append(edge)

        keep: Set[str] = set()
        for marker_id, seed_nodes in marker_to_nodes.items():
            allowed_edge_types = set(allowed_edge_types_by_marker.get(marker_id, {"DATA_DEP", "CONTROL_DEP", "EXCEPTION_DEP", "CFG_NEXT"}))
            if cfg_back_depth > 0:
                allowed_edge_types = set(allowed_edge_types) | {"CFG_NEXT"}
            depth = int(depth_by_marker.get(marker_id, 0))
            if depth <= 0:
                keep |= set(seed_nodes)
                continue
            frontier: Set[str] = set(seed_nodes)
            seen: Set[str] = set(seed_nodes)
            cfg_chain_counts: Dict[Tuple[str, str], int] = {}
            cur_depth = 0
            while frontier and cur_depth <= depth:
                next_frontier: Set[str] = set()
                for node_id in frontier:
                    keep.add(node_id)
                    for edge in backward_adj.get(node_id, []):
                        if edge.edge_type not in allowed_edge_types:
                            continue
                        if edge.edge_type in {"DATA_DEP", "CONTROL_DEP", "EXCEPTION_DEP", "LIFECYCLE_DEP"}:
                            pass
                        elif edge.edge_type == "CFG_NEXT":
                            if cur_depth >= cfg_back_depth:
                                continue
                            fn_name = str(graph.nodes.get(edge.src).function_name if graph.nodes.get(edge.src) else "")
                            if fn_name:
                                cfg_key = (marker_id, fn_name)
                                cfg_count = cfg_chain_counts.get(cfg_key, 0)
                                cfg_limit = max(0, int(cfg_limit_by_marker.get(marker_id, 2)))
                                if cfg_count >= cfg_limit:
                                    continue
                                cfg_chain_counts[cfg_key] = cfg_count + 1
                        else:
                            continue
                        if edge.src not in seen:
                            seen.add(edge.src)
                            next_frontier.add(edge.src)
                frontier = next_frontier
                cur_depth += 1

        return keep

    def _add_lifecycle_edges(
        self,
        graph: ReducedGraph,
        markers: List[Marker],
        marker_to_nodes: Dict[str, List[str]],
    ) -> None:
        edge_keys = {(edge.src, edge.dst, edge.edge_type) for edge in graph.edges}

        def add_lifecycle_edge(src: str, dst: str) -> None:
            key = (src, dst, "LIFECYCLE_DEP")
            if key in edge_keys or src == dst:
                return
            edge_keys.add(key)
            graph.edges.append(GraphEdge(src=src, dst=dst, edge_type="LIFECYCLE_DEP"))

        by_type: Dict[str, List[Marker]] = {}
        for marker in markers:
            by_type.setdefault(marker.marker_type, []).append(marker)

        marker_scope_keys: Dict[str, Set[str]] = {
            marker.marker_id: self._marker_scope_keys(marker, graph, marker_to_nodes)
            for marker in markers
        }
        marker_line_hint: Dict[str, int] = {
            marker.marker_id: self._marker_line_hint(marker, graph, marker_to_nodes)
            for marker in markers
        }

        marker_primary_node: Dict[str, str] = {}
        for marker in markers:
            primary = self._primary_marker_node(marker, graph, marker_to_nodes)
            if primary:
                marker_primary_node[marker.marker_id] = primary

        for template in self.profile.lifecycle_templates:
            params = template.get("params", {}) if isinstance(template.get("params", {}), dict) else {}
            pair_key = str(params.get("pair_key") or template.get("pair_key", "")).strip()
            required = template.get("requires")
            if required and len(required) == 2:
                left_type, right_type = required
                for left in by_type.get(left_type, []):
                    right = self._nearest_marker_match(
                        left=left,
                        right_candidates=by_type.get(right_type, []),
                        marker_scope_keys=marker_scope_keys,
                        marker_line_hint=marker_line_hint,
                        ordered=False,
                        pair_key=pair_key,
                    )
                    if right is None:
                        continue
                    src = marker_primary_node.get(left.marker_id)
                    dst = marker_primary_node.get(right.marker_id)
                    if src and dst:
                        add_lifecycle_edge(src, dst)

            order = template.get("requires_order")
            if order and len(order) == 2:
                left_type, right_type = order
                for left in by_type.get(left_type, []):
                    right = self._nearest_marker_match(
                        left=left,
                        right_candidates=by_type.get(right_type, []),
                        marker_scope_keys=marker_scope_keys,
                        marker_line_hint=marker_line_hint,
                        ordered=True,
                        pair_key=pair_key,
                    )
                    if right is None:
                        continue
                    if marker_line_hint[left.marker_id] > marker_line_hint[right.marker_id]:
                        continue
                    src = marker_primary_node.get(left.marker_id)
                    dst = marker_primary_node.get(right.marker_id)
                    if src and dst:
                        add_lifecycle_edge(src, dst)

    @staticmethod
    def _primary_marker_node(marker: Marker, graph: ReducedGraph, marker_to_nodes: Dict[str, List[str]]) -> str | None:
        node_ids = [node_id for node_id in marker_to_nodes.get(marker.marker_id, []) if node_id in graph.nodes]
        if not node_ids:
            return None
        ranked = sorted(
            node_ids,
            key=lambda node_id: (
                graph.nodes[node_id].line_start,
                graph.nodes[node_id].col_start,
                graph.nodes[node_id].line_end,
                graph.nodes[node_id].col_end,
                TempoSpatialReducer._node_ordinal(node_id),
                node_id,
            ),
        )
        return ranked[0]

    @staticmethod
    def _marker_line_hint(marker: Marker, graph: ReducedGraph, marker_to_nodes: Dict[str, List[str]]) -> int:
        node_lines = [graph.nodes[node_id].line_start for node_id in marker_to_nodes.get(marker.marker_id, []) if node_id in graph.nodes]
        return min(node_lines) if node_lines else marker.line_start

    @staticmethod
    def _name_scope_keys(name: str) -> Set[str]:
        lowered = name.lower()
        keys = {f"var:{lowered}"}
        if "unsub" in lowered or "subscribe" in lowered or "listener" in lowered or "handle" in lowered:
            keys.add(f"subscription_handle:{lowered}")
        if lowered in {"client", "session", "coordinator"} or lowered.endswith(("_client", "_session", "_coordinator")):
            keys.add(f"object:{lowered}")
        return keys

    def _marker_scope_keys(self, marker: Marker, graph: ReducedGraph, marker_to_nodes: Dict[str, List[str]]) -> Set[str]:
        keys: Set[str] = {f"file:{marker.file_path}", f"function:{marker.function_name}"}
        entity_pattern = re.compile(r"[a-z_]+\.[a-z0-9_]+")
        endpoint_pattern = re.compile(r"[a-z0-9_]+:[a-z0-9_.-]+", re.IGNORECASE)

        for node_id in marker_to_nodes.get(marker.marker_id, []):
            node = graph.nodes.get(node_id)
            if node is None:
                continue
            for name in node.defs | node.uses:
                keys |= self._name_scope_keys(name)

            raw = node.raw_repr.lower()
            for entity in entity_pattern.findall(raw):
                keys.add(f"entity:{entity}")
            for endpoint in endpoint_pattern.findall(raw):
                keys.add(f"target:{endpoint.lower()}")

        if marker.marker_type in {"SUBSCRIBE", "UNSUBSCRIBE"}:
            keys.add("class:subscription")
        if marker.marker_type in {"ENTRY_SETUP", "ENTRY_UNLOAD", "ENTRY_REMOVE"}:
            keys.add("class:lifecycle_entry")
        if marker.marker_type == "STATE_WRITE":
            keys.add("class:state_write")
        return keys

    @staticmethod
    def _pair_scoped_keys(keys: Set[str], pair_key: str) -> Set[str]:
        pair = str(pair_key).strip().lower()
        if not pair:
            return keys
        if pair in {"device_id", "endpoint", "host"}:
            scoped = {key for key in keys if key.startswith("target:")}
            return scoped or keys
        if pair in {"entity", "entity_id"}:
            scoped = {key for key in keys if key.startswith("entity:")}
            return scoped or keys
        if pair in {"subscription_handle", "handle"}:
            scoped = {key for key in keys if key.startswith("subscription_handle:") or key.startswith("var:")}
            return scoped or keys
        if pair in {"session", "client", "object"}:
            scoped = {key for key in keys if key.startswith("object:") or key.startswith("var:")}
            return scoped or keys
        return keys

    @staticmethod
    def _nearest_marker_match(
        left: Marker,
        right_candidates: List[Marker],
        marker_scope_keys: Dict[str, Set[str]],
        marker_line_hint: Dict[str, int],
        ordered: bool,
        pair_key: str = "",
    ) -> Marker | None:
        if not right_candidates:
            return None

        left_keys = TempoSpatialReducer._pair_scoped_keys(marker_scope_keys.get(left.marker_id, set()), pair_key)
        left_line = marker_line_hint.get(left.marker_id, left.line_start)
        ranked: List[Tuple[Tuple[int, int, int, int], Marker]] = []
        for right in right_candidates:
            if right.marker_id == left.marker_id:
                continue
            if right.file_path != left.file_path:
                continue

            right_line = marker_line_hint.get(right.marker_id, right.line_start)
            if ordered and right_line < left_line:
                continue

            right_keys = TempoSpatialReducer._pair_scoped_keys(marker_scope_keys.get(right.marker_id, set()), pair_key)
            overlap = len(left_keys & right_keys)
            same_function_penalty = 0 if left.function_name == right.function_name else 1
            direction_penalty = 0 if right_line >= left_line else 1
            distance = abs(right_line - left_line)
            rank = (-overlap, same_function_penalty, direction_penalty, distance)
            ranked.append((rank, right))

        if not ranked:
            return None
        ranked.sort(key=lambda item: item[0])
        return ranked[0][1]

    @staticmethod
    def _anchor_terms(target: OptimizationTarget | None) -> _AnchorTerms:
        if target is None:
            return _AnchorTerms(entities=set(), endpoints=set(), endpoint_prefixes=set(), macs=set(), uuids=set())

        anchors = target.target_anchors if isinstance(target.target_anchors, dict) else {}
        entities: Set[str] = set()
        endpoints: Set[str] = set()
        endpoint_prefixes: Set[str] = set()
        macs: Set[str] = set()
        uuids: Set[str] = set()

        for value in anchors.get("entities", []):
            token = str(value).strip().lower()
            if token and ENTITY_ID_RE.fullmatch(token):
                entities.add(token)

        for value in anchors.get("endpoints", []):
            token = str(value).strip().lower()
            if not token:
                continue
            if token.startswith(("http://", "https://")) or "/" in token:
                endpoint_prefixes.add(token)
            else:
                endpoints.add(token)

        for value in anchors.get("device_ids", []):
            token = str(value).strip().lower().replace("-", ":")
            if MAC_RE.fullmatch(token):
                macs.add(token)

        for value in anchors.get("characteristics", []):
            token = str(value).strip().lower()
            if UUID_RE.fullmatch(token):
                uuids.add(token)

        return _AnchorTerms(
            entities=entities,
            endpoints=endpoints,
            endpoint_prefixes=endpoint_prefixes,
            macs=macs,
            uuids=uuids,
        )

    @staticmethod
    def _lifecycle_required_markers(markers: List[Marker], templates: List[Dict[str, object]]) -> List[Marker]:
        def template_marker_types(template: Dict[str, object]) -> Set[str]:
            types: Set[str] = set()
            requires = template.get("requires")
            if isinstance(requires, list):
                types |= {str(item).strip().upper() for item in requires if str(item).strip()}
            requires_order = template.get("requires_order")
            if isinstance(requires_order, list):
                types |= {str(item).strip().upper() for item in requires_order if str(item).strip()}
            return types

        def is_semantic_required_template(template: Dict[str, object]) -> bool:
            if bool(template.get("semantic_required")):
                return True

            types = template_marker_types(template)
            if not types:
                return False

            if "ENTRY_UNLOAD" in types or "ENTRY_REMOVE" in types:
                return True
            if "UNSUBSCRIBE" in types:
                return True
            if {"SUBSCRIBE", "UNSUBSCRIBE"}.issubset(types):
                return True
            if {"COORD_REFRESH", "STATE_WRITE"}.issubset(types):
                return True

            template_id = str(template.get("template_id", "")).strip().lower()
            if any(
                token in template_id
                for token in {
                    "unsubscribe",
                    "unload",
                    "remove",
                    "teardown",
                    "cleanup",
                    "first_refresh",
                    "refresh_before_state_write",
                }
            ):
                return True
            return False

        required_types: Set[str] = set()
        for template in templates:
            if not is_semantic_required_template(template):
                continue
            required_types |= template_marker_types(template)
        if not required_types:
            return []
        return [marker for marker in markers if marker.marker_type.upper() in required_types]

    @staticmethod
    def _target_seed_markers(markers: List[Marker], target: OptimizationTarget | None) -> List[Marker]:
        if target is None:
            return markers
        abstract_hints = {"BLE_OP", "CLOUD_OP"}
        anchor_ops = {
            op.upper()
            for op in target.target_anchors.get("anchor_ops", [])
            if str(op).strip()
        }
        specific_anchor_ops = {op for op in anchor_ops if op not in abstract_hints}

        def has_explicit_anchor_signal(marker: Marker) -> bool:
            evidence = {str(item).strip() for item in getattr(marker, "evidence", []) if str(item).strip()}
            return "target_anchor_seed" in evidence or "target_anchor_op" in evidence

        def action_refs(marker: Marker) -> Set[str]:
            return TempoSpatialReducer._marker_action_refs(marker)

        def has_specific_peer(marker: Marker) -> bool:
            marker_type = str(marker.marker_type).strip().upper()
            if marker_type == "CLOUD_OP":
                specific_types = {
                    "CLOUD_HTTP_CALL",
                    "CLOUD_STATUS_CALL",
                    "CLOUD_429_CHECK",
                    "CLOUD_BACKOFF_SLEEP",
                    "CLOUD_TOKEN_REFRESH",
                } & specific_anchor_ops
            elif marker_type == "BLE_OP":
                specific_types = {
                    "BLE_GATT_OP",
                    "BLE_CONNECT",
                    "BLE_DISCONNECT",
                } & specific_anchor_ops
            else:
                return False
            if not specific_types:
                return False
            marker_refs = action_refs(marker)
            marker_file = str(getattr(marker, "file_path", "")).strip()
            for peer in markers:
                if peer.marker_id == marker.marker_id:
                    continue
                if str(getattr(peer, "marker_type", "")).strip().upper() not in specific_types:
                    continue
                if str(getattr(peer, "file_path", "")).strip() != marker_file:
                    continue
                peer_refs = action_refs(peer)
                if (
                    marker_refs
                    and marker_refs & peer_refs
                    and not (
                        TempoSpatialReducer._marker_supports_generalized_secondary_binding(marker)
                        and not marker_refs <= peer_refs
                    )
                ):
                    return True
            return False

        selected = [
            marker
            for marker in markers
            if has_explicit_anchor_signal(marker)
            or str(marker.marker_type).strip().upper() in specific_anchor_ops
            or (
                str(marker.marker_type).strip().upper() in abstract_hints
                and str(marker.marker_type).strip().upper() in anchor_ops
                and action_refs(marker)
                and not has_specific_peer(marker)
            )
        ]
        return selected or markers

    def _lifecycle_spatial_depth_for_marker(self, marker: Marker) -> int:
        if self.lifecycle_spatial_depth is not None:
            return self.lifecycle_spatial_depth

        deep_types = {
            "UNSUBSCRIBE",
            "ENTRY_UNLOAD",
            "ENTRY_REMOVE",
            "LOCK_RELEASE",
            "DISCONNECT",
            "BLE_DISCONNECT",
        }
        marker_type = str(marker.marker_type).strip().upper()
        return 2 if marker_type in deep_types else 1

    @staticmethod
    def _anchor_keep_nodes(graph: ReducedGraph, target: OptimizationTarget | None) -> Set[str]:
        terms = TempoSpatialReducer._anchor_terms(target)
        if not (terms.entities or terms.endpoints or terms.endpoint_prefixes or terms.macs or terms.uuids):
            return set()
        keep: Set[str] = set()
        for node in graph.nodes.values():
            text = f"{node.function_name} {node.raw_repr}".lower().replace("-", ":")

            entities = {value.lower() for value in ENTITY_ID_RE.findall(text)}
            endpoints = {value.lower() for value in ENDPOINT_RE.findall(text)}
            macs = {value.lower().replace("-", ":") for value in MAC_RE.findall(text)}
            uuids = {value.lower() for value in UUID_RE.findall(text)}

            matched = bool(
                (terms.entities and entities & terms.entities)
                or (terms.endpoints and endpoints & terms.endpoints)
                or (terms.macs and macs & terms.macs)
                or (terms.uuids and uuids & terms.uuids)
            )
            if not matched and terms.endpoint_prefixes:
                matched = any(prefix in text for prefix in terms.endpoint_prefixes)
            if matched:
                keep.add(node.node_id)
        return keep

    def reduce(
        self,
        path: str | Path,
        markers: List[Marker],
        optimization_target: OptimizationTarget | None = None,
    ) -> ReductionResult:
        graph, _ = self._build_full_graph(path)
        fn_index, fn_starts = self._index_fn_nodes(graph)
        marker_to_nodes = self._attach_marker_refs(graph, markers, fn_index=fn_index, fn_starts=fn_starts)

        target_seed_markers = self._target_seed_markers(markers, optimization_target)
        lifecycle_markers = self._lifecycle_required_markers(markers, self.profile.lifecycle_templates)
        expandable_target_seed_markers = [marker for marker in target_seed_markers if self._marker_expansion_allowed(marker)]


        temporal_nodes = self._temporal_keep(
            graph,
            expandable_target_seed_markers,
            marker_to_nodes,
            fn_index=fn_index,
            fn_starts=fn_starts,
        )
        spatial_nodes = self._spatial_keep(
            graph,
            expandable_target_seed_markers,
            {m.marker_id: marker_to_nodes.get(m.marker_id, []) for m in expandable_target_seed_markers},
            marker_strengths={m.marker_id: m.strength for m in expandable_target_seed_markers},
            respect_binding_policy=optimization_target is not None,
        )
        lifecycle_primary_seed_map_by_depth: Dict[int, Dict[str, List[str]]] = {}
        lifecycle_nodes: Set[str] = set()
        for marker in lifecycle_markers:
            primary = self._primary_marker_node(marker, graph, marker_to_nodes)
            if primary is None:
                continue
            lifecycle_nodes.add(primary)
            if not self._marker_expansion_allowed(marker):
                continue
            depth = self._lifecycle_spatial_depth_for_marker(marker)
            lifecycle_primary_seed_map_by_depth.setdefault(depth, {})[marker.marker_id] = [primary]

        lifecycle_spatial_nodes: Set[str] = set()
        for lifecycle_depth in sorted(lifecycle_primary_seed_map_by_depth):
            if lifecycle_depth <= 0:
                continue
            lifecycle_spatial_nodes |= self._spatial_keep_with_policy(
                graph=graph,
                marker_to_nodes=lifecycle_primary_seed_map_by_depth[lifecycle_depth],
                allowed_edge_types_by_marker={
                    marker_id: {"DATA_DEP", "EXCEPTION_DEP"}
                    for marker_id in lifecycle_primary_seed_map_by_depth[lifecycle_depth]
                },
                depth_by_marker={
                    marker_id: lifecycle_depth
                    for marker_id in lifecycle_primary_seed_map_by_depth[lifecycle_depth]
                },
                cfg_limit_by_marker={
                    marker_id: 0
                    for marker_id in lifecycle_primary_seed_map_by_depth[lifecycle_depth]
                },
                cfg_back_depth=0,
            )
        anchor_nodes = self._anchor_keep_nodes(graph, optimization_target)
        kept = temporal_nodes | spatial_nodes | anchor_nodes | lifecycle_nodes | lifecycle_spatial_nodes

        self._add_lifecycle_edges(graph, markers, marker_to_nodes)

        reduced_nodes = {nid: node for nid, node in graph.nodes.items() if nid in kept}
        reduced_edges = [
            edge
            for edge in graph.edges
            if edge.src in reduced_nodes and edge.dst in reduced_nodes
        ]
        reduced_mapping = {nid: graph.mapping[nid] for nid in reduced_nodes}
        reduced_marker_to_nodes = {
            marker_id: [node_id for node_id in node_ids if node_id in reduced_nodes]
            for marker_id, node_ids in marker_to_nodes.items()
        }

        reduced = ReducedGraph(nodes=reduced_nodes, edges=reduced_edges, mapping=reduced_mapping)
        return ReductionResult(reduced_graph=reduced, marker_to_nodes=reduced_marker_to_nodes, kept_node_ids=kept)
