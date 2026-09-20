from __future__ import annotations

from urllib.parse import urlparse
from dataclasses import dataclass, field
import re
from typing import Dict, List, Set, Tuple

from dsl.contracts import (
    DependencyEdge,
    EdgeKind,
    HAPProfile,
    MSSU,
    OptimizationTarget,
    RuleStatus,
    SoftConstraint,
    SoftConstraintKind,
    TypedDAG,
)


@dataclass
class DAGBuildDiagnostics:
    warnings: List[str] = field(default_factory=list)
    removed_hard_edges: List[Tuple[str, str]] = field(default_factory=list)
    _warning_keys: Set[str] = field(default_factory=set, repr=False)
    _removed_edge_keys: Set[Tuple[str, str]] = field(default_factory=set, repr=False)

    def warn(self, message: str, *, key: str | None = None) -> None:
        if key:
            if key in self._warning_keys:
                return
            self._warning_keys.add(key)
        self.warnings.append(message)

    def record_removed_edge(self, src: str, dst: str) -> None:
        edge = (src, dst)
        if edge in self._removed_edge_keys:
            return
        self._removed_edge_keys.add(edge)
        self.removed_hard_edges.append(edge)


class TypedDAGBuilder:
    def __init__(self, profile: HAPProfile) -> None:
        self.profile = profile

    _HINT_ALIASES: Dict[str, Set[str]] = {
        "ble_gatt_op": {"ble_gatt_op", "ble_op"},
        "ble_op": {"ble_op", "ble_gatt_op"},
        "ble_disconnect": {"ble_disconnect", "disconnect"},
        "disconnect": {"disconnect", "ble_disconnect"},
        "cloud_http_call": {"cloud_http_call", "cloud_op"},
        "cloud_op": {"cloud_op", "cloud_http_call"},
        "coord_refresh": {"coord_refresh", "coord_first_refresh"},
        "coord_first_refresh": {"coord_first_refresh", "coord_refresh"},
        "state_write": {"state_write", "ha_state_write"},
        "ha_state_write": {"ha_state_write", "state_write"},
    }
    _HARD_EDGE_ALLOWLIST: Set[Tuple[str, str]] = {
        ("PREPARE", "ACT"),
        ("CHECK", "ACT"),
        ("ACT", "UPDATE"),
        ("SYNC", "UPDATE"),
        ("INIT", "SYNC"),
        ("PREPARE", "CLEANUP"),
    }

    @staticmethod
    def _normalize_template_kind(value: str) -> str | None:
        kind = str(value).strip().upper()
        valid = {item.value for item in EdgeKind}
        if kind in valid:
            return kind
        if kind in {"DATA_DEP", "HARD_DATA"}:
            return EdgeKind.HARD_DATA.value
        if kind in {"CONTROL_DEP", "HARD_CONTROL"}:
            return EdgeKind.HARD_CONTROL.value
        if kind in {"LIFECYCLE_DEP", "HARD_LIFECYCLE"}:
            return EdgeKind.HARD_LIFECYCLE.value
        return None

    @staticmethod
    def _normalize_hint(value: str) -> str:
        hint = str(value).strip().lower()
        hint = hint.replace("-", "_").replace(" ", "_")
        return hint

    @staticmethod
    def _mssu_effect_tokens(mssu: MSSU) -> Set[str]:
        tokens: Set[str] = set()
        for effect in mssu.side_effect_sig:
            normalized = TypedDAGBuilder._normalize_hint(effect)
            if not normalized:
                continue
            tokens.add(normalized)
            if normalized.endswith("_op"):
                tokens.add(normalized[:-3])
            if normalized == "ble_gatt_op":
                tokens.add("ble_op")
            if normalized == "cloud_http_call":
                tokens.add("cloud_op")
            if normalized == "state_write":
                tokens.add("ha_state_write")
        return tokens

    @staticmethod
    def _mssu_matches_hint(mssu: MSSU, marker_hint: str) -> bool:
        hint = TypedDAGBuilder._normalize_hint(marker_hint)
        if not hint:
            return False
        tokens = TypedDAGBuilder._mssu_effect_tokens(mssu)
        return any(alias in tokens for alias in TypedDAGBuilder._HINT_ALIASES.get(hint, {hint}))

    @classmethod
    def _primary_effect_family(cls, mssu: MSSU) -> str:
        tokens = cls._mssu_effect_tokens(mssu)
        mssu_type = str(getattr(mssu, "mssu_type", "")).strip().upper()
        if mssu_type == "INIT" and "entry_setup" in tokens:
            return "entry_setup"
        if mssu_type == "CLEANUP":
            if "unsubscribe" in tokens:
                return "unsubscribe"
            if "entry_unload" in tokens:
                return "entry_unload"
            if "disconnect" in tokens or "ble_disconnect" in tokens:
                return "ble_disconnect"
        if mssu_type == "PREPARE":
            if "subscribe" in tokens:
                return "subscribe"
            if "ble_connect" in tokens:
                return "ble_connect"
        for family in (
            "ble_gatt_op",
            "ble_op",
            "cloud_http_call",
            "cloud_op",
            "state_write",
            "coord_first_refresh",
            "coord_refresh",
            "entry_remove",
            "entry_setup",
            "entry_unload",
            "subscribe",
            "unsubscribe",
            "ble_connect",
            "ble_disconnect",
        ):
            aliases = cls._HINT_ALIASES.get(family, {family})
            if aliases & tokens:
                return family
        return next(iter(sorted(tokens)), "")

    @classmethod
    def _hint_exact_match(cls, mssu: MSSU, marker_hint: str) -> bool:
        hint = cls._normalize_hint(marker_hint)
        if not hint:
            return False
        family = cls._primary_effect_family(mssu)
        if not family:
            return False
        aliases = cls._HINT_ALIASES.get(hint, {hint})
        return family in aliases

    @classmethod
    def _is_soft_only_mssu(cls, mssu: MSSU) -> bool:
        if bool(getattr(mssu, "is_shared_infra", False)):
            return True
        action_scope = cls._effective_action_refs(mssu)
        mssu_type = str(mssu.mssu_type).strip().upper()
        if mssu_type in {"INIT", "CLEANUP"} and not action_scope:
            return True
        return mssu_type == "UPDATE" and "state_write" in cls._mssu_effect_tokens(mssu)

    @classmethod
    def _allowed_hard_edge_pair(cls, src_mssu: MSSU, dst_mssu: MSSU) -> bool:
        pair = (str(src_mssu.mssu_type).strip().upper(), str(dst_mssu.mssu_type).strip().upper())
        return pair in cls._HARD_EDGE_ALLOWLIST

    @staticmethod
    def _strict_data_overlap(src_mssu: MSSU, dst_mssu: MSSU) -> Set[str]:
        overlap = {str(item).strip() for item in set(src_mssu.outputs) & set(dst_mssu.inputs) if str(item).strip()}
        noisy_tokens = {"self", "hass", "entry", "coordinator", "entity_id"}
        return {token for token in overlap if token.lower() not in noisy_tokens}

    @staticmethod
    def _canonical_rule_family(rule_id: str) -> str:
        return re.sub(r":part\d+$", "", str(rule_id).strip())

    @staticmethod
    def _soft_constraint_reason_rank(constraint: SoftConstraint) -> Tuple[int, str]:
        reason = str(constraint.params.get("reason", "")).lower()
        if reason == "cycle_break":
            return (3, reason)
        if reason.startswith("vdev_dep:"):
            return (2, reason)
        if reason.startswith("template:"):
            return (1, reason)
        if reason.startswith("candidate:"):
            return (0, reason)
        return (0, reason)

    @staticmethod
    def _effective_action_refs(mssu: MSSU) -> List[str]:
        refs = {
            str(action_id).strip()
            for action_id in getattr(mssu, "action_refs", [])
            if action_id is not None and str(action_id).strip()
        }
        raw_primary = getattr(mssu, "primary_action_ref", "")
        primary = "" if raw_primary is None else str(raw_primary).strip()
        if primary:
            refs.add(primary)
        refs.update(
            str(action_id).strip()
            for action_id in getattr(mssu, "secondary_action_refs", [])
            if action_id is not None and str(action_id).strip()
        )
        return sorted(refs)

    @staticmethod
    def _mssu_primary_action(mssu: MSSU) -> str:
        raw_primary = getattr(mssu, "primary_action_ref", "")
        primary = "" if raw_primary is None else str(raw_primary).strip()
        if primary:
            return primary
        refs = [
            str(action_id).strip()
            for action_id in getattr(mssu, "action_refs", [])
            if action_id is not None and str(action_id).strip()
        ]
        return refs[0] if len(refs) == 1 else ""

    @classmethod
    def _same_action_scope(cls, src_mssu: MSSU, dst_mssu: MSSU) -> bool:
        src_scope = set(cls._effective_action_refs(src_mssu))
        dst_scope = set(cls._effective_action_refs(dst_mssu))
        return bool(src_scope and dst_scope and src_scope & dst_scope)

    @staticmethod
    def _action_row(action_id: str, action_index: Dict[str, Dict[str, object]]) -> Dict[str, object] | None:
        return action_index.get(str(action_id).strip())

    @staticmethod
    def _action_is_writeback(action: Dict[str, object] | None) -> bool:
        if not isinstance(action, dict):
            return False
        protocol = str(action.get("protocol", "")).strip().upper()
        target_kind = str(action.get("target_kind", "")).strip().lower()
        return protocol == "HA" or target_kind == "ha_entity"

    @staticmethod
    def _action_is_aggregate_sink(action: Dict[str, object] | None) -> bool:
        if not isinstance(action, dict):
            return False
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        entity = str(target.get("entity_id") or target.get("id") or "").lower()
        return "overall" in entity or "aggregate" in entity

    @staticmethod
    def _mssu_type_priority(mssu: MSSU) -> int:
        priorities = {
            "ACT": 0,
            "UPDATE": 1,
            "CONFIRM": 2,
            "SYNC": 3,
            "PREPARE": 4,
            "CHECK": 5,
            "CLEANUP": 6,
            "FALLBACK": 7,
        }
        return priorities.get(str(mssu.mssu_type).strip().upper(), 99)

    @staticmethod
    def _generic_io_symbol(name: str) -> bool:
        token = str(name).strip().lower()
        if not token:
            return True
        generic = {
            "self",
            "cls",
            "hass",
            "entry",
            "data",
            "value",
            "result",
            "manager",
            "coordinator",
            "device",
            "_device",
            "client",
            "session",
            "api",
            "kwargs",
            "args",
            "position",
            "speed",
        }
        return token in generic or token.startswith("_attr_")

    @classmethod
    def _allow_cross_action_hard_data(
        cls,
        src_mssu: MSSU,
        dst_mssu: MSSU,
        symbol: str | None = None,
    ) -> bool:
        if symbol and cls._generic_io_symbol(symbol):
            return False
        src_actions = cls._effective_action_refs(src_mssu)
        dst_actions = cls._effective_action_refs(dst_mssu)
        if not src_actions or not dst_actions or cls._same_action_scope(src_mssu, dst_mssu):
            return True

        if bool(getattr(src_mssu, "is_aggregate_sink", False)) and not bool(getattr(dst_mssu, "is_aggregate_sink", False)):
            return False
        if bool(getattr(dst_mssu, "is_aggregate_sink", False)):
            return True
        src_lane = str(getattr(src_mssu, "lane_tag", "")).strip()
        dst_lane = str(getattr(dst_mssu, "lane_tag", "")).strip()
        if not src_lane or not dst_lane or src_lane != dst_lane:
            return False

        src_resource = str(getattr(src_mssu, "resource_instance_tag", "")).strip()
        dst_resource = str(getattr(dst_mssu, "resource_instance_tag", "")).strip()
        if src_resource and dst_resource:
            return src_resource == dst_resource
        if src_resource or dst_resource:
            return False

        return bool(getattr(src_mssu, "is_shared_infra", False)) and bool(getattr(dst_mssu, "is_shared_infra", False))

    @classmethod
    def _allow_template_hard_edge(cls, src_mssu: MSSU, dst_mssu: MSSU) -> bool:
        src_tokens = cls._mssu_effect_tokens(src_mssu)
        dst_tokens = cls._mssu_effect_tokens(dst_mssu)
        if "entry_setup" in src_tokens and "entry_unload" in dst_tokens:
            if not cls._same_action_scope(src_mssu, dst_mssu):
                return False
        src_actions = cls._effective_action_refs(src_mssu)
        dst_actions = cls._effective_action_refs(dst_mssu)
        if not src_actions or not dst_actions or cls._same_action_scope(src_mssu, dst_mssu):
            return True
        if bool(getattr(dst_mssu, "is_aggregate_sink", False)):
            return True
        src_lane = str(getattr(src_mssu, "lane_tag", "")).strip()
        dst_lane = str(getattr(dst_mssu, "lane_tag", "")).strip()
        if not src_lane or not dst_lane or src_lane != dst_lane:
            return False
        src_resource = str(getattr(src_mssu, "resource_instance_tag", "")).strip()
        dst_resource = str(getattr(dst_mssu, "resource_instance_tag", "")).strip()
        if src_resource and dst_resource and src_resource != dst_resource:
            return False
        if src_resource or dst_resource:
            return src_resource == dst_resource
        return bool(getattr(src_mssu, "is_shared_infra", False)) and bool(getattr(dst_mssu, "is_shared_infra", False))

    @classmethod
    def _template_pair_compatible(
        cls,
        src_mssu: MSSU,
        dst_mssu: MSSU,
        src_hint: str,
        dst_hint: str,
        *,
        allow_missing_resource_cleanup_pair: bool = False,
    ) -> bool:
        src_hint_n = cls._normalize_hint(src_hint)
        dst_hint_n = cls._normalize_hint(dst_hint)
        src_tokens = cls._mssu_effect_tokens(src_mssu)
        dst_tokens = cls._mssu_effect_tokens(dst_mssu)

        if "subscribe" in cls._HINT_ALIASES.get(src_hint_n, {src_hint_n}):
            if "subscribe" not in src_tokens:
                return False
            if str(src_mssu.mssu_type).strip().upper() != "PREPARE":
                return False
        if "unsubscribe" in cls._HINT_ALIASES.get(src_hint_n, {src_hint_n}):
            if "unsubscribe" not in src_tokens:
                return False
            if str(src_mssu.mssu_type).strip().upper() != "CLEANUP":
                return False
            src_resource = str(getattr(src_mssu, "resource_instance_tag", "") or "").strip()
            dst_resource = str(getattr(dst_mssu, "resource_instance_tag", "") or "").strip()
            if dst_resource:
                if not src_resource or src_resource != dst_resource:
                    return False
            else:
                same_action = cls._same_action_scope(src_mssu, dst_mssu)
                same_lane = str(getattr(src_mssu, "lane_tag", "") or "").strip() and str(getattr(src_mssu, "lane_tag", "") or "").strip() == str(getattr(dst_mssu, "lane_tag", "") or "").strip()
                if not same_action and not same_lane:
                    return False
        if "unsubscribe" in cls._HINT_ALIASES.get(dst_hint_n, {dst_hint_n}):
            if cls._primary_effect_family(dst_mssu) != "unsubscribe":
                return False
        if src_hint_n == "subscribe" and dst_hint_n == "unsubscribe":
            src_resource = str(getattr(src_mssu, "resource_instance_tag", "") or "").strip()
            dst_resource = str(getattr(dst_mssu, "resource_instance_tag", "") or "").strip()
            if not src_resource:
                return False
            if dst_resource:
                if src_resource != dst_resource:
                    return False
            else:
                if not allow_missing_resource_cleanup_pair:
                    return False
                if str(dst_mssu.mssu_type).strip().upper() != "CLEANUP":
                    return False
                if not bool(getattr(dst_mssu, "is_shared_infra", False)):
                    return False

        if src_hint_n == "entry_setup" and dst_hint_n == "entry_unload":
            if not cls._same_action_scope(src_mssu, dst_mssu):
                return False

        return True

    @classmethod
    def _allow_missing_resource_cleanup_pair(
        cls,
        src_mssu: MSSU,
        dst_candidates: List[MSSU],
        src_hint: str,
        dst_hint: str,
    ) -> bool:
        if cls._normalize_hint(src_hint) != "subscribe" or cls._normalize_hint(dst_hint) != "unsubscribe":
            return False
        if cls._primary_effect_family(src_mssu) != "subscribe":
            return False
        if str(getattr(src_mssu, "mssu_type", "")).strip().upper() != "PREPARE":
            return False
        src_resource = str(getattr(src_mssu, "resource_instance_tag", "") or "").strip()
        if not src_resource:
            return False

        saw_resourceful_cleanup = False
        saw_resource_missing_cleanup = False
        for dst_mssu in dst_candidates:
            if cls._primary_effect_family(dst_mssu) != "unsubscribe":
                continue
            if str(getattr(dst_mssu, "mssu_type", "")).strip().upper() != "CLEANUP":
                continue
            dst_resource = str(getattr(dst_mssu, "resource_instance_tag", "") or "").strip()
            if dst_resource:
                saw_resourceful_cleanup = True
                if dst_resource == src_resource:
                    return False
            elif bool(getattr(dst_mssu, "is_shared_infra", False)):
                saw_resource_missing_cleanup = True
        return saw_resource_missing_cleanup and not saw_resourceful_cleanup

    def _hard_edge_from_candidate(self, src: str, dst: str, edge_type: str) -> DependencyEdge | None:
        if edge_type == "DATA_DEP":
            return DependencyEdge(
                src_mssu=src,
                dst_mssu=dst,
                kind=EdgeKind.HARD_DATA.value,
                justification=[f"candidate:{edge_type}"],
                guardable=False,
            )
        return None

    @staticmethod
    def _soft_order_from_candidate(src: str, dst: str, edge_type: str) -> SoftConstraint:
        return SoftConstraint(
            kind=SoftConstraintKind.SOFT_ORDER.value,
            scope=[src, dst],
            params={"reason": f"candidate:{edge_type}"},
            guard="true",
            fallback="preserve_action_order",
        )

    def _is_semantic_lifecycle_candidate(self, src_mssu: MSSU, dst_mssu: MSSU) -> bool:
        src_tokens = self._mssu_effect_tokens(src_mssu)
        dst_tokens = self._mssu_effect_tokens(dst_mssu)
        if dst_mssu.mssu_type == "CLEANUP":
            return True
        cleanup_tokens = {
            "unsubscribe",
            "disconnect",
            "ble_disconnect",
            "close",
            "cleanup",
        }
        pairing_tokens = {
            "subscribe",
            "dispatcher_connect",
            "ble_connect",
            "connect",
        }
        if dst_tokens & cleanup_tokens and src_tokens & pairing_tokens:
            return True
        if {"coord_refresh", "coord_first_refresh"} & src_tokens and "state_write" in dst_tokens:
            return True
        return False

    def _edge_is_semantic_lifecycle(self, edge: DependencyEdge, nodes: Dict[str, MSSU]) -> bool:
        if edge.kind != EdgeKind.HARD_LIFECYCLE.value:
            return False
        if any(item.startswith("vdev_dep:") or item.startswith("io:") for item in edge.justification):
            return True

        pair_key = ""
        has_rule_template = False
        for item in edge.justification:
            text = str(item)
            if text.startswith("rule_template:"):
                has_rule_template = True
            elif text.startswith("pair_key:"):
                pair_key = text.split(":", 1)[1].strip().lower()
        if has_rule_template and pair_key in {"device_id", "endpoint", "host"}:
            return True

        dst_mssu = nodes.get(edge.dst_mssu)
        if dst_mssu is None:
            return False
        dst_tokens = self._mssu_effect_tokens(dst_mssu)
        if dst_mssu.mssu_type == "CLEANUP":
            return True
        if dst_tokens & {"unsubscribe", "disconnect", "ble_disconnect", "close", "cleanup"}:
            return True
        return False

    def _edge_removal_rank(self, nodes: Dict[str, MSSU], edge: DependencyEdge) -> Tuple[int, int, int, str, str]:
        justifications = [str(item) for item in edge.justification]
        is_candidate = any("candidate:" in item for item in justifications)
        is_template = any("rule_template:" in item for item in justifications)
        is_io_or_vdev = any(item.startswith("io:") or item.startswith("vdev_dep:") for item in justifications)
        is_semantic_lifecycle = self._edge_is_semantic_lifecycle(edge, nodes)
        protected = 1 if is_io_or_vdev or is_semantic_lifecycle or edge.kind == EdgeKind.HARD_DATA.value else 0
        kind_rank = {
            EdgeKind.HARD_CONTROL.value: 0,
            EdgeKind.HARD_LIFECYCLE.value: 1,
            EdgeKind.HARD_DATA.value: 2,
        }.get(edge.kind, 3)
        source_rank = 0 if is_candidate else 1 if is_template else 2
        return (protected, kind_rank, source_rank, edge.src_mssu, edge.dst_mssu)

    def _soft_order_from_template(self, src: str, dst: str, rule_id: str, tpl_idx: int, reason: str) -> SoftConstraint:
        return SoftConstraint(
            kind=SoftConstraintKind.SOFT_ORDER.value,
            scope=[src, dst],
            params={"reason": f"template:{rule_id}:{tpl_idx}:{reason}"},
            guard="true",
            fallback="preserve_action_order",
        )

    def _has_real_scope_tokens(self, mssu: MSSU, pair_key: str, action_index: Dict[str, Dict[str, object]]) -> bool:
        if not pair_key:
            return True
        tokens = self._mssu_scope_tokens(mssu, pair_key, action_index)
        return tokens != {"__nearest__"}

    def _inject_rule_template_hard_edges(
        self,
        mssus: List[MSSU],
        hard_edges: List[DependencyEdge],
        soft_edges: List[SoftConstraint],
        diagnostics: DAGBuildDiagnostics,
        optimization_target: OptimizationTarget | None,
    ) -> None:
        max_edges_per_template = 64
        action_index: Dict[str, Dict[str, object]] = {}
        action_rank: Dict[str, int] = {}
        if optimization_target is not None:
            for idx, action in enumerate(optimization_target.vdev_actions):
                action_id = str(action.get("action_id", "")).strip()
                if action_id:
                    action_index[action_id] = action
                    action_rank[action_id] = idx

        for rule in self.profile.rules:
            if rule.status == RuleStatus.DISABLED.value:
                continue
            rule_family = self._canonical_rule_family(rule.rule_id)
            for tpl_idx, tpl in enumerate(rule.hard_edge_templates):
                src_hint = str(tpl.get("src", "")).strip()
                dst_hint = str(tpl.get("dst", "")).strip()
                if not src_hint or not dst_hint:
                    continue
                kind = self._normalize_template_kind(str(tpl.get("kind", EdgeKind.HARD_CONTROL.value)))
                if kind is None:
                    diagnostics.warn(
                        f"Rule template kind unsupported for {rule.rule_id}[{tpl_idx}]",
                        key=f"unsupported-kind:{rule_family}:{tpl_idx}:{src_hint}:{dst_hint}",
                    )
                    continue

                src_candidates = [mssu for mssu in mssus if self._mssu_matches_hint(mssu, src_hint)]
                dst_candidates = [mssu for mssu in mssus if self._mssu_matches_hint(mssu, dst_hint)]
                if not src_candidates or not dst_candidates:
                    continue
                tpl_params = tpl.get("params", {}) if isinstance(tpl.get("params", {}), dict) else {}
                pair_key = str(tpl_params.get("pair_key") or tpl.get("pair_key", "")).strip()
                if not pair_key and (len(src_candidates) > 8 or len(dst_candidates) > 8):
                    diagnostics.warn(
                        f"Rule template widened to soft order: {rule.rule_id}[{tpl_idx}] "
                        f"src_candidates={len(src_candidates)} dst_candidates={len(dst_candidates)}",
                        key=f"wide-template:{rule_family}:{tpl_idx}:{src_hint}:{dst_hint}",
                    )
                    for src_mssu in src_candidates[:8]:
                        best_dst = self._pick_nearest_dst(
                            src_mssu=src_mssu,
                            dst_candidates=dst_candidates[:8],
                            src_hint=src_hint,
                            dst_hint=dst_hint,
                            pair_key="",
                            action_index=action_index,
                            action_rank=action_rank,
                        )
                        if best_dst is None or src_mssu.mssu_id == best_dst.mssu_id:
                            continue
                        soft_edges.append(
                            self._soft_order_from_template(
                                src=src_mssu.mssu_id,
                                dst=best_dst.mssu_id,
                                rule_id=rule.rule_id,
                                tpl_idx=tpl_idx,
                                reason="wide_template_scope",
                            )
                        )
                    continue

                injected = 0
                for src_mssu in src_candidates:
                    if pair_key and not self._has_real_scope_tokens(src_mssu, pair_key, action_index):
                        diagnostics.warn(
                            f"Rule template skipped hard bind: {rule.rule_id}[{tpl_idx}] no scope tokens for {src_mssu.mssu_id}",
                            key=f"missing-scope:{rule_family}:{tpl_idx}:{src_hint}:{dst_hint}:{pair_key}",
                        )
                        best_dst = self._pick_nearest_dst(
                            src_mssu=src_mssu,
                            dst_candidates=dst_candidates,
                            src_hint=src_hint,
                            dst_hint=dst_hint,
                            pair_key="",
                            action_index=action_index,
                            action_rank=action_rank,
                        )
                        if best_dst is not None and src_mssu.mssu_id != best_dst.mssu_id:
                            soft_edges.append(
                                self._soft_order_from_template(
                                    src=src_mssu.mssu_id,
                                    dst=best_dst.mssu_id,
                                    rule_id=rule.rule_id,
                                    tpl_idx=tpl_idx,
                                    reason="missing_scope_tokens",
                                )
                            )
                        continue
                    scoped_dst_candidates = dst_candidates
                    if pair_key:
                        scoped_dst_candidates = [
                            mssu for mssu in dst_candidates if self._has_real_scope_tokens(mssu, pair_key, action_index)
                        ]
                        if not scoped_dst_candidates:
                            diagnostics.warn(
                                f"Rule template skipped hard bind: {rule.rule_id}[{tpl_idx}] no dst scope tokens",
                                key=f"missing-dst-scope:{rule_family}:{tpl_idx}:{src_hint}:{dst_hint}:{pair_key}",
                            )
                            best_dst = self._pick_nearest_dst(
                                src_mssu=src_mssu,
                                dst_candidates=dst_candidates,
                                src_hint=src_hint,
                                dst_hint=dst_hint,
                                pair_key="",
                                action_index=action_index,
                                action_rank=action_rank,
                            )
                            if best_dst is not None and src_mssu.mssu_id != best_dst.mssu_id:
                                soft_edges.append(
                                    self._soft_order_from_template(
                                        src=src_mssu.mssu_id,
                                        dst=best_dst.mssu_id,
                                        rule_id=rule.rule_id,
                                        tpl_idx=tpl_idx,
                                        reason="missing_dst_scope_tokens",
                                    )
                                )
                            continue
                    best_dst = self._pick_nearest_dst(
                        src_mssu=src_mssu,
                        dst_candidates=scoped_dst_candidates,
                        src_hint=src_hint,
                        dst_hint=dst_hint,
                        pair_key=pair_key,
                        action_index=action_index,
                        action_rank=action_rank,
                    )
                    if best_dst is None:
                        fallback_dst = self._pick_nearest_dst(
                            src_mssu=src_mssu,
                            dst_candidates=scoped_dst_candidates,
                            src_hint="",
                            dst_hint="",
                            pair_key="",
                            action_index=action_index,
                            action_rank=action_rank,
                        )
                        if fallback_dst is not None and src_mssu.mssu_id != fallback_dst.mssu_id:
                            soft_edges.append(
                                self._soft_order_from_template(
                                    src=src_mssu.mssu_id,
                                    dst=fallback_dst.mssu_id,
                                    rule_id=rule.rule_id,
                                    tpl_idx=tpl_idx,
                                    reason="template_binding_failed_fallback",
                                )
                            )
                        continue
                    if src_mssu.mssu_id == best_dst.mssu_id:
                        continue
                    if not self._allow_template_hard_edge(src_mssu, best_dst):
                        soft_edges.append(
                            self._soft_order_from_template(
                                src=src_mssu.mssu_id,
                                dst=best_dst.mssu_id,
                                rule_id=rule.rule_id,
                                tpl_idx=tpl_idx,
                                reason="cross_action_scope_filtered",
                            )
                        )
                        continue

                    justification = [
                        f"rule_template:{rule.rule_id}:{tpl_idx}",
                        f"src_hint:{src_hint}",
                        f"dst_hint:{dst_hint}",
                        "pairing_rank:exact_family_same_action_same_lane_phase_then_nearest",
                    ]
                    if pair_key and pair_key != "nearest":
                        justification.append(f"pair_key:{pair_key}")
                    hard_edges.append(
                        DependencyEdge(
                            src_mssu=src_mssu.mssu_id,
                            dst_mssu=best_dst.mssu_id,
                            kind=kind,
                            justification=justification,
                            guardable=False,
                        )
                    )
                    injected += 1
                    if injected >= max_edges_per_template:
                        diagnostics.warn(
                            f"Rule template edge cap reached for {rule.rule_id}[{tpl_idx}]",
                            key=f"edge-cap:{rule_family}:{tpl_idx}:{src_hint}:{dst_hint}",
                        )
                        break

    @staticmethod
    def _action_scope_value(action: Dict[str, object], pair_key: str) -> str:
        pair = str(pair_key).strip().lower()
        if not pair:
            return ""
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}

        if pair == "device_id":
            return str(target.get("device_id") or target.get("id") or exec_cfg.get("device_id") or "")
        if pair == "endpoint":
            return str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or "")
        if pair == "host":
            endpoint = str(target.get("endpoint") or target.get("id") or exec_cfg.get("endpoint") or "")
            if endpoint.startswith("http://") or endpoint.startswith("https://"):
                return str(urlparse(endpoint).netloc)
            if ":" in endpoint:
                return endpoint.split(":", 1)[0]
            return endpoint
        return str(action.get(pair) or target.get(pair) or exec_cfg.get(pair) or "")

    def _mssu_scope_tokens(self, mssu: MSSU, pair_key: str, action_index: Dict[str, Dict[str, object]]) -> Set[str]:
        if not pair_key:
            return {"__nearest__"}
        tokens: Set[str] = set()
        for action_id in self._effective_action_refs(mssu):
            action = action_index.get(str(action_id))
            if action is None:
                continue
            value = self._action_scope_value(action, pair_key)
            if value:
                tokens.add(value)
        return tokens or {"__nearest__"}

    @staticmethod
    def _mssu_rank(mssu: MSSU, action_rank: Dict[str, int]) -> int:
        ranks = [action_rank.get(str(action_id), 10_000) for action_id in TypedDAGBuilder._effective_action_refs(mssu) if str(action_id)]
        if ranks:
            return min(ranks)
        return 10_000

    def _pick_nearest_dst(
        self,
        src_mssu: MSSU,
        dst_candidates: List[MSSU],
        src_hint: str,
        dst_hint: str,
        pair_key: str,
        action_index: Dict[str, Dict[str, object]],
        action_rank: Dict[str, int],
    ) -> MSSU | None:
        src_rank = self._mssu_rank(src_mssu, action_rank)
        src_scope = self._mssu_scope_tokens(src_mssu, pair_key, action_index)
        allow_missing_resource_cleanup_pair = self._allow_missing_resource_cleanup_pair(
            src_mssu,
            dst_candidates,
            src_hint,
            dst_hint,
        )
        ranked: List[Tuple[Tuple[int, int, int, int, int, int, int, int, str], MSSU]] = []
        for dst_mssu in dst_candidates:
            if src_mssu.mssu_id == dst_mssu.mssu_id:
                continue
            if not self._template_pair_compatible(
                src_mssu,
                dst_mssu,
                src_hint,
                dst_hint,
                allow_missing_resource_cleanup_pair=allow_missing_resource_cleanup_pair,
            ):
                continue
            dst_rank = self._mssu_rank(dst_mssu, action_rank)
            dst_scope = self._mssu_scope_tokens(dst_mssu, pair_key, action_index)
            src_exact, dst_exact, cleanup_specificity, same_action, same_lane, phase_compatible = self._template_pair_score(
                src_mssu,
                dst_mssu,
                src_hint,
                dst_hint,
            )
            scope_overlap = len(src_scope & dst_scope)
            direction_penalty = 0 if (not pair_key and src_rank == 10_000 and dst_rank == 10_000) else (0 if dst_rank >= src_rank else 1)
            distance = abs(dst_rank - src_rank)
            rank = (
                -src_exact,
                -dst_exact,
                -cleanup_specificity,
                -same_action,
                -same_lane,
                -phase_compatible,
                -scope_overlap,
                direction_penalty,
                distance,
                dst_mssu.mssu_id,
            )
            ranked.append((rank, dst_mssu))
        if not ranked:
            return None
        ranked.sort(key=lambda item: item[0])
        return ranked[0][1]

    def _template_pair_score(
        self,
        src_mssu: MSSU,
        dst_mssu: MSSU,
        src_hint: str,
        dst_hint: str,
    ) -> Tuple[int, int, int, int, int, int]:
        src_exact = int(self._hint_exact_match(src_mssu, src_hint))
        dst_exact = int(self._hint_exact_match(dst_mssu, dst_hint))
        cleanup_specificity = int(
            self._primary_effect_family(dst_mssu) == "unsubscribe"
            and self._mssu_effect_tokens(dst_mssu) == {"unsubscribe"}
        )
        same_action = int(self._same_action_scope(src_mssu, dst_mssu))
        same_lane = int(
            bool(getattr(src_mssu, "lane_tag", None))
            and getattr(src_mssu, "lane_tag", None) == getattr(dst_mssu, "lane_tag", None)
        )
        phase_compatible = int(
            str(getattr(src_mssu, "phase", "")).strip().upper() in {"RUNTIME", "TEARDOWN"}
            and str(getattr(dst_mssu, "phase", "")).strip().upper() == "TEARDOWN"
        )
        return (src_exact, dst_exact, cleanup_specificity, same_action, same_lane, phase_compatible)

    def _representative_mssus_for_action(
        self,
        action_id: str,
        nodes: Dict[str, MSSU],
        action_index: Dict[str, Dict[str, object]],
    ) -> List[str]:
        action_id_n = str(action_id).strip()
        scoped_nodes = [
            mssu
            for mssu in nodes.values()
            if action_id_n in self._effective_action_refs(mssu)
        ]
        if not scoped_nodes:
            return []
        primary_nodes = [mssu for mssu in scoped_nodes if self._mssu_primary_action(mssu) == action_id_n]
        candidate_nodes = primary_nodes or scoped_nodes

        action = self._action_row(action_id, action_index)
        if self._action_is_aggregate_sink(action):
            aggregate_nodes = [mssu for mssu in candidate_nodes if bool(getattr(mssu, "is_aggregate_sink", False))]
            if aggregate_nodes:
                chosen = min(aggregate_nodes, key=lambda mssu: (self._mssu_type_priority(mssu), mssu.mssu_id))
                return [chosen.mssu_id]

        if self._action_is_writeback(action):
            update_nodes = [mssu for mssu in candidate_nodes if str(mssu.mssu_type).strip().upper() == "UPDATE"]
            if update_nodes:
                chosen = min(update_nodes, key=lambda mssu: (self._mssu_type_priority(mssu), mssu.mssu_id))
                return [chosen.mssu_id]

        chosen = min(
            candidate_nodes,
            key=lambda mssu: (
                0 if self._mssu_primary_action(mssu) == action_id_n else 1,
                self._mssu_type_priority(mssu),
                mssu.mssu_id,
            ),
        )
        return [chosen.mssu_id]

    @staticmethod
    def _skip_cross_action_update_hard_edge(src_mssu: MSSU, dst_mssu: MSSU) -> bool:
        if src_mssu.mssu_id == dst_mssu.mssu_id:
            return True
        if str(src_mssu.mssu_type).strip().upper() != "UPDATE":
            return False
        if str(dst_mssu.mssu_type).strip().upper() != "UPDATE":
            return False
        src_actions = TypedDAGBuilder._effective_action_refs(src_mssu)
        dst_actions = TypedDAGBuilder._effective_action_refs(dst_mssu)
        if not src_actions or not dst_actions or TypedDAGBuilder._same_action_scope(src_mssu, dst_mssu):
            return False
        return not bool(getattr(dst_mssu, "is_aggregate_sink", False))

    def _candidate_hard_edge_allowed(self, src_mssu: MSSU, dst_mssu: MSSU, edge_type: str) -> bool:
        if self._is_soft_only_mssu(src_mssu) or self._is_soft_only_mssu(dst_mssu):
            return False
        if not self._allowed_hard_edge_pair(src_mssu, dst_mssu):
            return False
        if edge_type == "DATA_DEP" and not self._strict_data_overlap(src_mssu, dst_mssu):
            return False
        return True

    def _add_soft_constraints(self, mssus: List[MSSU], dag: TypedDAG, optimization_target: OptimizationTarget | None = None) -> None:
        mssu_ids = [mssu.mssu_id for mssu in mssus]
        critical_scope = [mssu.mssu_id for mssu in mssus if mssu.critical]

        for rule in self.profile.rules:
            if rule.status == RuleStatus.DISABLED.value:
                continue
            if not rule.soft_constraint_templates:
                continue
            for tpl in rule.soft_constraint_templates:
                kind = tpl.get("kind", SoftConstraintKind.BUDGET_K.value)
                if kind not in {item.value for item in SoftConstraintKind}:
                    continue
                raw_scope_hint = tpl.get("scope", [])
                if not isinstance(raw_scope_hint, list):
                    raw_scope_hint = [raw_scope_hint]
                scope_hint = [str(hint).strip() for hint in raw_scope_hint if str(hint).strip()]
                scope_nodes = [
                    mssu.mssu_id
                    for mssu in mssus
                    if any(self._mssu_matches_hint(mssu, hint) for hint in scope_hint)
                ]
                if not scope_nodes:
                    if scope_hint:
                        continue
                    scope_nodes = critical_scope or mssu_ids

                params = tpl.get("params", {})
                params = dict(params) if isinstance(params, dict) else {}
                params.setdefault("rule_id", rule.rule_id)
                params.setdefault("template_kind", kind)
                dag.soft_constraints.append(
                    SoftConstraint(
                        kind=kind,
                        scope=scope_nodes,
                        params=params,
                        guard=str(tpl.get("guard", rule.guard)),
                        fallback=str(tpl.get("fallback", rule.fallback)),
                    )
                )

        if optimization_target is not None:
            knobs = (
                optimization_target.constraints.get("optimization_knobs", {})
                if isinstance(optimization_target.constraints, dict)
                else {}
            )
            max_concurrency = knobs.get("max_concurrency", {}) if isinstance(knobs.get("max_concurrency", {}), dict) else {}
            for resource, limit in max_concurrency.items():
                if isinstance(limit, (int, float)):
                    resource_upper = str(resource).upper()
                    resource_scope = [
                        mssu.mssu_id
                        for mssu in mssus
                        if (
                            resource_upper == "BLE"
                            and any(token.startswith("ble_") or token == "ble_op" for token in self._mssu_effect_tokens(mssu))
                        )
                        or (
                            resource_upper == "CLOUD"
                            and any(token.startswith("cloud_") or token == "cloud_op" for token in self._mssu_effect_tokens(mssu))
                        )
                        or (
                            resource_upper == "HA"
                            and any(
                                token in {"ha_state_write", "state_write", "coord_refresh", "coord_first_refresh", "entry_setup", "entry_unload", "entry_remove"}
                                or token.startswith("entry_")
                                for token in self._mssu_effect_tokens(mssu)
                            )
                        )
                    ]
                    dag.soft_constraints.append(
                        SoftConstraint(
                            kind=SoftConstraintKind.BUDGET_K.value,
                            scope=resource_scope or critical_scope or mssu_ids,
                            params={"resource": resource_upper, "limit": int(limit)},
                            guard="resource_constrained",
                            fallback="reduce_parallelism",
                        )
                    )


    @staticmethod
    def _build_in_degree(nodes: Dict[str, MSSU], edges: List[DependencyEdge]) -> Dict[str, int]:
        indegree = {node_id: 0 for node_id in nodes}
        for edge in edges:
            indegree[edge.dst_mssu] = indegree.get(edge.dst_mssu, 0) + 1
        return indegree

    @staticmethod
    def _acyclic(nodes: Dict[str, MSSU], edges: List[DependencyEdge]) -> bool:
        indegree = TypedDAGBuilder._build_in_degree(nodes, edges)
        out: Dict[str, List[str]] = {node_id: [] for node_id in nodes}
        for edge in edges:
            out.setdefault(edge.src_mssu, []).append(edge.dst_mssu)

        queue = [node_id for node_id, degree in indegree.items() if degree == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for nxt in out.get(node, []):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        return visited == len(nodes)

    def _break_cycles(self, nodes: Dict[str, MSSU], edges: List[DependencyEdge], diagnostics: DAGBuildDiagnostics) -> List[DependencyEdge]:
        mutable = list(edges)
        while mutable and not TypedDAGBuilder._acyclic(nodes, mutable):
            remove_idx = min(range(len(mutable)), key=lambda idx: self._edge_removal_rank(nodes, mutable[idx]))
            removed = mutable.pop(remove_idx)
            diagnostics.warn(
                f"Hard cycle detected; demoted edge {removed.src_mssu}->{removed.dst_mssu} to SOFT_ORDER",
                key=f"hard-cycle:{removed.src_mssu}->{removed.dst_mssu}",
            )
            diagnostics.record_removed_edge(removed.src_mssu, removed.dst_mssu)
        return mutable

    @staticmethod
    def _dedup_soft_order_constraints(soft_constraints: List[SoftConstraint]) -> List[SoftConstraint]:
        kept: List[SoftConstraint] = []
        keep: Dict[Tuple[str, Tuple[str, ...]], SoftConstraint] = {}
        for constraint in soft_constraints:
            if constraint.kind != SoftConstraintKind.SOFT_ORDER.value:
                kept.append(constraint)
                continue
            key = (constraint.kind, tuple(constraint.scope))
            previous = keep.get(key)
            if previous is None:
                keep[key] = constraint
                continue
            if TypedDAGBuilder._soft_constraint_reason_rank(constraint) > TypedDAGBuilder._soft_constraint_reason_rank(previous):
                keep[key] = constraint
        return kept + list(keep.values())

    @staticmethod
    def _action_graph_sccs(
        nodes: Dict[str, MSSU],
        hard_edges: List[DependencyEdge],
    ) -> List[Set[str]]:
        adjacency: Dict[str, Set[str]] = {}
        for edge in hard_edges:
            src_mssu = nodes.get(edge.src_mssu)
            dst_mssu = nodes.get(edge.dst_mssu)
            if src_mssu is None or dst_mssu is None:
                continue
            src_actions = TypedDAGBuilder._effective_action_refs(src_mssu)
            dst_actions = TypedDAGBuilder._effective_action_refs(dst_mssu)
            if not src_actions or not dst_actions:
                continue
            for src_action in src_actions:
                for dst_action in dst_actions:
                    if src_action == dst_action:
                        continue
                    adjacency.setdefault(src_action, set()).add(dst_action)
                    adjacency.setdefault(dst_action, set())

        index = 0
        index_by_node: Dict[str, int] = {}
        lowlink: Dict[str, int] = {}
        stack: List[str] = []
        on_stack: Set[str] = set()
        components: List[Set[str]] = []

        def strongconnect(node: str) -> None:
            nonlocal index
            index_by_node[node] = index
            lowlink[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for nxt in adjacency.get(node, set()):
                if nxt not in index_by_node:
                    strongconnect(nxt)
                    lowlink[node] = min(lowlink[node], lowlink[nxt])
                elif nxt in on_stack:
                    lowlink[node] = min(lowlink[node], index_by_node[nxt])

            if lowlink[node] != index_by_node[node]:
                return

            component: Set[str] = set()
            while stack:
                member = stack.pop()
                on_stack.discard(member)
                component.add(member)
                if member == node:
                    break
            if len(component) > 1:
                components.append(component)
            elif node in adjacency.get(node, set()):
                components.append(component)

        for action_id in adjacency:
            if action_id not in index_by_node:
                strongconnect(action_id)

        return components

    def _break_action_level_cycles(
        self,
        nodes: Dict[str, MSSU],
        hard_edges: List[DependencyEdge],
        diagnostics: DAGBuildDiagnostics,
    ) -> List[DependencyEdge]:
        mutable = list(hard_edges)
        while True:
            sccs = self._action_graph_sccs(nodes, mutable)
            if not sccs:
                return mutable

            cycle_actions = set().union(*sccs)
            removable = [
                idx
                for idx, edge in enumerate(mutable)
                if (
                    nodes.get(edge.src_mssu) is not None
                    and nodes.get(edge.dst_mssu) is not None
                    and any(action_id in cycle_actions for action_id in self._effective_action_refs(nodes[edge.src_mssu]))
                    and any(action_id in cycle_actions for action_id in self._effective_action_refs(nodes[edge.dst_mssu]))
                    and any(
                        str(item).startswith("vdev_dep:") or str(item).startswith("rule_template:")
                        for item in edge.justification
                    )
                    and edge.kind != EdgeKind.HARD_DATA.value
                )
            ]
            if not removable:
                return mutable

            remove_idx = min(removable, key=lambda idx: self._edge_removal_rank(nodes, mutable[idx]))
            removed = mutable.pop(remove_idx)
            diagnostics.warn(
                f"Action-level hard cycle detected; demoted edge {removed.src_mssu}->{removed.dst_mssu} to SOFT_ORDER",
                key=f"action-hard-cycle:{removed.src_mssu}->{removed.dst_mssu}",
            )
            diagnostics.record_removed_edge(removed.src_mssu, removed.dst_mssu)

    def _inject_vdev_dependencies(
        self,
        nodes: Dict[str, MSSU],
        hard_edges: List[DependencyEdge],
        soft_constraints: List[SoftConstraint],
        optimization_target: OptimizationTarget | None,
        diagnostics: DAGBuildDiagnostics,
    ) -> None:
        if optimization_target is None:
            return

        action_index: Dict[str, Dict[str, object]] = {}
        for action in optimization_target.vdev_actions:
            action_id = str(action.get("action_id", "")).strip()
            if action_id:
                action_index[action_id] = action

        by_action: Dict[str, List[str]] = {
            action_id: self._representative_mssus_for_action(action_id, nodes, action_index)
            for action_id in action_index
        }

        for dep in optimization_target.hard_dependencies:
            before = str(dep.get("before", "")).strip()
            after = str(dep.get("after", "")).strip()
            if not before or not after:
                continue
            before_action = action_index.get(before)
            after_action = action_index.get(after)
            if before_action is None or after_action is None:
                continue

            if self._action_is_writeback(before_action) and self._action_is_writeback(after_action):
                if self._action_is_aggregate_sink(after_action):
                    pass
                elif self._action_is_aggregate_sink(before_action):
                    diagnostics.warnings.append(
                        f"Skipped reverse writeback hard dependency {before}->{after}; aggregate sink cannot source sibling writeback"
                    )
                    continue
                else:
                    scope = sorted({*by_action.get(before, []), *by_action.get(after, [])})
                    if scope:
                        soft_constraints.append(
                            SoftConstraint(
                                kind=SoftConstraintKind.SOFT_ORDER.value,
                                scope=scope,
                                params={"reason": f"vdev_dep_soft_writeback:{before}->{after}"},
                                guard="true",
                                fallback="preserve_action_order",
                            )
                        )
                    continue

            src_reps = by_action.get(before, [])
            dst_reps = by_action.get(after, [])
            if not src_reps or not dst_reps:
                diagnostics.warnings.append(f"Skipped vdev dependency without representatives: {before}->{after}")
                continue

            for src in src_reps:
                for dst in dst_reps:
                    if src == dst:
                        continue
                    src_mssu = nodes.get(src)
                    dst_mssu = nodes.get(dst)
                    if src_mssu is None or dst_mssu is None:
                        continue
                    if TypedDAGBuilder._skip_cross_action_update_hard_edge(src_mssu, dst_mssu):
                        diagnostics.warnings.append(
                            f"Skipped cross-action UPDATE hard dependency {src}->{dst} for {before}->{after}"
                        )
                        continue
                    hard_edges.append(
                        DependencyEdge(
                            src_mssu=src,
                            dst_mssu=dst,
                            kind=EdgeKind.HARD_CONTROL.value,
                            justification=[f"vdev_dep:{before}->{after}", str(dep.get("reason", ""))],
                            guardable=False,
                        )
                    )

        for dep in optimization_target.soft_dependencies:
            before = str(dep.get("before", "")).strip()
            after = str(dep.get("after", "")).strip()
            if not before or not after:
                continue
            scope = sorted({*by_action.get(before, []), *by_action.get(after, [])})
            if not scope:
                continue
            soft_constraints.append(
                SoftConstraint(
                    kind=SoftConstraintKind.MIN_GAP.value,
                    scope=scope,
                    params={"reason": str(dep.get("reason", "vdev_soft_dependency"))},
                    guard="true",
                    fallback="preserve_action_order",
                )
            )

    def build(
        self,
        mssus: List[MSSU],
        dependency_candidates: List[Tuple[str, str, str]],
        optimization_target: OptimizationTarget | None = None,
    ) -> tuple[TypedDAG, DAGBuildDiagnostics]:
        nodes = {mssu.mssu_id: mssu for mssu in mssus}
        hard_edges: List[DependencyEdge] = []
        candidate_soft: List[SoftConstraint] = []
        diagnostics = DAGBuildDiagnostics()

        for src, dst, edge_type in dependency_candidates:
            if edge_type == "DATA_DEP":
                src_mssu = nodes.get(src)
                dst_mssu = nodes.get(dst)
                if src_mssu is None or dst_mssu is None:
                    continue
                if not self._allow_cross_action_hard_data(src_mssu, dst_mssu):
                    candidate_soft.append(self._soft_order_from_candidate(src, dst, edge_type))
                    continue
                if not self._candidate_hard_edge_allowed(src_mssu, dst_mssu, edge_type):
                    candidate_soft.append(self._soft_order_from_candidate(src, dst, edge_type))
                    continue
                edge = self._hard_edge_from_candidate(src, dst, edge_type)
                if edge is not None:
                    hard_edges.append(edge)
                continue
            if edge_type == "LIFECYCLE_DEP":
                src_mssu = nodes.get(src)
                dst_mssu = nodes.get(dst)
                if (
                    src_mssu is not None
                    and dst_mssu is not None
                    and self._is_semantic_lifecycle_candidate(src_mssu, dst_mssu)
                    and self._candidate_hard_edge_allowed(src_mssu, dst_mssu, edge_type)
                ):
                    hard_edges.append(
                        DependencyEdge(
                            src_mssu=src,
                            dst_mssu=dst,
                            kind=EdgeKind.HARD_LIFECYCLE.value,
                            justification=[f"candidate:{edge_type}"],
                            guardable=False,
                        )
                    )
                else:
                    candidate_soft.append(self._soft_order_from_candidate(src, dst, edge_type))
                continue
            if edge_type in {"CONTROL_DEP", "EXCEPTION_DEP"}:
                candidate_soft.append(self._soft_order_from_candidate(src, dst, edge_type))

        self._inject_rule_template_hard_edges(
            mssus,
            hard_edges,
            candidate_soft,
            diagnostics,
            optimization_target=optimization_target,
        )


        producers_by_var: Dict[str, Set[str]] = {}
        for mssu in mssus:
            for output_name in mssu.outputs:
                producers_by_var.setdefault(str(output_name), set()).add(mssu.mssu_id)
        for mssu in mssus:
            for input_name in mssu.inputs:
                if self._generic_io_symbol(str(input_name)):
                    continue
                for producer_id in producers_by_var.get(str(input_name), set()):
                    if producer_id == mssu.mssu_id:
                        continue
                    producer_mssu = nodes.get(producer_id)
                    if producer_mssu is not None and self._skip_cross_action_update_hard_edge(producer_mssu, mssu):
                        continue
                    if producer_mssu is not None and not self._allow_cross_action_hard_data(producer_mssu, mssu, str(input_name)):
                        continue
                    if producer_mssu is not None and not self._candidate_hard_edge_allowed(producer_mssu, mssu, "DATA_DEP"):
                        candidate_soft.append(self._soft_order_from_candidate(producer_id, mssu.mssu_id, "DATA_DEP"))
                        continue
                    hard_edges.append(
                        DependencyEdge(
                            src_mssu=producer_id,
                            dst_mssu=mssu.mssu_id,
                            kind=EdgeKind.HARD_DATA.value,
                            justification=["io:outputs_intersect_inputs"],
                            guardable=False,
                        )
                    )


        dedup: Dict[Tuple[str, str, str], DependencyEdge] = {}
        for edge in hard_edges:
            dedup[(edge.src_mssu, edge.dst_mssu, edge.kind)] = edge
        hard_edges = list(dedup.values())

        injected_soft: List[SoftConstraint] = []
        self._inject_vdev_dependencies(nodes, hard_edges, injected_soft, optimization_target, diagnostics)
        dedup = {(edge.src_mssu, edge.dst_mssu, edge.kind): edge for edge in hard_edges}
        hard_edges = list(dedup.values())

        hard_edges = self._break_action_level_cycles(nodes, hard_edges, diagnostics)
        hard_edges = self._break_cycles(nodes, hard_edges, diagnostics)

        dag = TypedDAG(
            nodes=nodes,
            hard_edges=hard_edges,
            soft_constraints=[],
            resources={
                "BLE": {"type": "slot_pool"},
                "CLOUD": {"type": "rate_budget"},
                "HA": {"type": "event_loop"},
            },
        )

        dag.soft_constraints.extend(injected_soft)
        dag.soft_constraints.extend(candidate_soft)
        self._add_soft_constraints(mssus, dag, optimization_target=optimization_target)


        for src, dst in diagnostics.removed_hard_edges:
            dag.soft_constraints.append(
                SoftConstraint(
                    kind=SoftConstraintKind.SOFT_ORDER.value,
                    scope=[src, dst],
                    params={"reason": "cycle_break"},
                    guard="true",
                    fallback="force_topological_local_order",
                )
            )

        dag.soft_constraints = self._dedup_soft_order_constraints(dag.soft_constraints)

        return dag, diagnostics


DependencyGraphBuilder = TypedDAGBuilder
