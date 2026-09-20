from pathlib import Path

import pytest

from optimizer.m_minus1_scoping import build_optimization_target


def test_build_optimization_target_from_specs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_b = repo / "int_b.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")
    int_b.write_text("async def async_unload_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec.json"
    source_spec = tmp_path / "source_spec.json"
    run_spec = tmp_path / "run_spec.json"
    target_out = tmp_path / "target.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_demo_01", "name": "Demo VDev"},
  "sources": {"ha_core": {"repo_path": ".", "commit": "HEAD", "domains": ["demo"], "platforms": ["sensor"]}},
  "vdev": {
    "entrypoint": {"kind": "ha_service", "service": {"domain": "floweaver", "name": "run"}},
    "interfaces": {"state_contract": {"writes": [{"entity_id": "sensor.vdev_x"}] }},
    "actions": [
      {"action_id": "A1", "type": "read", "target": {"kind": "ble_device", "id": "ble:aa:bb:cc"}, "io": {"protocol": "BLE"}, "exec": {"kind": "ha_service_call", "domain": "ble_proxy", "service": "read", "data_template": {"device_id": "ble:aa:bb:cc"}}, "semantics": {"critical": true}},
      {"action_id": "A2", "type": "call_api", "target": {"kind": "cloud_endpoint", "id": "tuya:device.control"}, "io": {"protocol": "CLOUD"}, "exec": {"kind": "ha_service_call", "domain": "tuya", "service": "call_api", "data_template": {"endpoint": "tuya:device.control"}}, "semantics": {"critical": true}},
      {"action_id": "A3", "type": "write", "target": {"kind": "ha_entity", "id": "sensor.vdev_x", "entity_id": "sensor.vdev_x"}, "io": {"protocol": "HA"}, "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity", "data_template": {"entity_id": "sensor.vdev_x"}}, "semantics": {"critical": true}}
    ],
    "dependencies": {"hard": [{"before": "A1", "after": "A3"}, {"before": "A2", "after": "A3"}]}
  },
  "objectives": {"primary": "minimize_tail_latency"},
  "constraints": {"optimization_knobs": {"allow_concurrency": true, "max_concurrency": {"ble": 1, "cloud": 4, "total": 6}}},
  "validation": {"differential_tests": {"enabled": true, "scenarios": ["baseline_happy_path"], "runs_per_scenario": 2}}
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "commit": "HEAD",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_ble", "file_path": "{int_a}", "protocols": ["BLE"]}},
    {{"device_id": "dev_b", "integration": "demo_cloud", "file_path": "{int_b}", "protocols": ["CLOUD"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    run_spec.write_text(
        """
{
  "validation": {"differential_tests": {"enabled": true, "scenarios": ["baseline_happy_path"], "runs_per_scenario": 2}},
  "observation": {"canonicalization_version": "v1", "semantic_ops": ["STATE_WRITE"]},
  "profile_version": "ha_profile_default"
}
""",
        encoding="utf-8",
    )

    target = build_optimization_target(vdev_spec, source_spec, run_spec, target_out)
    assert len(target.source_scope["files"]) == 2
    assert "sensor.vdev_x" in target.target_anchors["entities"]
    assert target.target_anchors["required_state_writes"] == ["sensor.vdev_x"]
    assert target.critical_action_ids == ["A1", "A2", "A3"]
    assert target.validation["differential_tests"]["runs_per_scenario"] == 2


def test_build_optimization_target_fails_without_exec_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_invalid.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_invalid", "name": "Invalid VDev"},
  "vdev": {
    "actions": [
      {"action_id": "A1", "type": "read", "target": {"kind": "ble_device", "id": "ble:aa:bb"}, "io": {"protocol": "BLE"}, "semantics": {"critical": true}}
    ]
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_ble", "file_path": "{int_a}", "protocols": ["BLE"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        build_optimization_target(vdev_spec, source_spec)


def test_build_target_merges_explicit_and_derived_marker_hints(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_marker_hints", "name": "MarkerHints"},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "read",
        "target": {"kind": "ble_device", "id": "ble:aa:bb"},
        "io": {"protocol": "BLE"},
        "marker_hints": ["BLE_CONNECT"],
        "exec": {"kind": "ha_service_call", "domain": "ble_proxy", "service": "read_gatt"},
        "semantics": {"critical": true}
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_ble", "file_path": "{int_a}", "protocols": ["BLE"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    target = build_optimization_target(vdev_spec, source_spec)
    hints = set(target.vdev_actions[0]["marker_hints"])
    assert "BLE_OP" in hints
    assert "BLE_GATT_OP" in hints
    assert "BLE_CONNECT" in hints


def test_build_target_fails_on_unknown_target_kind(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_bad_kind.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_bad_kind", "name": "BadKind"},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "read",
        "target": {"kind": "cloud_like_guess", "id": "x"},
        "io": {"protocol": "CLOUD"},
        "exec": {"kind": "ha_service_call", "domain": "demo", "service": "call_api"},
        "semantics": {"critical": true}
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_cloud", "file_path": "{int_a}", "protocols": ["CLOUD"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        build_optimization_target(vdev_spec, source_spec)


def test_source_scope_domains_fallback_and_protocol_aggregation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "sensor_demo.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_domains.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_domain_fallback", "name": "DomainFallback"},
  "sources": {"ha_core": {"repo_path": ".", "commit": "HEAD", "domains": [], "platforms": []}},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "call_api",
        "target": {"kind": "cloud_endpoint", "id": "tuya:device.control"},
        "io": {"protocol": "CLOUD"},
        "exec": {"kind": "ha_service_call", "domain": "tuya", "service": "call_api"},
        "semantics": {"critical": true}
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_cloud", "file_path": "{int_a}", "protocols": ["CLOUD"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    target = build_optimization_target(vdev_spec, source_spec)
    assert target.source_scope["domains"] == ["demo_cloud"]
    assert "CLOUD" in target.source_scope["protocols"]
    assert "CLOUD" in target.validation["source_protocols"]
    assert "CLOUD" in target.constraints["source_protocols"]


def test_build_target_fails_on_dependency_with_unknown_action_id(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_bad_dep.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_bad_dep", "name": "BadDep"},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "write",
        "target": {"kind": "ha_entity", "id": "sensor.x", "entity_id": "sensor.x"},
        "io": {"protocol": "HA"},
        "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
        "semantics": {"critical": true}
      }
    ],
    "dependencies": {"hard": [{"before": "A1", "after": "A999"}]}
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_ha", "file_path": "{int_a}", "protocols": ["HA"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        build_optimization_target(vdev_spec, source_spec)


def test_validation_uses_deep_merge(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_validation.json"
    source_spec = tmp_path / "source_spec.json"
    run_spec = tmp_path / "run_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_validation", "name": "ValidationMerge"},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "write",
        "target": {"kind": "ha_entity", "id": "sensor.x", "entity_id": "sensor.x"},
        "io": {"protocol": "HA"},
        "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
        "semantics": {"critical": true}
      }
    ]
  },
  "validation": {
    "observation": {
      "canonicalization_version": "v1",
      "equivalence_whitelist": ["STATE_WRITE"],
      "semantic_ops": ["STATE_WRITE"]
    },
    "differential_tests": {"enabled": true}
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_ha", "file_path": "{int_a}", "protocols": ["HA"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    run_spec.write_text(
        """
{
  "validation": {
    "differential_tests": {"runs_per_scenario": 3}
  },
  "observation": {
    "semantic_ops": ["STATE_WRITE", "ENTRY_SETUP"]
  }
}
""",
        encoding="utf-8",
    )

    target = build_optimization_target(vdev_spec, source_spec, run_spec)
    assert target.validation["observation"]["canonicalization_version"] == "v1"
    assert target.validation["observation"]["equivalence_whitelist"] == ["STATE_WRITE"]
    assert target.validation["observation"]["semantic_ops"] == ["STATE_WRITE", "ENTRY_SETUP"]
    assert target.validation["differential_tests"]["enabled"] is True
    assert target.validation["differential_tests"]["runs_per_scenario"] == 3


def test_source_spec_list_input_is_supported_and_repo_path_can_be_none(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_list_source.json"
    source_spec = tmp_path / "source_spec_list.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_list_source", "name": "ListSource"},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "write",
        "target": {"kind": "ha_entity", "id": "sensor.x", "entity_id": "sensor.x"},
        "io": {"protocol": "HA"},
        "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
        "semantics": {"critical": true}
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
[
  {{"device_id": "dev_a", "integration": "demo_ha", "file_path": "{int_a}", "protocols": ["HA"]}}
]
""",
        encoding="utf-8",
    )

    target = build_optimization_target(vdev_spec, source_spec)
    assert len(target.source_scope["files"]) == 1
    assert target.source_scope["repo_path"] is None


def test_target_kind_field_is_explicit_for_sleep_action(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_sleep.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_sleep", "name": "SleepAction"},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "delay",
        "io": {"protocol": "CLOUD"},
        "exec": {"kind": "sleep", "seconds": 0.2},
        "semantics": {"critical": false}
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_cloud", "file_path": "{int_a}", "protocols": ["CLOUD"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    target = build_optimization_target(vdev_spec, source_spec)
    assert target.vdev_actions[0]["target_kind"] == ""


def test_required_state_writes_only_from_state_contract(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    int_a = repo / "int_a.py"
    int_a.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_only_action_entity.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_no_contract", "name": "NoContractWrite"},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "read",
        "target": {"kind": "ha_entity", "id": "sensor.downstream", "entity_id": "sensor.downstream"},
        "io": {"protocol": "HA"},
        "exec": {"kind": "ha_state_read", "entity_id": "sensor.downstream"},
        "semantics": {"critical": true}
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "dev_a", "integration": "demo_ha", "file_path": "{int_a}", "protocols": ["HA"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    target = build_optimization_target(vdev_spec, source_spec)
    assert "sensor.downstream" in target.target_anchors["entities"]
    assert target.target_anchors["required_state_writes"] == []


def test_build_target_derives_finer_runtime_families(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    integration_file = repo / "integration.py"
    integration_file.write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")

    vdev_spec = tmp_path / "vdev_spec_fine_hints.json"
    source_spec = tmp_path / "source_spec.json"

    vdev_spec.write_text(
        """
{
  "meta": {"spec_version": "0.1", "vdev_id": "vdev_fine_hints", "name": "FineHints"},
  "vdev": {
    "actions": [
      {
        "action_id": "A1",
        "type": "read",
        "target": {"kind": "ble_device", "id": "ble:aa:bb"},
        "io": {"protocol": "BLE"},
        "exec": {"kind": "ha_service_call", "domain": "esphome", "service": "subscribe_notify"},
        "semantics": {"critical": true}
      },
      {
        "action_id": "A2",
        "type": "status",
        "target": {"kind": "cloud_endpoint", "id": "ecobee:thermostat.home_1"},
        "io": {"protocol": "CLOUD"},
        "exec": {"kind": "ha_service_call", "domain": "ecobee", "service": "read_runtime"},
        "semantics": {"critical": true}
      },
      {
        "action_id": "A3",
        "type": "read",
        "target": {"kind": "ha_entity", "id": "light.hue_lr", "entity_id": "light.hue_lr"},
        "io": {"protocol": "LOCAL"},
        "exec": {"kind": "ha_state_read", "entity_id": "light.hue_lr"},
        "semantics": {"critical": false}
      },
      {
        "action_id": "A4",
        "type": "read",
        "target": {"kind": "ha_entity", "id": "sensor.topic", "entity_id": "sensor.topic"},
        "io": {"protocol": "MQTT"},
        "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message"},
        "semantics": {"critical": false}
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    source_spec.write_text(
        f"""
{{
  "repo_path": "{repo}",
  "integrations": [
    {{"device_id": "demo", "integration": "demo", "file_path": "{integration_file}", "protocols": ["BLE", "CLOUD", "LOCAL", "MQTT"]}}
  ]
}}
""",
        encoding="utf-8",
    )

    target = build_optimization_target(vdev_spec, source_spec)
    hints_by_action = {
        action["action_id"]: set(action["marker_hints"])
        for action in target.vdev_actions
    }

    assert {"BLE_NOTIFY_SUBSCRIBE", "SUBSCRIBE"} <= hints_by_action["A1"]
    assert {"CLOUD_STATUS_CALL", "POLL_UPDATE", "CLOUD_HTTP_CALL"} <= hints_by_action["A2"]
    assert "LOCAL_API_READ" in hints_by_action["A3"]
    assert {"MQTT_SUBSCRIBE", "SUBSCRIBE"} <= hints_by_action["A4"]
