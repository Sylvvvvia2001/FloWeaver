from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, List

from dsl.contracts import (
    Batch,
    ExecutionPlan,
    HAPProfile,
    Marker,
    OptimizationTarget,
    ReducedGraph,
    Rule,
    TypedDAG,
    ensure_optimization_target,
    now_utc_iso,
    to_dict,
)
from dsl.io import dump_json, load_json
from optimizer.action_primitives import validate_target_action_primitives
from optimizer.m1_detector_builder import (
    DetectorBuilderLLMError,
    _action_bindings,
    _preferred_family,
    _preferred_runtime_roles,
    _sha256_json,
    _source_bindings,
    _source_file_summary,
    build_llm_fallback_from_heuristic_draft,
    build_detector_profile_draft,
    build_unresolved_grounding_report,
    generate_detector_profile_draft_with_llm,
)
from optimizer.dependency_graph_builder import DAGBuildDiagnostics, DependencyGraphBuilder
from optimizer.equivalence_validator import EquivalenceValidator
from optimizer.generated_routine_assembler import VDevComponentArtifact, VDevCustomComponentAssembler
from optimizer.macro_level_scheduler import MacroLevelScheduler
from optimizer.micro_level_scheduler import MicroLevelScheduler
from optimizer.routine_interpreter import RoutineInterpreter
from optimizer.semantic_marker import MarkerSet, detect_markers
from optimizer.semantic_primitive_extractor import (
    MSSUBuildResult,
    MSSUBuilder,
    ReductionResult,
    TempoSpatialReducer,
)
from runtime.events import EventRecorder
from runtime.replay import ReplayResult, replay_scenarios
from runtime.scenarios import default_scenarios, scenarios_from_config


@dataclass
class OptimizerArtifacts:
    optimization_target: OptimizationTarget
    marker_set: MarkerSet
    reduction: ReductionResult
    mssu_result: MSSUBuildResult
    dag_diagnostics: DAGBuildDiagnostics
    component_assembly: VDevComponentArtifact
    trust_summary: Dict[str, Any]


class GroundingCoverageError(RuntimeError):
    pass


class FloWeaverOptimizer:
    def __init__(
        self,
        integration_name: str,
        profile_path: str | Path,
        out_dir: str | Path,
        integration_path: str | Path | None = None,
        vdev_spec_path: str | Path | None = None,
        source_spec_path: str | Path | None = None,
        run_spec_path: str | Path | None = None,
        optimization_target_path: str | Path | None = None,
        rollback_max_steps: int = 6,
        hardening_min_pass_rate: float = 0.98,
        hardening_min_coverage: float = 0.85,
    ) -> None:
        self.integration_name = integration_name
        self.integration_path = Path(integration_path) if integration_path else None
        self.profile_path = Path(profile_path)
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.vdev_spec_path = Path(vdev_spec_path) if vdev_spec_path else None
        self.source_spec_path = Path(source_spec_path) if source_spec_path else None
        self.run_spec_path = Path(run_spec_path) if run_spec_path else None
        self.optimization_target_path = Path(optimization_target_path) if optimization_target_path else None
        self.rollback_max_steps = int(rollback_max_steps)
        self.hardening_min_pass_rate = float(hardening_min_pass_rate)
        self.hardening_min_coverage = float(hardening_min_coverage)

    @staticmethod
    def _llm_detector_settings(optimization_target: OptimizationTarget) -> Dict[str, Any]:
        validation = optimization_target.validation if isinstance(optimization_target.validation, dict) else {}
        cfg = validation.get("llm_detector", {}) if isinstance(validation.get("llm_detector", {}), dict) else {}
        enabled = bool(cfg.get("enabled", True))
        return {
            "enabled": enabled,
            "api_base_url": str(
                cfg.get("api_base_url")
                or os.environ.get("FLOWEAVER_LLM_API_BASE_URL")
                or ""
            ).strip(),
            "api_key": str(
                cfg.get("api_key")
                or os.environ.get("FLOWEAVER_LLM_API_KEY")
                or ""
            ).strip(),
            "model": str(cfg.get("model") or os.environ.get("FLOWEAVER_LLM_MODEL") or "gpt-5").strip(),
            "timeout_s": int(cfg.get("timeout_s") or os.environ.get("FLOWEAVER_LLM_TIMEOUT_S") or 300),
            "max_attempts": int(cfg.get("max_attempts") or os.environ.get("FLOWEAVER_LLM_MAX_ATTEMPTS") or 0),
            "retry_backoff_s": float(cfg.get("retry_backoff_s") or os.environ.get("FLOWEAVER_LLM_RETRY_BACKOFF_S") or 0.75),
        }

    @classmethod
    def _should_try_llm_detector(cls, optimization_target: OptimizationTarget) -> bool:
        settings = cls._llm_detector_settings(optimization_target)
        return bool(settings["enabled"] and settings["api_base_url"] and settings["api_key"])

    @staticmethod
    def _write_detector_profile_drafts(out_dir: Path, llm_draft: Dict[str, Any]) -> List[str]:
        drafts = [
            row for row in llm_draft.get("detector_profile_drafts", [])
            if isinstance(row, dict) and row.get("runtime_families")
        ]
        if not drafts:
            return []
        profile_dir = out_dir / "m1_grounding_profiles_auto"
        profile_dir.mkdir(parents=True, exist_ok=True)
        written: List[str] = []
        for idx, draft in enumerate(drafts):
            integration = str(draft.get("integration", "")).strip().lower() or f"profile_{idx:02d}"
            path = profile_dir / f"{integration}.json"
            dump_json(path, draft)
            written.append(str(path))
        return written

    @staticmethod
    def _target_with_grounding_profiles(
        optimization_target: OptimizationTarget,
        grounding_profile_paths: List[str],
    ) -> OptimizationTarget:
        updated = deepcopy(optimization_target)
        validation = dict(updated.validation) if isinstance(updated.validation, dict) else {}
        existing = validation.get("grounding_profile_paths", [])
        rows = list(existing) if isinstance(existing, list) else ([existing] if existing else [])
        for path in grounding_profile_paths:
            token = str(path).strip()
            if token and token not in rows:
                rows.append(token)
        validation["grounding_profile_paths"] = rows
        updated.validation = validation
        return updated

    def _llm_detector_cache_root(self) -> Path:
        root = self.out_dir.parent / "_llm_detector_cache"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _llm_detector_cache_path(self, unresolved_report: Dict[str, Any]) -> Path:
        source_hash = str(unresolved_report.get("source_report_sha256", "")).strip() or _sha256_json(unresolved_report)
        return self._llm_detector_cache_root() / f"{source_hash}.json"

    def _load_cached_llm_detector_draft(self, unresolved_report: Dict[str, Any]) -> Dict[str, Any] | None:
        path = self._llm_detector_cache_path(unresolved_report)
        if not path.exists():
            return None
        try:
            payload = load_json(path)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        expected = str(unresolved_report.get("source_report_sha256", "")).strip() or _sha256_json(unresolved_report)
        actual = str(payload.get("source_report_sha256", "")).strip()
        if actual != expected:
            return None
        return payload

    def _write_cached_llm_detector_draft(self, unresolved_report: Dict[str, Any], llm_detector_draft: Dict[str, Any]) -> None:
        if not isinstance(llm_detector_draft, dict):
            return
        path = self._llm_detector_cache_path(unresolved_report)
        dump_json(path, llm_detector_draft)

    def _run_m1_stage(
        self,
        profile: HAPProfile,
        optimization_target: OptimizationTarget,
        source_files: List[Path],
    ) -> tuple[MarkerSet, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        marker_sets: List[MarkerSet] = [
            detect_markers(path=file_path, profile=profile, optimization_target=optimization_target)
            for file_path in source_files
        ]
        marker_set = self._merge_marker_sets(marker_sets)
        marker_grounding = self._marker_grounding_summary(marker_set, optimization_target)
        marker_set.diagnostics.update(marker_grounding)
        unresolved_report = build_unresolved_grounding_report(
            optimization_target,
            marker_grounding,
            marker_set.markers,
        )
        detector_profile_draft = build_detector_profile_draft(unresolved_report)
        return marker_set, marker_grounding, unresolved_report, detector_profile_draft

    @staticmethod
    def _summary_support_score(summary: Dict[str, Any], preferred_roles: set[str], family: str) -> int:
        if not summary:
            return 0
        family_n = str(family or "").strip().upper()
        path_signal_summary = [
            str(item).strip()
            for item in summary.get("path_signal_summary", [])
            if str(item).strip()
        ]
        score = 0
        if "runtime_read" in preferred_roles:
            score += 4 * len(summary.get("runtime_read_candidate_functions", []))
            score += sum(
                1
                for item in path_signal_summary
                if item.startswith("update_callback_function:")
                or item.startswith("read_function:")
                or item.startswith("read_call:")
                or item.startswith("refresh_call:")
                or item.startswith("awaited_refresh_call:")
            )
            if summary.get("shared_accessor_signals"):
                score += 2
            if any(
                item.startswith("state_accessor_property:") or item.startswith("state_accessor_call:")
                for item in path_signal_summary
            ):
                score += 1
        if "runtime_write" in preferred_roles:
            if family_n == "STATE_WRITE":
                score += sum(
                    2
                    for item in path_signal_summary
                    if item.startswith("state_write_function:")
                    or item.startswith("state_write_call:")
                    or item.startswith("awaited_state_write_call:")
                )
            else:
                score += 4 * len(summary.get("runtime_write_candidate_functions", []))
                score += sum(
                    1
                    for item in path_signal_summary
                    if item.startswith("state_write_function:") or item.startswith("state_write_call:")
                )
        if "runtime_connect" in preferred_roles:
            score += 4 * len(summary.get("runtime_connect_candidate_functions", []))
        if "runtime_subscribe" in preferred_roles:
            score += 4 * len(summary.get("runtime_subscribe_candidate_functions", []))
        return int(score)

    @staticmethod
    def _summary_runtime_carrier_strength(summary: Dict[str, Any], preferred_roles: set[str], family: str) -> int:
        if not summary:
            return 0
        family_n = str(family or "").strip().upper()
        file_stem = Path(str(summary.get("file_path", ""))).stem.strip().lower()
        candidate_names = {
            str(name).strip().lower()
            for name in summary.get("runtime_candidate_functions", [])
            if str(name).strip()
        }
        read_candidate_names = {
            str(name).strip().lower()
            for name in summary.get("runtime_read_candidate_functions", [])
            if str(name).strip()
        }
        write_candidate_names = {
            str(name).strip().lower()
            for name in summary.get("runtime_write_candidate_functions", [])
            if str(name).strip()
        }
        path_signal_summary = [
            str(item).strip().lower()
            for item in summary.get("path_signal_summary", [])
            if str(item).strip()
        ]
        representative_functions = (
            summary.get("representative_functions", [])
            if isinstance(summary.get("representative_functions", []), list)
            else []
        )

        strength = 0
        if "runtime_read" in preferred_roles:
            update_names = {
                "_async_update_data",
                "async_update_data",
                "async_update",
                "_async_update",
                "async_update_status",
                "_async_update_status",
            }
            if read_candidate_names & update_names:
                strength += 6
            if file_stem == "coordinator" and read_candidate_names:
                strength += 5
            if any(
                item.startswith("update_callback_function:")
                for item in path_signal_summary
            ) and any(
                item.startswith("state_write_function:")
                or item.startswith("state_write_call:")
                or item.startswith("awaited_state_write_call:")
                for item in path_signal_summary
            ):
                strength += 5
            for row in representative_functions:
                if not isinstance(row, dict):
                    continue
                row_name = str(row.get("function_name", "")).strip().lower()
                row_signals = [
                    str(item).strip().lower()
                    for item in row.get("path_signals", [])
                    if str(item).strip()
                ]
                if row_name in update_names and not any(
                    item.startswith("control_function:")
                    or item.startswith("control_call:")
                    or item.startswith("awaited_control_call:")
                    for item in row_signals
                ):
                    strength += 3
                    break

        if "runtime_write" in preferred_roles:
            if family_n == "STATE_WRITE":
                if any(
                    item.startswith("state_write_function:")
                    or item.startswith("state_write_call:")
                    or item.startswith("awaited_state_write_call:")
                    for item in path_signal_summary
                ):
                    strength += 6
            elif write_candidate_names or any(
                item.startswith("control_function:")
                or item.startswith("control_call:")
                or item.startswith("awaited_control_call:")
                for item in path_signal_summary
            ):
                strength += 5

        if "runtime_connect" in preferred_roles and (
            summary.get("runtime_connect_candidate_functions")
            or any(item.startswith("connect_call:") for item in path_signal_summary)
        ):
            strength += 4
        if "runtime_subscribe" in preferred_roles and (
            summary.get("runtime_subscribe_candidate_functions")
            or any(item.startswith("subscription_call:") for item in path_signal_summary)
        ):
            strength += 4

        if candidate_names <= {"async_migrate"}:
            strength -= 4
        return max(0, int(strength))

    def _expand_target_runtime_carriers(self, optimization_target: OptimizationTarget) -> OptimizationTarget:
        target = deepcopy(optimization_target)
        source_scope = deepcopy(target.source_scope if isinstance(target.source_scope, dict) else {})
        files = [str(Path(path).expanduser().resolve()) for path in source_scope.get("files", []) if str(path).strip()]
        file_bindings = [dict(row) for row in _source_bindings(target)]
        if not files or not file_bindings:
            return target

        summary_cache: Dict[tuple[str, str], Dict[str, Any]] = {}

        def _summary_for(file_path: str, integration: str) -> Dict[str, Any]:
            key = (str(Path(file_path).expanduser().resolve()), str(integration).strip().lower())
            if key not in summary_cache:
                summary_cache[key] = _source_file_summary(key[0], key[1])
            return summary_cache[key]

        existing_files = set(files)
        existing_binding_keys = {
            (
                str(row.get("device_id", "")).strip(),
                str(row.get("integration", "")).strip().lower(),
                str(Path(str(row.get("file_path", "")).strip()).expanduser().resolve()),
            )
            for row in file_bindings
            if str(row.get("device_id", "")).strip() and str(row.get("integration", "")).strip() and str(row.get("file_path", "")).strip()
        }
        added = False

        for action in target.vdev_actions:
            if not isinstance(action, dict):
                continue
            action_bindings = _action_bindings(action, file_bindings)
            if not action_bindings:
                continue
            family = _preferred_family(action)
            preferred_roles = {
                str(item).strip().lower()
                for item in _preferred_runtime_roles(action, family)
                if str(item).strip()
            }
            current_rows: List[tuple[int, int]] = []
            for row in action_bindings:
                file_path = str(row.get("file_path", "")).strip()
                integration = str(row.get("integration", "")).strip().lower()
                if not file_path or not integration:
                    continue
                summary = _summary_for(file_path, integration)
                current_rows.append(
                    (
                        self._summary_runtime_carrier_strength(summary, preferred_roles, family),
                        self._summary_support_score(summary, preferred_roles, family),
                    )
                )
            if any(strength > 0 for strength, _ in current_rows):
                continue

            candidate_rows: List[tuple[int, int, str, str]] = []
            seen_candidates: set[str] = set()
            for row in action_bindings:
                base_file = Path(str(row.get("file_path", "")).strip()).expanduser().resolve()
                integration = str(row.get("integration", "")).strip().lower()
                device_id = str(row.get("device_id", "")).strip()
                if not base_file.exists() or not integration:
                    continue
                for sibling in sorted(base_file.parent.glob("*.py")):
                    candidate_path = str(sibling.resolve())
                    binding_key = (device_id, integration, candidate_path)
                    if binding_key in existing_binding_keys or candidate_path in seen_candidates:
                        continue
                    seen_candidates.add(candidate_path)
                    summary = _summary_for(candidate_path, integration)
                    strength = self._summary_runtime_carrier_strength(summary, preferred_roles, family)
                    score = self._summary_support_score(summary, preferred_roles, family)
                    if strength <= 0 and score <= 0:
                        continue
                    candidate_rows.append((strength, score, candidate_path, integration))

            candidate_rows.sort(key=lambda item: (-int(item[0]), -int(item[1]), item[2]))
            if not candidate_rows:
                continue

            template = dict(action_bindings[0])
            for _, _, candidate_path, integration in candidate_rows[:2]:
                binding_row = dict(template)
                binding_row["file_path"] = candidate_path
                binding_row["integration"] = integration
                file_bindings.append(binding_row)
                existing_binding_keys.add(
                    (
                        str(binding_row.get("device_id", "")).strip(),
                        integration,
                        candidate_path,
                    )
                )
                existing_files.add(candidate_path)
                added = True

        if not added:
            return target

        source_scope["files"] = sorted(existing_files)
        source_scope["file_bindings"] = file_bindings
        target.source_scope = source_scope
        return target

    def _load_profile(self) -> HAPProfile:
        raw = load_json(self.profile_path)
        rules = [Rule(**rule) for rule in raw.get("rules", [])]
        return HAPProfile(
            profile_id=raw["profile_id"],
            schema_version=raw["schema_version"],
            created_at=raw["created_at"],
            provenance=raw.get("provenance", {}),
            marker_detectors=raw.get("marker_detectors", []),
            lifecycle_templates=raw.get("lifecycle_templates", []),
            rules=rules,
        )

    @staticmethod
    def _raw_to_target(raw: Dict[str, Any]) -> OptimizationTarget:
        target = OptimizationTarget(
            meta=raw.get("meta", {}),
            source_scope=raw.get("source_scope", {}),
            vdev_actions=raw.get("vdev_actions", []),
            target_anchors=raw.get("target_anchors", {}),
            entrypoint=raw.get("entrypoint", {}),
            objectives=raw.get("objectives", {}),
            constraints=raw.get("constraints", {}),
            validation=raw.get("validation", {}),
            hard_dependencies=raw.get("hard_dependencies", []),
            soft_dependencies=raw.get("soft_dependencies", []),
            critical_action_ids=raw.get("critical_action_ids", []),
        )
        ensure_optimization_target(target)
        return target

    def _fallback_target(self) -> OptimizationTarget:
        if self.integration_path is None:
            raise ValueError("integration_path is required when no vdev/source spec is provided")
        target = OptimizationTarget(
            meta={"spec_version": "fallback", "vdev_id": "fallback_vdev", "name": "Fallback VDev"},
            source_scope={
                "repo_path": str(self.integration_path.parent.resolve()),
                "commit": "HEAD",
                "domains": [self.integration_name],
                "platforms": [],
                "files": [str(self.integration_path.resolve())],
                "entrypoints": [{"kind": "function", "name": "async_setup_entry"}],
            },
            vdev_actions=[
                {
                    "action_id": "A0",
                    "type": "write",
                    "protocol": "HA",
                    "target": {"kind": "ha_entity", "id": "sensor.vdev_fallback", "entity_id": "sensor.vdev_fallback"},
                    "exec": {
                        "kind": "ha_service_call",
                        "domain": "homeassistant",
                        "service": "update_entity",
                        "data_template": {"entity_id": "sensor.vdev_fallback"},
                        "blocking": True,
                    },
                    "critical": True,
                    "marker_hints": ["STATE_WRITE"],
                }
            ],
            target_anchors={
                "entities": ["sensor.vdev_fallback"],
                "endpoints": [],
                "characteristics": [],
                "device_ids": [],
                "service_entrypoints": [],
                "anchor_ops": ["STATE_WRITE", "COORD_REFRESH"],
            },
            entrypoint={"kind": "function", "name": "async_setup_entry"},
            objectives={"primary": "minimize_tail_latency", "name": "Fallback VDev"},
            constraints={"optimization_knobs": {"allow_concurrency": True}},
            validation={"differential_tests": {"enabled": True}},
            hard_dependencies=[],
            soft_dependencies=[],
            critical_action_ids=["A0"],
        )
        ensure_optimization_target(target)
        return target

    def _load_target(self) -> OptimizationTarget:
        if self.optimization_target_path:
            target = self._raw_to_target(load_json(self.optimization_target_path))
            validate_target_action_primitives(target)
            dump_json(self.out_dir / "m_minus1_target.json", target)
            return target

        if self.vdev_spec_path and self.source_spec_path:
            engine = RoutineInterpreter.from_files(
                vdev_spec_path=self.vdev_spec_path,
                source_spec_path=self.source_spec_path,
                run_spec_path=self.run_spec_path,
            )
            artifacts = engine.build_target()
            validate_target_action_primitives(artifacts.optimization_target)
            dump_json(self.out_dir / "m_minus1_target.json", artifacts.optimization_target)
            return artifacts.optimization_target

        target = self._fallback_target()
        validate_target_action_primitives(target)
        dump_json(self.out_dir / "m_minus1_target.json", target)
        return target

    @staticmethod
    def _ordered_markers(markers: List[Marker]) -> List[Marker]:
        return sorted(markers, key=lambda m: (m.phase, m.file_path, m.function_name, m.line_start, m.marker_type))

    @staticmethod
    def _marker_target(marker: Marker, target: OptimizationTarget) -> str:
        return FloWeaverOptimizer._marker_target_for_action(marker, None, target)

    @staticmethod
    def _action_observable_target(action: Dict[str, Any]) -> str:
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        data_template = exec_cfg.get("data_template", {}) if isinstance(exec_cfg.get("data_template", {}), dict) else {}

        for key in ("entity_id", "id"):
            value = target.get(key)
            if value:
                return str(value)
        for key in ("entity_id", "device_id", "endpoint", "id"):
            value = data_template.get(key)
            if value:
                return str(value)
        for key in ("entity_id", "endpoint", "device_id"):
            value = exec_cfg.get(key)
            if value:
                return str(value)
        if exec_cfg.get("domain") and exec_cfg.get("service"):
            return f"{exec_cfg['domain']}.{exec_cfg['service']}"
        return str(action.get("action_id", "unknown_action"))

    @classmethod
    def _marker_target_for_action(
        cls,
        marker: Marker,
        action: Dict[str, Any] | None,
        target: OptimizationTarget,
    ) -> str:
        if action:
            return cls._action_observable_target(action)
        if marker.marker_type == "STATE_WRITE" and target.target_anchors.get("entities"):
            return target.target_anchors["entities"][0]
        if marker.marker_type in {
            "CLOUD_OP",
            "CLOUD_HTTP_CALL",
            "CLOUD_TOKEN_REFRESH",
            "CLOUD_BACKOFF_SLEEP",
            "CLOUD_BATCH_CALL",
            "CLOUD_SESSION_REUSE",
            "CLOUD_429_CHECK",
        } and target.target_anchors.get("endpoints"):
            return target.target_anchors["endpoints"][0]
        if marker.marker_type in {
            "BLE_OP",
            "BLE_CONNECT",
            "BLE_DISCONNECT",
            "BLE_GATT_OP",
            "BLE_SCAN",
            "BLE_RETRY_OR_TIMEOUT",
        } and target.target_anchors.get("device_ids"):
            return target.target_anchors["device_ids"][0]
        return f"{marker.function_name}:{marker.line_start}"

    @staticmethod
    def _plan_order(plan: Any) -> List[str]:
        if isinstance(plan, ExecutionPlan):
            return EquivalenceValidator._plan_execution_order(plan)
        ordered: List[str] = []
        for batch in plan.ordered_batches:
            for group in batch.parallel_groups:
                ordered.extend(str(node) for node in group)
        return ordered

    @staticmethod
    def _action_index(target: OptimizationTarget) -> Dict[str, Dict[str, Any]]:
        return {
            str(action.get("action_id")): action
            for action in target.vdev_actions
            if action.get("action_id")
        }

    @staticmethod
    def _action_target(action: Dict[str, Any]) -> str:
        return FloWeaverOptimizer._action_observable_target(action)

    @staticmethod
    def _action_op(action: Dict[str, Any]) -> str:
        hints = action.get("marker_hints", [])
        if hints:
            return str(hints[0])
        protocol = str(action.get("protocol", "HA")).upper()
        if protocol == "BLE":
            return "BLE_GATT_OP"
        if protocol == "CLOUD":
            return "CLOUD_HTTP_CALL"
        if str(action.get("type", "")).lower() == "write":
            return "STATE_WRITE"
        return "ACTION_EXEC"

    @staticmethod
    def _action_provider(action: Dict[str, Any]) -> str:
        protocol = str(action.get("protocol", "HA")).upper()
        if protocol == "MQTT":
            return "LOCAL"
        if protocol in {"BLE", "CLOUD", "HA", "LOCAL"}:
            return protocol
        return "SYS"

    @staticmethod
    def _marker_owner_action(marker: Marker) -> str:
        primary = str(getattr(marker, "primary_action_id", "") or "").strip()
        if primary:
            return primary
        refs = [
            str(action_id).strip()
            for action_id in getattr(marker, "related_action_ids", [])
            if str(action_id).strip()
        ]
        if len(refs) == 1:
            return refs[0]
        return ""

    @classmethod
    def _primary_action_marker_mapping(cls, ordered_markers: List[Marker], target: OptimizationTarget) -> Dict[str, List[Marker]]:
        actions = cls._action_index(target)
        mapping: Dict[str, List[Marker]] = {action_id: [] for action_id in actions}
        for marker in ordered_markers:
            owner = cls._marker_owner_action(marker)
            if owner in mapping:
                mapping[owner].append(marker)
        return mapping

    @classmethod
    def _baseline_action_order(cls, ordered_markers: List[Marker], target: OptimizationTarget) -> List[str]:
        del ordered_markers
        actions = list(cls._action_index(target).keys())
        if not actions:
            return []

        rank = {action_id: idx for idx, action_id in enumerate(actions)}
        outgoing: Dict[str, Set[str]] = {action_id: set() for action_id in actions}
        indegree: Dict[str, int] = {action_id: 0 for action_id in actions}

        for dep in target.hard_dependencies:
            before = str(dep.get("before", "") or "").strip()
            after = str(dep.get("after", "") or "").strip()
            if not before or not after or before == after:
                continue
            if before not in outgoing or after not in indegree:
                continue
            if after in outgoing[before]:
                continue
            outgoing[before].add(after)
            indegree[after] += 1

        ready = sorted([action_id for action_id in actions if indegree[action_id] == 0], key=lambda action_id: (rank[action_id], action_id))
        ordered: List[str] = []
        while ready:
            action_id = ready.pop(0)
            ordered.append(action_id)
            for nxt in sorted(outgoing.get(action_id, set()), key=lambda item: (rank.get(item, 10_000), item)):
                indegree[nxt] = max(0, indegree.get(nxt, 0) - 1)
                if indegree[nxt] == 0 and nxt not in ordered and nxt not in ready:
                    ready.append(nxt)
            ready.sort(key=lambda item: (rank.get(item, 10_000), item))

        if len(ordered) != len(actions):
            remaining = [action_id for action_id in actions if action_id not in ordered]
            ordered.extend(remaining)
        return ordered

    def _emit_action_markers(
        self,
        rec: EventRecorder,
        scenario: Any,
        action_id: str,
        action: Dict[str, Any],
        markers: List[Marker],
        target: OptimizationTarget,
    ) -> None:
        params = {"scenario": scenario.scenario_id, "action_id": action_id}
        if markers:
            for marker in markers:
                rec.emit(
                    provider=self._action_provider(action),
                    op=marker.marker_type,
                    target=self._marker_target_for_action(marker, action, target),
                    params_abst=params,
                    phase=marker.phase,
                )
            return
        rec.emit(
            provider=self._action_provider(action),
            op=self._action_op(action),
            target=self._action_target(action),
            params_abst=params,
            phase="RUNTIME",
        )

    def _simulate_baseline_runner(self, ordered_markers: List[Marker], target: OptimizationTarget):
        action_index = self._action_index(target)
        action_markers = self._primary_action_marker_mapping(ordered_markers, target)
        baseline_action_order = self._baseline_action_order(ordered_markers, target)

        def runner(rec: EventRecorder, scenario: Any) -> None:
            for action_id in baseline_action_order:
                action = action_index.get(action_id)
                if action is None:
                    continue
                self._emit_action_markers(rec, scenario, action_id, action, action_markers.get(action_id, []), target)

        return runner

    @staticmethod
    def _marker_action_refs(marker: Marker) -> List[str]:
        primary = str(getattr(marker, "primary_action_id", "") or "").strip()
        secondary = [
            str(action_id).strip()
            for action_id in getattr(marker, "secondary_action_ids", [])
            if str(action_id).strip()
        ]
        is_shared = bool(
            secondary
            or str(getattr(marker, "marker_type", "")).strip().upper()
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
        if primary:
            refs = [primary]
            if is_shared:
                refs.extend(secondary)
            return sorted(set(refs))
        return sorted(
            {
                str(action_id).strip()
                for action_id in getattr(marker, "related_action_ids", [])
                if str(action_id).strip()
            }
        )

    @staticmethod
    def _marker_matches_action_hint(marker_type: str, action_hints: List[Any]) -> bool:
        marker = str(marker_type).strip().upper()
        hints = {str(item).strip().upper() for item in action_hints if str(item).strip()}
        if marker in hints:
            return True
        if marker.startswith("BLE_") and "BLE_OP" in hints:
            return True
        if marker.startswith("CLOUD_") and "CLOUD_OP" in hints:
            return True
        if marker in {"COORD_REFRESH", "COORD_FIRST_REFRESH"} and ({"COORD_REFRESH", "COORD_FIRST_REFRESH"} & hints):
            return True
        return False

    @classmethod
    def _marker_action_refs_for_coverage(cls, marker: Marker, target: OptimizationTarget) -> List[str]:
        explicit = cls._marker_action_refs(marker)
        if explicit:
            return explicit
        candidates: List[str] = []
        for action in target.vdev_actions:
            action_id = str(action.get("action_id", "")).strip()
            if not action_id:
                continue
            if cls._marker_matches_action_hint(str(getattr(marker, "marker_type", "")), action.get("marker_hints", [])):
                candidates.append(action_id)
        return [candidates[0]] if len(candidates) == 1 else []

    def _action_marker_mapping(self, ordered_markers: List[Marker], target: OptimizationTarget) -> Dict[str, List[Marker]]:
        actions = self._action_index(target)
        mapping: Dict[str, List[Marker]] = {action_id: [] for action_id in actions}

        for action_id, action in actions.items():
            hints = {str(item).upper() for item in action.get("marker_hints", [])}
            target_key = self._action_target(action)
            for marker in ordered_markers:
                marker_refs = self._marker_action_refs(marker)
                if action_id in marker_refs:
                    mapping[action_id].append(marker)
                    continue
                if marker_refs:
                    continue
                marker_match = marker.marker_type.upper() in hints
                target_match = self._marker_target(marker, target) == target_key
                if marker_match or target_match:
                    mapping[action_id].append(marker)

        return mapping

    def _simulate_optimized_runner(self, ordered_markers: List[Marker], plan: Any, target: OptimizationTarget):
        action_order = self._plan_order(plan)
        action_index = self._action_index(target)
        action_markers = self._primary_action_marker_mapping(ordered_markers, target)

        def runner(rec: EventRecorder, scenario: Any) -> None:
            for action_id in action_order:
                action = action_index.get(action_id)
                if action is None:
                    continue
                self._emit_action_markers(rec, scenario, action_id, action, action_markers.get(action_id, []), target)

        return runner

    @staticmethod
    def _merge_marker_sets(marker_sets: List[MarkerSet]) -> MarkerSet:
        markers = [marker for marker_set in marker_sets for marker in marker_set.markers]
        index: Dict[str, List[str]] = {}
        direct = 0
        alias = 0
        grounding_profile_loaded_paths = set()
        grounding_profile_rule_count = 0
        grounding_profile_file_rule_count = 0
        grounding_profile_match_count = 0
        for marker_set in marker_sets:
            for fn_name, ids in marker_set.index_by_function.items():
                index.setdefault(fn_name, []).extend(ids)
            match_counts = marker_set.diagnostics.get("match_counts", {}) if isinstance(marker_set.diagnostics, dict) else {}
            direct += int(match_counts.get("direct", 0))
            alias += int(match_counts.get("alias", 0))
            grounding_profile_loaded_paths |= {
                str(item)
                for item in marker_set.diagnostics.get("grounding_profile_loaded_paths", [])
                if str(item).strip()
            }
            grounding_profile_rule_count = max(
                grounding_profile_rule_count,
                int(marker_set.diagnostics.get("grounding_profile_rule_count", 0) or 0),
            )
            grounding_profile_file_rule_count += int(marker_set.diagnostics.get("grounding_profile_file_rule_count", 0) or 0)
            grounding_profile_match_count += int(marker_set.diagnostics.get("grounding_profile_match_count", 0) or 0)
        total = direct + alias
        diagnostics = {
            "match_counts": {"direct": direct, "alias": alias, "total": total},
            "alias_precision_estimate": round((0.9 * alias + direct) / total, 4) if total else 1.0,
            "grounding_profile_loaded_paths": sorted(grounding_profile_loaded_paths),
            "grounding_profile_rule_count": grounding_profile_rule_count,
            "grounding_profile_file_rule_count": grounding_profile_file_rule_count,
            "grounding_profile_match_count": grounding_profile_match_count,
        }
        return MarkerSet(markers=markers, index_by_function=index, diagnostics=diagnostics)

    @staticmethod
    def _merge_reductions(reductions: List[ReductionResult]) -> ReductionResult:
        merged_graph = ReducedGraph(nodes={}, edges=[], mapping={})
        marker_to_nodes: Dict[str, List[str]] = {}
        kept = set()
        for item in reductions:
            merged_graph.nodes.update(item.reduced_graph.nodes)
            merged_graph.edges.extend(item.reduced_graph.edges)
            merged_graph.mapping.update(item.reduced_graph.mapping)
            marker_to_nodes.update(item.marker_to_nodes)
            kept |= set(item.kept_node_ids)
        return ReductionResult(reduced_graph=merged_graph, marker_to_nodes=marker_to_nodes, kept_node_ids=kept)

    @staticmethod
    def _merge_mssu_results(results: List[MSSUBuildResult]) -> MSSUBuildResult:
        mssus = []
        internal: Dict[str, List[Any]] = {}
        deps = set()
        for result in results:
            mssus.extend(result.mssus)
            internal.update(result.mssu_internal_edges)
            deps |= set(result.dependency_candidates)
        return MSSUBuildResult(mssus=mssus, mssu_internal_edges=internal, dependency_candidates=sorted(deps))

    @staticmethod
    def _critical_action_ids(target: OptimizationTarget) -> List[str]:
        critical_ids = [str(item) for item in target.critical_action_ids if str(item).strip()]
        if critical_ids:
            return sorted(set(critical_ids))
        return sorted(
            {
                str(action.get("action_id", "")).strip()
                for action in target.vdev_actions
                if str(action.get("action_id", "")).strip() and bool(action.get("critical", False))
            }
        )

    @staticmethod
    def _allow_partial_target_grounding(target: OptimizationTarget) -> bool:
        constraints = target.constraints if isinstance(target.constraints, dict) else {}
        knobs = constraints.get("optimization_knobs", {}) if isinstance(constraints.get("optimization_knobs", {}), dict) else {}
        if bool(knobs.get("allow_partial_target_grounding")):
            return True
        validation = target.validation if isinstance(target.validation, dict) else {}
        return bool(validation.get("allow_partial_target_grounding"))

    @staticmethod
    def _module_enabled(target: OptimizationTarget, module_name: str, default: bool = True) -> bool:
        validation = target.validation if isinstance(target.validation, dict) else {}
        modules = validation.get("modules", {}) if isinstance(validation.get("modules", {}), dict) else {}
        constraints = target.constraints if isinstance(target.constraints, dict) else {}
        knobs = constraints.get("optimization_knobs", {}) if isinstance(constraints.get("optimization_knobs", {}), dict) else {}
        aliases = {
            "routine_interpreter": ("m_minus1", "scoping", "vdev_spec_ingestion"),
            "primitive_extractor": ("m1_to_m3", "m1_m2_m3"),
            "semantic_marker": ("m1", "m1_grounding", "grounding", "marker_grounding", "detector_builder"),
            "semantic_primitive_extractor": ("m2", "m3", "m2_tempo_spatial_reducer", "m3_mssu_builder", "tempo_spatial_reducer", "mssu_builder"),
            "constraint_aware_orchestrator": ("orchestrator", "m4_to_micro", "m4_m5_micro"),
            "dependency_graph_builder": ("m4", "m4_dag_builder", "dag", "dag_builder", "typed_dag"),
            "macro_level_scheduler": ("m5", "m5_macro_scheduler", "macro_scheduler", "coarse_scheduler"),
            "micro_level_scheduler": ("micro_scheduler", "micro_refinement", "combined_micro_refinement"),
            "component_assembler": ("m7", "m7_component_assembler", "assembler", "custom_component_assembler"),
            "equivalence_validator": ("m6", "m6_trust_validator", "trust_validator", "trust_layer"),
        }
        direct_keys = (module_name, module_name.replace("_", "-"), module_name.replace("_", ""))
        for key in direct_keys:
            if key in modules:
                return bool(modules[key])

        alias_values: List[bool] = []
        for key in aliases.get(module_name, ()):
            if key in modules:
                alias_values.append(bool(modules[key]))
        if alias_values:
            return all(alias_values)

        for key in direct_keys + aliases.get(module_name, ()):
            enable_key = f"enable_{key}"
            disable_key = f"disable_{key}"
            if enable_key in knobs:
                return bool(knobs[enable_key])
            if disable_key in knobs:
                return not bool(knobs[disable_key])
        return bool(default)

    @classmethod
    def _module_switches(cls, target: OptimizationTarget) -> Dict[str, bool]:
        primitive_extractor = cls._module_enabled(target, "primitive_extractor", True)
        semantic_marker = primitive_extractor and cls._module_enabled(target, "semantic_marker", True)
        semantic_primitive_extractor = primitive_extractor and cls._module_enabled(target, "semantic_primitive_extractor", True)
        orchestrator = cls._module_enabled(target, "constraint_aware_orchestrator", True)
        return {
            "routine_interpreter": cls._module_enabled(target, "routine_interpreter", True),
            "primitive_extractor": primitive_extractor,
            "semantic_marker": semantic_marker,
            "semantic_primitive_extractor": semantic_primitive_extractor,
            "constraint_aware_orchestrator": orchestrator,
            "dependency_graph_builder": orchestrator and cls._module_enabled(target, "dependency_graph_builder", True),
            "macro_level_scheduler": orchestrator and cls._module_enabled(target, "macro_level_scheduler", True),
            "micro_level_scheduler": orchestrator and cls._module_enabled(target, "micro_level_scheduler", True),
            "component_assembler": cls._module_enabled(target, "component_assembler", True),
            "equivalence_validator": cls._module_enabled(target, "equivalence_validator", True),
        }

    @staticmethod
    def _disabled_reduction() -> ReductionResult:
        return ReductionResult(reduced_graph=ReducedGraph(), marker_to_nodes={}, kept_node_ids=set())

    @staticmethod
    def _disabled_mssu_result(reason: str) -> MSSUBuildResult:
        return MSSUBuildResult(
            mssus=[],
            mssu_internal_edges={},
            dependency_candidates=[],
            build_status="DISABLED",
            summary={
                "build_status": "DISABLED",
                "reason": reason,
                "missing_critical_action_ids": [],
            },
        )

    def _serial_execution_plan(self, target: OptimizationTarget, reason: str, module_switches: Dict[str, bool]) -> ExecutionPlan:
        batches = [
            Batch(
                batch_id=f"serial_{idx:03d}",
                parallel_groups=[[action_id]],
                constraints=[reason],
                guards=[],
                fallback=[{"kind": "module_disabled", "scope": [action_id], "action": "serial_execution", "params": {"reason": reason}}],
            )
            for idx, action_id in enumerate(self._baseline_action_order([], target))
        ]
        action_lanes = {
            str(action.get("action_id", "")): MacroLevelScheduler._action_lane(action)
            for action in target.vdev_actions
            if str(action.get("action_id", "")).strip()
        }
        return ExecutionPlan(
            ordered_batches=batches,
            meta={
                "node_kind": "action_id",
                "scheduler": "serial_ablation",
                "reason": reason,
                "action_lanes": action_lanes,
                "module_switches": dict(module_switches),
            },
        )

    def _disabled_component_artifact(self) -> VDevComponentArtifact:
        out_root = self.out_dir / "reassembly_disabled"
        return VDevComponentArtifact(
            output_root=str(out_root),
            custom_component_dir=str(out_root),
            domain="",
            service_name="",
            manifest_path="",
            init_path="",
            executor_path="",
            services_path="",
            plan_path=str(self.out_dir / "m5_trust_plan.json"),
            target_path="",
            install_doc_path="",
        )

    @staticmethod
    def _marker_has_high_quality_runtime_binding(marker: Marker) -> bool:
        if str(getattr(marker, "phase", "")).upper() != "RUNTIME":
            return False
        primary = str(getattr(marker, "primary_action_id", "") or "").strip()
        if not primary:
            return False
        if float(getattr(marker, "binding_score", 0.0) or 0.0) < 0.75:
            return False
        evidence = {str(item).strip() for item in getattr(marker, "evidence", []) if str(item).strip()}
        if "context_missing:module_hints" in evidence:
            return False
        if any(item.startswith("phase_mismatch:") for item in evidence):
            return False
        return True

    @classmethod
    def _marker_grounding_summary(cls, marker_set: MarkerSet, target: OptimizationTarget) -> Dict[str, Any]:
        critical_ids = cls._critical_action_ids(target)
        resolved_action_ids = sorted(
            {
                str(action_id)
                for marker in marker_set.markers
                for action_id in cls._marker_action_refs_for_coverage(marker, target)
                if str(action_id).strip()
            }
        )
        resolved_runtime_action_ids_raw = sorted(
            {
                str(action_id)
                for marker in marker_set.markers
                if str(getattr(marker, "phase", "")).upper() == "RUNTIME"
                for action_id in cls._marker_action_refs_for_coverage(marker, target)
                if str(action_id).strip()
            }
        )
        resolved_runtime_action_ids = sorted(
            {
                str(getattr(marker, "primary_action_id", "")).strip()
                for marker in marker_set.markers
                if cls._marker_has_high_quality_runtime_binding(marker)
            }
        )
        missing_critical = sorted(set(critical_ids) - set(resolved_action_ids))
        return {
            "marker_coverage_ok": not missing_critical,
            "resolved_action_ids": resolved_action_ids,
            "resolved_runtime_action_ids": resolved_runtime_action_ids,
            "resolved_runtime_action_ids_raw": resolved_runtime_action_ids_raw,
            "critical_action_ids": critical_ids,
            "missing_critical_action_ids": missing_critical,
            "resolved_runtime_action_count": len(resolved_runtime_action_ids),
            "resolved_runtime_action_count_raw": len(resolved_runtime_action_ids_raw),
        }

    @classmethod
    def _reduction_grounding_summary(
        cls,
        reduction: ReductionResult,
        markers: List[Marker],
        target: OptimizationTarget,
    ) -> Dict[str, Any]:
        anchor_node_ids = sorted(
            {
                node_id
                for marker in markers
                if cls._marker_action_refs_for_coverage(marker, target)
                for node_id in reduction.marker_to_nodes.get(marker.marker_id, [])
            }
        )
        return {
            "anchor_nodes": anchor_node_ids,
            "anchor_node_count": len(anchor_node_ids),
        }

    def _source_files(self, target: OptimizationTarget) -> List[Path]:
        files = [Path(path) for path in target.source_scope.get("files", [])]
        missing = [str(path) for path in files if not path.exists()]
        if missing:
            raise ValueError("Missing source file(s) in OptimizationTarget.source_scope.files: " + ", ".join(missing))
        return files

    @staticmethod
    def _offline_runtime_metrics(target: OptimizationTarget) -> Dict[str, Any]:
        validation = target.validation if isinstance(target.validation, dict) else {}
        inline_metrics = validation.get("offline_metrics", {})
        if isinstance(inline_metrics, dict) and inline_metrics:
            return inline_metrics

        metrics_path = validation.get("offline_metrics_path")
        if metrics_path:
            path = Path(str(metrics_path)).expanduser().resolve()
            if not path.exists():
                raise ValueError(f"offline_metrics_path does not exist: {path}")
            payload = load_json(path)
            if not isinstance(payload, dict):
                raise ValueError(f"offline_metrics_path must contain a JSON object: {path}")
            return payload
        return {}

    @staticmethod
    def _mssu_locations(mssu: Any, graph: ReducedGraph) -> List[str]:
        locs: List[str] = []
        for node_id in mssu.node_ids:
            node = graph.nodes.get(node_id)
            if node is None:
                continue
            locs.append(f"{node.file_path}:{node.line_start}")
        deduped = sorted(set(locs))
        return deduped

    @staticmethod
    def _edge_origin(justification: List[str]) -> Dict[str, Any]:
        origin: Dict[str, Any] = {"kind": "derived", "details": list(justification)}
        for item in justification:
            text = str(item)
            if text.startswith("rule_template:"):
                parts = text.split(":")
                if len(parts) >= 3:
                    origin.update({"kind": "rule_template", "rule_id": parts[1], "template_index": parts[2]})
            elif text.startswith("vdev_dep:"):
                origin.update({"kind": "vdev_dependency", "dependency": text.replace("vdev_dep:", "", 1)})
            elif text.startswith("candidate:"):
                origin.update({"kind": "graph_candidate", "candidate_type": text.replace("candidate:", "", 1)})
            elif text.startswith("io:"):
                origin.update({"kind": "io_dependency", "dependency": text})
        return origin

    def _hard_edge_witness(self, dag: Any, graph: ReducedGraph, markers: List[Marker]) -> Dict[str, Any]:
        marker_by_id = {marker.marker_id: marker for marker in markers}
        rows: List[Dict[str, Any]] = []
        for edge in dag.hard_edges:
            src_mssu = dag.nodes.get(edge.src_mssu)
            dst_mssu = dag.nodes.get(edge.dst_mssu)
            if src_mssu is None or dst_mssu is None:
                continue

            src_marker_set: set[str] = set()
            dst_marker_set: set[str] = set()
            for node_id in src_mssu.node_ids:
                node = graph.nodes.get(node_id)
                if node is not None:
                    src_marker_set.update(str(item) for item in node.marker_refs)
            for node_id in dst_mssu.node_ids:
                node = graph.nodes.get(node_id)
                if node is not None:
                    dst_marker_set.update(str(item) for item in node.marker_refs)
            src_marker_ids = sorted(src_marker_set)
            dst_marker_ids = sorted(dst_marker_set)

            def marker_refs(ids: List[str]) -> List[Dict[str, Any]]:
                refs: List[Dict[str, Any]] = []
                for marker_id in ids:
                    marker = marker_by_id.get(marker_id)
                    if marker is None:
                        continue
                    refs.append(
                        {
                            "marker_id": marker.marker_id,
                            "marker_type": marker.marker_type,
                            "location": f"{marker.file_path}:{marker.line_start}",
                        }
                    )
                return refs

            rows.append(
                {
                    "edge": {
                        "src_mssu": edge.src_mssu,
                        "dst_mssu": edge.dst_mssu,
                        "kind": edge.kind,
                    },
                    "origin": self._edge_origin(edge.justification),
                    "src_locations": self._mssu_locations(src_mssu, graph),
                    "dst_locations": self._mssu_locations(dst_mssu, graph),
                    "src_marker_refs": marker_refs(src_marker_ids),
                    "dst_marker_refs": marker_refs(dst_marker_ids),
                }
            )

        return {"edge_count": len(rows), "edges": rows}

    def run(self) -> OptimizerArtifacts:
        profile = self._load_profile()
        optimization_target = self._load_target()
        optimization_target = self._expand_target_runtime_carriers(optimization_target)
        dump_json(self.out_dir / "m_minus1_target.json", optimization_target)
        module_switches = self._module_switches(optimization_target)
        dump_json(
            self.out_dir / "module_switches.json",
            {
                "schema_version": "floweaver_module_switches/v1",
                "created_at": now_utc_iso(),
                "modules": module_switches,
            },
        )

        needs_source_files = any(
            module_switches[name]
            for name in ("semantic_marker", "semantic_primitive_extractor")
        )
        source_files = self._source_files(optimization_target) if needs_source_files else []
        if needs_source_files and not source_files:
            raise ValueError("No valid source files found in OptimizationTarget.source_scope.files")


        llm_detector_draft: Dict[str, Any] | None = None
        if module_switches["semantic_marker"]:
            marker_set, marker_grounding, unresolved_report, detector_profile_draft = self._run_m1_stage(
                profile,
                optimization_target,
                source_files,
            )

            if marker_grounding["missing_critical_action_ids"] and not self._allow_partial_target_grounding(optimization_target):
                if self._should_try_llm_detector(optimization_target):
                    settings = self._llm_detector_settings(optimization_target)
                    llm_detector_draft = self._load_cached_llm_detector_draft(unresolved_report)
                    if llm_detector_draft is None:
                        try:
                            llm_detector_draft = generate_detector_profile_draft_with_llm(
                                unresolved_report,
                                api_base_url=str(settings["api_base_url"]),
                                api_key=str(settings["api_key"]),
                                model=str(settings["model"]),
                                timeout_s=int(settings["timeout_s"]),
                                max_attempts=int(settings["max_attempts"]),
                                retry_backoff_s=float(settings["retry_backoff_s"]),
                            )
                            self._write_cached_llm_detector_draft(unresolved_report, llm_detector_draft)
                        except DetectorBuilderLLMError as exc:
                            llm_detector_draft = build_llm_fallback_from_heuristic_draft(
                                detector_profile_draft,
                                reason=str(exc),
                            )
                            llm_detector_draft["builder_version"] = "pipeline_llm_fallback"
                            llm_detector_draft["llm_error"] = str(exc)
                    dump_json(self.out_dir / "m1_detector_profile_draft_llm.json", llm_detector_draft)
                    grounding_profile_paths = self._write_detector_profile_drafts(self.out_dir, llm_detector_draft)
                    if grounding_profile_paths:
                        optimization_target = self._target_with_grounding_profiles(optimization_target, grounding_profile_paths)
                        marker_set, marker_grounding, unresolved_report, detector_profile_draft = self._run_m1_stage(
                            profile,
                            optimization_target,
                            source_files,
                        )
        else:
            marker_set = MarkerSet(markers=[], index_by_function={}, diagnostics={"module_disabled": "semantic_marker"})
            marker_grounding = {
                "marker_coverage_ok": True,
                "resolved_action_ids": [],
                "resolved_runtime_action_ids": [],
                "resolved_runtime_action_ids_raw": [],
                "critical_action_ids": self._critical_action_ids(optimization_target),
                "missing_critical_action_ids": [],
                "resolved_runtime_action_count": 0,
                "resolved_runtime_action_count_raw": 0,
            }
            unresolved_report = {"module_disabled": "semantic_marker"}
            detector_profile_draft = {"module_disabled": "semantic_marker"}

        dump_json(self.out_dir / "m1_markers.json", [to_dict(marker) for marker in marker_set.markers])
        dump_json(self.out_dir / "m1_marker_report.json", marker_set.diagnostics)
        dump_json(self.out_dir / "m1_unresolved_grounding_report.json", unresolved_report)
        dump_json(self.out_dir / "m1_detector_profile_draft.json", detector_profile_draft)
        if marker_grounding["missing_critical_action_ids"] and not self._allow_partial_target_grounding(optimization_target):
            raise GroundingCoverageError(
                "GROUNDING_FAILED:M1 critical actions not grounded into code markers: "
                + ", ".join(marker_grounding["missing_critical_action_ids"])
            )


        if module_switches["semantic_primitive_extractor"]:
            reducer = TempoSpatialReducer(profile)
            mssu_builder = MSSUBuilder(profile)
            reductions: List[ReductionResult] = []
            mssu_results: List[MSSUBuildResult] = []

            markers_by_file: Dict[str, List[Marker]] = {}
            for marker in marker_set.markers:
                markers_by_file.setdefault(marker.file_path, []).append(marker)

            for file_idx, file_path in enumerate(source_files):
                file_markers = markers_by_file.get(str(file_path), [])
                reduction_item = reducer.reduce(file_path, file_markers, optimization_target=optimization_target)
                reductions.append(reduction_item)

                mssu_item = mssu_builder.build(
                    reduction_item.reduced_graph,
                    file_markers,
                    reduction_item.marker_to_nodes,
                    optimization_target=optimization_target,
                    mssu_id_prefix=f"mssu{file_idx:02d}",
                )
                mssu_results.append(mssu_item)

            reduction = self._merge_reductions(reductions) if reductions else self._disabled_reduction()
            reduction_grounding = self._reduction_grounding_summary(reduction, marker_set.markers, optimization_target)
            mssu_result = self._merge_mssu_results(mssu_results) if mssu_results else self._disabled_mssu_result("empty_m2_reduction")
            mssu_result.summary = MSSUBuilder.summarize_grounding(mssu_result.mssus, optimization_target)
            mssu_result.build_status = str(mssu_result.summary.get("build_status", "OK"))
        else:
            reduction = self._disabled_reduction()
            reduction_grounding = {"anchor_nodes": [], "anchor_node_count": 0}
            mssu_result = self._disabled_mssu_result("module_disabled:semantic_primitive_extractor")

        dump_json(
            self.out_dir / "m2_reduced_graph.json",
            {
                "nodes": {node_id: to_dict(node) for node_id, node in reduction.reduced_graph.nodes.items()},
                "edges": [to_dict(edge) for edge in reduction.reduced_graph.edges],
                "mapping": reduction.reduced_graph.mapping,
                "kept_nodes": sorted(reduction.kept_node_ids),
                "anchor_nodes": reduction_grounding["anchor_nodes"],
                "source_files": [str(path) for path in source_files],
            },
        )

        dump_json(
            self.out_dir / "m3_mssu.json",
            {
                "mssus": [to_dict(mssu) for mssu in mssu_result.mssus],
                "dependency_candidates": [list(item) for item in mssu_result.dependency_candidates],
                "summary": mssu_result.summary or {},
            },
        )
        if (
            mssu_result.summary
            and mssu_result.summary.get("missing_critical_action_ids")
            and not self._allow_partial_target_grounding(optimization_target)
        ):
            raise GroundingCoverageError(
                "GROUNDING_FAILED:M3 critical actions not grounded into MSSUs: "
                + ", ".join(mssu_result.summary["missing_critical_action_ids"])
            )


        if module_switches["dependency_graph_builder"]:
            dag_builder = DependencyGraphBuilder(profile)
            dag, diagnostics = dag_builder.build(
                mssu_result.mssus,
                mssu_result.dependency_candidates,
                optimization_target=optimization_target,
            )
        else:
            dag = TypedDAG()
            diagnostics = DAGBuildDiagnostics(warnings=["module_disabled:dependency_graph_builder"])
        dump_json(
            self.out_dir / "m4_typed_dag.json",
            {
                "nodes": {node_id: to_dict(mssu) for node_id, mssu in dag.nodes.items()},
                "hard_edges": [to_dict(edge) for edge in dag.hard_edges],
                "soft_constraints": [to_dict(constraint) for constraint in dag.soft_constraints],
                "resources": dag.resources,
                "diagnostics": {
                    "warnings": diagnostics.warnings,
                    "removed_hard_edges": diagnostics.removed_hard_edges,
                },
            },
        )
        critical_ids = self._critical_action_ids(optimization_target)
        if module_switches["dependency_graph_builder"] and not self._allow_partial_target_grounding(optimization_target):
            if reduction_grounding["anchor_node_count"] == 0 and critical_ids:
                raise GroundingCoverageError(
                    "GROUNDING_FAILED:M2 no anchor nodes grounded from critical actions"
                )
            if len(critical_ids) > 1 and len(dag.hard_edges) == 0:
                raise GroundingCoverageError(
                    "GROUNDING_FAILED:M4 no hard edges available for multi-critical target"
                )


        scheduler = MacroLevelScheduler()
        runtime_metrics = self._offline_runtime_metrics(optimization_target)
        if runtime_metrics:
            dump_json(self.out_dir / "offline_runtime_metrics.json", runtime_metrics)
        if module_switches["macro_level_scheduler"]:
            plan = scheduler.schedule(dag, runtime_metrics=runtime_metrics, optimization_target=optimization_target)
        else:
            plan = self._serial_execution_plan(
                optimization_target,
                "module_disabled:macro_level_scheduler",
                module_switches,
            )
        plan.meta.setdefault("module_switches", dict(module_switches))
        macro_plan = plan
        dump_json(self.out_dir / "m5_macro_execution_plan.json", to_dict(macro_plan))

        if module_switches["micro_level_scheduler"]:
            target_meta = optimization_target.meta if isinstance(optimization_target.meta, dict) else {}
            micro_refiner = MicroLevelScheduler()
            try:
                micro_result = micro_refiner.refine_case(
                    vdev_id=str(target_meta.get("vdev_id") or self.integration_name),
                    case_name=str(target_meta.get("name") or target_meta.get("case_name") or self.integration_name),
                    target=optimization_target,
                    plan=macro_plan,
                )
                dump_json(self.out_dir / "micro_level_scheduler_result.json", micro_result)
                if micro_result.validation.passed:
                    plan = micro_result.refined_plan
                    plan.meta.setdefault("module_switches", dict(module_switches))
                else:
                    plan = macro_plan
            except Exception as exc:
                dump_json(
                    self.out_dir / "micro_level_scheduler_result.json",
                    {
                        "enabled": True,
                        "passed": False,
                        "fallback": "macro_plan",
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                )
                plan = macro_plan
        else:
            dump_json(
                self.out_dir / "micro_level_scheduler_result.json",
                {"enabled": False, "reason": "module_disabled:micro_level_scheduler"},
            )

        dump_json(self.out_dir / "m5_execution_plan.json", to_dict(plan))
        trust_plan = scheduler.compress_plan_for_trust(plan)
        dump_json(self.out_dir / "m5_trust_plan.json", to_dict(trust_plan))


        assembler = VDevCustomComponentAssembler(self.out_dir / "reassembly")
        if module_switches["component_assembler"]:
            component_assembly = assembler.assemble(
                optimization_target=optimization_target,
                execution_plan=plan,
                profile_path=self.profile_path,
            )
        else:
            component_assembly = self._disabled_component_artifact()
            dump_json(self.out_dir / "m7_component_assembly.json", {"enabled": False, "reason": "module_disabled:component_assembler"})


        ordered_markers = self._ordered_markers(marker_set.markers)

        scenarios = scenarios_from_config(optimization_target.validation)
        if not scenarios:
            scenarios = default_scenarios()

        if module_switches["equivalence_validator"]:
            dump_json(
                self.out_dir / "m6_progress.json",
                {
                    "phase": "replay_start",
                    "updated_at": now_utc_iso(),
                    "scenario_count": len(scenarios),
                    "plan_batch_count": len(trust_plan.ordered_batches),
                },
            )
            dump_json(
                self.out_dir / "execution_certificate.partial.json",
                {
                    "schema_version": "execution_certificate_partial/v1",
                    "created_at": now_utc_iso(),
                    "integration": self.integration_name,
                    "status": "RUNNING",
                    "phase": "replay_start",
                    "plan_summary": {
                        "batch_count": len(trust_plan.ordered_batches),
                        "action_count": len(self._plan_order(trust_plan)),
                    },
                    "replay_summary": None,
                    "counterexample_summary": None,
                },
            )

            replay_results: List[ReplayResult] = replay_scenarios(
                integration=self.integration_name,
                scenarios=scenarios,
                baseline_runner=self._simulate_baseline_runner(ordered_markers, optimization_target),
                optimized_runner=self._simulate_optimized_runner(ordered_markers, trust_plan, optimization_target),
            )
            dump_json(
                self.out_dir / "m6_progress.json",
                {
                    "phase": "replay_done",
                    "updated_at": now_utc_iso(),
                    "scenario_count": len(scenarios),
                    "replay_result_count": len(replay_results),
                },
            )

            trust = EquivalenceValidator(self.integration_name, str(self.out_dir))
            trust_result = trust.evaluate(
                replay_results=replay_results,
                dag=dag,
                rules=profile.rules,
                profile_version=profile.profile_id,
                optimization_target=optimization_target,
                execution_plan=trust_plan,
                replay_with_plan=lambda candidate_plan: replay_scenarios(
                    integration=self.integration_name,
                    scenarios=scenarios,
                    baseline_runner=self._simulate_baseline_runner(ordered_markers, optimization_target),
                    optimized_runner=self._simulate_optimized_runner(ordered_markers, candidate_plan, optimization_target),
                ),
                replan_with_dag=lambda candidate_dag: scheduler.compress_plan_for_trust(
                    scheduler.schedule(
                        candidate_dag,
                        runtime_metrics=runtime_metrics,
                        optimization_target=optimization_target,
                    )
                ),
                rollback_max_steps=self.rollback_max_steps,
                hardening_min_pass_rate=self.hardening_min_pass_rate,
                hardening_min_coverage=self.hardening_min_coverage,
            )

            final_plan = trust_result.final_plan or plan
            final_dag = trust_result.final_dag or dag
            rollback_log = trust_result.rollback_log
            trust_summary = trust_result.summary
        else:
            final_plan = trust_plan
            final_dag = dag
            rollback_log = []
            trust_summary = {"status": "SKIPPED", "module_disabled": "equivalence_validator"}
            dump_json(
                self.out_dir / "execution_certificate.partial.json",
                {
                    "schema_version": "execution_certificate_partial/v1",
                    "created_at": now_utc_iso(),
                    "integration": self.integration_name,
                    "status": "SKIPPED",
                    "phase": "equivalence_validator_disabled",
                    "plan_summary": {
                        "batch_count": len(trust_plan.ordered_batches),
                        "action_count": len(self._plan_order(trust_plan)),
                    },
                    "replay_summary": None,
                    "counterexample_summary": None,
                },
            )

        dump_json(self.out_dir / "m5_trust_plan.json", final_plan)
        dump_json(
            self.out_dir / "m4_typed_dag.json",
            {
                "nodes": {node_id: to_dict(mssu) for node_id, mssu in final_dag.nodes.items()},
                "hard_edges": [to_dict(edge) for edge in final_dag.hard_edges],
                "soft_constraints": [to_dict(constraint) for constraint in final_dag.soft_constraints],
                "resources": final_dag.resources,
                "diagnostics": {
                    "warnings": diagnostics.warnings,
                    "removed_hard_edges": diagnostics.removed_hard_edges,
                    "m6_rollback": rollback_log,
                },
            },
        )
        if module_switches["component_assembler"]:
            dump_json(component_assembly.plan_path, final_plan)
        dump_json(
            self.out_dir / "hard_edge_witness.json",
            self._hard_edge_witness(final_dag, reduction.reduced_graph, marker_set.markers),
        )

        if module_switches["component_assembler"] and module_switches["equivalence_validator"]:
            assembler.attach_certificate(component_assembly, self.out_dir / "execution_certificate.json")

        return OptimizerArtifacts(
            optimization_target=optimization_target,
            marker_set=marker_set,
            reduction=reduction,
            mssu_result=mssu_result,
            dag_diagnostics=diagnostics,
            component_assembly=component_assembly,
            trust_summary=trust_summary,
        )
