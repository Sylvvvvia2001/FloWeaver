from pathlib import Path

from dsl.contracts import Batch, ExecutionPlan, Marker, Phase, Provider
from dsl.io import load_json
import optimizer.pipeline as optimizer_pipeline
from optimizer.pipeline import GroundingCoverageError
from optimizer.pipeline import FloWeaverOptimizer
from profile_builder.pipeline import HAPProfileBuilder
from runtime.events import EventRecorder
from runtime.trace import compare_traces


def test_profile_and_optimizer_pipeline(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text(
        "The integration must implement async_setup_entry for the config entry.\nEntities should unsubscribe on unload to avoid stale listeners.",
        encoding="utf-8",
    )
    (repo / "demo.py").write_text(
        """
async def async_setup_entry(hass, entry):
    await coordinator.async_config_entry_first_refresh()
    entity.async_write_ha_state()
    unsub = dispatcher_connect(hass, \"sig\", entity.async_write_ha_state)
    hass.data[entry.entry_id] = {\"unsub\": unsub}
    return True

async def async_unload_entry(hass, entry):
    unsub = hass.data[entry.entry_id][\"unsub\"]
    unsub()
    return True
""",
        encoding="utf-8",
    )

    profile_out = tmp_path / "profile"
    builder = HAPProfileBuilder(docs, repo, profile_out)
    artifacts = builder.run(profile_id="test_profile")

    assert (profile_out / "ha_profile.json").exists()
    assert artifacts.profile.rules

    opt_out = tmp_path / "opt"
    optimizer = FloWeaverOptimizer(
        integration_name="demo",
        integration_path=repo / "demo.py",
        profile_path=profile_out / "ha_profile.json",
        out_dir=opt_out,
    )
    result = optimizer.run()

    assert result.marker_set.markers
    assert (opt_out / "execution_certificate.json").exists()
    assert (opt_out / "m1_marker_report.json").exists()
    assert (opt_out / "m5_trust_plan.json").exists()
    witness = load_json(opt_out / "hard_edge_witness.json")
    assert "edge_count" in witness
    assert "edges" in witness


def test_optimizer_pipeline_from_vdev_specs(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text(
        "The integration must implement async_setup_entry for the config entry.\nSubscriptions should be cleaned up on unload for the entity lifecycle.",
        encoding="utf-8",
    )
    (repo / "ble_integration.py").write_text(
        """
async def async_setup_entry(hass, entry):
    await client.connect()
    value = await client.read_gatt_char("temp")
    entity.async_write_ha_state()
    return value
""",
        encoding="utf-8",
    )
    (repo / "cloud_integration.py").write_text(
        """
async def async_setup_entry(hass, entry):
    result = await client.call_api("tuya:device.control")
    entity.async_write_ha_state()
    return result

async def async_unload_entry(hass, entry):
    unsub = hass.data[entry.entry_id]["unsub"]
    unsub()
    return True
""",
        encoding="utf-8",
    )

    profile_out = tmp_path / "profile"
    builder = HAPProfileBuilder(docs, repo, profile_out)
    builder.run(profile_id="test_profile")

    vdev_spec = tmp_path / "vdev_spec.json"
    source_spec = tmp_path / "source_spec.json"
    run_spec = tmp_path / "run_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_demo_01", "name": "Demo VDev"},
  "sources": {"ha_core": {"repo_path": ".", "commit": "HEAD", "domains": ["demo"], "platforms": ["sensor"]}},
  "vdev": {
    "entrypoint": {"kind": "ha_service", "service": {"domain": "floweaver", "name": "run"}},
    "interfaces": {"state_contract": {"writes": [{"entity_id": "sensor.vdev_x"}]}},
    "actions": [
      {"action_id": "A1", "type": "read", "target": {"kind": "ble_device", "id": "ble:aa:bb:cc"}, "io": {"protocol": "BLE"}, "exec": {"kind": "ha_service_call", "domain": "ble_proxy", "service": "read", "data_template": {"device_id": "ble:aa:bb:cc"}}, "semantics": {"critical": true}},
      {"action_id": "A2", "type": "call_api", "target": {"kind": "cloud_endpoint", "id": "tuya:device.control"}, "io": {"protocol": "CLOUD"}, "exec": {"kind": "ha_service_call", "domain": "tuya", "service": "call_api", "data_template": {"endpoint": "tuya:device.control"}}, "semantics": {"critical": true}},
      {"action_id": "A3", "type": "write", "target": {"kind": "ha_entity", "id": "sensor.vdev_x", "entity_id": "sensor.vdev_x"}, "io": {"protocol": "HA"}, "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity", "data_template": {"entity_id": "sensor.vdev_x"}}, "semantics": {"critical": true}}
    ],
    "dependencies": {"hard": [{"before": "A1", "after": "A3"}, {"before": "A2", "after": "A3"}]}
  },
  "objectives": {"primary": "minimize_tail_latency"},
  "constraints": {"optimization_knobs": {"allow_concurrency": true, "max_concurrency": {"ble": 1, "cloud": 2, "total": 3}}},
  "validation": {"differential_tests": {"enabled": true, "scenarios": ["baseline_happy_path"], "runs_per_scenario": 2}}
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "ble_dev", "integration": "demo_ble", "file_path": "{repo / 'ble_integration.py'}", "protocols": ["BLE"]}},
    {{"device_id": "cloud_dev", "integration": "demo_cloud", "file_path": "{repo / 'cloud_integration.py'}", "protocols": ["CLOUD"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    run_spec.write_text(
        """
{
  "validation": {"differential_tests": {"enabled": true, "scenarios": ["baseline_happy_path"], "runs_per_scenario": 2}},
  "observation": {"canonicalization_version": "v1", "semantic_ops": ["STATE_WRITE", "BLE_OP", "CLOUD_OP"]}
}
""",
        encoding="utf-8",
    )

    opt_out = tmp_path / "opt"
    optimizer = FloWeaverOptimizer(
        integration_name="vdev_demo",
        profile_path=profile_out / "ha_profile.json",
        out_dir=opt_out,
        vdev_spec_path=vdev_spec,
        source_spec_path=source_spec,
        run_spec_path=run_spec,
    )
    result = optimizer.run()

    assert len(result.optimization_target.source_scope["files"]) == 2
    assert (opt_out / "m_minus1_target.json").exists()
    assert (opt_out / "execution_certificate.json").exists()
    assert (opt_out / "m5_trust_plan.json").exists()
    assert (opt_out / "hard_edge_witness.json").exists()
    m5_plan = load_json(opt_out / "m5_execution_plan.json")
    flat_nodes = [node for batch in m5_plan["ordered_batches"] for group in batch["parallel_groups"] for node in group]
    assert "A1" in flat_nodes and "A2" in flat_nodes and "A3" in flat_nodes


def test_pipeline_replay_model_is_action_local_and_symmetric(tmp_path: Path) -> None:
    optimizer = FloWeaverOptimizer(
        integration_name="demo",
        profile_path=tmp_path / "missing_profile.json",
        out_dir=tmp_path / "opt",
    )
    target = optimizer._raw_to_target(
        {
            "source_scope": {"files": [str(tmp_path / "demo.py")]},
            "vdev_actions": [
                {
                    "action_id": "A4",
                    "protocol": "CLOUD",
                    "target": {"kind": "cloud_endpoint", "id": "tuya:light.living_room.status"},
                    "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
                },
                {
                    "action_id": "A8",
                    "protocol": "HA",
                    "target": {"kind": "ha_entity", "entity_id": "sensor.demo"},
                    "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
                },
            ],
            "critical_action_ids": ["A4", "A8"],
        }
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="CLOUD_HTTP_CALL",
            file_path=str(tmp_path / "demo.py"),
            function_name="async_status",
            line_start=10,
            line_end=10,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A4",
            related_action_ids=["A4"],
        ),
        Marker(
            marker_id="m2",
            marker_type="STATE_WRITE",
            file_path=str(tmp_path / "demo.py"),
            function_name="async_publish",
            line_start=20,
            line_end=20,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A8",
            related_action_ids=["A8"],
        ),
    ]
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A4"], ["A8"]],
                constraints=[],
                session_policy={},
                rate_policy={},
                guards=[],
                fallback=[],
            )
        ],
        meta={},
    )
    scenario = type("Scenario", (), {"scenario_id": "s0"})()
    baseline_rec = EventRecorder("demo", "s0", "baseline")
    optimized_rec = EventRecorder("demo", "s0", "optimized")

    optimizer._simulate_baseline_runner(markers, target)(baseline_rec, scenario)
    optimizer._simulate_optimized_runner(markers, plan, target)(optimized_rec, scenario)

    baseline_trace = baseline_rec.as_trace()
    assert baseline_trace.events[0].target == "tuya:light.living_room.status"
    assert baseline_trace.events[1].target == "sensor.demo"

    diff = compare_traces(baseline_rec.as_trace(), optimized_rec.as_trace())
    assert diff.strict_equal
    assert diff.tolerant_equal


def test_pipeline_baseline_action_order_prefers_target_dependency_order(tmp_path: Path) -> None:
    optimizer = FloWeaverOptimizer(
        integration_name="demo",
        profile_path=tmp_path / "missing_profile.json",
        out_dir=tmp_path / "opt2",
    )
    target = optimizer._raw_to_target(
        {
            "source_scope": {"files": [str(tmp_path / "demo.py")]},
            "vdev_actions": [
                {
                    "action_id": "A1",
                    "protocol": "BLE",
                    "target": {"kind": "ble_device", "id": "ble:a1"},
                    "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
                },
                {
                    "action_id": "A2",
                    "protocol": "BLE",
                    "target": {"kind": "ble_device", "id": "ble:a2"},
                    "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
                },
                {
                    "action_id": "A3",
                    "protocol": "HA",
                    "target": {"kind": "ha_entity", "entity_id": "sensor.demo"},
                    "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
                },
            ],
            "hard_dependencies": [
                {"before": "A1", "after": "A2"},
                {"before": "A2", "after": "A3"},
            ],
            "critical_action_ids": ["A1", "A2", "A3"],
        }
    )
    markers = [
        Marker(
            marker_id="m_a3",
            marker_type="STATE_WRITE",
            file_path=str(tmp_path / "demo.py"),
            function_name="writeback",
            line_start=30,
            line_end=30,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A3",
            related_action_ids=["A3"],
        ),
        Marker(
            marker_id="m_a2",
            marker_type="BLE_CONNECT",
            file_path=str(tmp_path / "demo.py"),
            function_name="connect",
            line_start=10,
            line_end=10,
            strength="STRONG",
            phase=Phase.TEARDOWN.value,
            primary_action_id="A2",
            related_action_ids=["A2"],
        ),
        Marker(
            marker_id="m_a1",
            marker_type="BLE_GATT_OP",
            file_path=str(tmp_path / "demo.py"),
            function_name="read",
            line_start=20,
            line_end=20,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A1",
            related_action_ids=["A1"],
        ),
    ]

    ordered = optimizer._ordered_markers(markers)
    assert optimizer._baseline_action_order(ordered, target) == ["A1", "A2", "A3"]


def test_optimizer_fails_fast_when_critical_actions_not_grounded(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text(
        "The integration must implement async_setup_entry.\nEntities should write state after refresh.",
        encoding="utf-8",
    )
    source = repo / "state_only.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    entity.async_write_ha_state()
    return True
""",
        encoding="utf-8",
    )

    profile_out = tmp_path / "profile"
    builder = HAPProfileBuilder(docs, repo, profile_out)
    builder.run(profile_id="test_profile")

    vdev_spec = tmp_path / "vdev_spec.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_demo_ungrounded", "name": "Ungrounded Demo"},
  "sources": {"ha_core": {"repo_path": ".", "commit": "HEAD", "domains": ["demo"], "platforms": ["sensor"]}},
  "vdev": {
    "entrypoint": {"kind": "ha_service", "service": {"domain": "floweaver", "name": "run"}},
    "interfaces": {"state_contract": {"writes": [{"entity_id": "sensor.vdev_x"}]}},
    "actions": [
      {"action_id": "A1", "type": "read", "target": {"kind": "ble_device", "id": "ble:aa:bb:cc"}, "io": {"protocol": "BLE"}, "exec": {"kind": "ha_service_call", "domain": "switchbot", "service": "refresh"}, "semantics": {"critical": true}},
      {"action_id": "A3", "type": "write", "target": {"kind": "ha_entity", "id": "sensor.vdev_x", "entity_id": "sensor.vdev_x"}, "io": {"protocol": "HA"}, "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity", "data_template": {"entity_id": "sensor.vdev_x"}}, "semantics": {"critical": true}}
    ],
    "dependencies": {"hard": [{"before": "A1", "after": "A3"}]}
  },
  "objectives": {"primary": "minimize_tail_latency"},
  "constraints": {"optimization_knobs": {"allow_concurrency": true}},
  "validation": {"differential_tests": {"enabled": true, "scenarios": ["baseline_happy_path"], "runs_per_scenario": 1}}
}
""",
        encoding="utf-8",
    )
    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "demo", "integration": "demo", "file_path": "{source}", "protocols": ["HA"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    opt_out = tmp_path / "opt"
    optimizer = FloWeaverOptimizer(
        integration_name="ungrounded_demo",
        profile_path=profile_out / "ha_profile.json",
        out_dir=opt_out,
        vdev_spec_path=vdev_spec,
        source_spec_path=source_spec,
    )

    try:
        optimizer.run()
    except GroundingCoverageError as exc:
        assert "GROUNDING_FAILED:M1" in str(exc)
    else:
        raise AssertionError("expected optimizer grounding gate to fail")

    report = load_json(opt_out / "m1_marker_report.json")
    assert report["marker_coverage_ok"] is False
    assert "A1" in report["missing_critical_action_ids"]
    unresolved = load_json(opt_out / "m1_unresolved_grounding_report.json")
    draft = load_json(opt_out / "m1_detector_profile_draft.json")
    assert unresolved["schema_version"] == "m1_unresolved_grounding_report/v3"
    assert "A1" in unresolved["missing_critical_action_ids"]
    assert unresolved["source_report_sha256"]
    assert draft["schema_version"] == "m1_detector_draft/v3"
    assert draft["prompt_version"] == "m1_detector_builder_prompt/v3"
    assert draft["proposal_count"] == 0


def test_optimizer_pipeline_enables_llm_detector_by_default_when_env_is_present(monkeypatch) -> None:
    target = optimizer_pipeline.OptimizationTarget(
        source_scope={"files": ["/tmp/demo.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "ha_service_call"}}],
        validation={},
    )

    monkeypatch.delenv("FLOWEAVER_LLM_API_BASE_URL", raising=False)
    monkeypatch.delenv("FLOWEAVER_LLM_API_KEY", raising=False)
    assert FloWeaverOptimizer._should_try_llm_detector(target) is False

    monkeypatch.setenv("FLOWEAVER_LLM_API_BASE_URL", "https://example.invalid/v1/chat/completions")
    monkeypatch.setenv("FLOWEAVER_LLM_API_KEY", "test-key")
    assert FloWeaverOptimizer._should_try_llm_detector(target) is True


def test_optimizer_pipeline_appends_auto_grounding_profiles_without_mutating_original_target() -> None:
    target = optimizer_pipeline.OptimizationTarget(
        source_scope={"files": ["/tmp/demo.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "ha_service_call"}}],
        validation={"grounding_profile_paths": ["/tmp/existing.json"]},
    )

    updated = FloWeaverOptimizer._target_with_grounding_profiles(target, ["/tmp/auto_a.json", "/tmp/auto_b.json"])

    assert target.validation["grounding_profile_paths"] == ["/tmp/existing.json"]
    assert updated.validation["grounding_profile_paths"] == [
        "/tmp/existing.json",
        "/tmp/auto_a.json",
        "/tmp/auto_b.json",
    ]


def test_optimizer_expands_helper_only_bindings_to_runtime_carriers(tmp_path: Path) -> None:
    integration_dir = tmp_path / "xiaomi_ble"
    integration_dir.mkdir()
    helper_file = integration_dir / "device.py"
    runtime_file = integration_dir / "sensor.py"
    helper_file.write_text(
        """
def device_key_to_bluetooth_entity_key(device_key):
    return device_key
""",
        encoding="utf-8",
    )
    runtime_file.write_text(
        """
async def async_update(self):
    return await self.device.read_status()
""",
        encoding="utf-8",
    )

    optimizer = FloWeaverOptimizer(
        integration_name="demo",
        profile_path=tmp_path / "missing_profile.json",
        out_dir=tmp_path / "opt",
    )
    target = optimizer._raw_to_target(
        {
            "source_scope": {
                "files": [str(helper_file)],
                "file_bindings": [
                    {
                        "device_id": "ble:xiaomi_ble:bedside_lamp_right",
                        "integration": "xiaomi_ble",
                        "file_path": str(helper_file),
                        "protocols": ["BLE"],
                    }
                ],
            },
            "vdev_actions": [
                {
                    "action_id": "A1",
                    "type": "read_status",
                    "protocol": "BLE",
                    "target_kind": "ble_device",
                    "target": {"kind": "ble_device", "id": "ble:xiaomi_ble:bedside_lamp_right"},
                    "marker_hints": ["BLE_OP"],
                    "exec": {"kind": "ha_service_call", "domain": "xiaomi_ble", "service": "read_status"},
                }
            ],
            "critical_action_ids": ["A1"],
        }
    )

    expanded = optimizer._expand_target_runtime_carriers(target)
    assert str(runtime_file.resolve()) in expanded.source_scope["files"]
    assert any(
        row.get("file_path") == str(runtime_file.resolve())
        for row in expanded.source_scope["file_bindings"]
    )


def test_optimizer_expands_weak_platform_read_binding_to_coordinator_carrier(tmp_path: Path) -> None:
    integration_dir = tmp_path / "roku"
    integration_dir.mkdir()
    platform_file = integration_dir / "media_player.py"
    coordinator_file = integration_dir / "coordinator.py"
    platform_file.write_text(
        """
async def async_media_play(self):
    await self.coordinator.async_request_refresh()
""",
        encoding="utf-8",
    )
    coordinator_file.write_text(
        """
async def _async_update_data(self):
    return await self.roku.update()
""",
        encoding="utf-8",
    )

    optimizer = FloWeaverOptimizer(
        integration_name="demo",
        profile_path=tmp_path / "missing_profile.json",
        out_dir=tmp_path / "opt",
    )
    target = optimizer._raw_to_target(
        {
            "source_scope": {
                "files": [str(platform_file)],
                "file_bindings": [
                    {
                        "device_id": "local:roku:living_room_tv",
                        "integration": "roku",
                        "file_path": str(platform_file),
                        "protocols": ["LOCAL"],
                    }
                ],
            },
            "vdev_actions": [
                {
                    "action_id": "A1",
                    "type": "get_state",
                    "protocol": "LOCAL",
                    "target_kind": "local_api",
                    "target": {"kind": "local_api", "id": "local:roku:living_room_tv"},
                    "marker_hints": ["LOCAL_API_READ"],
                    "exec": {"kind": "ha_service_call", "domain": "roku", "service": "get_state"},
                }
            ],
            "critical_action_ids": ["A1"],
        }
    )

    expanded = optimizer._expand_target_runtime_carriers(target)
    assert str(coordinator_file.resolve()) in expanded.source_scope["files"]
    assert any(
        row.get("file_path") == str(coordinator_file.resolve())
        for row in expanded.source_scope["file_bindings"]
    )


def test_optimizer_expands_state_write_bindings_to_writeback_carriers(tmp_path: Path) -> None:
    integration_dir = tmp_path / "hue" / "v2"
    integration_dir.mkdir(parents=True)
    light_file = integration_dir / "light.py"
    entity_file = integration_dir / "entity.py"
    light_file.write_text(
        """
async def async_turn_on(self):
    await self.bridge.async_request_call()
""",
        encoding="utf-8",
    )
    entity_file.write_text(
        """
def _handle_event(self, event_type, resource):
    self.on_update()
    self.async_write_ha_state()
""",
        encoding="utf-8",
    )

    optimizer = FloWeaverOptimizer(
        integration_name="demo",
        profile_path=tmp_path / "missing_profile.json",
        out_dir=tmp_path / "opt",
    )
    target = optimizer._raw_to_target(
        {
            "source_scope": {
                "files": [str(light_file)],
                "file_bindings": [
                    {
                        "device_id": "sensor.vdev_demo_local_lane",
                        "integration": "hue",
                        "file_path": str(light_file),
                        "protocols": ["HA"],
                    }
                ],
            },
            "vdev_actions": [
                {
                    "action_id": "A1",
                    "type": "write",
                    "protocol": "HA",
                    "target_kind": "ha_entity",
                    "target": {"kind": "ha_entity", "id": "sensor.vdev_demo_local_lane", "entity_id": "sensor.vdev_demo_local_lane"},
                    "marker_hints": ["STATE_WRITE"],
                    "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
                }
            ],
            "critical_action_ids": ["A1"],
        }
    )

    expanded = optimizer._expand_target_runtime_carriers(target)
    assert str(entity_file.resolve()) in expanded.source_scope["files"]
    assert any(
        row.get("file_path") == str(entity_file.resolve())
        for row in expanded.source_scope["file_bindings"]
    )


def test_module_switches_use_paper_names_with_legacy_aliases(tmp_path: Path) -> None:
    target = FloWeaverOptimizer._raw_to_target(
        {
            "source_scope": {"files": [str(tmp_path / "demo.py")]},
            "vdev_actions": [
                {
                    "action_id": "A1",
                    "protocol": "HA",
                    "target": {"kind": "ha_entity", "entity_id": "sensor.demo"},
                    "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
                }
            ],
            "validation": {"modules": {"primitive_extractor": False, "m5_macro_scheduler": False}},
        }
    )

    switches = FloWeaverOptimizer._module_switches(target)

    assert switches["primitive_extractor"] is False
    assert switches["semantic_marker"] is False
    assert switches["semantic_primitive_extractor"] is False
    assert switches["macro_level_scheduler"] is False
