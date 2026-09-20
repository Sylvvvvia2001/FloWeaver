from pathlib import Path

from dsl.contracts import (
    DEFAULT_LIFECYCLE_TEMPLATES,
    DEFAULT_MARKER_DETECTORS,
    HAPProfile,
    MarkerStrength,
    OptimizationTarget,
    Phase,
    PROFILE_SCHEMA_VERSION,
    Rule,
    now_utc_iso,
)
from optimizer.m1_markers import detect_markers
from optimizer.pipeline import FloWeaverOptimizer


def test_detect_ha_markers(tmp_path: Path) -> None:
    source = tmp_path / "integration.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    unsub = dispatcher_connect(hass, \"sig\", lambda: None)
    entity.async_write_ha_state()
    return True

async def async_unload_entry(hass, entry):
    data = hass.data[entry.entry_id]
    data[\"unsub\"]()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r1",
                title="t",
                category="lifecycle",
                evidence_ids=["DOC_x"],
            )
        ],
    )

    marker_set = detect_markers(source, profile)
    kinds = {m.marker_type for m in marker_set.markers}
    assert "ENTRY_SETUP" in kinds
    assert "ENTRY_UNLOAD" in kinds
    assert "STATE_WRITE" in kinds
    assert "SUBSCRIBE" in kinds
    assert "UNSUBSCRIBE" in kinds


def test_detect_markers_with_import_and_variable_alias(tmp_path: Path) -> None:
    source = tmp_path / "integration_alias.py"
    source.write_text(
        """
from homeassistant.helpers.dispatcher import dispatcher_connect as dc

async def async_setup_entry(hass, entry):
    state_writer = entity.async_write_ha_state
    unsub = dc(hass, "sig", state_writer)
    state_writer()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="lifecycle", evidence_ids=["DOC_x"])],
    )

    marker_set = detect_markers(source, profile)
    kinds = {m.marker_type for m in marker_set.markers}
    assert "SUBSCRIBE" in kinds
    assert "STATE_WRITE" in kinds
    assert marker_set.diagnostics["match_counts"]["alias"] >= 1


def test_protocol_detector_respects_module_hints(tmp_path: Path) -> None:
    source = tmp_path / "integration_protocol.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    await client.connect()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            *DEFAULT_MARKER_DETECTORS,
            {
                "id": "call:protocol:ble_connect",
                "type": "BLE_CONNECT",
                "match": {"call_attrs": ["connect"], "module_hints": ["bleak"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )

    marker_set = detect_markers(source, profile)
    ble_markers = [marker for marker in marker_set.markers if marker.marker_type == "BLE_CONNECT"]
    assert ble_markers
    assert all(marker.strength == "MEDIUM" for marker in ble_markers)
    assert marker_set.diagnostics["protocol_context_downgraded"] >= 1


def test_protocol_detector_matches_with_module_hints(tmp_path: Path) -> None:
    source = tmp_path / "integration_protocol_import.py"
    source.write_text(
        """
from bleak import BleakClient

async def async_setup_entry(hass, entry):
    await client.connect()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            *DEFAULT_MARKER_DETECTORS,
            {
                "id": "call:protocol:ble_connect",
                "type": "BLE_CONNECT",
                "match": {"call_attrs": ["connect"], "module_hints": ["bleak"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )

    marker_set = detect_markers(source, profile)
    kinds = {m.marker_type for m in marker_set.markers}
    assert "BLE_CONNECT" in kinds


def test_protocol_detector_matches_import_alias_and_symbol_alias(tmp_path: Path) -> None:
    source = tmp_path / "integration_alias_protocol.py"
    source.write_text(
        """
import aiohttp as ah
from aiohttp import ClientSession as CS

async def async_setup_entry(hass, entry):
    s1 = CS()
    await s1.request("GET", "https://api.example.com/device")
    s2 = ah.ClientSession()
    await s2.request("POST", "https://api.example.com/device")
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:cloud:session",
                "type": "CLOUD_SESSION_REUSE",
                "match": {"call_attrs": ["clientsession"], "module_hints": ["aiohttp"]},
                "strength": "WEAK",
                "phase": "RUNTIME",
            },
            {
                "id": "call:cloud:request",
                "type": "CLOUD_HTTP_CALL",
                "match": {"call_attrs": ["request", "session.request"], "module_hints": ["aiohttp"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )

    marker_set = detect_markers(source, profile)
    kinds = {m.marker_type for m in marker_set.markers}
    assert "CLOUD_SESSION_REUSE" in kinds
    assert "CLOUD_HTTP_CALL" in kinds
    assert marker_set.diagnostics["match_counts"]["alias"] >= 1


def test_cloud_runtime_noise_without_context_is_dropped_when_target_present(tmp_path: Path) -> None:
    source = tmp_path / "integration_cloud_noise.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    await client.request("GET", "/local")
    entity.async_write_ha_state()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:cloud:request",
                "type": "CLOUD_HTTP_CALL",
                "match": {"call_attrs": ["request"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
            {
                "id": "call:state_write",
                "type": "STATE_WRITE",
                "match": {"call_attrs": ["async_write_ha_state"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="observable", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "protocol": "HA", "marker_hints": ["STATE_WRITE"], "exec": {"kind": "ha_service_call"}}],
        target_anchors={},
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    assert all(marker.marker_type != "CLOUD_HTTP_CALL" for marker in marker_set.markers)


def test_cloud_runtime_marker_accepts_wrapped_cloud_context(tmp_path: Path) -> None:
    source_dir = tmp_path / "tuya"
    source_dir.mkdir()
    source = source_dir / "light.py"
    source.write_text(
        """
from tuya_sharing import Manager

async def async_turn_on(hass, device_manager, wrapper, device):
    commands = wrapper.get_update_commands(device, True)
    await hass.async_add_executor_job(device_manager.send_commands, device.id, commands)
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "marker_hints": ["CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            }
        ],
        target_anchors={},
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    cloud_markers = [marker for marker in marker_set.markers if marker.marker_type == "CLOUD_OP"]
    assert cloud_markers
    assert cloud_markers[0].primary_action_id == "A1"


def test_shared_infra_marker_requires_strong_binding_reason_for_ownership(tmp_path: Path) -> None:
    source = tmp_path / "integration_shared_infra.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    dispatcher_connect(hass, "sig", lambda: None)
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="lifecycle", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "protocol": "BLE", "marker_hints": ["SUBSCRIBE"], "exec": {"kind": "ha_service_call"}}],
        target_anchors={},
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    subscribe = next(marker for marker in marker_set.markers if marker.marker_type == "SUBSCRIBE")
    assert subscribe.primary_action_id is None


def test_anchor_strengthening_uses_precise_matching(tmp_path: Path) -> None:
    source = tmp_path / "integration_anchor_precision.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    set_state("sensor.vdev_extra", "on")
    call_api("tuya:device.control_extra")
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:state_write",
                "type": "STATE_WRITE",
                "match": {"call_attrs": ["set_state"]},
                "strength": "MEDIUM",
                "phase": "RUNTIME",
            },
            {
                "id": "call:cloud",
                "type": "CLOUD_HTTP_CALL",
                "match": {"call_attrs": ["call_api"]},
                "strength": "MEDIUM",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="observable", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={
            "entities": ["sensor.vdev"],
            "endpoints": ["tuya:device.control"],
            "device_ids": [],
            "characteristics": [],
            "anchor_ops": [],
            "required_state_writes": [],
        },
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    assert marker_set.markers
    assert all(marker.strength != "STRONG" for marker in marker_set.markers)


def test_helper_phase_inference_from_setup_caller(tmp_path: Path) -> None:
    source = tmp_path / "integration_phase_infer.py"
    source.write_text(
        """
from bleak import BleakClient

async def _setup_helper(client):
    await client.connect()

async def async_setup_entry(hass, entry):
    await _setup_helper(client)
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:protocol:ble_connect",
                "type": "BLE_CONNECT",
                "match": {"call_attrs": ["connect"], "module_hints": ["bleak"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )

    marker_set = detect_markers(source, profile)
    helper_markers = [marker for marker in marker_set.markers if marker.function_name == "_setup_helper" and marker.marker_type == "BLE_CONNECT"]
    assert helper_markers
    assert all(marker.phase == "SETUP" for marker in helper_markers)
    assert marker_set.diagnostics["helper_phase_inferred_count"] >= 1


def test_marker_id_keeps_same_line_multi_calls_distinct(tmp_path: Path) -> None:
    source = tmp_path / "integration_same_line.py"
    source.write_text(
        """
from bleak import BleakClient

async def async_setup_entry(hass, entry):
    client.connect(); client.connect()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:protocol:ble_connect",
                "type": "BLE_CONNECT",
                "match": {"call_attrs": ["connect"], "module_hints": ["bleak"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )

    marker_set = detect_markers(source, profile)
    connect_markers = [marker for marker in marker_set.markers if marker.marker_type == "BLE_CONNECT"]
    marker_ids = {marker.marker_id for marker in connect_markers}
    assert len(connect_markers) == 2
    assert len(marker_ids) == 2


def test_marker_related_action_ids_by_target_anchor_match(tmp_path: Path) -> None:
    source = tmp_path / "integration_related_action.py"
    source.write_text(
        """
from bleak import BleakClient

async def async_setup_entry(hass, entry):
    await client.connect("ble:aa:bb:cc")
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:protocol:ble_connect",
                "type": "BLE_CONNECT",
                "match": {"call_attrs": ["connect"], "module_hints": ["bleak"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[
            {
                "action_id": "A1",
                "marker_hints": ["BLE_CONNECT"],
                "target": {"kind": "ble_device", "id": "ble:aa:bb:cc"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "run"},
            },
            {
                "action_id": "A2",
                "marker_hints": ["CLOUD_HTTP_CALL"],
                "target": {"kind": "cloud_endpoint", "id": "tuya:device.control"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "run"},
            },
        ],
        target_anchors={},
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    connect_markers = [marker for marker in marker_set.markers if marker.marker_type == "BLE_CONNECT"]
    assert connect_markers
    assert "A1" in connect_markers[0].related_action_ids


def test_coarse_anchor_ops_do_not_force_strong(tmp_path: Path) -> None:
    source = tmp_path / "integration_coarse_anchor_ops.py"
    source.write_text(
        """
from bleak import BleakClient

async def async_setup_entry(hass, entry):
    await client.connect()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:protocol:ble_connect",
                "type": "BLE_CONNECT",
                "match": {"call_attrs": ["connect"], "module_hints": ["bleak"]},
                "strength": "MEDIUM",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[
            {
                "action_id": "A1",
                "marker_hints": ["BLE_OP"],
                "target": {"kind": "ble_device", "id": "ble:aa:bb:cc"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "run"},
            }
        ],
        target_anchors={"anchor_ops": ["BLE_OP"]},
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    ble_markers = [marker for marker in marker_set.markers if marker.marker_type == "BLE_CONNECT"]
    assert ble_markers
    assert all(marker.strength == "MEDIUM" for marker in ble_markers)
    assert all("target_anchor_seed" not in marker.evidence for marker in ble_markers)


def test_unsubscribe_related_actions_prefers_subscribe_binding(tmp_path: Path) -> None:
    source = tmp_path / "integration_unsub_related.py"
    source.write_text(
        """
from homeassistant.helpers.dispatcher import dispatcher_connect

async def async_setup_entry(hass, entry):
    unsub = dispatcher_connect(hass, "sig:vdev", lambda: None)
    return True

async def async_unload_entry(hass, entry):
    unsub()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="lifecycle", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[
            {
                "action_id": "A_SUB",
                "marker_hints": ["SUBSCRIBE", "UNSUBSCRIBE"],
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "run", "data_template": {"sig": "sig:vdev"}},
            }
        ],
        target_anchors={},
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    unsubscribe_markers = [marker for marker in marker_set.markers if marker.marker_type == "UNSUBSCRIBE"]
    assert unsubscribe_markers
    assert any("A_SUB" in marker.related_action_ids for marker in unsubscribe_markers)


def test_marker_related_action_ids_use_file_binding_and_service_tokens(tmp_path: Path) -> None:
    source_dir = tmp_path / "switchbot"
    source_dir.mkdir()
    source = source_dir / "coordinator.py"
    source.write_text(
        """
async def async_update_data(self):
    await manager.refresh()
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:protocol:ble_gatt_op",
                "type": "BLE_GATT_OP",
                "match": {"call_attrs": ["refresh"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "ble:switchbot:demo",
                    "integration": "switchbot",
                    "file_path": str(source),
                    "protocols": ["BLE", "HA"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "marker_hints": ["BLE_GATT_OP"],
                "target": {"kind": "ble_device", "id": "ble:switchbot:demo"},
                "exec": {"kind": "ha_service_call", "domain": "switchbot", "service": "refresh"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    ble_markers = [marker for marker in marker_set.markers if marker.marker_type == "BLE_GATT_OP"]
    assert ble_markers
    assert ble_markers[0].related_action_ids == ["A1"]
    assert any("action_match:file_binding_match" in item for item in ble_markers[0].evidence)


def test_ble_bound_device_calls_emit_ble_op_and_skip_disconnect_alias(tmp_path: Path) -> None:
    source_dir = tmp_path / "switchbot"
    source_dir.mkdir()
    source = source_dir / "cover.py"
    source.write_text(
        """
async def async_close_cover(self):
    await self._device.close()
    self.async_write_ha_state()
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            *DEFAULT_MARKER_DETECTORS,
            {
                "id": "call:ble_disconnect",
                "type": "BLE_DISCONNECT",
                "match": {"call_attrs": ["disconnect", "close"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
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
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "target": {"kind": "ble_device", "id": "ble:switchbot:curtain_lr"},
                "exec": {"kind": "ha_service_call", "domain": "switchbot", "service": "refresh_cover"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    ble_ops = [marker for marker in marker_set.markers if marker.marker_type == "BLE_OP"]
    ble_disconnects = [marker for marker in marker_set.markers if marker.marker_type == "BLE_DISCONNECT"]

    assert ble_ops
    assert ble_ops[0].primary_action_id == "A1"
    assert "heuristic:ble_device_runtime_call" in ble_ops[0].evidence
    assert not ble_disconnects


def test_unbound_protocol_marker_does_not_bind_by_protocol_only(tmp_path: Path) -> None:
    bound_dir = tmp_path / "tuya"
    bound_dir.mkdir()
    bound_source = bound_dir / "light.py"
    bound_source.write_text(
        """
async def async_status(self):
    await client.request("GET", "/status")
""",
        encoding="utf-8",
    )
    unrelated_dir = tmp_path / "switchbot"
    unrelated_dir.mkdir()
    unrelated_source = unrelated_dir / "cover.py"
    unrelated_source.write_text(
        """
async def async_cover(self):
    await client.request("GET", "/other")
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
            marker_detectors=[
                {
                    "id": "call:cloud_http_call",
                    "type": "CLOUD_HTTP_CALL",
                    "match": {"call_attrs": ["request"]},
                    "strength": "STRONG",
                    "phase": "RUNTIME",
                },
            ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(bound_source), str(unrelated_source)],
            "file_bindings": [
                {
                    "device_id": "tuya:light.living_room.status",
                    "integration": "tuya",
                    "file_path": str(bound_source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "marker_hints": ["CLOUD_HTTP_CALL", "CLOUD_OP"],
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.living_room.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A4"],
    )

    marker_set = detect_markers(unrelated_source, profile, optimization_target=target)
    cloud_markers = [marker for marker in marker_set.markers if marker.marker_type == "CLOUD_HTTP_CALL"]
    assert cloud_markers == []


def test_teardown_ble_connect_is_phase_mismatch_and_not_high_quality_runtime_binding(tmp_path: Path) -> None:
    source = tmp_path / "integration_teardown_ble.py"
    source.write_text(
        """
from bleak import BleakClient

async def async_unload_entry(hass, entry):
    await client.connect("ble:demo")
    return True
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {
                "id": "call:protocol:ble_connect",
                "type": "BLE_CONNECT",
                "match": {"call_attrs": ["connect"], "module_hints": ["bleak"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "ble:demo",
                    "integration": source.parent.name,
                    "file_path": str(source),
                    "protocols": ["BLE"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A2",
                "protocol": "BLE",
                "marker_hints": ["BLE_CONNECT"],
                "target": {"kind": "ble_device", "id": "ble:demo"},
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "turn_on"},
            }
        ],
        target_anchors={},
        critical_action_ids=["A2"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    connect = next(marker for marker in marker_set.markers if marker.marker_type == "BLE_CONNECT")

    assert connect.phase == Phase.TEARDOWN.value
    assert connect.strength == MarkerStrength.MEDIUM.value
    assert "phase_mismatch:teardown_connect" in connect.evidence

    summary = FloWeaverOptimizer._marker_grounding_summary(marker_set, target)
    assert summary["resolved_action_ids"] == ["A2"]
    assert summary["resolved_runtime_action_ids_raw"] == []
    assert summary["resolved_runtime_action_ids"] == []
    assert summary["resolved_runtime_action_count"] == 0


def test_grounding_profile_drives_deterministic_marker_detection(tmp_path: Path) -> None:
    source_dir = tmp_path / "ecobee"
    source_dir.mkdir()
    source = source_dir / "climate.py"
    source.write_text(
        """
async def async_update(self):
    return await self.client.get_thermostat()
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "ecobee_grounding.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v1",
  "integration": "ecobee",
  "version": "v1",
  "runtime_families": [
    {
      "rule_id": "ecobee:status_call",
      "family": "CLOUD_STATUS_CALL",
      "file_globs": ["ecobee/climate.py"],
      "call_patterns": ["get_thermostat"],
      "function_name_patterns": ["async_update"],
      "required_context": ["runtime_update_path"],
      "forbidden_context": ["dunder_init", "entity_property_getter"],
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.7,
        "emit_threshold": 0.7,
        "boost_if_names": ["update", "status"]
      }
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
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
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    cloud_status_markers = [marker for marker in marker_set.markers if marker.marker_type == "CLOUD_STATUS_CALL"]
    assert cloud_status_markers
    assert any(marker.primary_action_id == "A1" for marker in cloud_status_markers)
    assert any(
        any(item.startswith("grounding_profile_rule:ecobee:status_call") for item in marker.evidence)
        for marker in cloud_status_markers
    )
    assert marker_set.diagnostics["grounding_profile_rule_count"] == 1
    assert marker_set.diagnostics["grounding_profile_match_count"] == 1
    assert str(grounding_profile) in marker_set.diagnostics["grounding_profile_loaded_paths"]


def test_grounding_profile_v2_respects_negative_patterns_and_binding_hints(tmp_path: Path) -> None:
    source_dir = tmp_path / "ecobee"
    source_dir.mkdir()
    source = source_dir / "climate.py"
    source.write_text(
        """
class DemoClimate:
    async def __init__(self):
        return await self.client.get_thermostat()

    async def async_update(self):
        return await self.client.get_thermostat()
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "ecobee_grounding_v2.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v2",
  "integration": "ecobee",
  "version": "draft_llm",
  "runtime_families": [
    {
      "rule_id": "ecobee:status_call:v2",
      "family": "CLOUD_STATUS_CALL",
      "file_globs": ["ecobee/climate.py"],
      "call_patterns": ["get_thermostat"],
      "function_name_patterns": ["async_update", "__init__"],
      "negative_function_patterns": ["__init__"],
      "required_context": ["runtime_update_path"],
      "forbidden_context": ["dunder_init", "entity_property_getter"],
      "binding_hints": {
        "preferred_action_kinds": ["status"],
        "boost_target_tokens": ["read_runtime", "runtime"],
        "phase": "RUNTIME"
      },
      "runtime_path_evidence": ["runtime_function:async_update", "runtime_call:get_thermostat"],
      "negative_evidence": ["negative_function:__init__"],
      "why_not_setup": ["exclude_setup_function:__init__"],
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.7,
        "emit_threshold": 0.7,
        "boost_if_names": ["update", "status"]
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
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
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "ecobee:thermostat.home_1"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "ecobee", "service": "read_runtime"},
            }
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    cloud_status_markers = [marker for marker in marker_set.markers if marker.marker_type == "CLOUD_STATUS_CALL"]
    assert len(cloud_status_markers) == 1
    marker = cloud_status_markers[0]
    assert marker.primary_action_id == "A1"
    assert marker.function_name == "async_update"
    assert "action_match:binding_hint_action_kind" in marker.evidence
    assert "action_match:binding_hint_target_token" in marker.evidence
    assert "grounding_profile:runtime_path:runtime_function:async_update" in marker.evidence


def test_grounding_profile_binding_hint_target_tokens_use_exact_matching(tmp_path: Path) -> None:
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
    grounding_profile = tmp_path / "tuya_grounding_v2.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v2",
  "integration": "tuya",
  "version": "draft_llm",
  "runtime_families": [
    {
      "rule_id": "tuya:status_call:v2",
      "family": "CLOUD_STATUS_CALL",
      "file_globs": ["tuya/switch.py"],
      "call_patterns": ["skip_update", "self._dpcode_wrapper.skip_update"],
      "function_name_patterns": ["_process_device_update"],
      "required_context": ["runtime_update_path"],
      "forbidden_context": ["dunder_init", "entity_property_getter", "setup_function"],
      "binding_hints": {
        "preferred_action_kinds": ["status"],
        "boost_target_tokens": ["energy_strip_2", "tuya:switch.energy_strip_2.status"],
        "phase": "RUNTIME"
      },
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.7,
        "emit_threshold": 0.7
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "tuya:switch.energy_strip_1.status",
                    "integration": "tuya",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                },
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
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:switch.energy_strip_1.status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "provider": "tuya"},
            },
            {
                "action_id": "A2",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:switch.energy_strip_2.status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "provider": "tuya"},
            }
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1", "A2"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    cloud_status_markers = [marker for marker in marker_set.markers if marker.marker_type == "CLOUD_STATUS_CALL"]
    assert len(cloud_status_markers) == 1
    marker = cloud_status_markers[0]
    assert marker.primary_action_id == "A2"
    assert "related_actions:A2" in marker.evidence


def test_grounding_profile_v3_suppresses_local_baseline_control_noise(tmp_path: Path) -> None:
    source_dir = tmp_path / "tuya"
    source_dir.mkdir()
    source = source_dir / "light.py"
    source.write_text(
        """
from tuya_sharing import Manager

class DemoLight:
    async def async_update(self):
        return await self.client.get_status()

    async def async_turn_on(self):
        return await self._async_send_commands()
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "tuya_grounding_v3.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "tuya",
  "version": "draft_llm_v3",
  "runtime_families": [
    {
      "rule_id": "tuya:light_runtime_status_read",
      "family": "CLOUD_STATUS_CALL",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A1"],
      "origin_cluster_id": "tuya__light__cloud_status_call__status__cloud",
      "file_globs": ["tuya/light.py"],
      "call_patterns": ["get_status", "self.client.get_status"],
      "function_name_patterns": ["async_update"],
      "negative_function_patterns": ["async_turn_on"],
      "negative_call_patterns": ["_async_send_commands", "async_turn_on", "async_set_*"],
      "required_context": ["runtime_update_path"],
      "forbidden_context": ["dunder_init", "entity_property_getter", "setup_function"],
      "required_path_signals": ["read_function:async_update"],
      "forbidden_path_signals": ["control_function:async_turn_on"],
      "required_runtime_roles": ["runtime_read"],
      "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
      "binding_hints": {
        "preferred_action_kinds": ["status"],
        "boost_target_tokens": ["demo", "tuya:light.demo.status"],
        "phase": "RUNTIME"
      },
      "runtime_path_evidence": ["runtime_function:async_update", "runtime_call:get_status"],
      "negative_evidence": ["negative_function:async_turn_on"],
      "why_not_setup": ["exclude_role:runtime_write:async_turn_on"],
      "why_not_more_general": "single file provides the reusable runtime status idiom",
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.7,
        "emit_threshold": 0.7,
        "boost_if_names": ["update", "status"]
      },
      "source_file_paths": ["tuya/light.py"],
      "source_unresolved_action_ids": ["A1"],
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
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
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.demo.status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "provider": "tuya"},
            }
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    assert any(
        marker.marker_type == "CLOUD_STATUS_CALL" and marker.function_name == "async_update"
        for marker in marker_set.markers
    )
    assert not any(
        marker.marker_type == "CLOUD_OP" and marker.function_name == "async_turn_on"
        for marker in marker_set.markers
    )
    assert marker_set.diagnostics["grounding_profile_suppressed_baseline_count"] >= 1


def test_grounding_profile_v3_allows_generalized_secondary_binding(tmp_path: Path) -> None:
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
    grounding_profile = tmp_path / "tuya_grounding_v3_generalized.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "tuya",
  "version": "draft_llm_v3",
  "runtime_families": [
    {
      "rule_id": "tuya:switch_runtime_status_read",
      "family": "CLOUD_STATUS_CALL",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A1", "A2"],
      "origin_cluster_id": "tuya__switch__cloud_status_call__status__cloud",
      "file_globs": ["tuya/switch.py"],
      "call_patterns": ["skip_update", "self._dpcode_wrapper.skip_update"],
      "function_name_patterns": ["_process_device_update"],
      "required_context": ["runtime_update_path"],
      "forbidden_context": ["dunder_init", "entity_property_getter", "setup_function"],
      "binding_hints": {
        "preferred_action_kinds": ["status"],
        "boost_target_tokens": [
          "energy_strip_1",
          "tuya:switch.energy_strip_1.status",
          "energy_strip_2",
          "tuya:switch.energy_strip_2.status"
        ],
        "phase": "RUNTIME"
      },
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.7,
        "emit_threshold": 0.7
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "tuya:switch.energy_strip_1.status",
                    "integration": "tuya",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                },
                {
                    "device_id": "tuya:switch.energy_strip_2.status",
                    "integration": "tuya",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                },
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:switch.energy_strip_1.status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "provider": "tuya"},
            },
            {
                "action_id": "A2",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "tuya:switch.energy_strip_2.status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "provider": "tuya"},
            },
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1", "A2"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    cloud_status_markers = [marker for marker in marker_set.markers if marker.marker_type == "CLOUD_STATUS_CALL"]
    assert len(cloud_status_markers) == 1
    marker = cloud_status_markers[0]
    assert {marker.primary_action_id, *marker.secondary_action_ids} == {"A1", "A2"}
    assert "action_match:generalized_profile_secondary_binding" in marker.evidence


def test_grounding_profile_v3_merges_duplicate_profile_markers_with_distinct_action_sets(tmp_path: Path) -> None:
    source_dir = tmp_path / "xiaomi_ble"
    source_dir.mkdir()
    source = source_dir / "__init__.py"
    source.write_text(
        """
def process_service_info(service_info):
    return data.update(service_info)
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "xiaomi_ble_grounding_v3_duplicate_actions.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "xiaomi_ble",
  "version": "draft_llm_v3",
  "runtime_families": [
    {
      "rule_id": "xiaomi_ble:sensor_read",
      "family": "BLE_OP",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A1", "A2"],
      "file_globs": ["xiaomi_ble/__init__.py"],
      "call_patterns": ["update", "data.update"],
      "function_name_patterns": ["process_service_info"],
      "required_context": ["runtime_path"],
      "required_runtime_roles": ["runtime_read"],
      "binding_hints": {"preferred_action_kinds": ["read_sensor"], "phase": "RUNTIME"},
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {"base": 0.7, "emit_threshold": 0.7},
      "reviewer_status": "draft"
    },
    {
      "rule_id": "xiaomi_ble:status_read",
      "family": "BLE_OP",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A3", "A4"],
      "file_globs": ["xiaomi_ble/__init__.py"],
      "call_patterns": ["update", "data.update"],
      "function_name_patterns": ["process_service_info"],
      "required_context": ["runtime_path"],
      "required_runtime_roles": ["runtime_read"],
      "binding_hints": {"preferred_action_kinds": ["read_status"], "phase": "RUNTIME"},
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {"base": 0.7, "emit_threshold": 0.7},
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {"device_id": "ble:demo.sensor_1", "integration": "xiaomi_ble", "file_path": str(source), "protocols": ["BLE"]},
                {"device_id": "ble:demo.sensor_2", "integration": "xiaomi_ble", "file_path": str(source), "protocols": ["BLE"]},
                {"device_id": "ble:demo.status_1", "integration": "xiaomi_ble", "file_path": str(source), "protocols": ["BLE"]},
                {"device_id": "ble:demo.status_2", "integration": "xiaomi_ble", "file_path": str(source), "protocols": ["BLE"]},
            ],
        },
        vdev_actions=[
            {"action_id": "A1", "type": "read_sensor", "protocol": "BLE", "target": {"kind": "ble_device", "id": "ble:demo.sensor_1"}, "marker_hints": ["BLE_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A2", "type": "read_sensor", "protocol": "BLE", "target": {"kind": "ble_device", "id": "ble:demo.sensor_2"}, "marker_hints": ["BLE_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A3", "type": "read_status", "protocol": "BLE", "target": {"kind": "ble_device", "id": "ble:demo.status_1"}, "marker_hints": ["BLE_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A4", "type": "read_status", "protocol": "BLE", "target": {"kind": "ble_device", "id": "ble:demo.status_2"}, "marker_hints": ["BLE_OP"], "exec": {"kind": "ha_service_call"}},
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1", "A2", "A3", "A4"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    ble_markers = [marker for marker in marker_set.markers if marker.marker_type == "BLE_OP"]
    assert len(ble_markers) == 1
    assert set(ble_markers[0].related_action_ids) == {"A1", "A2", "A3", "A4"}


def test_grounding_profile_v3_uses_required_path_signals_for_setup_only_helper_reads(tmp_path: Path) -> None:
    source_dir = tmp_path / "demo"
    source_dir.mkdir()
    source = source_dir / "status.py"
    source.write_text(
        """
class DemoStatus:
    async def async_setup_entry(self):
        return self._build_snapshot()

    def _build_snapshot(self):
        return self.device.read_device_status()
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "demo_grounding_v3_helper.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "demo",
  "version": "draft_llm_v3",
  "runtime_families": [
    {
      "rule_id": "demo:file_runtime_status_read",
      "family": "CLOUD_STATUS_CALL",
      "action_kind": "status",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A1", "A2"],
      "origin_cluster_id": "demo__status__cloud_status_call__status__cloud",
      "file_globs": ["demo/status.py"],
      "call_patterns": ["read_device_status", "self.device.read_device_status"],
      "function_name_patterns": ["_build_snapshot"],
      "required_context": ["runtime_update_path"],
      "forbidden_context": ["dunder_init", "entity_property_getter", "setup_function"],
      "required_path_signals": [
        "read_function:_build_snapshot",
        "read_call:self.device.read_device_status",
        "state_accessor_call:self.device.read_device_status"
      ],
      "required_runtime_roles": ["runtime_read"],
      "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
      "binding_hints": {
        "preferred_action_kinds": ["status"],
        "boost_target_tokens": [
          "room_a",
          "demo:climate.room_a.status",
          "room_b",
          "demo:climate.room_b.status"
        ],
        "phase": "RUNTIME"
      },
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.7,
        "emit_threshold": 0.7,
        "boost_if_names": ["status", "read"]
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "demo:climate.room_a.status",
                    "integration": "demo",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                },
                {
                    "device_id": "demo:climate.room_b.status",
                    "integration": "demo",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                },
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "demo:climate.room_a.status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status", "provider": "demo"},
            },
            {
                "action_id": "A2",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "demo:climate.room_b.status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status", "provider": "demo"},
            },
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1", "A2"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    cloud_status_markers = [
        marker for marker in marker_set.markers
        if marker.marker_type == "CLOUD_STATUS_CALL" and marker.function_name == "_build_snapshot"
    ]
    assert len(cloud_status_markers) == 1
    marker = cloud_status_markers[0]
    assert {marker.primary_action_id, *marker.secondary_action_ids} == {"A1", "A2"}
    assert any(item.startswith("grounding_profile_rule:demo:file_runtime_status_read") for item in marker.evidence)


def test_grounding_profile_v3_local_accessor_fallback_matches_property_getter(tmp_path: Path) -> None:
    source_dir = tmp_path / "hue" / "v2"
    source_dir.mkdir(parents=True)
    source = source_dir / "light.py"
    source.write_text(
        """
class DemoHueLight:
    @property
    def is_on(self):
        return self.resource.on.on
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "hue_local_accessor.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "hue",
  "version": "draft_llm_v3",
  "runtime_families": [
    {
      "rule_id": "hue:light_local_accessor_read",
      "family": "LOCAL_API_READ",
      "action_kind": "get_state",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A1"],
      "origin_cluster_id": "hue__light__local_api_read__get_state__local",
      "file_globs": ["hue/v2/light.py"],
      "function_name_patterns": ["is_on"],
      "call_patterns": [],
      "required_context": ["runtime_path"],
      "forbidden_context": ["dunder_init", "entity_property_getter"],
      "required_path_signals": ["property_function:is_on"],
      "forbidden_path_signals": ["control_function:async_turn_on"],
      "required_runtime_roles": ["runtime_read"],
      "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
      "allow_accessor_fallback": true,
      "binding_hints": {
        "preferred_action_kinds": ["get_state"],
        "boost_target_tokens": ["hue:bridge_1:bedroom_ceiling_group"],
        "phase": "RUNTIME"
      },
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.75,
        "emit_threshold": 0.7
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
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
                "type": "get_state",
                "protocol": "LOCAL",
                "target_kind": "local_endpoint",
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:bedroom_ceiling_group"},
                "marker_hints": ["LOCAL_API_READ"],
                "exec": {"kind": "ha_service_call", "domain": "hue", "service": "get_state"},
            }
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    local_markers = [marker for marker in marker_set.markers if marker.marker_type == "LOCAL_API_READ"]
    assert len(local_markers) == 1
    assert local_markers[0].primary_action_id == "A1"
    assert local_markers[0].function_name == "is_on"


def test_grounding_profile_v3_state_write_matches_coordinator_update_carrier(tmp_path: Path) -> None:
    source_dir = tmp_path / "tplink"
    source_dir.mkdir()
    source = source_dir / "entity.py"
    source.write_text(
        """
class DemoEntity:
    def _handle_coordinator_update(self):
        self._async_call_update_attrs()
        self.async_write_ha_state()
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "tplink_state_write.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "tplink",
  "version": "draft_llm_v3",
  "runtime_families": [
    {
      "rule_id": "tplink:entity_runtime_writeback",
      "family": "STATE_WRITE",
      "action_kind": "write",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A1"],
      "origin_cluster_id": "tplink__entity__state_write__write__ha",
      "file_globs": ["tplink/entity.py"],
      "function_name_patterns": ["_handle_coordinator_update"],
      "call_patterns": ["async_write_ha_state"],
      "required_context": ["runtime_path"],
      "forbidden_context": ["dunder_init"],
      "required_path_signals": ["state_write_function:_handle_coordinator_update", "state_write_call:async_write_ha_state"],
      "forbidden_path_signals": ["setup_function:async_setup_entry"],
      "required_runtime_roles": ["runtime_write"],
      "forbidden_runtime_roles": ["setup", "property_getter"],
      "binding_hints": {
        "preferred_action_kinds": ["write"],
        "boost_target_tokens": ["sensor.vdev_demo_lane"],
        "phase": "RUNTIME"
      },
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.75,
        "emit_threshold": 0.7
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
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
                "type": "write",
                "protocol": "HA",
                "target_kind": "ha_entity",
                "target": {"kind": "ha_entity", "id": "sensor.vdev_demo_lane", "entity_id": "sensor.vdev_demo_lane"},
                "marker_hints": ["STATE_WRITE"],
                "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
            }
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    state_write_markers = [marker for marker in marker_set.markers if marker.marker_type == "STATE_WRITE"]
    assert len(state_write_markers) == 1
    assert state_write_markers[0].primary_action_id == "A1"
    assert state_write_markers[0].function_name == "_handle_coordinator_update"


def test_grounding_profile_v3_control_rule_requires_service_token_alignment(tmp_path: Path) -> None:
    source_dir = tmp_path / "ecobee"
    source_dir.mkdir()
    source = source_dir / "climate.py"
    source.write_text(
        """
class DemoClimate:
    async def create_vacation_service(self):
        return await self.client.create_vacation()

    async def set_temperature(self):
        return await self.client.set_temperature()

    async def delete_vacation_service(self):
        return await self.client.delete_vacation()
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "ecobee_control_alignment.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "ecobee",
  "version": "draft_llm",
  "runtime_families": [
    {
      "rule_id": "ecobee:file_runtime_write_set_temperature",
      "family": "CLOUD_OP",
      "action_kind": "set_temperature",
      "generalization_scope": "file_specific",
      "file_globs": ["ecobee/climate.py"],
      "function_name_patterns": ["*service*", "set_temperature"],
      "required_context": ["runtime_path"],
      "required_path_signals": ["control_function:set_temperature", "control_call:set_temperature"],
      "required_runtime_roles": ["runtime_write"],
      "binding_hints": {
        "preferred_action_kinds": ["control", "set_temperature"],
        "required_service_tokens": ["set_temperature"],
        "phase": "RUNTIME"
      },
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.7,
        "emit_threshold": 0.7
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "ecobee:thermostat.office.set_temperature",
                    "integration": "ecobee",
                    "file_path": str(source),
                    "protocols": ["CLOUD"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "set_temperature",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"kind": "cloud_endpoint", "id": "ecobee:thermostat.office.set_temperature"},
                "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"],
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "set_temperature"},
            }
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    cloud_op_markers = [marker for marker in marker_set.markers if marker.marker_type == "CLOUD_OP"]
    assert len(cloud_op_markers) == 1
    assert cloud_op_markers[0].function_name == "set_temperature"
    assert cloud_op_markers[0].primary_action_id == "A1"


def test_grounding_profile_v3_refresh_like_ble_rule_matches_update_callback_carrier(tmp_path: Path) -> None:
    source_dir = tmp_path / "switchbot"
    source_dir.mkdir()
    source = source_dir / "cover.py"
    source.write_text(
        """
class DemoCover:
    def _handle_coordinator_update(self):
        self._attr_is_opening = self._device.is_opening()
        self.async_write_ha_state()
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "switchbot_refresh.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "switchbot",
  "version": "draft_llm_v3",
  "runtime_families": [
    {
      "rule_id": "switchbot:cover_ble_op",
      "family": "BLE_OP",
      "action_kind": "refresh_cover",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A1"],
      "origin_cluster_id": "switchbot__cover__ble_op__refresh_cover__ble",
      "file_globs": ["switchbot/cover.py"],
      "function_name_patterns": ["_handle_coordinator_update"],
      "call_patterns": [],
      "required_context": ["runtime_path"],
      "forbidden_context": ["dunder_init"],
      "required_path_signals": ["update_callback_function:_handle_coordinator_update"],
      "forbidden_path_signals": ["control_function:async_open_cover"],
      "required_runtime_roles": ["runtime_read"],
      "forbidden_runtime_roles": ["runtime_write", "setup", "property_getter", "helper"],
      "binding_hints": {
        "preferred_action_kinds": ["refresh_cover"],
        "boost_target_tokens": ["ble:switchbot:curtain_lr"],
        "phase": "RUNTIME"
      },
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.75,
        "emit_threshold": 0.7
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
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
                "type": "refresh_cover",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"kind": "ble_device", "id": "ble:switchbot:curtain_lr"},
                "marker_hints": ["BLE_OP"],
                "exec": {"kind": "ha_service_call", "domain": "switchbot", "service": "refresh_cover"},
            }
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    ble_markers = [marker for marker in marker_set.markers if marker.marker_type == "BLE_OP"]
    assert len(ble_markers) == 1
    assert ble_markers[0].primary_action_id == "A1"
    assert ble_markers[0].function_name == "_handle_coordinator_update"


def test_grounding_profile_v3_hybrid_runtime_subscription_context_matches_subscription_carrier(tmp_path: Path) -> None:
    source_dir = tmp_path / "mqtt"
    source_dir.mkdir()
    source = source_dir / "sensor.py"
    source.write_text(
        """
class DemoMqttSensor:
    def _state_message_received(self, msg):
        self._update_state(msg)

    def _update_state(self, msg):
        self._last_message = msg
""",
        encoding="utf-8",
    )
    grounding_profile = tmp_path / "mqtt_subscribe.json"
    grounding_profile.write_text(
        """
{
  "schema_version": "m1_grounding_profile/v3",
  "integration": "mqtt",
  "version": "draft_llm_v3",
  "runtime_families": [
    {
      "rule_id": "mqtt:sensor_runtime_subscribe",
      "family": "SUBSCRIBE",
      "action_kind": "read_last_message",
      "generalization_scope": "file_specific",
      "generalizes_actions": ["A1"],
      "origin_cluster_id": "mqtt__sensor__subscribe__read_last_message__local",
      "file_globs": ["mqtt/sensor.py"],
      "function_name_patterns": ["_state_message_received"],
      "call_patterns": [],
      "required_context": ["runtime_path", "subscription_path"],
      "forbidden_context": ["dunder_init"],
      "required_path_signals": ["subscription_function:_state_message_received"],
      "required_runtime_roles": ["runtime_read", "runtime_subscribe"],
      "forbidden_runtime_roles": ["runtime_write", "setup"],
      "binding_hints": {
        "preferred_action_kinds": ["read_last_message"],
        "boost_target_tokens": ["mqtt:air_quality_node_living_room"],
        "phase": "RUNTIME"
      },
      "phase": "RUNTIME",
      "strength": "MEDIUM",
      "confidence": {
        "base": 0.75,
        "emit_threshold": 0.7
      },
      "reviewer_status": "draft"
    }
  ]
}
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )
    target = OptimizationTarget(
        source_scope={
            "files": [str(source)],
            "file_bindings": [
                {
                    "device_id": "mqtt:air_quality_node_living_room",
                    "integration": "mqtt",
                    "file_path": str(source),
                    "protocols": ["LOCAL"],
                }
            ],
        },
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "read_last_message",
                "protocol": "LOCAL",
                "target_kind": "local_endpoint",
                "target": {"kind": "local_endpoint", "id": "mqtt:air_quality_node_living_room"},
                "marker_hints": ["SUBSCRIBE"],
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message"},
            }
        ],
        target_anchors={},
        validation={"grounding_profile_paths": [str(grounding_profile)]},
        critical_action_ids=["A1"],
    )

    marker_set = detect_markers(source, profile, optimization_target=target)
    subscribe_markers = [marker for marker in marker_set.markers if marker.marker_type == "SUBSCRIBE"]
    assert len(subscribe_markers) == 1
    assert subscribe_markers[0].primary_action_id == "A1"
    assert subscribe_markers[0].function_name == "_state_message_received"
