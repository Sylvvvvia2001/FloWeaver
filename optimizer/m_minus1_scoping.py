from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from dsl.contracts import OptimizationTarget, SourceFileBinding, ensure_optimization_target
from dsl.io import dump_json, load_json
from optimizer.action_primitives import validate_target_action_primitives


PROTOCOL_TO_MARKERS: Dict[str, List[str]] = {
    "BLE": ["BLE_OP"],
    "CLOUD": ["CLOUD_OP"],
    "LOCAL": ["LOCAL_API_READ"],
    "MQTT": ["MQTT_SUBSCRIBE"],
    "HA": ["STATE_WRITE"],
}

TARGET_KIND_ALIAS: Dict[str, str] = {
    "ha_entity": "ha_entity",
    "entity": "ha_entity",
    "cloud_endpoint": "cloud_endpoint",
    "cloud_api": "cloud_endpoint",
    "ble_device": "ble_device",
    "ble_characteristic": "ble_characteristic",
    "gatt_characteristic": "ble_characteristic",
    "ble_gatt_characteristic": "ble_characteristic",
}

KNOWN_PLATFORMS = {
    "sensor",
    "binary_sensor",
    "switch",
    "light",
    "climate",
    "fan",
    "cover",
    "button",
    "number",
    "select",
    "text",
    "scene",
    "humidifier",
    "water_heater",
    "lock",
    "alarm_control_panel",
    "camera",
    "media_player",
    "remote",
    "vacuum",
    "valve",
    "update",
    "event",
    "device_tracker",
}

EXEC_PRIMITIVE_KINDS = {
    "ha_service_call",
    "ha_state_read",
    "wait_state",
    "sleep",
    "retry_backoff",
}


class VDevSpecError(ValueError):
    pass


@dataclass
class ScopingArtifacts:
    optimization_target: OptimizationTarget
    source_bindings: List[SourceFileBinding]


SourceSpecInput = Dict[str, Any] | List[Dict[str, Any]]


class VDevScopingEngine:
    def __init__(self, vdev_spec: Dict[str, Any], source_spec: SourceSpecInput, run_spec: Dict[str, Any] | None = None) -> None:
        self.vdev_spec = vdev_spec
        self.source_spec = self._normalize_source_spec(source_spec)
        self.run_spec = run_spec or {}

    @classmethod
    def from_files(
        cls,
        vdev_spec_path: str | Path,
        source_spec_path: str | Path,
        run_spec_path: str | Path | None = None,
    ) -> "VDevScopingEngine":
        vdev_spec = load_json(vdev_spec_path)
        source_spec = load_json(source_spec_path)
        run_spec = load_json(run_spec_path) if run_spec_path else {}
        return cls(vdev_spec=vdev_spec, source_spec=source_spec, run_spec=run_spec)

    @staticmethod
    def _normalize_protocol(value: Any) -> str:
        if value is None:
            return "HA"
        return str(value).strip().upper()

    @staticmethod
    def _resolve_path(path: str | Path) -> str:
        return str(Path(path).expanduser().resolve())

    @staticmethod
    def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(base)
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = VDevScopingEngine._deep_merge_dict(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged

    @staticmethod
    def _normalize_source_spec(spec: SourceSpecInput) -> Dict[str, Any]:
        if isinstance(spec, list):
            return {"integrations": list(spec)}
        if isinstance(spec, dict):
            return dict(spec)
        raise VDevSpecError(f"source_spec must be dict or list, got {type(spec)!r}")

    @staticmethod
    def _iter_source_bindings(spec: SourceSpecInput) -> Iterable[SourceFileBinding]:
        entries: Sequence[Dict[str, Any]]

        if isinstance(spec, list):
            entries = spec
        elif "integrations" in spec and isinstance(spec["integrations"], list):
            entries = spec["integrations"]
        elif "files" in spec and isinstance(spec["files"], list):
            entries = spec["files"]
        elif "mappings" in spec and isinstance(spec["mappings"], list):
            entries = spec["mappings"]
        else:
            entries = []

        for row in entries:
            file_path = row.get("file_path") or row.get("path")
            if not file_path:
                continue
            yield SourceFileBinding(
                device_id=str(row.get("device_id", row.get("device", "unknown_device"))),
                integration=str(row.get("integration", row.get("domain", "unknown_integration"))),
                file_path=VDevScopingEngine._resolve_path(file_path),
                protocols=[VDevScopingEngine._normalize_protocol(v) for v in row.get("protocols", [])],
            )

    @staticmethod
    def _canonical_target_kind(kind_raw: str) -> str:
        key = str(kind_raw).strip().lower()
        canonical = TARGET_KIND_ALIAS.get(key)
        if canonical is None:
            raise VDevSpecError(
                f"Unsupported target.kind '{kind_raw}'. "
                f"Allowed values: {sorted(set(TARGET_KIND_ALIAS))}"
            )
        return canonical

    @staticmethod
    def _anchor_from_target(target: Dict[str, Any]) -> Dict[str, List[str]]:
        anchors: Dict[str, List[str]] = {
            "entities": [],
            "endpoints": [],
            "characteristics": [],
            "device_ids": [],
        }

        kind_raw = str(target.get("kind", "")).strip()
        if not kind_raw:
            return anchors
        kind = VDevScopingEngine._canonical_target_kind(kind_raw)
        target_id = str(target.get("id", ""))
        entity_id = str(target.get("entity_id", ""))

        if entity_id:
            anchors["entities"].append(entity_id)

        if kind == "ha_entity":
            entity = entity_id or target_id
            if entity:
                anchors["entities"].append(entity)
        elif kind == "cloud_endpoint":
            endpoint = str(target.get("endpoint", "")).strip() or target_id
            if endpoint:
                anchors["endpoints"].append(endpoint)
        elif kind == "ble_device":
            device_id = str(target.get("device_id", "")).strip() or target_id
            if device_id:
                anchors["device_ids"].append(device_id)
        elif kind == "ble_characteristic":
            characteristic = str(target.get("characteristic", "")).strip() or target_id
            if characteristic:
                anchors["characteristics"].append(characteristic)
            device_id = str(target.get("device_id", "")).strip()
            if device_id:
                anchors["device_ids"].append(device_id)

        return anchors

    @staticmethod
    def _merge_anchor_values(left: Dict[str, List[str]], right: Dict[str, List[str]]) -> Dict[str, List[str]]:
        merged = {k: list(left.get(k, [])) for k in set(left) | set(right)}
        for key, values in right.items():
            merged.setdefault(key, [])
            merged[key].extend(values)
        for key, values in merged.items():
            seen = set()
            deduped: List[str] = []
            for value in values:
                if not value or value in seen:
                    continue
                seen.add(value)
                deduped.append(value)
            merged[key] = deduped
        return merged

    @staticmethod
    def _normalize_exec_primitive(action_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
        primitive = row.get("exec")
        if not isinstance(primitive, dict):
            raise VDevSpecError(
                f"Action '{action_id}' must define executable mapping in `exec` "
                "(ha_service_call/ha_state_read/wait_state/sleep/retry_backoff)"
            )

        kind = str(primitive.get("kind", "")).strip()
        if kind not in EXEC_PRIMITIVE_KINDS:
            raise VDevSpecError(
                f"Action '{action_id}' exec.kind '{kind}' is unsupported; "
                f"expected one of {sorted(EXEC_PRIMITIVE_KINDS)}"
            )

        normalized = dict(primitive)
        normalized["kind"] = kind

        if kind == "ha_service_call":
            if not normalized.get("domain") or not normalized.get("service"):
                raise VDevSpecError(f"Action '{action_id}' ha_service_call requires domain and service")
            normalized.setdefault("data_template", {})
            normalized.setdefault("blocking", True)
        elif kind == "ha_state_read":
            if not normalized.get("entity_id"):
                raise VDevSpecError(f"Action '{action_id}' ha_state_read requires entity_id")
            normalized.setdefault("attribute", "state")
        elif kind == "wait_state":
            if not normalized.get("entity_id"):
                raise VDevSpecError(f"Action '{action_id}' wait_state requires entity_id")
            normalized.setdefault("timeout_s", 10)
            normalized.setdefault("poll_interval_s", 0.25)
        elif kind == "sleep":
            normalized.setdefault("seconds", 0.1)
        elif kind == "retry_backoff":
            normalized.setdefault("base_ms", 200)
            normalized.setdefault("factor", 2.0)
            normalized.setdefault("attempts", 3)

        return normalized

    @staticmethod
    def _normalize_marker_hints(values: Any) -> List[str]:
        if not isinstance(values, list):
            return []
        out: List[str] = []
        seen = set()
        for value in values:
            token = str(value).strip().upper()
            if not token or token in seen:
                continue
            seen.add(token)
            out.append(token)
        return out

    @staticmethod
    def _derive_marker_hints(
        protocol: str,
        action_type: str,
        target_kind: str,
        exec_primitive: Dict[str, Any],
    ) -> List[str]:
        hints: List[str] = list(PROTOCOL_TO_MARKERS.get(protocol, []))
        action_type_l = action_type.lower()
        exec_kind = str(exec_primitive.get("kind", "")).strip()

        service_token = ""
        if exec_kind == "ha_service_call":
            domain = str(exec_primitive.get("domain", "")).strip().lower()
            service = str(exec_primitive.get("service", "")).strip().lower()
            service_token = f"{domain}.{service}".strip(".")

        if protocol == "BLE":
            if target_kind == "ble_characteristic":
                hints.append("BLE_GATT_OP")
            if action_type_l in {"read", "write"} and target_kind in {"ble_device", "ble_characteristic"}:
                hints.append("BLE_GATT_OP")
            if "connect" in service_token:
                hints.append("BLE_CONNECT")
            if any(token in service_token for token in {"disconnect", "close"}):
                hints.append("BLE_DISCONNECT")
            if any(token in service_token for token in {"scan", "discover"}):
                hints.append("BLE_SCAN")
            if any(token in service_token for token in {"notify", "subscribe", "listener", "listen"}):
                hints.append("BLE_NOTIFY_SUBSCRIBE")
                hints.append("SUBSCRIBE")
            if any(token in service_token for token in {"unsubscribe", "unsub"}):
                hints.append("UNSUBSCRIBE")
            if any(token in service_token for token in {"read", "write", "notify", "gatt", "subscribe", "unsubscribe"}):
                hints.append("BLE_GATT_OP")
            if exec_kind in {"sleep", "retry_backoff"}:
                hints.append("BLE_RETRY_OR_TIMEOUT")

        if protocol == "CLOUD":
            if action_type_l in {"call_api", "read", "write", "status", "read_runtime", "poll"}:
                hints.append("CLOUD_HTTP_CALL")
            if any(token in service_token for token in {"request", "get", "post", "put", "patch", "delete", "call_api", "api"}):
                hints.append("CLOUD_HTTP_CALL")
            if action_type_l in {"read", "status", "read_runtime", "poll"}:
                hints.append("CLOUD_STATUS_CALL")
            if any(token in service_token for token in {"status", "runtime", "fetch", "poll", "refresh", "update"}):
                hints.append("CLOUD_STATUS_CALL")
            if action_type_l in {"status", "read_runtime", "poll"} or any(
                token in service_token for token in {"poll", "refresh", "update"}
            ):
                hints.append("POLL_UPDATE")
            if any(token in service_token for token in {"login", "auth", "token", "refresh", "oauth"}):
                hints.append("CLOUD_TOKEN_REFRESH")
            if any(token in service_token for token in {"batch", "bulk"}):
                hints.append("CLOUD_BATCH_CALL")
            if any(token in service_token for token in {"session", "clientsession"}):
                hints.append("CLOUD_SESSION_REUSE")
            if exec_kind in {"sleep", "retry_backoff"}:
                hints.append("CLOUD_BACKOFF_SLEEP")

        if protocol == "LOCAL":
            if action_type_l in {"read", "status", "get_state", "read_runtime", "call_api"} or exec_kind == "ha_state_read":
                hints.append("LOCAL_API_READ")
            if any(token in service_token for token in {"subscribe", "listen", "message"}):
                hints.append("MQTT_SUBSCRIBE")

        if protocol == "MQTT":
            hints.append("MQTT_SUBSCRIBE")
            if any(token in service_token for token in {"subscribe", "listen", "message", "read_last_message"}):
                hints.append("SUBSCRIBE")

        if protocol == "HA" and action_type_l == "write":
            hints.append("STATE_WRITE")

        deduped = []
        seen = set()
        for hint in hints:
            token = str(hint).strip().upper()
            if not token or token in seen:
                continue
            seen.add(token)
            deduped.append(token)
        return deduped

    def _normalize_actions(self) -> tuple[List[Dict[str, Any]], Dict[str, List[str]], List[str]]:
        raw_actions = self.vdev_spec.get("vdev", {}).get("actions", [])
        if not isinstance(raw_actions, list) or not raw_actions:
            raise VDevSpecError("vdev.actions is required and must be a non-empty list")

        normalized: List[Dict[str, Any]] = []
        target_anchors: Dict[str, List[str]] = {
            "entities": [],
            "endpoints": [],
            "characteristics": [],
            "device_ids": [],
            "service_entrypoints": [],
            "anchor_ops": [],
            "required_state_writes": [],
        }
        critical_ids: List[str] = []

        for row in raw_actions:
            action_id = row.get("action_id")
            if not action_id:
                raise VDevSpecError("Each action must include action_id")

            io = row.get("io", {}) if isinstance(row.get("io", {}), dict) else {}
            protocol = self._normalize_protocol(io.get("protocol"))
            semantics = row.get("semantics", {}) if isinstance(row.get("semantics", {}), dict) else {}
            critical = bool(semantics.get("critical", False))
            if critical:
                critical_ids.append(str(action_id))

            target = row.get("target", {}) if isinstance(row.get("target", {}), dict) else {}
            exec_primitive = self._normalize_exec_primitive(str(action_id), row)

            kind_raw = str(target.get("kind", "")).strip()
            if not kind_raw and exec_primitive.get("kind") not in {"sleep", "retry_backoff"}:
                raise VDevSpecError(f"Action '{action_id}' target.kind is required for exec.kind={exec_primitive.get('kind')}")
            target_kind = self._canonical_target_kind(kind_raw) if kind_raw else ""

            explicit_marker_hints = self._normalize_marker_hints(row.get("marker_hints", []))
            explicit_marker_hints += self._normalize_marker_hints(semantics.get("marker_hints", []))
            marker_hints = self._derive_marker_hints(
                protocol=protocol,
                action_type=str(row.get("type", "act")),
                target_kind=target_kind,
                exec_primitive=exec_primitive,
            )
            marker_hints.extend(explicit_marker_hints)
            marker_hints = self._normalize_marker_hints(marker_hints)

            anchors = self._anchor_from_target(target)
            target_anchors = self._merge_anchor_values(target_anchors, anchors)
            for hint in marker_hints:
                if hint not in target_anchors["anchor_ops"]:
                    target_anchors["anchor_ops"].append(hint)

            normalized.append(
                {
                    "action_id": str(action_id),
                    "type": str(row.get("type", "act")),
                    "protocol": protocol,
                    "target_kind": target_kind,
                    "target": target,
                    "exec": exec_primitive,
                    "critical": critical,
                    "side_effects": list(semantics.get("side_effects", [])),
                    "must_happen_before": list(semantics.get("must_happen_before", [])),
                    "marker_hints": marker_hints,
                }
            )

        contract = self.vdev_spec.get("vdev", {}).get("interfaces", {}).get("state_contract", {})
        for item in contract.get("writes", []) if isinstance(contract, dict) else []:
            entity_id = item.get("entity_id")
            if entity_id:
                target_anchors["entities"].append(str(entity_id))
                target_anchors["required_state_writes"].append(str(entity_id))

        entrypoint = self.vdev_spec.get("vdev", {}).get("entrypoint", {})
        if isinstance(entrypoint, dict) and entrypoint.get("kind") == "ha_service":
            service = entrypoint.get("service", {}) if isinstance(entrypoint.get("service", {}), dict) else {}
            domain = service.get("domain")
            name = service.get("name")
            if domain and name:
                target_anchors["service_entrypoints"].append(f"{domain}.{name}")

        target_anchors = self._merge_anchor_values({}, target_anchors)
        return normalized, target_anchors, critical_ids

    @staticmethod
    def _source_domains_from_bindings(bindings: List[SourceFileBinding]) -> List[str]:
        domains = sorted({binding.integration for binding in bindings if binding.integration and binding.integration != "unknown_integration"})
        return domains

    @staticmethod
    def _source_platforms_from_bindings(bindings: List[SourceFileBinding]) -> List[str]:
        found = set()
        for binding in bindings:
            path = Path(binding.file_path)
            tokens = set(path.stem.lower().replace("-", "_").split("_"))
            tokens |= {part.lower() for part in path.parts}
            for token in KNOWN_PLATFORMS:
                if token in tokens:
                    found.add(token)
        return sorted(found)

    @staticmethod
    def _source_protocols_from_bindings(bindings: List[SourceFileBinding]) -> List[str]:
        values = sorted({protocol for binding in bindings for protocol in binding.protocols if protocol})
        return values

    @staticmethod
    def _source_platforms_from_spec(source_spec: Dict[str, Any]) -> List[str]:
        rows: List[str] = []
        top = source_spec.get("platforms", [])
        if isinstance(top, list):
            rows.extend(str(item).strip() for item in top if str(item).strip())
        entries: Sequence[Dict[str, Any]]
        if isinstance(source_spec, list):
            entries = source_spec
        elif "integrations" in source_spec and isinstance(source_spec["integrations"], list):
            entries = source_spec["integrations"]
        elif "files" in source_spec and isinstance(source_spec["files"], list):
            entries = source_spec["files"]
        elif "mappings" in source_spec and isinstance(source_spec["mappings"], list):
            entries = source_spec["mappings"]
        else:
            entries = []
        for row in entries:
            platform = row.get("platform")
            if platform:
                rows.append(str(platform).strip())
            platforms = row.get("platforms", [])
            if isinstance(platforms, list):
                rows.extend(str(item).strip() for item in platforms if str(item).strip())
        return sorted({item for item in rows if item})

    def _normalize_source_scope(self, bindings: List[SourceFileBinding]) -> Dict[str, Any]:
        ha_core = self.vdev_spec.get("sources", {}).get("ha_core", {})
        source_repo = self.source_spec.get("repo_path") or ha_core.get("repo_path")
        if source_repo:
            repo_path = Path(self._resolve_path(source_repo))
            if not repo_path.exists():
                raise VDevSpecError(f"Source repo path does not exist: {repo_path}")

        files = [binding.file_path for binding in bindings]
        if not files:
            raise VDevSpecError("SourceSpec must include at least one integration file mapping")
        missing_files = [path for path in files if not Path(path).exists()]
        if missing_files:
            raise VDevSpecError("SourceSpec contains missing file(s): " + ", ".join(missing_files))

        entrypoints = []
        entrypoint = self.vdev_spec.get("vdev", {}).get("entrypoint", {})
        if isinstance(entrypoint, dict):
            entrypoints.append(entrypoint)

        domains = list(ha_core.get("domains", []))
        if not domains:
            domains = self._source_domains_from_bindings(bindings)

        platforms = list(ha_core.get("platforms", []))
        if not platforms:
            platforms = self._source_platforms_from_spec(self.source_spec)
        if not platforms:
            platforms = self._source_platforms_from_bindings(bindings)

        protocols = self._source_protocols_from_bindings(bindings)

        return {
            "repo_path": self._resolve_path(source_repo) if source_repo else None,
            "commit": str(ha_core.get("commit", self.source_spec.get("commit", "HEAD"))),
            "domains": domains,
            "platforms": platforms,
            "protocols": protocols,
            "files": files,
            "entrypoints": entrypoints,
            "file_bindings": [binding.__dict__ for binding in bindings],
        }

    def _normalize_validation(self) -> Dict[str, Any]:
        validation = deepcopy(self.vdev_spec.get("validation", {})) if isinstance(self.vdev_spec.get("validation", {}), dict) else {}

        run_validation = self.run_spec.get("validation", {})
        if isinstance(run_validation, dict):
            validation = self._deep_merge_dict(validation, run_validation)

        observation = self.run_spec.get("observation", {})
        if isinstance(observation, dict):
            base_observation = validation.get("observation", {})
            if not isinstance(base_observation, dict):
                base_observation = {}
            merged = self._deep_merge_dict(
                {
                    "canonicalization_version": "v1",
                    "equivalence_whitelist": [],
                    "semantic_ops": [],
                },
                base_observation,
            )
            merged = self._deep_merge_dict(merged, observation)
            validation["observation"] = merged

        sampling = self.run_spec.get("sampling", {})
        if isinstance(sampling, dict):
            validation["sampling"] = self._deep_merge_dict(
                validation.get("sampling", {}) if isinstance(validation.get("sampling", {}), dict) else {},
                sampling,
            )

        fault_model = self.run_spec.get("fault_model", {})
        if isinstance(fault_model, dict):
            validation["fault_model"] = self._deep_merge_dict(
                validation.get("fault_model", {}) if isinstance(validation.get("fault_model", {}), dict) else {},
                fault_model,
            )

        profile_version = self.run_spec.get("profile_version")
        if profile_version:
            validation["profile_version"] = profile_version

        return validation

    @staticmethod
    def _normalize_dependencies(rows: List[Dict[str, Any]], action_ids: set[str], dep_kind: str) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for idx, dep in enumerate(rows):
            before = str(dep.get("before", "")).strip()
            after = str(dep.get("after", "")).strip()
            if not before or not after:
                raise VDevSpecError(f"{dep_kind} dependency[{idx}] must include before/after")
            if before == after:
                raise VDevSpecError(f"{dep_kind} dependency[{idx}] cannot reference identical before/after '{before}'")
            if before not in action_ids or after not in action_ids:
                raise VDevSpecError(
                    f"{dep_kind} dependency[{idx}] references unknown action_id: {before}->{after}; "
                    f"known actions={sorted(action_ids)}"
                )
            row = dict(dep)
            row["before"] = before
            row["after"] = after
            normalized.append(row)
        return normalized

    def build_target(self) -> ScopingArtifacts:
        meta = self.vdev_spec.get("meta", {})
        if not meta.get("vdev_id"):
            raise VDevSpecError("vdev_spec.meta.vdev_id is required")

        bindings = list(self._iter_source_bindings(self.source_spec))
        source_scope = self._normalize_source_scope(bindings)
        actions, target_anchors, critical_ids = self._normalize_actions()
        action_ids = {str(action.get("action_id", "")).strip() for action in actions if str(action.get("action_id", "")).strip()}

        dependencies = self.vdev_spec.get("vdev", {}).get("dependencies", {})
        hard_rows = list(dependencies.get("hard", [])) if isinstance(dependencies, dict) else []
        soft_rows = list(dependencies.get("soft", [])) if isinstance(dependencies, dict) else []
        hard_deps = self._normalize_dependencies(hard_rows, action_ids, dep_kind="hard")
        soft_deps = self._normalize_dependencies(soft_rows, action_ids, dep_kind="soft")

        validation = self._normalize_validation()
        constraints = dict(self.vdev_spec.get("constraints", {})) if isinstance(self.vdev_spec.get("constraints", {}), dict) else {}
        source_protocols = list(source_scope.get("protocols", []))
        if source_protocols:
            validation.setdefault("source_protocols", source_protocols)
            constraints.setdefault("source_protocols", source_protocols)

        target = OptimizationTarget(
            meta=dict(meta),
            source_scope=source_scope,
            vdev_actions=actions,
            target_anchors=target_anchors,
            entrypoint=dict(self.vdev_spec.get("vdev", {}).get("entrypoint", {})),
            objectives=dict(self.vdev_spec.get("objectives", {})),
            constraints=constraints,
            validation=validation,
            hard_dependencies=hard_deps,
            soft_dependencies=soft_deps,
            critical_action_ids=critical_ids,
        )
        ensure_optimization_target(target)
        validate_target_action_primitives(target)
        return ScopingArtifacts(optimization_target=target, source_bindings=bindings)


def build_optimization_target(
    vdev_spec_path: str | Path,
    source_spec_path: str | Path,
    run_spec_path: str | Path | None = None,
    out_path: str | Path | None = None,
) -> OptimizationTarget:
    engine = VDevScopingEngine.from_files(vdev_spec_path, source_spec_path, run_spec_path)
    artifacts = engine.build_target()
    if out_path:
        dump_json(out_path, artifacts.optimization_target)
    return artifacts.optimization_target
