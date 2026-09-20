from pathlib import Path

from dsl.contracts import (
    DEFAULT_LIFECYCLE_TEMPLATES,
    DEFAULT_MARKER_DETECTORS,
    GraphEdge,
    GraphNode,
    HAPProfile,
    Marker,
    OptimizationTarget,
    PROFILE_SCHEMA_VERSION,
    ReducedGraph,
    Rule,
    now_utc_iso,
)
from optimizer.m1_markers import detect_markers
from optimizer.m2_reduction import TempoSpatialReducer


def _profile() -> HAPProfile:
    return HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="lifecycle", evidence_ids=["DOC_x"])],
    )


def test_reducer_keeps_nested_blocks_and_scoped_lifecycle_pairing(tmp_path: Path) -> None:
    source = tmp_path / "integration.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    unsub_a = dispatcher_connect(hass, "sig_a", lambda: None)
    if True:
        unsub_b = dispatcher_connect(hass, "sig_b", lambda: None)
        entity.async_write_ha_state()
    return True

async def async_unload_entry(hass, entry):
    unsub_b()
    unsub_a()
    return True
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    reducer = TempoSpatialReducer(profile)
    result = reducer.reduce(source, marker_set.markers)

    node_ids = list(result.reduced_graph.nodes)
    assert any("." in node_id.split(":")[2] for node_id in node_ids)

    lifecycle_edges = [edge for edge in result.reduced_graph.edges if edge.edge_type == "LIFECYCLE_DEP"]
    assert lifecycle_edges
    assert len(lifecycle_edges) <= 3


def test_reducer_keeps_lifecycle_markers_even_when_target_seed_is_narrow(tmp_path: Path) -> None:
    source = tmp_path / "integration_lifecycle_required.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    unsub = dispatcher_connect(hass, "sig_x", lambda: None)
    return True

async def update_runtime(entity):
    entity.async_write_ha_state()
    return True

async def async_unload_entry(hass, entry):
    unsub()
    return True
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"anchor_ops": ["STATE_WRITE"]},
    )
    reducer = TempoSpatialReducer(profile)
    result = reducer.reduce(source, marker_set.markers, optimization_target=target)

    unsub_markers = [marker for marker in marker_set.markers if marker.marker_type == "UNSUBSCRIBE"]
    assert unsub_markers
    assert any(result.marker_to_nodes.get(marker.marker_id) for marker in unsub_markers)
    assert any(node.function_name == "async_unload_entry" for node in result.reduced_graph.nodes.values())


def test_reducer_expands_try_subtree_for_marker_inside_try(tmp_path: Path) -> None:
    source = tmp_path / "integration_try_finally.py"
    source.write_text(
        """
async def update_runtime(entity):
    try:
        entity.async_write_ha_state()
    finally:
        cleanup()
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    reducer = TempoSpatialReducer(profile)
    result = reducer.reduce(source, marker_set.markers)
    raw_nodes = [node.raw_repr.lower() for node in result.reduced_graph.nodes.values()]
    assert any("cleanup" in text for text in raw_nodes)


def test_reducer_anchor_keep_uses_precise_tokens(tmp_path: Path) -> None:
    source = tmp_path / "integration_anchor_precision.py"
    source.write_text(
        """
async def update_runtime():
    call_api("tuya:device.control_extra")
    call_api("tuya:device.control")
    set_state("sensor.vdev_extra")
    set_state("sensor.vdev")
""",
        encoding="utf-8",
    )

    profile = _profile()
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={
            "entities": ["sensor.vdev"],
            "endpoints": ["tuya:device.control"],
            "anchor_ops": [],
        },
    )
    reducer = TempoSpatialReducer(profile)
    result = reducer.reduce(source, [], optimization_target=target)
    raw_nodes = [node.raw_repr.lower() for node in result.reduced_graph.nodes.values()]
    assert any("tuya:device.control" in text for text in raw_nodes)
    assert any("sensor.vdev" in text for text in raw_nodes)
    assert all("tuya:device.control_extra" not in text for text in raw_nodes)
    assert all("sensor.vdev_extra" not in text for text in raw_nodes)


def test_reducer_cfg_back_depth_limits_spatial_bloat(tmp_path: Path) -> None:
    source = tmp_path / "integration_cfg_depth.py"
    source.write_text(
        """
async def update_runtime(entity):
    x = 1
    y = 2
    entity.async_write_ha_state()
    return x + y
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    reducer = TempoSpatialReducer(profile, spatial_depth=2, cfg_back_depth=0)
    result = reducer.reduce(source, marker_set.markers)
    raw_nodes = [node.raw_repr.lower() for node in result.reduced_graph.nodes.values()]
    assert any("async_write_ha_state" in text for text in raw_nodes)
    assert all("name('x', store())" not in text for text in raw_nodes)
    assert all("name('y', store())" not in text for text in raw_nodes)


def test_lifecycle_markers_do_not_expand_temporal_windows(tmp_path: Path) -> None:
    source = tmp_path / "integration_lifecycle_window.py"
    source.write_text(
        """
async def update_runtime(entity, hass):
    unsub = dispatcher_connect(hass, "sig_x", lambda: None)
    noise_before = do_noise("before")
    entity.async_write_ha_state()
    noise_after = do_noise("after")
    unsub()
    return noise_before, noise_after
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"anchor_ops": ["STATE_WRITE"]},
    )
    reducer = TempoSpatialReducer(profile, spatial_depth=0, cfg_back_depth=0)
    result = reducer.reduce(source, marker_set.markers, optimization_target=target)
    raw_nodes = [node.raw_repr.lower() for node in result.reduced_graph.nodes.values()]
    assert any("async_write_ha_state" in text for text in raw_nodes)
    assert any("dispatcher_connect" in text for text in raw_nodes)
    assert any("unsub" in text and "call(name('unsub'" in text for text in raw_nodes)
    assert all("do_noise('before')" not in text for text in raw_nodes)
    assert all("do_noise('after')" not in text for text in raw_nodes)


def test_target_seed_markers_keeps_generic_cloud_op_without_specific_peer() -> None:
    generic = Marker(
        marker_id="m1",
        marker_type="CLOUD_OP",
        file_path="/tmp/a.py",
        function_name="async_turn_on",
        line_start=10,
        line_end=10,
        strength="STRONG",
        phase="RUNTIME",
        primary_action_id="A1",
        related_action_ids=["A1"],
    )
    specific_other_action = Marker(
        marker_id="m2",
        marker_type="CLOUD_HTTP_CALL",
        file_path="/tmp/a.py",
        function_name="status",
        line_start=20,
        line_end=20,
        strength="STRONG",
        phase="RUNTIME",
        primary_action_id="A2",
        related_action_ids=["A2"],
    )
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A2", "protocol": "CLOUD", "marker_hints": ["CLOUD_HTTP_CALL"], "exec": {"kind": "ha_service_call"}},
        ],
        target_anchors={"anchor_ops": ["CLOUD_OP", "CLOUD_HTTP_CALL"]},
    )

    selected = TempoSpatialReducer._target_seed_markers([generic, specific_other_action], target)
    assert {marker.marker_id for marker in selected} == {"m1", "m2"}


def test_target_seed_markers_keeps_generalized_cloud_op_when_specific_peer_is_incomplete() -> None:
    generic = Marker(
        marker_id="m1",
        marker_type="CLOUD_OP",
        file_path="/tmp/a.py",
        function_name="async_turn_on",
        line_start=10,
        line_end=10,
        strength="STRONG",
        phase="RUNTIME",
        primary_action_id="A10",
        related_action_ids=["A10", "A7", "A8", "A9"],
        secondary_action_ids=["A7", "A8", "A9"],
        evidence=["action_match:generalized_profile_secondary_binding"],
    )
    specific_primary_only = Marker(
        marker_id="m2",
        marker_type="CLOUD_HTTP_CALL",
        file_path="/tmp/a.py",
        function_name="async_turn_on",
        line_start=11,
        line_end=11,
        strength="STRONG",
        phase="RUNTIME",
        primary_action_id="A10",
        related_action_ids=["A10"],
    )
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {"action_id": "A7", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A8", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A9", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A10", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"], "exec": {"kind": "ha_service_call"}},
        ],
        target_anchors={"anchor_ops": ["CLOUD_OP", "CLOUD_HTTP_CALL"]},
    )

    selected = TempoSpatialReducer._target_seed_markers([generic, specific_primary_only], target)
    assert {marker.marker_id for marker in selected} == {"m1", "m2"}


def test_unbound_shared_infra_marker_attaches_but_does_not_expand(tmp_path: Path) -> None:
    source = tmp_path / "integration_shared_attach.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    dispatcher_connect(hass, "sig_x", lambda: None)
    warmup_a = prepare("a")
    warmup_b = prepare("b")
    return True
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    subscribe = next(marker for marker in marker_set.markers if marker.marker_type == "SUBSCRIBE")
    assert subscribe.primary_action_id is None

    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "protocol": "BLE", "marker_hints": ["STATE_WRITE"], "exec": {"kind": "ha_service_call"}}],
        target_anchors={"anchor_ops": ["SUBSCRIBE"]},
    )
    reducer = TempoSpatialReducer(profile, spatial_depth=2, cfg_back_depth=1)
    result = reducer.reduce(source, marker_set.markers, optimization_target=target)
    raw_nodes = [node.raw_repr.lower() for node in result.reduced_graph.nodes.values()]
    assert any("dispatcher_connect" in text for text in raw_nodes)
    assert all("prepare('a')" not in text for text in raw_nodes)
    assert all("prepare('b')" not in text for text in raw_nodes)


def test_lifecycle_edges_use_primary_marker_nodes_only(tmp_path: Path) -> None:
    source = tmp_path / "integration_primary_lifecycle_edge.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    pre = prepare()
    post = finalize()
    return pre and post

async def async_unload_entry(hass, entry):
    clean_a = cleanup_a()
    clean_b = cleanup_b()
    return clean_a and clean_b
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {"id": "func:setup", "type": "ENTRY_SETUP", "match": {"function_names": ["async_setup_entry"]}, "strength": "STRONG", "phase": "SETUP"},
            {"id": "func:unload", "type": "ENTRY_UNLOAD", "match": {"function_names": ["async_unload_entry"]}, "strength": "STRONG", "phase": "TEARDOWN"},
        ],
        lifecycle_templates=[
            {
                "template_id": "pair:entry_setup_unload",
                "requires_order": ["ENTRY_SETUP", "ENTRY_UNLOAD"],
                "edge_kind": "HARD_LIFECYCLE",
            }
        ],
        rules=[Rule(rule_id="r1", title="t", category="lifecycle", evidence_ids=["DOC_x"])],
    )

    marker_set = detect_markers(source, profile)
    reducer = TempoSpatialReducer(profile)
    result = reducer.reduce(source, marker_set.markers)
    lifecycle_edges = [edge for edge in result.reduced_graph.edges if edge.edge_type == "LIFECYCLE_DEP"]
    assert len(lifecycle_edges) == 1


def test_reducer_emits_exception_dep_edges_for_try_handlers(tmp_path: Path) -> None:
    source = tmp_path / "integration_exception_edges.py"
    source.write_text(
        """
async def update_runtime(entity):
    try:
        entity.async_write_ha_state()
    except Exception:
        recover()
    finally:
        cleanup()
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    reducer = TempoSpatialReducer(profile)
    result = reducer.reduce(source, marker_set.markers)
    exception_edges = [edge for edge in result.reduced_graph.edges if edge.edge_type == "EXCEPTION_DEP"]
    assert exception_edges


def test_lifecycle_required_markers_filters_non_semantic_templates() -> None:
    profile = _profile()
    reducer = TempoSpatialReducer(profile)

    markers = [
        Marker(
            marker_id="m1",
            marker_type="BLE_CONNECT",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=1,
            line_end=1,
        ),
        Marker(
            marker_id="m2",
            marker_type="BLE_GATT_OP",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=2,
            line_end=2,
        ),
        Marker(
            marker_id="m3",
            marker_type="UNSUBSCRIBE",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=3,
            line_end=3,
        ),
    ]

    templates = [
        {"template_id": "proto_pair", "requires_order": ["BLE_CONNECT", "BLE_GATT_OP"]},
        {"template_id": "pair:subscribe_unsubscribe", "requires": ["SUBSCRIBE", "UNSUBSCRIBE"]},
    ]
    required = reducer._lifecycle_required_markers(markers, templates)
    required_types = {marker.marker_type for marker in required}
    assert required_types == {"UNSUBSCRIBE"}


def test_lifecycle_nodes_keep_primary_only(tmp_path: Path) -> None:
    source = tmp_path / "integration_lifecycle_primary_keep.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    v1 = 1
    v2 = 2
    v3 = 3
    return True

async def update_runtime(entity):
    entity.async_write_ha_state()
    return True

async def async_unload_entry(hass, entry):
    a1 = 1
    a2 = 2
    a3 = 3
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
        lifecycle_templates=[
            {
                "template_id": "must_keep_unload",
                "requires_order": ["ENTRY_UNLOAD", "STATE_WRITE"],
                "edge_kind": "HARD_LIFECYCLE",
                "semantic_required": True,
            }
        ],
        rules=[Rule(rule_id="r1", title="t", category="lifecycle", evidence_ids=["DOC_x"])],
    )
    marker_set = detect_markers(source, profile)
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"anchor_ops": ["STATE_WRITE"]},
    )
    reducer = TempoSpatialReducer(profile, spatial_depth=0, cfg_back_depth=0)
    result = reducer.reduce(source, marker_set.markers, optimization_target=target)
    unload_nodes = [node for node in result.reduced_graph.nodes.values() if node.function_name == "async_unload_entry"]
    unload_lines = sorted({node.line_start for node in unload_nodes})
    assert len(unload_lines) == 1


def test_lifecycle_narrow_spatial_closure_keeps_unsubscribe_source(tmp_path: Path) -> None:
    source = tmp_path / "integration_lifecycle_spatial.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    unsub = dispatcher_connect(hass, "sig_x", lambda: None)
    hass.data["unsub"] = unsub
    return True

async def update_runtime(entity):
    entity.async_write_ha_state()
    return True

async def async_unload_entry(hass, entry):
    unsub = hass.data["unsub"]
    unsub()
    return True
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"anchor_ops": ["STATE_WRITE"]},
    )
    reducer = TempoSpatialReducer(profile, spatial_depth=1, cfg_back_depth=0)
    result = reducer.reduce(source, marker_set.markers, optimization_target=target)
    unload_nodes = [node for node in result.reduced_graph.nodes.values() if node.function_name == "async_unload_entry"]
    unload_raw = [node.raw_repr for node in unload_nodes]
    assert not any("Name('unsub', Store())" in raw and "Subscript" in raw for raw in unload_raw)
    assert any("Call(Name('unsub'" in raw for raw in unload_raw)
    assert any("Call(Name('unsub', Load())" in raw for raw in unload_raw)


def test_temporal_slack_preserves_line_after_next_marker(tmp_path: Path) -> None:
    source = tmp_path / "integration_temporal_slack.py"
    source.write_text(
        """
async def update_runtime():
    first_refresh()
    payload = build_payload()
    write_state()
    tail = finalize()
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {"id": "m1", "type": "COORD_REFRESH", "match": {"call_attrs": ["first_refresh"]}, "strength": "STRONG", "phase": "RUNTIME"},
            {"id": "m2", "type": "STATE_WRITE", "match": {"call_attrs": ["write_state"]}, "strength": "STRONG", "phase": "RUNTIME"},
        ],
        lifecycle_templates=[],
        rules=[Rule(rule_id="r1", title="t", category="lifecycle", evidence_ids=["DOC_x"])],
    )
    marker_set = detect_markers(source, profile)
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"anchor_ops": ["COORD_REFRESH", "STATE_WRITE"]},
    )

    reducer = TempoSpatialReducer(profile, spatial_depth=0, cfg_back_depth=0, temporal_slack_lines=1)
    result = reducer.reduce(source, marker_set.markers, optimization_target=target)
    raw_nodes = [node.raw_repr.lower() for node in result.reduced_graph.nodes.values()]
    assert not any("finalize" in text for text in raw_nodes)


def test_lifecycle_adaptive_depth_keeps_two_hop_unsubscribe_source(tmp_path: Path) -> None:
    source = tmp_path / "integration_lifecycle_adaptive_depth.py"
    source.write_text(
        """
async def async_setup_entry(hass, entry):
    unsub = dispatcher_connect(hass, "sig_x", lambda: None)
    hass.data["unsub"] = unsub
    return True

async def update_runtime(entity):
    entity.async_write_ha_state()
    return True

async def async_unload_entry(hass, entry):
    stored = hass.data["unsub"]
    unsub = stored
    unsub()
    return True
""",
        encoding="utf-8",
    )

    profile = _profile()
    marker_set = detect_markers(source, profile)
    target = OptimizationTarget(
        source_scope={"files": [str(source)]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"anchor_ops": ["STATE_WRITE"]},
    )

    reducer = TempoSpatialReducer(profile, spatial_depth=0, cfg_back_depth=0)
    result = reducer.reduce(source, marker_set.markers, optimization_target=target)
    unload_nodes = [node for node in result.reduced_graph.nodes.values() if node.function_name == "async_unload_entry"]
    unload_raw = [node.raw_repr for node in unload_nodes]
    assert not any("Name('stored', Store())" in raw and "Subscript" in raw for raw in unload_raw)
    assert not any("Name('unsub', Store())" in raw and "Name('stored', Load())" in raw for raw in unload_raw)
    assert any("Call(Name('unsub'" in raw for raw in unload_raw)
    assert any("Call(Name('unsub', Load())" in raw for raw in unload_raw)


def test_spatial_cfg_backtracking_is_disabled_for_non_strong_markers(tmp_path: Path) -> None:
    source = tmp_path / "integration_medium_cfg.py"
    source.write_text(
        """
async def update_runtime():
    warmup = prepare()
    maybe_update()
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {"id": "m1", "type": "CUSTOM_OP", "match": {"call_attrs": ["maybe_update"]}, "strength": "MEDIUM", "phase": "RUNTIME"},
        ],
        lifecycle_templates=[],
        rules=[Rule(rule_id="r1", title="t", category="general", evidence_ids=["DOC_x"])],
    )
    marker_set = detect_markers(source, profile)
    reducer = TempoSpatialReducer(profile, spatial_depth=2, cfg_back_depth=1)
    result = reducer.reduce(source, marker_set.markers)
    raw_nodes = [node.raw_repr.lower() for node in result.reduced_graph.nodes.values()]
    assert any("maybe_update" in text for text in raw_nodes)
    assert all("prepare" not in text for text in raw_nodes)


def test_spatial_cfg_backtracking_is_kept_for_strong_markers(tmp_path: Path) -> None:
    source = tmp_path / "integration_strong_cfg.py"
    source.write_text(
        """
async def update_runtime():
    warmup = prepare()
    do_update()
""",
        encoding="utf-8",
    )

    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[
            {"id": "m1", "type": "CUSTOM_OP", "match": {"call_attrs": ["do_update"]}, "strength": "STRONG", "phase": "RUNTIME"},
        ],
        lifecycle_templates=[],
        rules=[Rule(rule_id="r1", title="t", category="general", evidence_ids=["DOC_x"])],
    )
    marker_set = detect_markers(source, profile)
    reducer = TempoSpatialReducer(profile, spatial_depth=2, cfg_back_depth=1)
    result = reducer.reduce(source, marker_set.markers)
    raw_nodes = [node.raw_repr.lower() for node in result.reduced_graph.nodes.values()]
    assert any("do_update" in text for text in raw_nodes)
    assert any("prepare" in text for text in raw_nodes)


def test_primary_marker_node_selection_is_stable() -> None:
    marker = Marker(
        marker_id="m1",
        marker_type="STATE_WRITE",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=10,
        line_end=10,
    )
    graph = ReducedGraph(
        nodes={
            "f:f:0.1:10": GraphNode(
                node_id="f:f:0.1:10",
                file_path="/tmp/a.py",
                function_name="f",
                line_start=10,
                line_end=10,
                col_start=12,
                col_end=18,
                stmt_kind="Expr",
            ),
            "f:f:0.0:10": GraphNode(
                node_id="f:f:0.0:10",
                file_path="/tmp/a.py",
                function_name="f",
                line_start=10,
                line_end=10,
                col_start=4,
                col_end=10,
                stmt_kind="Expr",
            ),
        },
        edges=[],
        mapping={},
    )

    first = TempoSpatialReducer._primary_marker_node(
        marker,
        graph,
        {"m1": ["f:f:0.1:10", "f:f:0.0:10"]},
    )
    second = TempoSpatialReducer._primary_marker_node(
        marker,
        graph,
        {"m1": ["f:f:0.0:10", "f:f:0.1:10"]},
    )
    assert first == "f:f:0.0:10"
    assert second == "f:f:0.0:10"


def test_ble_connect_is_not_treated_as_shared_infra_marker() -> None:
    assert TempoSpatialReducer._is_shared_infra_marker_type("BLE_CONNECT") is False
    assert TempoSpatialReducer._is_shared_infra_marker_type("BLE_DISCONNECT") is False


def test_cfg_backtracking_is_capped_per_anchor_for_protocol_markers() -> None:
    graph = ReducedGraph(
        nodes={
            f"n{i}": GraphNode(
                node_id=f"n{i}",
                file_path="/tmp/a.py",
                function_name="f",
                line_start=i,
                line_end=i,
                stmt_kind="Expr",
            )
            for i in range(1, 8)
        },
        edges=[
            GraphEdge(src=f"n{i}", dst=f"n{i+1}", edge_type="CFG_NEXT")
            for i in range(1, 7)
        ],
        mapping={},
    )
    marker = Marker(
        marker_id="m1",
        marker_type="BLE_CONNECT",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=7,
        line_end=7,
        primary_action_id="A2",
    )
    kept = TempoSpatialReducer._spatial_keep_with_policy(
        graph=graph,
        marker_to_nodes={"m1": ["n7"]},
        allowed_edge_types_by_marker={"m1": TempoSpatialReducer._allowed_edge_types_for_marker(marker)},
        depth_by_marker={"m1": 8},
        cfg_limit_by_marker={"m1": TempoSpatialReducer._cfg_chain_limit_for_marker(marker.marker_type)},
        cfg_back_depth=8,
    )
    assert kept == {"n6", "n7"}


def test_bound_setup_and_teardown_shared_markers_attach_but_do_not_expand() -> None:
    marker = Marker(
        marker_id="m1",
        marker_type="ENTRY_UNLOAD",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=3,
        line_end=3,
        primary_action_id="A9",
        phase="TEARDOWN",
    )

    assert TempoSpatialReducer._marker_expansion_allowed(marker) is False


def test_closure_depth_treats_generalized_secondary_binding_as_bound_anchor() -> None:
    marker = Marker(
        marker_id="m1",
        marker_type="CLOUD_HTTP_CALL",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=10,
        line_end=10,
        primary_action_id=None,
        secondary_action_ids=["A7", "A8"],
        phase="RUNTIME",
    )

    assert TempoSpatialReducer._closure_depth_for_marker(marker, default_depth=2) == 1
