from pathlib import Path

from dsl.contracts import (
    DEFAULT_LIFECYCLE_TEMPLATES,
    DEFAULT_MARKER_DETECTORS,
    GraphEdge,
    GraphNode,
    HAPProfile,
    MSSU,
    Marker,
    Phase,
    OptimizationTarget,
    PROFILE_SCHEMA_VERSION,
    ReducedGraph,
    Rule,
    now_utc_iso,
)
from optimizer.m1_markers import detect_markers
from optimizer.m2_reduction import TempoSpatialReducer
from optimizer.m3_mssu import MSSUBuilder


def _profile() -> HAPProfile:
    return HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="general", evidence_ids=["DOC_x"])],
    )


def test_m3_uses_medium_markers_as_seeds(tmp_path: Path) -> None:
    source = tmp_path / "integration.py"
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
    markers = detect_markers(source, profile)
    reduction = TempoSpatialReducer(profile).reduce(source, markers.markers)
    result = MSSUBuilder(profile).build(reduction.reduced_graph, markers.markers, reduction.marker_to_nodes)

    assert result.mssus


def test_m3_maps_protocol_specific_markers_to_generic_action_hints(tmp_path: Path) -> None:
    source = tmp_path / "integration.py"
    source.write_text(
        """
from bleak import BleakClient

async def async_setup_entry(hass, entry):
    await client.connect()
    await client.read_gatt_char("abc")
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
                "match": {"call_attrs": ["connect"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
            {
                "id": "call:protocol:ble_gatt_op",
                "type": "BLE_GATT_OP",
                "match": {"call_attrs": ["read_gatt_char"]},
                "strength": "STRONG",
                "phase": "RUNTIME",
            },
        ],
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[Rule(rule_id="r1", title="t", category="protocol", evidence_ids=["DOC_x"])],
    )

    target = OptimizationTarget(
        meta={"vdev_id": "v"},
        source_scope={"files": [str(source)]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "run"},
                "critical": True,
                "marker_hints": ["BLE_OP"],
            }
        ],
        target_anchors={},
        entrypoint={},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1"],
    )

    markers = detect_markers(source, profile, optimization_target=target)
    reduction = TempoSpatialReducer(profile).reduce(source, markers.markers, optimization_target=target)
    result = MSSUBuilder(profile).build(
        reduction.reduced_graph,
        markers.markers,
        reduction.marker_to_nodes,
        optimization_target=target,
    )

    protocol_mssus = [mssu for mssu in result.mssus if "ble_connect" in mssu.side_effect_sig or "ble_gatt_op" in mssu.side_effect_sig]
    assert protocol_mssus
    assert all("A1" in mssu.action_refs for mssu in protocol_mssus)
    ble_connect_mssus = [mssu for mssu in result.mssus if "ble_connect" in mssu.side_effect_sig]
    assert ble_connect_mssus
    assert all(mssu.mssu_type == "PREPARE" for mssu in ble_connect_mssus)
    assert all("resource_available" in mssu.required_guards for mssu in ble_connect_mssus)


def test_m3_claims_overlapping_nodes_without_reassigning_owner() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Assign", defs={"token"}),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr", uses={"token"}),
            "n3": GraphNode(node_id="n3", file_path="/tmp/a.py", function_name="f", line_start=3, line_end=3, stmt_kind="Expr", uses={"token"}),
        },
        edges=[
            GraphEdge(src="n1", dst="n2", edge_type="DATA_DEP"),
            GraphEdge(src="n2", dst="n3", edge_type="DATA_DEP"),
        ],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="SUBSCRIBE", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, strength="STRONG", phase=Phase.RUNTIME.value),
        Marker(marker_id="m2", marker_type="STATE_WRITE", file_path="/tmp/a.py", function_name="f", line_start=3, line_end=3, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n2"], "m2": ["n3"]}

    result = MSSUBuilder(_profile(), closure_depth=2).build(graph, markers, marker_to_nodes)

    assert len(result.mssus) == 2
    first_nodes = set(result.mssus[0].node_ids)
    second_nodes = set(result.mssus[1].node_ids)
    assert first_nodes == {"n1", "n2"}
    assert second_nodes == {"n3"}
    assert ("mssu_000_subscribe", "mssu_001_state_write", "DATA_DEP") in result.dependency_candidates


def test_m3_closure_does_not_expand_via_cfg_next() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Assign", defs={"warmup"}),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr"),
        },
        edges=[GraphEdge(src="n1", dst="n2", edge_type="CFG_NEXT")],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="STATE_WRITE", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n2"]}

    result = MSSUBuilder(_profile(), closure_depth=2).build(graph, markers, marker_to_nodes)
    assert result.mssus[0].node_ids == ["n2"]


def test_m3_outputs_ignore_cfg_next_escape() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Assign", defs={"token"}),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr"),
        },
        edges=[GraphEdge(src="n1", dst="n2", edge_type="CFG_NEXT")],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="SUBSCRIBE", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n1"]}

    result = MSSUBuilder(_profile(), closure_depth=0).build(graph, markers, marker_to_nodes)
    assert result.mssus[0].outputs == set()


def test_m3_cloud_protocol_markers_get_type_guard_and_exception_labels() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(
                node_id="n1",
                file_path="/tmp/a.py",
                function_name="f",
                line_start=1,
                line_end=1,
                stmt_kind="Try",
                raw_repr="Raise(Name('ConfigEntryAuthFailed', Load()))",
            ),
            "n2": GraphNode(
                node_id="n2",
                file_path="/tmp/a.py",
                function_name="f",
                line_start=2,
                line_end=2,
                stmt_kind="Expr",
                raw_repr="Call(Attribute(Name('session', Load()), 'request', Load()), [])",
            ),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="CLOUD_TOKEN_REFRESH", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, strength="STRONG", phase=Phase.RUNTIME.value),
        Marker(marker_id="m2", marker_type="CLOUD_HTTP_CALL", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n1"], "m2": ["n2"]}

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes)
    refresh = next(mssu for mssu in result.mssus if mssu.mssu_id.endswith("cloud_token_refresh"))
    call = next(mssu for mssu in result.mssus if mssu.mssu_id.endswith("cloud_http_call"))

    assert refresh.mssu_type == "PREPARE"
    assert call.mssu_type == "ACT"
    assert "rate_limit_budget_ok" in refresh.required_guards
    assert "rate_limit_budget_ok" in call.required_guards
    assert "AuthFailed" in refresh.exceptions


def test_m3_cloud_closure_ignores_control_context_and_stays_shallow() -> None:
    graph = ReducedGraph(
        nodes={
            "n0": GraphNode(node_id="n0", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="If"),
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Assign", defs={"request"}),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=3, line_end=3, stmt_kind="Expr"),
            "n3": GraphNode(node_id="n3", file_path="/tmp/a.py", function_name="f", line_start=4, line_end=4, stmt_kind="Expr"),
        },
        edges=[
            GraphEdge(src="n0", dst="n2", edge_type="CONTROL_DEP"),
            GraphEdge(src="n1", dst="n2", edge_type="DATA_DEP"),
            GraphEdge(src="n2", dst="n3", edge_type="LIFECYCLE_DEP"),
        ],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="CLOUD_HTTP_CALL", file_path="/tmp/a.py", function_name="f", line_start=3, line_end=3, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n2"]}

    result = MSSUBuilder(_profile(), closure_depth=3).build(graph, markers, marker_to_nodes)
    mssu = result.mssus[0]

    assert "n0" not in mssu.node_ids
    assert set(mssu.node_ids) == {"n1", "n2"}


def test_m3_overlap_seed_borrows_one_hop_data_context_and_adds_conservative_dep() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Assign", defs={"token"}),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr", uses={"token"}),
        },
        edges=[GraphEdge(src="n1", dst="n2", edge_type="DATA_DEP")],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="SUBSCRIBE", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, strength="STRONG", phase=Phase.RUNTIME.value),
        Marker(marker_id="m2", marker_type="STATE_WRITE", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n2"], "m2": ["n2"]}

    result = MSSUBuilder(_profile(), closure_depth=2).build(graph, markers, marker_to_nodes)

    first = result.mssus[0]
    second = result.mssus[1]
    assert set(first.node_ids) == {"n1", "n2"}
    assert set(second.node_ids) == {"n2"}
    assert (first.mssu_id, second.mssu_id, "DATA_DEP") in result.dependency_candidates


def test_m3_prefers_related_action_ids_over_broad_protocol_hint() -> None:
    marker = Marker(
        marker_id="m1",
        marker_type="BLE_GATT_OP",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=1,
        line_end=1,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        related_action_ids=["A2"],
    )
    target = OptimizationTarget(
        meta={"vdev_id": "v"},
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "BLE", "exec": {"kind": "ha_service_call"}, "marker_hints": ["BLE_OP"]},
            {"action_id": "A2", "protocol": "BLE", "exec": {"kind": "ha_service_call"}, "marker_hints": ["BLE_OP"], "critical": True},
        ],
        critical_action_ids=["A2"],
    )

    refs, critical = MSSUBuilder._action_refs_for_marker(marker, target)
    assert refs == ["A2"]
    assert critical is True


def test_m3_preserves_generalized_secondary_refs_for_profile_bound_marker() -> None:
    marker = Marker(
        marker_id="m1",
        marker_type="CLOUD_STATUS_CALL",
        file_path="/tmp/a.py",
        function_name="_build_snapshot",
        line_start=1,
        line_end=1,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A1",
        secondary_action_ids=["A2"],
        related_action_ids=["A1", "A2"],
        evidence=[
            "grounding_profile_rule:demo:file_runtime_status_read",
            "action_match:generalized_profile_secondary_binding",
        ],
    )
    target = OptimizationTarget(
        meta={"vdev_id": "v"},
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "status",
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_OP"],
                "critical": True,
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "type": "status",
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_OP"],
                "critical": True,
            },
        ],
        critical_action_ids=["A1", "A2"],
    )

    refs, critical = MSSUBuilder._action_refs_for_marker(marker, target)
    assert refs == ["A1", "A2"]
    assert critical is True


def test_m3_forbids_cloud_http_call_to_cloud_op_candidate() -> None:
    builder = MSSUBuilder(_profile())
    src = MSSU(
        mssu_id="src",
        mssu_type="ACT",
        phase=Phase.RUNTIME.value,
        node_ids=["n1"],
        side_effect_sig={"cloud_http_call"},
        primary_action_ref="A4",
        action_refs=["A4"],
        lane_tag="CLOUD",
    )
    dst = MSSU(
        mssu_id="dst",
        mssu_type="ACT",
        phase=Phase.RUNTIME.value,
        node_ids=["n2"],
        side_effect_sig={"cloud_op"},
        primary_action_ref="A5",
        action_refs=["A5"],
        lane_tag="CLOUD",
    )

    assert builder._forbid_candidate_pair(src, dst) is True


def test_m3_forbids_entry_setup_to_unsubscribe_candidate() -> None:
    builder = MSSUBuilder(_profile())
    src = MSSU(
        mssu_id="src",
        mssu_type="INIT",
        phase=Phase.SETUP.value,
        node_ids=["n1"],
        side_effect_sig={"entry_setup"},
        is_shared_infra=True,
    )
    dst = MSSU(
        mssu_id="dst",
        mssu_type="CLEANUP",
        phase=Phase.TEARDOWN.value,
        node_ids=["n2"],
        side_effect_sig={"unsubscribe"},
        is_shared_infra=True,
    )

    assert builder._forbid_candidate_pair(src, dst) is True


def test_m3_skips_shared_cloud_op_candidate_nodes() -> None:
    mssu = MSSU(
        mssu_id="cloud_helper",
        mssu_type="ACT",
        phase=Phase.RUNTIME.value,
        node_ids=["n1"],
        side_effect_sig={"cloud_op", "external_call_cloud"},
        is_shared_infra=True,
    )

    assert MSSUBuilder._skip_candidate_source_or_target(mssu) is True


def test_m3_propagates_subscribe_resource_tag_to_shared_unsubscribe_cleanup() -> None:
    builder = MSSUBuilder(_profile())
    graph = ReducedGraph(
        nodes={
            "f.py:fn:1": GraphNode(node_id="f.py:fn:1", file_path="f.py", function_name="fn", line_start=1, line_end=1, stmt_kind="Expr"),
            "f.py:fn:2": GraphNode(node_id="f.py:fn:2", file_path="f.py", function_name="fn", line_start=2, line_end=2, stmt_kind="Expr"),
        },
        edges=[],
        mapping={},
    )
    sub = MSSU(
        mssu_id="sub",
        mssu_type="PREPARE",
        phase=Phase.RUNTIME.value,
        node_ids=["f.py:fn:1"],
        side_effect_sig={"subscribe"},
        primary_action_ref="A3",
        action_refs=["A3"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:relay",
    )
    unsub = MSSU(
        mssu_id="unsub",
        mssu_type="CLEANUP",
        phase=Phase.TEARDOWN.value,
        node_ids=["f.py:fn:2"],
        side_effect_sig={"unsubscribe"},
        is_shared_infra=True,
    )

    out = builder._propagate_shared_cleanup_resource_tags([sub, unsub], graph)
    propagated = next(mssu for mssu in out if mssu.mssu_id == "unsub")
    assert propagated.resource_instance_tag == "ble:relay"
    assert propagated.lane_tag == "BLE_LOCAL"


def test_m3_summary_reports_missing_critical_actions() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(
                node_id="n1",
                file_path="/tmp/a.py",
                function_name="f",
                line_start=1,
                line_end=1,
                stmt_kind="Expr",
            ),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="STATE_WRITE",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=1,
            line_end=1,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            related_action_ids=["A3"],
        ),
    ]
    marker_to_nodes = {"m1": ["n1"]}
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {"action_id": "A1", "critical": True, "exec": {"kind": "ha_service_call"}, "marker_hints": ["BLE_OP"]},
            {"action_id": "A3", "critical": True, "exec": {"kind": "ha_service_call"}, "marker_hints": ["STATE_WRITE"]},
        ],
        critical_action_ids=["A1", "A3"],
    )

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes, optimization_target=target)
    assert result.build_status == "PARTIAL_GROUNDING"
    assert result.summary is not None
    assert result.summary["missing_critical_action_ids"] == ["A1"]


def test_m3_allows_generalized_cluster_bound_mssu_to_resolve_multiple_actions() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(
                node_id="n1",
                file_path="/tmp/a.py",
                function_name="_build_snapshot",
                line_start=1,
                line_end=1,
                stmt_kind="Expr",
                raw_repr="Call(Attribute(Name('device', Load()), 'read_device_status', Load()), [])",
            ),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="CLOUD_STATUS_CALL",
            file_path="/tmp/a.py",
            function_name="_build_snapshot",
            line_start=1,
            line_end=1,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A1",
            secondary_action_ids=["A2"],
            related_action_ids=["A1", "A2"],
            evidence=[
                "grounding_profile_rule:demo:file_runtime_status_read",
                "action_match:generalized_profile_secondary_binding",
            ],
        ),
    ]
    marker_to_nodes = {"m1": ["n1"]}
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "type": "status",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_OP"],
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "type": "status",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status"},
                "marker_hints": ["CLOUD_STATUS_CALL", "CLOUD_OP"],
            },
        ],
        critical_action_ids=["A1", "A2"],
    )

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes, optimization_target=target)
    assert result.summary is not None
    assert result.summary["missing_critical_action_ids"] == []
    assert result.summary["multi_bound_nonshared_mssu_ids"] == []
    assert result.summary["resolved_action_refs"] == ["A1", "A2"]
    mssu = result.mssus[0]
    assert mssu.primary_action_ref == "A1"
    assert mssu.secondary_action_refs == ["A2"]
    assert mssu.action_refs == ["A1", "A2"]


def test_m3_prune_keeps_control_guard_for_effectful_node() -> None:
    nodes = {
        "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="If"),
        "n2": GraphNode(
            node_id="n2",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=2,
            line_end=2,
            stmt_kind="Expr",
            effects={"external_call_cloud"},
        ),
        "n3": GraphNode(node_id="n3", file_path="/tmp/a.py", function_name="f", line_start=3, line_end=3, stmt_kind="Assign", defs={"x"}),
    }
    for idx in range(4, 14):
        nodes[f"n{idx}"] = GraphNode(
            node_id=f"n{idx}",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=idx,
            line_end=idx,
            stmt_kind="Assign",
            defs={f"tmp_{idx}"},
        )

    edges = [
        GraphEdge(src="n1", dst="n2", edge_type="CONTROL_DEP"),
        GraphEdge(src="n3", dst="n2", edge_type="DATA_DEP"),
    ]
    for idx in range(4, 14):
        edges.append(GraphEdge(src=f"n{idx}", dst="n2", edge_type="DATA_DEP"))

    graph = ReducedGraph(
        nodes=nodes,
        edges=edges,
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="CLOUD_HTTP_CALL", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n2"]}

    result = MSSUBuilder(_profile(), closure_depth=2, max_nodes_per_mssu=8).build(graph, markers, marker_to_nodes)
    node_ids = set(result.mssus[0].node_ids)
    assert "n1" not in node_ids
    assert "n2" in node_ids
    assert len(node_ids) <= 8


def test_m3_try_without_handlers_or_raise_does_not_emit_generic_exception() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(
                node_id="n1",
                file_path="/tmp/a.py",
                function_name="f",
                line_start=1,
                line_end=1,
                stmt_kind="Try",
                raw_repr="Try(body=[Expr(Name('x', Load()))], handlers=[], orelse=[], finalbody=[])",
            ),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="SUBSCRIBE", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n1"]}

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes)
    assert result.mssus[0].exceptions == set()


def test_m3_closure_expands_via_exception_dep() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Try"),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr"),
        },
        edges=[GraphEdge(src="n1", dst="n2", edge_type="EXCEPTION_DEP")],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="UNSUBSCRIBE", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, strength="STRONG", phase=Phase.TEARDOWN.value),
    ]
    marker_to_nodes = {"m1": ["n2"]}

    result = MSSUBuilder(_profile(), closure_depth=2).build(graph, markers, marker_to_nodes)
    assert set(result.mssus[0].node_ids) == {"n1", "n2"}


def test_m3_teardown_overlap_borrow_stays_with_seed_when_context_already_claimed() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Assign", defs={"root_handle"}),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Assign", defs={"stored"}, uses={"root_handle"}),
            "n3": GraphNode(node_id="n3", file_path="/tmp/a.py", function_name="f", line_start=3, line_end=3, stmt_kind="Expr", uses={"stored"}),
        },
        edges=[
            GraphEdge(src="n1", dst="n2", edge_type="DATA_DEP"),
            GraphEdge(src="n2", dst="n3", edge_type="DATA_DEP"),
        ],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="SUBSCRIBE", file_path="/tmp/a.py", function_name="f", line_start=3, line_end=3, strength="STRONG", phase=Phase.RUNTIME.value),
        Marker(marker_id="m2", marker_type="UNSUBSCRIBE", file_path="/tmp/a.py", function_name="f", line_start=3, line_end=3, strength="STRONG", phase=Phase.TEARDOWN.value),
    ]
    marker_to_nodes = {"m1": ["n3"], "m2": ["n3"]}

    result = MSSUBuilder(_profile(), closure_depth=0).build(graph, markers, marker_to_nodes)
    first = result.mssus[0]
    second = result.mssus[1]
    assert set(first.node_ids) == {"n2", "n3"}
    assert set(second.node_ids) == {"n3"}
    assert (first.mssu_id, second.mssu_id, "DATA_DEP") in result.dependency_candidates


def test_m3_dependency_candidates_filter_cfg_next() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Expr"),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr"),
        },
        edges=[GraphEdge(src="n1", dst="n2", edge_type="CFG_NEXT")],
        mapping={},
    )
    markers = [
        Marker(marker_id="m1", marker_type="SUBSCRIBE", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, strength="STRONG", phase=Phase.RUNTIME.value),
        Marker(marker_id="m2", marker_type="STATE_WRITE", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, strength="STRONG", phase=Phase.RUNTIME.value),
    ]
    marker_to_nodes = {"m1": ["n1"], "m2": ["n2"]}

    result = MSSUBuilder(_profile(), closure_depth=0).build(graph, markers, marker_to_nodes)
    assert result.dependency_candidates == []


def test_m3_state_write_without_writeback_lane_becomes_shared_infra() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Expr"),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="STATE_WRITE",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=1,
            line_end=1,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A1",
            related_action_ids=["A1"],
        )
    ]
    marker_to_nodes = {"m1": ["n1"]}
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[{"action_id": "A1", "protocol": "BLE", "marker_hints": ["STATE_WRITE"], "exec": {"kind": "ha_service_call"}}],
        critical_action_ids=["A1"],
    )

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes, optimization_target=target)
    mssu = result.mssus[0]
    assert mssu.is_shared_infra is True
    assert mssu.action_refs == []
    assert mssu.primary_action_ref is None


def test_m3_dependency_candidates_filter_cross_lane_non_writeback() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Expr"),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr"),
        },
        edges=[GraphEdge(src="n1", dst="n2", edge_type="DATA_DEP")],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="BLE_GATT_OP",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=1,
            line_end=1,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A1",
            related_action_ids=["A1"],
        ),
        Marker(
            marker_id="m2",
            marker_type="CLOUD_HTTP_CALL",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=2,
            line_end=2,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A2",
            related_action_ids=["A2"],
        ),
    ]
    marker_to_nodes = {"m1": ["n1"], "m2": ["n2"]}
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "BLE", "marker_hints": ["BLE_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A2", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP"], "exec": {"kind": "ha_service_call"}},
        ],
        critical_action_ids=["A1", "A2"],
    )

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes, optimization_target=target)
    assert result.dependency_candidates == []


def test_m3_policy_only_shared_marker_does_not_inherit_action_from_closure() -> None:
    marker = Marker(
        marker_id="m1",
        marker_type="ENTRY_SETUP",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=1,
        line_end=1,
        strength="STRONG",
        phase=Phase.SETUP.value,
    )
    peer = Marker(
        marker_id="m2",
        marker_type="CLOUD_HTTP_CALL",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=2,
        line_end=2,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A1",
        related_action_ids=["A1"],
        binding_reason=["hint_exact_match", "file_binding_match"],
    )
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Expr", marker_refs=["m1"]),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr", marker_refs=["m2"]),
        },
        edges=[],
        mapping={},
    )
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[{"action_id": "A1", "protocol": "CLOUD", "marker_hints": ["CLOUD_HTTP_CALL"]}],
        target_anchors={},
    )

    builder = MSSUBuilder(_profile())
    base = builder._action_binding_for_marker(marker, target)
    refined = builder._refine_binding_from_closure(marker, {"n1", "n2"}, graph, {"m1": marker, "m2": peer}, target, base)

    assert refined["primary_action_ref"] is None
    assert refined["action_refs"] == []
    assert refined["is_shared_infra"] is True


def test_m3_generic_protocol_marker_yields_to_specific_peer() -> None:
    generic = Marker(
        marker_id="m1",
        marker_type="CLOUD_OP",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=1,
        line_end=1,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A1",
        related_action_ids=["A1"],
        binding_reason=[
            "hint_exact_match",
            "file_binding_match",
            "integration_binding_match",
            "protocol_binding_match",
            "service_token_match",
        ],
        evidence=["heuristic:cloud_runtime_call", "related_actions:A1"],
    )
    specific = Marker(
        marker_id="m2",
        marker_type="CLOUD_HTTP_CALL",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=2,
        line_end=2,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A1",
        related_action_ids=["A1"],
        binding_reason=["hint_exact_match", "file_binding_match"],
    )
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Expr", marker_refs=["m1"]),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr", marker_refs=["m2"]),
        },
        edges=[],
        mapping={},
    )
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[{"action_id": "A1", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"]}],
        target_anchors={},
    )

    builder = MSSUBuilder(_profile())
    base = builder._action_binding_for_marker(generic, target)
    refined = builder._refine_binding_from_closure(generic, {"n1", "n2"}, graph, {"m1": generic, "m2": specific}, target, base)

    assert refined["primary_action_ref"] is None
    assert refined["action_refs"] == []


def test_m3_generic_protocol_marker_keeps_secondary_refs_when_specific_peer_is_incomplete() -> None:
    generic = Marker(
        marker_id="m1",
        marker_type="CLOUD_OP",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=1,
        line_end=1,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A10",
        related_action_ids=["A10", "A7", "A8", "A9"],
        secondary_action_ids=["A7", "A8", "A9"],
        binding_reason=[
            "hint_exact_match",
            "file_binding_match",
            "integration_binding_match",
            "protocol_binding_match",
            "service_token_match",
        ],
        evidence=[
            "heuristic:cloud_runtime_call",
            "action_match:generalized_profile_secondary_binding",
            "related_actions:A10,A7,A8,A9",
        ],
    )
    specific = Marker(
        marker_id="m2",
        marker_type="CLOUD_HTTP_CALL",
        file_path="/tmp/a.py",
        function_name="f",
        line_start=2,
        line_end=2,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A10",
        related_action_ids=["A10"],
        binding_reason=["hint_exact_match", "file_binding_match"],
    )
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Expr", marker_refs=["m1"]),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr", marker_refs=["m2"]),
        },
        edges=[],
        mapping={},
    )
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {"action_id": "A7", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"]},
            {"action_id": "A8", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"]},
            {"action_id": "A9", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"]},
            {"action_id": "A10", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP", "CLOUD_HTTP_CALL"]},
        ],
        target_anchors={},
    )

    builder = MSSUBuilder(_profile())
    base = builder._action_binding_for_marker(generic, target)
    refined = builder._refine_binding_from_closure(generic, {"n1", "n2"}, graph, {"m1": generic, "m2": specific}, target, base)

    assert refined["primary_action_ref"] == "A10"
    assert refined["action_refs"] == ["A10", "A7", "A8", "A9"]
    assert refined["is_shared_infra"] is False


def test_m3_preserves_explicit_profile_binding_over_closure_ownership() -> None:
    profile_marker = Marker(
        marker_id="m1",
        marker_type="CLOUD_STATUS_CALL",
        file_path="/tmp/a.py",
        function_name="_get_temperature_wrappers",
        line_start=10,
        line_end=12,
        strength="STRONG",
        phase=Phase.SETUP.value,
        primary_action_id="A18",
        related_action_ids=["A18"],
        binding_reason=["hint_exact_match", "file_binding_match", "binding_hint_action_id"],
        evidence=["grounding_profile_rule:tuya:climate_runtime_status_read"],
    )
    control_peer = Marker(
        marker_id="m2",
        marker_type="CLOUD_OP",
        file_path="/tmp/a.py",
        function_name="async_set_temperature",
        line_start=13,
        line_end=13,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A11",
        related_action_ids=["A11"],
        binding_reason=["hint_exact_match", "file_binding_match"],
    )
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="_get_temperature_wrappers", line_start=10, line_end=12, stmt_kind="If", marker_refs=["m1", "m2"]),
        },
        edges=[],
        mapping={},
    )
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {"action_id": "A11", "protocol": "CLOUD", "marker_hints": ["CLOUD_OP"], "exec": {"kind": "ha_service_call"}},
            {"action_id": "A18", "protocol": "CLOUD", "marker_hints": ["CLOUD_STATUS_CALL"], "exec": {"kind": "ha_service_call"}},
        ],
        critical_action_ids=["A11", "A18"],
        target_anchors={},
    )

    builder = MSSUBuilder(_profile())
    base = builder._action_binding_for_marker(profile_marker, target)
    refined = builder._refine_binding_from_closure(
        profile_marker,
        {"n1"},
        graph,
        {"m1": profile_marker, "m2": control_peer},
        target,
        base,
    )

    assert refined["primary_action_ref"] == "A18"
    assert refined["action_refs"] == ["A18"]


def test_m3_preserves_explicit_ha_writeback_primary_owner_under_closure() -> None:
    writeback = Marker(
        marker_id="m1",
        marker_type="STATE_WRITE",
        file_path="/tmp/a.py",
        function_name="_handle_coordinator_update",
        line_start=1,
        line_end=1,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A2",
        related_action_ids=["A2"],
        binding_reason=["hint_exact_match", "file_binding_match"],
    )
    peer = Marker(
        marker_id="m2",
        marker_type="LOCAL_API_READ",
        file_path="/tmp/a.py",
        function_name="_handle_coordinator_update",
        line_start=2,
        line_end=2,
        strength="STRONG",
        phase=Phase.RUNTIME.value,
        primary_action_id="A1",
        related_action_ids=["A1"],
        binding_reason=["hint_exact_match", "file_binding_match"],
    )
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="_handle_coordinator_update", line_start=1, line_end=1, stmt_kind="Expr", marker_refs=["m1"]),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="_handle_coordinator_update", line_start=2, line_end=2, stmt_kind="Expr", marker_refs=["m2"]),
        },
        edges=[],
        mapping={},
    )
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "LOCAL",
                "marker_hints": ["LOCAL_API_READ"],
                "exec": {"kind": "ha_service_call", "domain": "tplink", "service": "get_state"},
            },
            {
                "action_id": "A2",
                "protocol": "HA",
                "marker_hints": ["STATE_WRITE"],
                "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
                "target": {"entity_id": "sensor.vdev_local_lane"},
            },
        ],
        target_anchors={},
    )

    builder = MSSUBuilder(_profile())
    base = builder._action_binding_for_marker(writeback, target)
    refined = builder._refine_binding_from_closure(writeback, {"n1", "n2"}, graph, {"m1": writeback, "m2": peer}, target, base)

    assert refined["primary_action_ref"] == "A2"
    assert refined["action_refs"] == ["A2"]


def test_m3_compacts_identical_runtime_fragments_for_same_action() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f1", line_start=1, line_end=1, stmt_kind="Expr", uses={"self"}),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f2", line_start=2, line_end=2, stmt_kind="Expr", uses={"self"}),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="STATE_WRITE",
            file_path="/tmp/a.py",
            function_name="f1",
            line_start=1,
            line_end=1,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A1",
            related_action_ids=["A1"],
        ),
        Marker(
            marker_id="m2",
            marker_type="STATE_WRITE",
            file_path="/tmp/a.py",
            function_name="f2",
            line_start=2,
            line_end=2,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A1",
            related_action_ids=["A1"],
        ),
    ]
    marker_to_nodes = {"m1": ["n1"], "m2": ["n2"]}
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "HA",
                "marker_hints": ["STATE_WRITE"],
                "target": {"entity_id": "sensor.vdev_hybrid_transport_ble_lane"},
                "exec": {"kind": "ha_service_call", "domain": "fan", "service": "publish"},
            }
        ],
        critical_action_ids=["A1"],
    )

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes, optimization_target=target)
    assert len(result.mssus) == 1
    mssu = result.mssus[0]
    assert mssu.primary_action_ref == "A1"
    assert mssu.node_ids == ["n1", "n2"]


def test_m3_compacts_same_action_fragments_by_primary_effect_family() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f1", line_start=1, line_end=1, stmt_kind="Expr", uses={"self"}),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f2", line_start=2, line_end=2, stmt_kind="Expr", uses={"self", "kwargs"}),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="BLE_OP",
            file_path="/tmp/a.py",
            function_name="f1",
            line_start=1,
            line_end=1,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A1",
            related_action_ids=["A1"],
        ),
        Marker(
            marker_id="m2",
            marker_type="BLE_OP",
            file_path="/tmp/a.py",
            function_name="f2",
            line_start=2,
            line_end=2,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A1",
            related_action_ids=["A1"],
        ),
    ]
    marker_to_nodes = {"m1": ["n1"], "m2": ["n2"]}
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[{"action_id": "A1", "protocol": "BLE", "marker_hints": ["BLE_OP"], "exec": {"kind": "ha_service_call"}}],
        critical_action_ids=["A1"],
    )

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes, optimization_target=target)
    assert len(result.mssus) == 1
    assert result.mssus[0].node_ids == ["n1", "n2"]


def test_m3_compacts_cloud_http_call_family_across_setup_and_runtime() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="setup_one", line_start=1, line_end=1, stmt_kind="Expr"),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="setup_two", line_start=2, line_end=2, stmt_kind="Expr"),
            "n3": GraphNode(node_id="n3", file_path="/tmp/a.py", function_name="runtime", line_start=3, line_end=3, stmt_kind="Expr"),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="CLOUD_HTTP_CALL",
            file_path="/tmp/a.py",
            function_name="setup_one",
            line_start=1,
            line_end=1,
            strength="STRONG",
            phase=Phase.SETUP.value,
            primary_action_id="A4",
            related_action_ids=["A4"],
        ),
        Marker(
            marker_id="m2",
            marker_type="CLOUD_HTTP_CALL",
            file_path="/tmp/a.py",
            function_name="setup_two",
            line_start=2,
            line_end=2,
            strength="STRONG",
            phase=Phase.SETUP.value,
            primary_action_id="A4",
            related_action_ids=["A4"],
        ),
        Marker(
            marker_id="m3",
            marker_type="CLOUD_HTTP_CALL",
            file_path="/tmp/a.py",
            function_name="runtime",
            line_start=3,
            line_end=3,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
            primary_action_id="A4",
            related_action_ids=["A4"],
        ),
    ]
    marker_to_nodes = {"m1": ["n1"], "m2": ["n2"], "m3": ["n3"]}
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[{"action_id": "A4", "protocol": "CLOUD", "marker_hints": ["CLOUD_HTTP_CALL"], "exec": {"kind": "ha_service_call"}}],
        critical_action_ids=["A4"],
    )

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes, optimization_target=target)

    assert len(result.mssus) == 1
    assert result.mssus[0].primary_action_ref == "A4"
    assert result.mssus[0].phase == Phase.RUNTIME.value
    assert result.mssus[0].node_ids == ["n1", "n2", "n3"]


def test_m3_drops_teardown_unowned_shared_ble_ops() -> None:
    teardown_ble = MSSU(
        mssu_id="mssu_ble",
        mssu_type="ACT",
        phase=Phase.TEARDOWN.value,
        node_ids=["n1"],
        side_effect_sig={"ble_op", "external_call_ble"},
        action_refs=[],
        is_shared_infra=True,
    )
    assert MSSUBuilder._drop_teardown_unowned_ble_ops(teardown_ble) is True


def test_m3_normalizes_a2_teardown_ble_connect_when_it_is_the_only_owner() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="clear_key", line_start=1, line_end=1, stmt_kind="Expr"),
        },
        edges=[],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="BLE_CONNECT",
            file_path="/tmp/a.py",
            function_name="clear_key",
            line_start=1,
            line_end=1,
            strength="MEDIUM",
            phase=Phase.TEARDOWN.value,
            primary_action_id="A2",
            related_action_ids=["A2"],
        ),
    ]
    marker_to_nodes = {"m1": ["n1"]}
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/a.py"]},
        vdev_actions=[{"action_id": "A2", "protocol": "BLE", "marker_hints": ["BLE_CONNECT"], "exec": {"kind": "ha_service_call"}}],
        critical_action_ids=["A2"],
    )

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes, optimization_target=target)

    assert len(result.mssus) == 1
    mssu = result.mssus[0]
    assert mssu.primary_action_ref == "A2"
    assert mssu.action_refs == ["A2"]
    assert mssu.is_shared_infra is True
    assert mssu.phase == Phase.SETUP.value


def test_m3_demotes_a2_teardown_ble_connect_when_alternative_owner_exists() -> None:
    connect = MSSU(
        mssu_id="connect",
        mssu_type="PREPARE",
        phase=Phase.TEARDOWN.value,
        node_ids=["n1"],
        side_effect_sig={"ble_connect", "external_call_ble"},
        primary_action_ref="A2",
        action_refs=["A2"],
        is_shared_infra=True,
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:device",
        critical=True,
    )
    alt = MSSU(
        mssu_id="alt",
        mssu_type="ACT",
        phase=Phase.RUNTIME.value,
        node_ids=["n2"],
        side_effect_sig={"ble_op"},
        primary_action_ref="A2",
        action_refs=["A2"],
    )

    normalized = MSSUBuilder._normalize_teardown_connect_mssu(connect, [connect, alt])
    assert normalized.primary_action_ref is None
    assert normalized.action_refs == []
    assert normalized.phase == Phase.TEARDOWN.value


def test_m3_skips_runtime_to_setup_dependency_candidates() -> None:
    graph = ReducedGraph(
        nodes={
            "n1": GraphNode(node_id="n1", file_path="/tmp/a.py", function_name="f", line_start=1, line_end=1, stmt_kind="Expr"),
            "n2": GraphNode(node_id="n2", file_path="/tmp/a.py", function_name="f", line_start=2, line_end=2, stmt_kind="Expr"),
        },
        edges=[GraphEdge(src="n1", dst="n2", edge_type="DATA_DEP")],
        mapping={},
    )
    markers = [
        Marker(
            marker_id="m1",
            marker_type="CLOUD_HTTP_CALL",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=1,
            line_end=1,
            strength="STRONG",
            phase=Phase.RUNTIME.value,
        ),
        Marker(
            marker_id="m2",
            marker_type="ENTRY_SETUP",
            file_path="/tmp/a.py",
            function_name="f",
            line_start=2,
            line_end=2,
            strength="STRONG",
            phase=Phase.SETUP.value,
        ),
    ]
    marker_to_nodes = {"m1": ["n1"], "m2": ["n2"]}

    result = MSSUBuilder(_profile()).build(graph, markers, marker_to_nodes)
    assert result.dependency_candidates == []
