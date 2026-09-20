from pathlib import Path
from http.client import RemoteDisconnected
import json

from dsl.contracts import OptimizationTarget
from optimizer.m1_detector_builder import (
    _merge_runtime_family_with_heuristic_defaults,
    _validate_runtime_family_against_cluster,
    build_detector_profile_draft,
    build_unresolved_grounding_report,
    generate_detector_profile_draft_with_llm,
)


def test_build_unresolved_grounding_report_and_detector_draft(tmp_path: Path) -> None:
    source_dir = tmp_path / "ecobee"
    source_dir.mkdir()
    source = source_dir / "climate.py"
    source.write_text(
        """
import aiohttp

async def async_update(self):
    return await self.client.get_thermostat()
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "ecobee:thermostat.home_1",
                    "integration": "ecobee",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "ecobee:thermostat.home_1"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "ecobee", "service": "read_runtime"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )
    grounding = {
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
    }

    report = build_unresolved_grounding_report(target, grounding)
    assert report["schema_version"] == "m1_unresolved_grounding_report/v3"
    assert report["builder_version"] == "m1_detector_builder/v3"
    assert report["source_report_sha256"]
    assert report["missing_critical_action_ids"] == ["A1"]
    assert report["unresolved_actions"][0]["integrations"] == ["ecobee"]
    assert "no_runtime_family_detected" in report["unresolved_actions"][0]["miss_reason_summary"]
    assert report["source_file_summaries"][0]["imports"] == ["aiohttp"]
    assert report["source_file_summaries"][0]["runtime_candidate_functions"] == ["async_update"]
    assert report["source_file_summaries"][0]["runtime_read_candidate_functions"] == ["async_update"]
    assert "read_function:async_update" in report["source_file_summaries"][0]["path_signal_summary"]
    assert "awaited_read_call:self.client.get_thermostat" in report["source_file_summaries"][0]["path_signal_summary"]
    assert report["source_file_summaries"][0]["representative_functions"][0]["snippet"]
    assert report["unresolved_actions"][0]["preferred_runtime_roles"] == ["runtime_read"]
    assert "ecobee:thermostat.home_1" in report["unresolved_actions"][0]["target_identity_tokens"]
    assert "cloud_runtime_read" in report["unresolved_actions"][0]["runtime_archetypes"]
    assert report["unresolved_actions"][0]["path_signal_focus"]["preferred_signals"]
    assert report["unresolved_actions"][0]["path_contrast_examples"][0]["preferred_examples"][0]["path_kind"] == "read_path"
    assert report["unresolved_actions"][0]["positive_selector_missing_reason"] == ""
    assert report["source_file_summaries"][0]["shared_accessor_signals"] == []

    draft = build_detector_profile_draft(report)
    assert draft["schema_version"] == "m1_detector_draft/v3"
    assert draft["prompt_version"] == "m1_detector_builder_prompt/v3"
    assert draft["source_report_sha256"] == report["source_report_sha256"]
    assert draft["cluster_count"] == 1
    assert draft["proposal_count"] == 1
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["integration"] == "ecobee"
    assert proposal["family"] == "CLOUD_STATUS_CALL"
    assert proposal["generalization_scope"] == "file_specific"
    assert proposal["generalizes_actions"] == ["A1"]
    assert proposal["origin_cluster_id"]
    assert "runtime_update_path" in proposal["required_context"]
    assert proposal["required_path_signals"]
    assert proposal["forbidden_path_signals"]
    assert "negative_function_patterns" in proposal
    assert "async_turn_on" in proposal["negative_function_patterns"]
    assert "async_turn_on" in proposal["negative_call_patterns"]
    assert proposal["preferred_runtime_roles"] == ["runtime_read"]
    assert "cloud_runtime_read" in proposal["runtime_archetypes"]
    assert proposal["positive_prototypes"]
    assert "negative_prototypes" in proposal
    assert proposal["action_kind"] == "read_runtime"
    assert proposal["allow_accessor_fallback"] is False
    assert proposal["binding_hints"]["preferred_action_kinds"] == ["status", "poll_update"]
    assert proposal["runtime_path_evidence"]
    assert "path_signal:read_function:async_update" in proposal["runtime_path_evidence"]
    assert proposal["source_unresolved_action_ids"] == ["A1"]
    assert draft["cluster_summaries"][0]["promotion_decision"] == "promote"


def test_build_detector_profile_draft_allows_private_coordinator_update_carrier(tmp_path: Path) -> None:
    source_dir = tmp_path / "airthings_ble"
    source_dir.mkdir()
    source = source_dir / "coordinator.py"
    source.write_text(
        """
async def _async_setup(self):
    await close_stale_connections_by_address(self.address)

async def _async_update_data(self):
    return await self.airthings.update_device(self.ble_device)
""",
        encoding="utf-8",
    )
    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "ble:airthings_ble:living_room_air",
                    "integration": "airthings_ble",
                    "file_path": str(source),
                    "protocols": ["BLE"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "type": "read_sensor",
                "target_kind": "ble_device",
                "target": {"kind": "ble_device", "id": "ble:airthings_ble:living_room_air"},
                "marker_hints": ["BLE_OP"],
                "exec": {"kind": "ha_service_call", "domain": "airthings_ble", "service": "read_sensor"},
            }
        ],
        critical_action_ids=["A1"],
    )
    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]

    assert proposal["function_name_patterns"] == ["_async_update_data"]
    assert "helper" not in proposal["forbidden_runtime_roles"]
    assert "setup" in proposal["forbidden_runtime_roles"]


def test_build_detector_profile_draft_prefers_read_role_over_control_role(tmp_path: Path) -> None:
    source_dir = tmp_path / "tuya"
    source_dir.mkdir()
    source = source_dir / "light.py"
    source.write_text(
        """
async def async_update(self):
    await self.coordinator.async_request_refresh()
    return self.device.status()

async def async_turn_on(self):
    return await self._async_send_commands()

@property
def brightness(self):
    return self._read_wrapper(self._brightness_wrapper)
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "tuya:light.demo.status",
                    "integration": "tuya",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "status",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.demo.status"},
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )
    grounding = {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []}
    report = build_unresolved_grounding_report(target, grounding)
    summary = report["source_file_summaries"][0]
    assert summary["runtime_read_candidate_functions"] == ["async_update"]
    assert "brightness" in summary["helper_candidate_functions"]
    assert summary["path_contrast_examples"]["property_path_examples"][0]["function_name"] == "brightness"
    assert "state_accessor_property:brightness" in summary["path_contrast_examples"]["property_path_examples"][0]["path_signals"]
    assert report["unresolved_actions"][0]["path_signal_focus"]["preferred_signals"]
    assert report["unresolved_actions"][0]["path_signal_focus"]["forbidden_signals"]
    assert report["unresolved_actions"][0]["path_contrast_examples"][0]["supporting_examples"][0]["function_name"] == "brightness"
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["function_name_patterns"] == ["async_update"]
    assert "get_thermostat" not in proposal["call_patterns"]
    assert "get_remote_sensors" not in proposal["call_patterns"]
    assert "async_turn_on" in proposal["negative_function_patterns"]
    assert any(
        item.startswith("path_signal:refresh_call:") or item.startswith("path_signal:state_accessor_call:")
        for item in proposal["runtime_path_evidence"]
    )
    assert any(item.startswith("negative_path_signal:control_function:") for item in proposal["negative_evidence"])


def test_build_detector_profile_draft_uses_discriminative_target_tokens(tmp_path: Path) -> None:
    source_dir = tmp_path / "tuya"
    source_dir.mkdir()
    source = source_dir / "switch.py"
    source.write_text(
        """
def _process_device_update(self):
    return self._dpcode_wrapper.skip_update()
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "tuya:switch.energy_strip_2.status",
                    "integration": "tuya",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "status",
                "target_kind": "cloud_endpoint",
                "target": {
                    "kind": "cloud_endpoint",
                    "id": "tuya:switch.energy_strip_2.status",
                    "endpoint": "tuya:switch.energy_strip_2.status",
                },
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {
                    "kind": "ha_service_call",
                    "domain": "switch",
                    "service": "status",
                    "provider": "tuya",
                    "data_template": {
                        "endpoint": "tuya:switch.energy_strip_2.status",
                        "endpoint_group_key": "energy_hvac_energy",
                        "host_group_key": "tuya",
                    },
                },
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )
    grounding = {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []}

    report = build_unresolved_grounding_report(target, grounding)
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    boost_tokens = proposal["binding_hints"]["boost_target_tokens"]
    assert "energy_strip_2" in boost_tokens
    assert "tuya:switch.energy_strip_2.status" in boost_tokens
    assert "status" not in boost_tokens
    assert "switch" not in boost_tokens
    assert "cloud_endpoint" not in boost_tokens
    assert "energy_hvac_energy" not in boost_tokens
    assert "ha_service_call" not in boost_tokens
    assert "tuya" not in boost_tokens


def test_build_detector_profile_draft_prefers_control_selector_aligned_setter(tmp_path: Path) -> None:
    source_dir = tmp_path / "ecobee"
    source_dir.mkdir()
    source = source_dir / "climate.py"
    source.write_text(
        """
def create_vacation_service(service):
    thermostat.create_vacation(service.data)
    thermostat.schedule_update_ha_state(True)

def delete_vacation_service(service):
    thermostat.delete_vacation(service.data)
    thermostat.schedule_update_ha_state(True)

def set_hvac_mode(self, hvac_mode):
    self.data.ecobee.set_hvac_mode(self.thermostat_index, hvac_mode)
    self.update_without_throttle = True
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "ecobee:thermostat.office.set_hvac_mode",
                    "integration": "ecobee",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "set_hvac_mode",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "ecobee:thermostat.office.set_hvac_mode"},
                "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "set_hvac_mode", "provider": "ecobee"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )
    grounding = {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []}

    report = build_unresolved_grounding_report(target, grounding)
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["family"] == "CLOUD_OP"
    assert proposal["action_kind"] == "set_hvac_mode"
    assert "set_hvac_mode" in proposal["function_name_patterns"]
    assert "create_vacation_service" not in proposal["function_name_patterns"]
    assert "delete_vacation_service" not in proposal["function_name_patterns"]


def test_build_detector_profile_draft_uses_synthetic_accessor_positive_for_property_heavy_status(tmp_path: Path) -> None:
    source_dir = tmp_path / "tuya"
    source_dir.mkdir()
    source = source_dir / "light.py"
    source.write_text(
        """
async def async_turn_on(self):
    return await self._async_send_commands()

async def async_turn_off(self):
    return await self._async_send_wrapper_updates()

@property
def is_on(self):
    return self._read_wrapper(self._switch_wrapper)
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "tuya:light.demo.status",
                    "integration": "tuya",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "status",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.demo.status"},
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )
    grounding = {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []}

    report = build_unresolved_grounding_report(target, grounding)
    summary = report["source_file_summaries"][0]
    assert summary["runtime_read_candidate_functions"] == []
    assert summary["shared_accessor_signals"] == ["_read_wrapper"]
    draft = build_detector_profile_draft(report)
    assert draft["proposal_count"] == 1
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["allow_accessor_fallback"] is True
    assert proposal["generalization_scope"] == "file_specific"
    assert "is_on" in proposal["function_name_patterns"]


def test_build_detector_profile_draft_promotes_synthetic_accessor_positive_when_repeated(tmp_path: Path) -> None:
    source_dir = tmp_path / "tuya"
    source_dir.mkdir()
    source = source_dir / "light.py"
    source.write_text(
        """
@property
def is_on(self):
    return self._read_wrapper(self._switch_wrapper)

@property
def brightness(self):
    return self._read_wrapper(self._brightness_wrapper)

async def async_turn_on(self):
    return await self._async_send_commands()
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "tuya:light.demo.status",
                    "integration": "tuya",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "status",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.demo.status"},
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )
    grounding = {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []}

    report = build_unresolved_grounding_report(target, grounding)
    assert "state_accessor_call:self._read_wrapper" in report["source_file_summaries"][0]["shared_accessor_signals"]
    draft = build_detector_profile_draft(report)
    assert draft["proposal_count"] == 1
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["allow_accessor_fallback"] is True
    assert proposal["call_patterns"] == []
    assert any(
        proto["prototype_kind"] == "synthetic_accessor_positive"
        for proto in proposal["positive_prototypes"]
    )
    assert draft["cluster_summaries"][0]["promotion_decision"] == "promote"


def test_build_detector_profile_draft_treats_cloud_control_actions_as_runtime_write(tmp_path: Path) -> None:
    source_dir = tmp_path / "tuya"
    source_dir.mkdir()
    source = source_dir / "light.py"
    source.write_text(
        """
async def async_turn_on(self, **kwargs):
    commands = self._switch_wrapper.get_update_commands(self.device, True)
    commands.extend(self._brightness_wrapper.get_update_commands(self.device, kwargs.get("brightness")))
    await self._async_send_commands(commands)

async def async_turn_off(self, **kwargs):
    await self._async_send_wrapper_updates(self._switch_wrapper, False)

@property
def is_on(self):
    return self._read_wrapper(self._switch_wrapper)
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "tuya:light.demo.turn_on",
                    "integration": "tuya",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "turn_on",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.demo.turn_on"},
                "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "turn_on"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )
    grounding = {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []}

    report = build_unresolved_grounding_report(target, grounding)
    unresolved = report["unresolved_actions"][0]
    assert unresolved["preferred_runtime_roles"] == ["runtime_write"]
    assert "cloud_runtime_control" in unresolved["runtime_archetypes"]
    assert unresolved["positive_selector_missing_reason"] == ""

    draft = build_detector_profile_draft(report)
    assert draft["proposal_count"] == 1
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["family"] == "CLOUD_OP"
    assert proposal["preferred_runtime_roles"] == ["runtime_write"]
    assert proposal["binding_hints"]["preferred_action_kinds"] == ["control", "turn_on"]
    assert "turn_on" in proposal["binding_hints"]["required_service_tokens"]
    assert proposal["required_context"] == ["runtime_path"]
    assert "async_turn_on" in proposal["function_name_patterns"]
    assert any(signal.startswith("control_function:async_turn_on") for signal in proposal["required_path_signals"])
    assert any(signal.startswith("control_call:") or signal.startswith("awaited_control_call:") for signal in proposal["required_path_signals"])
    assert any(
        proto["prototype_kind"] == "positive" and proto["function_name"] == "async_turn_on"
        for proto in proposal["positive_prototypes"]
    )


def test_generate_detector_profile_draft_with_llm_normalizes_chat_response(monkeypatch) -> None:
    unresolved_report = {
        "schema_version": "m1_unresolved_grounding_report/v3",
        "builder_version": "m1_detector_builder/v3",
        "source_report_sha256": "report-sha",
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
        "unresolved_actions": [
            {
                "action_id": "A1",
                "integrations": ["ecobee"],
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "bound_files": ["/tmp/ecobee/climate.py"],
                "exec_domain": "ecobee",
                "exec_service": "read_runtime",
                "action_type": "read_runtime",
            }
        ],
        "source_file_summaries": [],
    }
    heuristic_draft = {
        "proposal_count": 0,
        "detector_profile_drafts": [],
        "cluster_summaries": [
            {
                "cluster_id": "ecobee_cluster",
                "integration": "ecobee",
                "family": "CLOUD_STATUS_CALL",
                "action_kind": "read_runtime",
                "promotion_decision": "llm_refine",
                "promotability_score": 4,
                "positive_prototypes": [],
                "negative_prototypes": [],
                "heuristic_rule": {
                    "rule_id": "ecobee:climate_runtime_status_read",
                    "integration": "ecobee",
                    "family": "CLOUD_STATUS_CALL",
                    "action_kind": "read_runtime",
                    "generalization_scope": "file_specific",
                    "generalizes_actions": ["A1"],
                    "origin_cluster_id": "ecobee_cluster",
                    "file_globs": ["ecobee/climate.py"],
                    "call_patterns": ["get_thermostat"],
                    "function_name_patterns": ["async_update"],
                    "negative_call_patterns": [],
                    "negative_function_patterns": ["__init__"],
                    "required_context": ["runtime_update_path"],
                    "forbidden_context": ["dunder_init", "entity_property_getter"],
                    "required_path_signals": ["read_function:async_update"],
                    "forbidden_path_signals": [],
                    "required_runtime_roles": ["runtime_read"],
                    "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
                    "binding_hints": {"preferred_action_kinds": ["status"], "boost_target_tokens": ["runtime"], "phase": "RUNTIME"},
                    "positive_prototypes": [],
                    "negative_prototypes": [],
                    "runtime_path_evidence": ["runtime_function:async_update"],
                    "negative_evidence": ["negative_function:__init__"],
                    "why_not_setup": ["exclude_setup_function:__init__"],
                    "phase": "RUNTIME",
                    "strength": "MEDIUM",
                    "confidence": {"base": 0.8, "emit_threshold": 0.75, "boost_if_imports": ["aiohttp"], "boost_if_names": ["update"]},
                    "source_file_paths": ["ecobee/climate.py"],
                    "source_unresolved_action_ids": ["A1"],
                    "reviewer_status": "draft",
                },
            }
        ],
    }
    monkeypatch.setattr("optimizer.m1_detector_builder.build_detector_profile_draft", lambda report: heuristic_draft)

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return (
                b'{"choices":[{"message":{"content":"{\\"decision\\":\\"refine\\",\\"runtime_family\\":{\\"rule_id\\":\\"ecobee:a1:cloud_status\\",'
                b'\\"family\\":\\"CLOUD_STATUS_CALL\\",\\"file_globs\\":[\\"ecobee/climate.py\\"],'
                b'\\"call_patterns\\":[\\"get_thermostat\\"],\\"function_name_patterns\\":[\\"async_update\\"],'
                b'\\"negative_function_patterns\\":[\\"__init__\\"],'
                b'\\"required_context\\":[\\"runtime_update_path\\",\\"coordinator_update_path\\"],\\"forbidden_context\\":[\\"dunder_init\\",\\"property_path\\"],'
                b'\\"binding_hints\\":{\\"preferred_action_kinds\\":[\\"status\\"],\\"boost_target_tokens\\":[\\"runtime\\"],\\"phase\\":\\"RUNTIME\\"},'
                b'\\"runtime_path_evidence\\":[\\"runtime_function:async_update\\"],'
                b'\\"negative_evidence\\":[\\"negative_function:__init__\\"],'
                b'\\"why_not_setup\\":[\\"exclude_setup_function:__init__\\"],'
                b'\\"phase\\":\\"RUNTIME\\",\\"strength\\":\\"MEDIUM\\",\\"confidence\\":{\\"base\\":0.8,'
                b'\\"emit_threshold\\":0.75,\\"boost_if_imports\\":[\\"aiohttp\\"],\\"boost_if_names\\":[\\"update\\"]}}}"}}]}'
            )

    def _fake_urlopen(req, timeout=0):
        del req, timeout
        return _FakeResponse()

    monkeypatch.setattr("optimizer.m1_detector_builder.request.urlopen", _fake_urlopen)
    draft = generate_detector_profile_draft_with_llm(
        unresolved_report,
        api_base_url="https://example.invalid/v1/chat/completions",
        api_key="test-key",
        model="gpt-5",
        timeout_s=30,
    )

    assert draft["schema_version"] == "m1_detector_draft/v3"
    assert draft["llm_request"]["base_url"] == "${FLOWEAVER_LLM_API_BASE_URL}"
    assert "https://example.invalid/v1/chat/completions" not in json.dumps(draft)
    assert "test-key" not in json.dumps(draft)
    assert draft["proposal_count"] == 1
    assert draft["prompt_version"] == "m1_detector_builder_prompt/v3"
    assert draft["request_sha256"]
    assert draft["source_report_sha256"] == "report-sha"
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["family"] == "CLOUD_STATUS_CALL"
    assert proposal["rule_id"] == "ecobee:a1:cloud_status"
    assert proposal["generalization_scope"] == "file_specific"
    assert proposal["confidence"]["emit_threshold"] == 0.75
    assert proposal["binding_hints"]["preferred_action_kinds"] == ["status"]
    assert proposal["negative_function_patterns"] == ["__init__"]
    assert proposal["required_context"] == ["runtime_update_path"]
    assert proposal["forbidden_context"] == ["dunder_init", "entity_property_getter"]
    assert draft["cluster_decisions"][0]["decision"] == "refine"


def test_generate_detector_profile_draft_with_llm_filters_control_path_for_read_like_actions(monkeypatch) -> None:
    unresolved_report = {
        "schema_version": "m1_unresolved_grounding_report/v3",
        "builder_version": "m1_detector_builder/v3",
        "source_report_sha256": "report-sha",
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
        "unresolved_actions": [
            {
                "action_id": "A1",
                "integrations": ["tuya"],
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "bound_files": ["/tmp/tuya/light.py"],
                "exec_domain": "light",
                "exec_service": "status",
                "action_type": "status",
            }
        ],
        "source_file_summaries": [],
    }

    heuristic_draft = {
        "proposal_count": 1,
        "detector_profile_drafts": [],
        "cluster_summaries": [
            {
                "cluster_id": "tuya_cluster",
                "integration": "tuya",
                "family": "CLOUD_STATUS_CALL",
                "action_kind": "status",
                "promotion_decision": "llm_refine",
                "promotability_score": 6,
                "positive_prototypes": [],
                "negative_prototypes": [],
                "heuristic_rule": {
                    "rule_id": "tuya:good:status",
                    "integration": "tuya",
                    "family": "CLOUD_STATUS_CALL",
                    "action_kind": "status",
                    "generalization_scope": "file_specific",
                    "generalizes_actions": ["A1"],
                    "origin_cluster_id": "tuya_cluster",
                    "file_globs": ["tuya/light.py"],
                    "call_patterns": ["get_status"],
                    "function_name_patterns": ["async_update"],
                    "negative_call_patterns": ["_async_send_commands"],
                    "negative_function_patterns": ["async_turn_on"],
                    "required_context": ["runtime_update_path"],
                    "forbidden_context": ["dunder_init", "entity_property_getter"],
                    "required_path_signals": ["read_function:async_update"],
                    "forbidden_path_signals": ["control_function:async_turn_on"],
                    "required_runtime_roles": ["runtime_read"],
                    "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
                    "binding_hints": {"preferred_action_kinds": ["status"], "boost_target_tokens": ["demo"], "phase": "RUNTIME"},
                    "positive_prototypes": [],
                    "negative_prototypes": [],
                    "runtime_path_evidence": ["runtime_function:async_update", "runtime_call:get_status"],
                    "negative_evidence": [],
                    "why_not_setup": [],
                    "phase": "RUNTIME",
                    "strength": "MEDIUM",
                    "confidence": {"base": 0.8, "emit_threshold": 0.75},
                    "source_file_paths": ["tuya/light.py"],
                    "source_unresolved_action_ids": ["A1"],
                    "reviewer_status": "draft",
                },
            }
        ],
    }
    monkeypatch.setattr("optimizer.m1_detector_builder.build_detector_profile_draft", lambda report: heuristic_draft)

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return (
                b'{"choices":[{"message":{"content":"{\\"decision\\":\\"refine\\",\\"runtime_family\\":{'
                b'\\"rule_id\\":\\"tuya:bad:status\\",\\"family\\":\\"CLOUD_STATUS_CALL\\",'
                b'\\"file_globs\\":[\\"tuya/light.py\\"],\\"call_patterns\\":[\\"_async_send_commands\\",\\"turn_on\\"],'
                b'\\"function_name_patterns\\":[\\"async_turn_on\\"],\\"required_context\\":[\\"runtime_update_path\\"],'
                b'\\"forbidden_context\\":[\\"dunder_init\\"],\\"binding_hints\\":{\\"preferred_action_kinds\\":[\\"status\\"],'
                b'\\"boost_target_tokens\\":[\\"status\\"],\\"phase\\":\\"RUNTIME\\"},'
                b'\\"runtime_path_evidence\\":[\\"runtime_function:async_turn_on\\"],'
                b'\\"negative_evidence\\":[],\\"why_not_setup\\":[],\\"phase\\":\\"RUNTIME\\",\\"strength\\":\\"MEDIUM\\",'
                b'\\"confidence\\":{\\"base\\":0.8,\\"emit_threshold\\":0.75},'
                b'\\"origin_action_id\\":\\"A1\\",\\"source_unresolved_action_ids\\":[\\"A1\\"],\\"reviewer_status\\":\\"candidate\\"}}"}}]}'
            )

    def _fake_urlopen(req, timeout=0):
        del req, timeout
        return _FakeResponse()

    monkeypatch.setattr("optimizer.m1_detector_builder.request.urlopen", _fake_urlopen)
    draft = generate_detector_profile_draft_with_llm(
        unresolved_report,
        api_base_url="https://example.invalid/v1/chat/completions",
        api_key="test-key",
        model="gpt-5",
        timeout_s=30,
        max_attempts=1,
        retry_backoff_s=0,
    )

    proposals = draft["detector_profile_drafts"][0]["runtime_families"]
    assert len(proposals) == 1
    assert proposals[0]["rule_id"] == "tuya:good:status"
    assert draft["cluster_decisions"][0]["decision"] == "heuristic_fallback"


def test_generate_detector_profile_draft_with_llm_skips_llm_for_promote_clusters(monkeypatch) -> None:
    unresolved_report = {
        "schema_version": "m1_unresolved_grounding_report/v3",
        "builder_version": "m1_detector_builder/v3",
        "source_report_sha256": "report-sha",
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
        "unresolved_actions": [
            {
                "action_id": "A1",
                "integrations": ["ecobee"],
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "bound_files": ["/tmp/ecobee/climate.py"],
                "exec_domain": "ecobee",
                "exec_service": "read_runtime",
                "action_type": "read_runtime",
            }
        ],
        "source_file_summaries": [],
    }
    heuristic_draft = {
        "proposal_count": 1,
        "detector_profile_drafts": [],
        "cluster_summaries": [
            {
                "cluster_id": "ecobee_cluster",
                "integration": "ecobee",
                "family": "CLOUD_STATUS_CALL",
                "action_kind": "read_runtime",
                "promotion_decision": "promote",
                "promotability_score": 9,
                "positive_prototypes": [],
                "negative_prototypes": [],
                "heuristic_rule": {
                    "rule_id": "ecobee:climate_runtime_status_read",
                    "integration": "ecobee",
                    "family": "CLOUD_STATUS_CALL",
                    "action_kind": "read_runtime",
                    "generalization_scope": "file_specific",
                    "generalizes_actions": ["A1"],
                    "origin_cluster_id": "ecobee_cluster",
                    "file_globs": ["ecobee/climate.py"],
                    "call_patterns": ["get_thermostat"],
                    "function_name_patterns": ["async_update"],
                    "negative_call_patterns": [],
                    "negative_function_patterns": ["__init__"],
                    "required_context": ["runtime_update_path"],
                    "forbidden_context": ["dunder_init"],
                    "required_path_signals": ["read_function:async_update"],
                    "forbidden_path_signals": [],
                    "required_runtime_roles": ["runtime_read"],
                    "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
                    "binding_hints": {"preferred_action_kinds": ["status"], "boost_target_tokens": ["runtime"], "phase": "RUNTIME"},
                    "positive_prototypes": [],
                    "negative_prototypes": [],
                    "runtime_path_evidence": ["runtime_function:async_update"],
                    "negative_evidence": [],
                    "why_not_setup": [],
                    "phase": "RUNTIME",
                    "strength": "MEDIUM",
                    "confidence": {"base": 0.8, "emit_threshold": 0.75},
                    "source_file_paths": ["ecobee/climate.py"],
                    "source_unresolved_action_ids": ["A1"],
                    "reviewer_status": "draft",
                },
            }
        ],
    }
    monkeypatch.setattr("optimizer.m1_detector_builder.build_detector_profile_draft", lambda report: heuristic_draft)

    def _fake_urlopen(req, timeout=0):
        del req, timeout
        raise AssertionError("LLM should not be called for promote clusters")

    monkeypatch.setattr("optimizer.m1_detector_builder.request.urlopen", _fake_urlopen)
    draft = generate_detector_profile_draft_with_llm(
        unresolved_report,
        api_base_url="https://example.invalid/v1/chat/completions",
        api_key="test-key",
        model="gpt-5",
        timeout_s=30,
    )

    assert draft["proposal_count"] == 1
    assert draft["cluster_decisions"][0]["decision"] == "heuristic_accept"
    assert draft["detector_profile_drafts"][0]["runtime_families"][0]["rule_id"] == "ecobee:climate_runtime_status_read"


def test_generate_detector_profile_draft_with_llm_allows_abstain(monkeypatch) -> None:
    unresolved_report = {
        "schema_version": "m1_unresolved_grounding_report/v3",
        "builder_version": "m1_detector_builder/v3",
        "source_report_sha256": "report-sha",
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
        "unresolved_actions": [
            {
                "action_id": "A1",
                "integrations": ["tuya"],
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "bound_files": ["/tmp/tuya/light.py"],
                "exec_domain": "light",
                "exec_service": "status",
                "action_type": "status",
            }
        ],
        "source_file_summaries": [],
    }

    heuristic_draft = {
        "proposal_count": 0,
        "detector_profile_drafts": [],
        "cluster_summaries": [
            {
                "cluster_id": "tuya_cluster",
                "integration": "tuya",
                "family": "CLOUD_STATUS_CALL",
                "action_kind": "status",
                "promotion_decision": "llm_refine",
                "promotability_score": 3,
                "positive_prototypes": [],
                "negative_prototypes": [],
                "heuristic_rule": {
                    "rule_id": "tuya:heuristic:status",
                    "integration": "tuya",
                    "family": "CLOUD_STATUS_CALL",
                    "action_kind": "status",
                    "generalization_scope": "file_specific",
                    "generalizes_actions": ["A1"],
                    "origin_cluster_id": "tuya_cluster",
                    "file_globs": ["tuya/light.py"],
                    "call_patterns": ["get_status"],
                    "function_name_patterns": ["async_update"],
                    "negative_call_patterns": [],
                    "negative_function_patterns": [],
                    "required_context": ["runtime_update_path"],
                    "forbidden_context": ["dunder_init"],
                    "required_path_signals": ["read_function:async_update"],
                    "forbidden_path_signals": [],
                    "required_runtime_roles": ["runtime_read"],
                    "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
                    "binding_hints": {"preferred_action_kinds": ["status"], "boost_target_tokens": ["demo"], "phase": "RUNTIME"},
                    "positive_prototypes": [],
                    "negative_prototypes": [],
                    "runtime_path_evidence": ["runtime_function:async_update"],
                    "negative_evidence": [],
                    "why_not_setup": [],
                    "phase": "RUNTIME",
                    "strength": "MEDIUM",
                    "confidence": {"base": 0.8, "emit_threshold": 0.75},
                    "source_file_paths": ["tuya/light.py"],
                    "source_unresolved_action_ids": ["A1"],
                    "reviewer_status": "draft",
                },
            }
        ],
    }
    monkeypatch.setattr("optimizer.m1_detector_builder.build_detector_profile_draft", lambda report: heuristic_draft)

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"decision\\":\\"abstain\\"}"}}]}'

    def _fake_urlopen(req, timeout=0):
        del req, timeout
        return _FakeResponse()

    monkeypatch.setattr("optimizer.m1_detector_builder.request.urlopen", _fake_urlopen)
    draft = generate_detector_profile_draft_with_llm(
        unresolved_report,
        api_base_url="https://example.invalid/v1/chat/completions",
        api_key="test-key",
        model="gpt-5",
        timeout_s=30,
    )

    assert draft["schema_version"] == "m1_detector_draft/v3"
    assert draft["proposal_count"] == 0
    assert draft["detector_profile_drafts"] == []
    assert draft["llm_abstained"] is True
    assert draft["cluster_decisions"][0]["decision"] == "abstain"


def test_generate_detector_profile_draft_with_llm_retries_malformed_cluster_response(monkeypatch) -> None:
    unresolved_report = {
        "schema_version": "m1_unresolved_grounding_report/v3",
        "builder_version": "m1_detector_builder/v3",
        "source_report_sha256": "report-sha",
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
        "unresolved_actions": [
            {
                "action_id": "A1",
                "integrations": ["ecobee"],
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "bound_files": ["/tmp/ecobee/climate.py"],
                "exec_domain": "ecobee",
                "exec_service": "read_runtime",
                "action_type": "read_runtime",
            }
        ],
        "source_file_summaries": [],
    }
    heuristic_draft = {
        "proposal_count": 1,
        "detector_profile_drafts": [],
        "cluster_summaries": [
            {
                "cluster_id": "ecobee_cluster",
                "integration": "ecobee",
                "family": "CLOUD_STATUS_CALL",
                "action_kind": "read_runtime",
                "promotion_decision": "llm_refine",
                "promotability_score": 4,
                "bound_files": ["/tmp/ecobee/climate.py"],
                "action_ids": ["A1"],
                "generalizes_actions": ["A1"],
                "positive_prototypes": [],
                "negative_prototypes": [],
                "heuristic_rule": {
                    "rule_id": "ecobee:climate_runtime_status_read",
                    "integration": "ecobee",
                    "family": "CLOUD_STATUS_CALL",
                    "action_kind": "read_runtime",
                    "generalization_scope": "file_specific",
                    "generalizes_actions": ["A1"],
                    "origin_cluster_id": "ecobee_cluster",
                    "file_globs": ["ecobee/climate.py"],
                    "call_patterns": ["get_thermostat"],
                    "function_name_patterns": ["async_update"],
                    "negative_call_patterns": [],
                    "negative_function_patterns": ["__init__"],
                    "required_context": ["runtime_update_path"],
                    "forbidden_context": ["dunder_init", "entity_property_getter"],
                    "required_path_signals": ["read_function:async_update"],
                    "forbidden_path_signals": [],
                    "required_runtime_roles": ["runtime_read"],
                    "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
                    "binding_hints": {"preferred_action_kinds": ["status"], "boost_target_tokens": ["runtime"], "phase": "RUNTIME"},
                    "positive_prototypes": [],
                    "negative_prototypes": [],
                    "runtime_path_evidence": ["runtime_function:async_update"],
                    "negative_evidence": ["negative_function:__init__"],
                    "why_not_setup": ["exclude_setup_function:__init__"],
                    "phase": "RUNTIME",
                    "strength": "MEDIUM",
                    "confidence": {"base": 0.8, "emit_threshold": 0.75},
                    "source_file_paths": ["ecobee/climate.py"],
                    "source_unresolved_action_ids": ["A1"],
                    "reviewer_status": "draft",
                },
            }
        ],
    }
    monkeypatch.setattr("optimizer.m1_detector_builder.build_detector_profile_draft", lambda report: heuristic_draft)

    responses = [
        b'{"choices":[{"message":{"content":"{\\"decision\\":\\"refine\\",\\"runtime_family\\":{\\"rule_id\\":\\"bad\\",\\"file_globs\\":[\\"ecobee/climate.py\\"]}}"}}]}',
        b'{"choices":[{"message":{"content":"{\\"decision\\":\\"refine\\",\\"runtime_family\\":{\\"rule_id\\":\\"ecobee:good\\",\\"family\\":\\"CLOUD_STATUS_CALL\\",\\"file_globs\\":[\\"ecobee/climate.py\\"],\\"function_name_patterns\\":[\\"async_update\\"],\\"call_patterns\\":[\\"get_thermostat\\"],\\"required_context\\":[\\"runtime_update_path\\"],\\"forbidden_context\\":[\\"dunder_init\\"],\\"binding_hints\\":{\\"preferred_action_kinds\\":[\\"status\\"],\\"boost_target_tokens\\":[\\"runtime\\"],\\"phase\\":\\"RUNTIME\\"}}}"}}]}',
    ]

    class _FakeResponse:
        def __init__(self, body: bytes):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self._body

    def _fake_urlopen(req, timeout=0):
        del req, timeout
        body = responses.pop(0)
        return _FakeResponse(body)

    monkeypatch.setattr("optimizer.m1_detector_builder.request.urlopen", _fake_urlopen)
    draft = generate_detector_profile_draft_with_llm(
        unresolved_report,
        api_base_url="https://example.invalid/v1/chat/completions",
        api_key="test-key",
        model="gpt-5",
        timeout_s=30,
        max_attempts=2,
        retry_backoff_s=0,
    )

    assert draft["proposal_count"] == 1
    assert draft["cluster_decisions"][0]["decision"] == "refine"
    assert draft["cluster_decisions"][0]["attempts"] == 2
    assert "missing family" in str(draft["cluster_decisions"][0]["llm_error"]).lower()


def test_generate_detector_profile_draft_with_llm_falls_back_to_heuristic_after_retry_budget(monkeypatch) -> None:
    unresolved_report = {
        "schema_version": "m1_unresolved_grounding_report/v3",
        "builder_version": "m1_detector_builder/v3",
        "source_report_sha256": "report-sha",
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
        "unresolved_actions": [
            {
                "action_id": "A1",
                "integrations": ["tuya"],
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "bound_files": ["/tmp/tuya/light.py"],
                "exec_domain": "light",
                "exec_service": "status",
                "action_type": "status",
            }
        ],
        "source_file_summaries": [],
    }
    heuristic_rule = {
        "rule_id": "tuya:heuristic:status",
        "integration": "tuya",
        "family": "CLOUD_STATUS_CALL",
        "action_kind": "status",
        "generalization_scope": "file_specific",
        "generalizes_actions": ["A1"],
        "origin_cluster_id": "tuya_cluster",
        "file_globs": ["tuya/light.py"],
        "call_patterns": ["_read_wrapper"],
        "function_name_patterns": ["brightness"],
        "negative_call_patterns": [],
        "negative_function_patterns": ["async_turn_on"],
        "required_context": ["runtime_path"],
        "forbidden_context": ["dunder_init"],
        "required_path_signals": ["state_accessor_call:self._read_wrapper"],
        "forbidden_path_signals": ["control_function:async_turn_on"],
        "required_runtime_roles": ["runtime_read"],
        "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
        "allow_accessor_fallback": True,
        "binding_hints": {"preferred_action_kinds": ["status"], "boost_target_tokens": ["demo"], "phase": "RUNTIME"},
        "positive_prototypes": [{"prototype_kind": "synthetic_accessor_positive"}],
        "negative_prototypes": [],
        "runtime_path_evidence": ["path_signal:state_accessor_call:self._read_wrapper"],
        "negative_evidence": ["negative_path_signal:control_function:async_turn_on"],
        "why_not_setup": [],
        "phase": "RUNTIME",
        "strength": "MEDIUM",
        "confidence": {"base": 0.8, "emit_threshold": 0.75},
        "source_file_paths": ["tuya/light.py"],
        "source_unresolved_action_ids": ["A1"],
        "reviewer_status": "draft",
    }
    heuristic_draft = {
        "proposal_count": 1,
        "detector_profile_drafts": [],
        "cluster_summaries": [
            {
                "cluster_id": "tuya_cluster",
                "integration": "tuya",
                "family": "CLOUD_STATUS_CALL",
                "action_kind": "status",
                "promotion_decision": "llm_refine",
                "promotability_score": 6,
                "bound_files": ["/tmp/tuya/light.py"],
                "action_ids": ["A1"],
                "generalizes_actions": ["A1"],
                "positive_prototypes": [],
                "negative_prototypes": [],
                "heuristic_rule": heuristic_rule,
            }
        ],
    }
    monkeypatch.setattr("optimizer.m1_detector_builder.build_detector_profile_draft", lambda report: heuristic_draft)

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"decision\\":\\"refine\\",\\"runtime_family\\":{\\"rule_id\\":\\"bad\\",\\"file_globs\\":[\\"other.py\\"]}}"}}]}'

    def _fake_urlopen(req, timeout=0):
        del req, timeout
        return _FakeResponse()

    monkeypatch.setattr("optimizer.m1_detector_builder.request.urlopen", _fake_urlopen)
    draft = generate_detector_profile_draft_with_llm(
        unresolved_report,
        api_base_url="https://example.invalid/v1/chat/completions",
        api_key="test-key",
        model="gpt-5",
        timeout_s=30,
        max_attempts=2,
        retry_backoff_s=0,
    )

    assert draft["proposal_count"] == 1
    assert draft["detector_profile_drafts"][0]["runtime_families"][0]["rule_id"] == "tuya:heuristic:status"
    assert draft["cluster_decisions"][0]["decision"] == "heuristic_fallback"
    assert draft["cluster_decisions"][0]["attempts"] == 2


def test_build_detector_profile_draft_uses_accessor_fallback_for_local_api_read(tmp_path: Path) -> None:
    source_dir = tmp_path / "hue" / "v2"
    source_dir.mkdir(parents=True)
    source = source_dir / "light.py"
    source.write_text(
        """
class DemoHueLight:
    @property
    def is_on(self):
        return self.resource.on.on

    @property
    def brightness(self):
        return self.resource.dimming.brightness
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "hue:bridge_1:bedroom_ceiling_group",
                    "integration": "hue",
                    "file_path": str(source),
                    "protocols": ["LOCAL"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "LOCAL",
                "type": "get_state",
                "target_kind": "local_endpoint",
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:bedroom_ceiling_group"},
                "marker_hints": ["LOCAL_API_READ"],
                "exec": {"kind": "ha_service_call", "domain": "hue", "service": "get_state"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["family"] == "LOCAL_API_READ"
    assert proposal["allow_accessor_fallback"] is True
    assert proposal["generalization_scope"] == "file_specific"
    assert proposal["function_name_patterns"] == ["is_on"]
    assert any(signal.startswith("property_function:is_on") for signal in proposal["required_path_signals"])


def test_build_detector_profile_draft_prefers_state_write_carriers_for_state_write(tmp_path: Path) -> None:
    source_dir = tmp_path / "tplink"
    source_dir.mkdir()
    source = source_dir / "entity.py"
    source.write_text(
        """
class DemoEntity:
    def _handle_coordinator_update(self):
        self._async_call_update_attrs()
        self.async_write_ha_state()

    async def async_refresh_after(self):
        await self.coordinator.async_request_refresh()
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "sensor.vdev_demo_lane",
                    "integration": "tplink",
                    "file_path": str(source),
                    "protocols": ["HA"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "HA",
                "type": "write",
                "target_kind": "ha_entity",
                "target": {"kind": "ha_entity", "id": "sensor.vdev_demo_lane", "entity_id": "sensor.vdev_demo_lane"},
                "marker_hints": ["STATE_WRITE"],
                "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["family"] == "STATE_WRITE"
    assert proposal["required_runtime_roles"] == ["runtime_write"]
    assert "_handle_coordinator_update" in proposal["function_name_patterns"]
    assert "async_write_ha_state" in proposal["call_patterns"]
    assert "async_refresh_after" not in proposal["function_name_patterns"]


def test_build_detector_profile_draft_uses_update_callback_snapshot_for_refresh_cover(tmp_path: Path) -> None:
    source_dir = tmp_path / "switchbot"
    source_dir.mkdir()
    source = source_dir / "cover.py"
    source.write_text(
        """
async def async_open_cover(self, **kwargs):
    await self._device.open()
    self.async_write_ha_state()

def _handle_coordinator_update(self):
    self._attr_is_opening = self._device.is_opening()
    self.async_write_ha_state()
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "ble:switchbot:curtain_lr",
                    "integration": "switchbot",
                    "file_path": str(source),
                    "protocols": ["BLE"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "type": "refresh_cover",
                "target_kind": "ble_device",
                "target": {"kind": "ble_device", "id": "ble:switchbot:curtain_lr"},
                "marker_hints": ["BLE_OP"],
                "exec": {"kind": "ha_service_call", "domain": "switchbot", "service": "refresh_cover"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["family"] == "BLE_OP"
    assert proposal["required_runtime_roles"] == ["runtime_read"]
    assert proposal["function_name_patterns"] == ["_handle_coordinator_update"]
    assert any(
        proto["function_name"] == "_handle_coordinator_update"
        for proto in proposal["positive_prototypes"]
    )
    assert any(signal.startswith("update_callback_function:_handle_coordinator_update") for signal in proposal["required_path_signals"])


def test_build_detector_profile_draft_promotes_update_event_callback_for_read_sensor(tmp_path: Path) -> None:
    source_dir = tmp_path / "xiaomi_ble"
    source_dir.mkdir()
    source = source_dir / "event.py"
    source.write_text(
        """
from homeassistant.core import callback

class Demo:
    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(self.hass, self._update_signal, self._async_handle_event))

    @callback
    def _async_handle_event(self, event):
        self._trigger_event(event)
        self.async_write_ha_state()
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "ble:xiaomi_ble:window_sensor_bedroom",
                    "integration": "xiaomi_ble",
                    "file_path": str(source),
                    "protocols": ["BLE"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "type": "read_sensor",
                "target_kind": "ble_device",
                "target": {"kind": "ble_device", "id": "ble:xiaomi_ble:window_sensor_bedroom"},
                "marker_hints": ["BLE_OP"],
                "exec": {"kind": "ha_service_call", "domain": "event", "service": "read_sensor"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["family"] == "BLE_OP"
    assert proposal["required_runtime_roles"] == ["runtime_read"]
    assert proposal["function_name_patterns"] == ["_async_handle_event"]
    assert any(
        proto["prototype_kind"] in {"positive", "synthetic_update_snapshot_positive"}
        for proto in proposal["positive_prototypes"]
    )


def test_build_detector_profile_draft_splits_multi_file_clusters_by_file(tmp_path: Path) -> None:
    mqtt_dir = tmp_path / "mqtt"
    mqtt_dir.mkdir()
    subscription_source = mqtt_dir / "subscription.py"
    subscription_source.write_text(
        """
def subscribe(callback):
    return callback
""",
        encoding="utf-8",
    )
    sensor_source = mqtt_dir / "sensor.py"
    sensor_source.write_text(
        """
from homeassistant.core import callback

@callback
def _update_state(msg):
    return msg.payload
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(subscription_source), str(sensor_source)],
            "file_bindings": [
                {
                    "device_id": "mqtt:power_meter_kitchen",
                    "integration": "mqtt",
                    "file_path": str(subscription_source),
                    "protocols": ["LOCAL"],
                },
                {
                    "device_id": "mqtt:power_meter_kitchen",
                    "integration": "mqtt",
                    "file_path": str(sensor_source),
                    "protocols": ["LOCAL"],
                },
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "LOCAL",
                "type": "read_last_message",
                "target_kind": "mqtt_topic",
                "target": {"kind": "mqtt_topic", "id": "mqtt:power_meter_kitchen"},
                "marker_hints": ["SUBSCRIBE", "MQTT_SUBSCRIBE"],
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    cluster_ids = {row["cluster_id"] for row in draft["cluster_summaries"]}
    assert any("mqtt__sensor__" in cid for cid in cluster_ids)
    assert any("mqtt__subscription__" in cid for cid in cluster_ids)


def test_build_detector_profile_draft_drops_incidental_call_patterns_for_read_like_subscribe(tmp_path: Path) -> None:
    mqtt_dir = tmp_path / "mqtt"
    mqtt_dir.mkdir()
    source = mqtt_dir / "sensor.py"
    source.write_text(
        """
from homeassistant.core import callback

@callback
def _update_state(msg):
    async_call_later(None, 1, lambda *_: None)
    template(msg.payload)
    return msg.payload
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "mqtt:power_meter_kitchen",
                    "integration": "mqtt",
                    "file_path": str(source),
                    "protocols": ["LOCAL"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "LOCAL",
                "type": "read_last_message",
                "target_kind": "mqtt_topic",
                "target": {"kind": "mqtt_topic", "id": "mqtt:power_meter_kitchen"},
                "marker_hints": ["SUBSCRIBE", "MQTT_SUBSCRIBE"],
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert proposal["family"] in {"SUBSCRIBE", "MQTT_SUBSCRIBE"}
    assert proposal["required_runtime_roles"] == ["runtime_read", "runtime_subscribe"]
    assert proposal["required_context"] == ["runtime_path", "subscription_path"]
    assert proposal["function_name_patterns"] == ["_update_state"]
    assert proposal["call_patterns"] == []


def test_build_detector_profile_draft_prefers_update_snapshot_carrier_over_refresh_wrapper(tmp_path: Path) -> None:
    source_dir = tmp_path / "tplink"
    source_dir.mkdir()
    source = source_dir / "entity.py"
    source.write_text(
        """
def async_refresh_after(func):
    async def _async_wrap(self, *args, **kwargs):
        await self.coordinator.async_request_refresh()
        return await func(self, *args, **kwargs)
    return _async_wrap

class DemoEntity:
    @callback
    def _handle_coordinator_update(self):
        self._async_call_update_attrs()
        super()._handle_coordinator_update()

    @callback
    def _async_call_update_attrs(self):
        return self._async_update_attrs()
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "tplink:plug.coffee_machine",
                    "integration": "tplink",
                    "file_path": str(source),
                    "protocols": ["LOCAL"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "LOCAL",
                "type": "get_state",
                "target_kind": "local_endpoint",
                "target": {"kind": "local_endpoint", "id": "tplink:plug.coffee_machine"},
                "marker_hints": ["LOCAL_API_READ"],
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "get_state"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert "_handle_coordinator_update" in proposal["function_name_patterns"]
    assert any(
        signal.startswith("update_callback_function:_handle_coordinator_update")
        for signal in proposal["required_path_signals"]
    )
    assert "async_refresh_after" not in proposal["function_name_patterns"]
    assert "_async_wrap" not in proposal["function_name_patterns"]


def test_build_detector_profile_draft_prunes_conflicting_negative_selectors(tmp_path: Path) -> None:
    source_dir = tmp_path / "demo"
    source_dir.mkdir()
    source = source_dir / "status.py"
    source.write_text(
        """
async def async_update(self):
    return await self.client.get_status()

async def async_setup_entry(hass, entry):
    await self.client.get_status()
    return True
""",
        encoding="utf-8",
    )

    target = OptimizationTarget(
        meta={"vdev_id": "vdev_demo", "name": "Demo"},
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "demo:light.status",
                    "integration": "demo",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "status",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "demo:light.status"},
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "status"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    report = build_unresolved_grounding_report(target, {"missing_critical_action_ids": ["A1"], "resolved_action_ids": []})
    draft = build_detector_profile_draft(report)
    proposal = draft["detector_profile_drafts"][0]["runtime_families"][0]
    assert "get_status" in proposal["call_patterns"]
    assert "get_status" not in proposal["negative_call_patterns"]


def test_merge_runtime_family_keeps_heuristic_selectors_when_llm_lists_are_empty() -> None:
    heuristic_rule = {
        "rule_id": "demo:file_runtime_status_read",
        "function_name_patterns": ["async_update"],
        "call_patterns": ["get_status"],
        "binding_hints": {
            "preferred_action_kinds": ["status"],
            "boost_target_tokens": ["demo:light.status"],
            "phase": "RUNTIME",
        },
    }
    runtime_family = {
        "function_name_patterns": [],
        "call_patterns": [],
        "binding_hints": {"preferred_action_kinds": [], "boost_target_tokens": []},
    }
    merged = _merge_runtime_family_with_heuristic_defaults(runtime_family, heuristic_rule)
    assert merged["function_name_patterns"] == ["async_update"]
    assert merged["call_patterns"] == ["get_status"]
    assert merged["binding_hints"]["preferred_action_kinds"] == ["status"]
    assert merged["binding_hints"]["boost_target_tokens"] == ["demo:light.status"]


def test_validate_runtime_family_rejects_missing_positive_selector() -> None:
    cluster = {
        "integration": "demo",
        "family": "CLOUD_STATUS_CALL",
        "action_kind": "status",
        "bound_files": ["demo/status.py"],
        "generalizes_actions": ["A1"],
    }
    heuristic_rule = {
        "required_path_signals": ["read_function:async_update"],
        "function_name_patterns": ["async_update"],
    }
    runtime_family = {
        "integration": "demo",
        "family": "CLOUD_STATUS_CALL",
        "action_kind": "status",
        "file_globs": ["demo/status.py"],
        "required_path_signals": ["read_function:async_update"],
        "function_name_patterns": [],
        "call_patterns": [],
    }
    try:
        _validate_runtime_family_against_cluster(runtime_family, cluster=cluster, heuristic_rule=heuristic_rule)
    except RuntimeError as exc:
        assert "positive selector" in str(exc)
    else:
        raise AssertionError("expected positive-selector validation failure")


def test_generate_detector_profile_draft_with_llm_timeout_falls_back_to_heuristic(monkeypatch) -> None:
    unresolved_report = {
        "schema_version": "m1_unresolved_grounding_report/v3",
        "builder_version": "m1_detector_builder/v3",
        "source_report_sha256": "report-sha",
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
        "unresolved_actions": [
            {
                "action_id": "A1",
                "integrations": ["ecobee"],
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "bound_files": ["/tmp/ecobee/climate.py"],
                "exec_domain": "ecobee",
                "exec_service": "read_runtime",
                "action_type": "read_runtime",
            }
        ],
        "source_file_summaries": [],
    }
    heuristic_draft = {
        "proposal_count": 1,
        "detector_profile_drafts": [],
        "cluster_summaries": [
            {
                "cluster_id": "ecobee_cluster",
                "integration": "ecobee",
                "family": "CLOUD_STATUS_CALL",
                "action_kind": "read_runtime",
                "promotion_decision": "llm_refine",
                "promotability_score": 6,
                "bound_files": ["/tmp/ecobee/climate.py"],
                "action_ids": ["A1"],
                "generalizes_actions": ["A1"],
                "positive_prototypes": [],
                "negative_prototypes": [],
                "heuristic_rule": {
                    "rule_id": "ecobee:climate_runtime_status_read",
                    "integration": "ecobee",
                    "family": "CLOUD_STATUS_CALL",
                    "action_kind": "read_runtime",
                    "generalization_scope": "file_specific",
                    "generalizes_actions": ["A1"],
                    "origin_cluster_id": "ecobee_cluster",
                    "file_globs": ["ecobee/climate.py"],
                    "call_patterns": ["get_thermostat"],
                    "function_name_patterns": ["async_update"],
                    "negative_call_patterns": [],
                    "negative_function_patterns": ["__init__"],
                    "required_context": ["runtime_update_path"],
                    "forbidden_context": ["dunder_init"],
                    "required_path_signals": ["read_function:async_update"],
                    "forbidden_path_signals": [],
                    "required_runtime_roles": ["runtime_read"],
                    "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
                    "binding_hints": {"preferred_action_kinds": ["status"], "boost_target_tokens": ["runtime"], "phase": "RUNTIME"},
                    "positive_prototypes": [],
                    "negative_prototypes": [],
                    "runtime_path_evidence": ["runtime_function:async_update"],
                    "negative_evidence": [],
                    "why_not_setup": [],
                    "phase": "RUNTIME",
                    "strength": "MEDIUM",
                    "confidence": {"base": 0.8, "emit_threshold": 0.75},
                    "source_file_paths": ["ecobee/climate.py"],
                    "source_unresolved_action_ids": ["A1"],
                    "reviewer_status": "draft",
                },
            }
        ],
    }
    monkeypatch.setattr("optimizer.m1_detector_builder.build_detector_profile_draft", lambda report: heuristic_draft)

    def _fake_urlopen(req, timeout=0):
        del req, timeout
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr("optimizer.m1_detector_builder.request.urlopen", _fake_urlopen)
    draft = generate_detector_profile_draft_with_llm(
        unresolved_report,
        api_base_url="https://example.invalid/v1/chat/completions",
        api_key="test-key",
        model="gpt-5",
        timeout_s=30,
        max_attempts=1,
        retry_backoff_s=0,
    )

    assert draft["proposal_count"] == 1
    assert draft["cluster_decisions"][0]["decision"] == "heuristic_fallback"
    assert "timeout" in str(draft["cluster_decisions"][0]["llm_error"]).lower()


def test_generate_detector_profile_draft_with_llm_remote_disconnect_falls_back_to_heuristic(monkeypatch) -> None:
    unresolved_report = {
        "schema_version": "m1_unresolved_grounding_report/v3",
        "builder_version": "m1_detector_builder/v3",
        "source_report_sha256": "report-sha",
        "missing_critical_action_ids": ["A1"],
        "resolved_action_ids": [],
        "unresolved_actions": [
            {
                "action_id": "A1",
                "integrations": ["ecobee"],
                "marker_hints": ["CLOUD_STATUS_CALL"],
                "bound_files": ["/tmp/ecobee/climate.py"],
                "exec_domain": "ecobee",
                "exec_service": "read_runtime",
                "action_type": "read_runtime",
            }
        ],
        "source_file_summaries": [],
    }
    heuristic_draft = {
        "proposal_count": 1,
        "detector_profile_drafts": [],
        "cluster_summaries": [
            {
                "cluster_id": "ecobee_cluster",
                "integration": "ecobee",
                "family": "CLOUD_STATUS_CALL",
                "action_kind": "read_runtime",
                "promotion_decision": "llm_refine",
                "promotability_score": 6,
                "bound_files": ["/tmp/ecobee/climate.py"],
                "action_ids": ["A1"],
                "generalizes_actions": ["A1"],
                "positive_prototypes": [],
                "negative_prototypes": [],
                "heuristic_rule": {
                    "rule_id": "ecobee:climate_runtime_status_read",
                    "integration": "ecobee",
                    "family": "CLOUD_STATUS_CALL",
                    "action_kind": "read_runtime",
                    "generalization_scope": "file_specific",
                    "generalizes_actions": ["A1"],
                    "origin_cluster_id": "ecobee_cluster",
                    "file_globs": ["ecobee/climate.py"],
                    "call_patterns": ["get_thermostat"],
                    "function_name_patterns": ["async_update"],
                    "negative_call_patterns": [],
                    "negative_function_patterns": ["__init__"],
                    "required_context": ["runtime_update_path"],
                    "forbidden_context": ["dunder_init"],
                    "required_path_signals": ["read_function:async_update"],
                    "forbidden_path_signals": [],
                    "required_runtime_roles": ["runtime_read"],
                    "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
                    "binding_hints": {
                        "preferred_action_kinds": ["status"],
                        "boost_target_tokens": ["runtime"],
                        "phase": "RUNTIME",
                    },
                    "positive_prototypes": [],
                    "negative_prototypes": [],
                    "runtime_path_evidence": ["runtime_function:async_update"],
                    "negative_evidence": [],
                    "why_not_setup": [],
                    "phase": "RUNTIME",
                    "strength": "MEDIUM",
                    "confidence": {"base": 0.8, "emit_threshold": 0.75},
                    "source_file_paths": ["ecobee/climate.py"],
                    "source_unresolved_action_ids": ["A1"],
                    "reviewer_status": "draft",
                },
            }
        ],
    }
    monkeypatch.setattr("optimizer.m1_detector_builder.build_detector_profile_draft", lambda report: heuristic_draft)

    def _fake_urlopen(req, timeout=0):
        del req, timeout
        raise RemoteDisconnected("Remote end closed connection without response")

    monkeypatch.setattr("optimizer.m1_detector_builder.request.urlopen", _fake_urlopen)
    draft = generate_detector_profile_draft_with_llm(
        unresolved_report,
        api_base_url="https://example.invalid/v1/chat/completions",
        api_key="test-key",
        model="gpt-5",
        timeout_s=30,
        max_attempts=1,
        retry_backoff_s=0,
    )

    assert draft["proposal_count"] == 1
    assert draft["cluster_decisions"][0]["decision"] == "heuristic_fallback"
    assert "remote end closed connection" in str(draft["cluster_decisions"][0]["llm_error"]).lower()
