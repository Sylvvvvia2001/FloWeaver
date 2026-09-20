from dsl.contracts import (
    DEFAULT_LIFECYCLE_TEMPLATES,
    DEFAULT_MARKER_DETECTORS,
    HAPProfile,
    MSSU,
    OptimizationTarget,
    PROFILE_SCHEMA_VERSION,
    Rule,
    now_utc_iso,
)
from optimizer.m4_typed_dag import TypedDAGBuilder


def _profile() -> HAPProfile:
    return HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r1",
                title="cloud pacing",
                category="protocol",
                marker_hints=["CLOUD_OP"],
                soft_constraint_templates=[
                    {"kind": "BACKOFF_WINDOW", "scope": ["CLOUD_OP"], "params": {"base_ms": 200}}
                ],
                evidence_ids=["DOC_x"],
            ),
            Rule(
                rule_id="r2",
                title="refresh before write",
                category="lifecycle",
                marker_hints=["COORD_REFRESH", "STATE_WRITE"],
                hard_edge_templates=[{"src": "coord_refresh", "dst": "state_write", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["DOC_y"],
            ),
        ],
    )


def test_cycle_break_in_hard_edges() -> None:
    mssu_a = MSSU(mssu_id="a", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], outputs={"x"}, inputs={"y"})
    mssu_b = MSSU(mssu_id="b", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], outputs={"y"}, inputs={"x"})

    builder = TypedDAGBuilder(_profile())
    dag, diagnostics = builder.build(
        [mssu_a, mssu_b],
        [
            ("a", "b", "DATA_DEP"),
            ("b", "a", "DATA_DEP"),
        ],
    )

    assert not dag.hard_edges
    assert any(constraint.kind == "SOFT_ORDER" for constraint in dag.soft_constraints)


def test_rule_hard_edge_template_is_injected() -> None:
    mssu_refresh = MSSU(mssu_id="r", mssu_type="SYNC", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"coord_refresh"})
    mssu_write = MSSU(mssu_id="w", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n2"], side_effect_sig={"state_write"})

    dag, _ = TypedDAGBuilder(_profile()).build([mssu_refresh, mssu_write], dependency_candidates=[])
    assert any(edge.src_mssu == "r" and edge.dst_mssu == "w" and edge.kind == "HARD_LIFECYCLE" for edge in dag.hard_edges)


def test_rule_hard_edge_template_alias_binds_ble_op_candidate() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_ble",
                title="connect before gatt op",
                category="protocol",
                hard_edge_templates=[{"src": "BLE_CONNECT", "dst": "BLE_GATT_OP", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["CODE_ble"],
            )
        ],
    )
    mssu_connect = MSSU(mssu_id="connect", mssu_type="PREPARE", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"ble_connect"})
    mssu_op = MSSU(mssu_id="op", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], side_effect_sig={"ble_op"})

    dag, diagnostics = TypedDAGBuilder(profile).build([mssu_connect, mssu_op], dependency_candidates=[])

    assert any(edge.src_mssu == "connect" and edge.dst_mssu == "op" for edge in dag.hard_edges)
    assert not diagnostics.warnings


def test_non_applicable_split_templates_are_silent() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="rule_setup_refresh:part1",
                title="setup before refresh",
                category="lifecycle",
                hard_edge_templates=[{"src": "ENTRY_SETUP", "dst": "COORD_REFRESH", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["DOC_1"],
            ),
            Rule(
                rule_id="rule_setup_refresh:part2",
                title="setup before refresh",
                category="lifecycle",
                hard_edge_templates=[{"src": "ENTRY_SETUP", "dst": "COORD_REFRESH", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["DOC_2"],
            ),
        ],
    )
    mssu_setup = MSSU(mssu_id="setup", mssu_type="INIT", phase="SETUP", node_ids=["n1"], side_effect_sig={"entry_setup"})

    dag, diagnostics = TypedDAGBuilder(profile).build([mssu_setup], dependency_candidates=[])

    assert not dag.hard_edges
    assert diagnostics.warnings == []


def test_template_pairing_prefers_exact_unsubscribe_family_over_nearest_token_overlap() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_sub_unsub",
                title="subscribe cleanup",
                category="cleanup",
                hard_edge_templates=[{"src": "SUBSCRIBE", "dst": "UNSUBSCRIBE", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["TEST_sub"],
            )
        ],
    )
    mssu_sub = MSSU(
        mssu_id="sub",
        mssu_type="PREPARE",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"subscribe"},
        primary_action_ref="A3",
        action_refs=["A3"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:relay",
        is_shared_infra=True,
    )
    mssu_entry_setup = MSSU(
        mssu_id="setupish",
        mssu_type="INIT",
        phase="SETUP",
        node_ids=["n2"],
        side_effect_sig={"entry_setup", "unsubscribe", "external_call_cloud"},
        is_shared_infra=True,
    )
    mssu_unsub = MSSU(
        mssu_id="unsub",
        mssu_type="CLEANUP",
        phase="TEARDOWN",
        node_ids=["n3"],
        side_effect_sig={"unsubscribe"},
        resource_instance_tag="ble:relay",
        is_shared_infra=True,
    )

    dag, _ = TypedDAGBuilder(profile).build([mssu_sub, mssu_entry_setup, mssu_unsub], dependency_candidates=[])

    assert any(edge.src_mssu == "sub" and edge.dst_mssu == "unsub" for edge in dag.hard_edges)
    assert not any(edge.src_mssu == "sub" and edge.dst_mssu == "setupish" for edge in dag.hard_edges)
    chosen = next(edge for edge in dag.hard_edges if edge.src_mssu == "sub" and edge.dst_mssu == "unsub")
    assert "pair_key:nearest" not in chosen.justification
    assert "pairing_rank:exact_family_same_action_same_lane_phase_then_nearest" in chosen.justification


def test_subscribe_unsubscribe_pair_requires_same_resource_instance() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_sub_unsub",
                title="subscribe cleanup",
                category="cleanup",
                hard_edge_templates=[{"src": "SUBSCRIBE", "dst": "UNSUBSCRIBE", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["TEST_sub"],
            )
        ],
    )
    mssu_sub = MSSU(
        mssu_id="sub",
        mssu_type="PREPARE",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"subscribe"},
        resource_instance_tag="ble:relay:a",
    )
    mssu_unsub = MSSU(
        mssu_id="unsub",
        mssu_type="CLEANUP",
        phase="TEARDOWN",
        node_ids=["n2"],
        side_effect_sig={"unsubscribe"},
        resource_instance_tag="ble:relay:b",
    )

    dag, _ = TypedDAGBuilder(profile).build([mssu_sub, mssu_unsub], dependency_candidates=[])

    assert dag.hard_edges == []


def test_subscribe_unsubscribe_pair_allows_shared_cleanup_without_resource_when_no_better_match() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_sub_unsub",
                title="subscribe cleanup",
                category="cleanup",
                hard_edge_templates=[{"src": "SUBSCRIBE", "dst": "UNSUBSCRIBE", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["TEST_sub"],
            )
        ],
    )
    mssu_sub = MSSU(
        mssu_id="sub",
        mssu_type="PREPARE",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"subscribe"},
        primary_action_ref="A3",
        action_refs=["A3"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:relay",
        is_shared_infra=True,
    )
    mssu_unsub_shared = MSSU(
        mssu_id="unsub_shared",
        mssu_type="CLEANUP",
        phase="TEARDOWN",
        node_ids=["n2"],
        side_effect_sig={"unsubscribe"},
        is_shared_infra=True,
    )
    mssu_unsub_helper = MSSU(
        mssu_id="unsub_helper",
        mssu_type="CLEANUP",
        phase="TEARDOWN",
        node_ids=["n3"],
        side_effect_sig={"external_call_cloud", "unsubscribe"},
        is_shared_infra=True,
    )

    dag, _ = TypedDAGBuilder(profile).build([mssu_sub, mssu_unsub_shared, mssu_unsub_helper], dependency_candidates=[])

    assert any(edge.src_mssu == "sub" and edge.dst_mssu == "unsub_shared" for edge in dag.hard_edges)
    assert not any(
        item.params.get("reason") == "template:r_sub_unsub:0:template_binding_failed_fallback"
        for item in dag.soft_constraints
    )


def test_pair_key_template_avoids_wide_scope_warning_when_scope_can_narrow() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_ble_pair",
                title="connect before op by device",
                category="protocol",
                hard_edge_templates=[
                    {
                        "src": "BLE_CONNECT",
                        "dst": "BLE_GATT_OP",
                        "kind": "HARD_LIFECYCLE",
                        "params": {"pair_key": "device_id"},
                    }
                ],
                evidence_ids=["CODE_ble"],
            )
        ],
    )
    mssu_connect = MSSU(
        mssu_id="connect",
        mssu_type="PREPARE",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"ble_connect"},
        primary_action_ref="A1",
        action_refs=["A1"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:device:one",
    )
    mssu_op_match = MSSU(
        mssu_id="op_match",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n2"],
        side_effect_sig={"ble_op"},
        primary_action_ref="A1",
        action_refs=["A1"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:device:one",
    )
    extra_ops = [
        MSSU(
            mssu_id=f"op_other_{idx}",
            mssu_type="ACT",
            phase="RUNTIME",
            node_ids=[f"n_extra_{idx}"],
            side_effect_sig={"ble_op"},
            primary_action_ref=f"A{idx + 2}",
            action_refs=[f"A{idx + 2}"],
            lane_tag="BLE_LOCAL",
            resource_instance_tag=f"ble:device:{idx + 2}",
        )
        for idx in range(9)
    ]
    target = OptimizationTarget(
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "BLE", "target_kind": "ble_device", "target": {"device_id": "ble:device:one"}},
            *[
                {
                    "action_id": f"A{idx + 2}",
                    "protocol": "BLE",
                    "target_kind": "ble_device",
                    "target": {"device_id": f"ble:device:{idx + 2}"},
                }
                for idx in range(9)
            ],
        ],
    )

    dag, diagnostics = TypedDAGBuilder(profile).build(
        [mssu_connect, mssu_op_match, *extra_ops],
        dependency_candidates=[],
        optimization_target=target,
    )

    assert any(edge.src_mssu == "connect" and edge.dst_mssu == "op_match" for edge in dag.hard_edges)
    assert not any("widened to soft order" in warning for warning in diagnostics.warnings)


def test_candidate_control_dep_is_softened_to_soft_order() -> None:
    mssu_a = MSSU(mssu_id="a", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"])
    mssu_b = MSSU(mssu_id="b", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"])

    dag, _ = TypedDAGBuilder(_profile()).build([mssu_a, mssu_b], dependency_candidates=[("a", "b", "CONTROL_DEP")])

    assert not dag.hard_edges
    assert any(
        constraint.kind == "SOFT_ORDER" and constraint.scope == ["a", "b"]
        for constraint in dag.soft_constraints
    )


def test_candidate_data_dep_to_state_write_is_softened_for_soft_only_update() -> None:
    mssu_act = MSSU(
        mssu_id="act",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n1"],
        outputs={"temperature"},
        primary_action_ref="A1",
        action_refs=["A1"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:one",
    )
    mssu_write = MSSU(
        mssu_id="write",
        mssu_type="UPDATE",
        phase="RUNTIME",
        node_ids=["n2"],
        inputs={"temperature"},
        side_effect_sig={"state_write"},
        primary_action_ref="A7",
        action_refs=["A7"],
        lane_tag="WRITEBACK_BLE",
        resource_instance_tag="sensor.ble_lane",
    )

    dag, _ = TypedDAGBuilder(_profile()).build([mssu_act, mssu_write], dependency_candidates=[("act", "write", "DATA_DEP")])
    assert not dag.hard_edges
    assert any(item.kind == "SOFT_ORDER" and item.scope == ["act", "write"] for item in dag.soft_constraints)


def test_candidate_lifecycle_dep_stays_hard_for_cleanup_semantics() -> None:
    mssu_sub = MSSU(mssu_id="sub", mssu_type="PREPARE", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"subscribe"})
    mssu_unsub = MSSU(mssu_id="unsub", mssu_type="CLEANUP", phase="TEARDOWN", node_ids=["n2"], side_effect_sig={"unsubscribe"})

    dag, _ = TypedDAGBuilder(_profile()).build([mssu_sub, mssu_unsub], dependency_candidates=[("sub", "unsub", "LIFECYCLE_DEP")])

    assert not dag.hard_edges
    assert any(item.kind == "SOFT_ORDER" and item.scope == ["sub", "unsub"] for item in dag.soft_constraints)


def test_template_nearest_choice_is_stable_without_action_refs() -> None:
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
                title="refresh before write",
                category="lifecycle",
                hard_edge_templates=[{"src": "coord_refresh", "dst": "state_write", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["DOC_x"],
            )
        ],
    )
    mssu_refresh = MSSU(mssu_id="r", mssu_type="SYNC", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"coord_refresh"})
    mssu_write_b = MSSU(mssu_id="write_b", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n2"], side_effect_sig={"state_write"})
    mssu_write_a = MSSU(mssu_id="write_a", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n3"], side_effect_sig={"state_write"})

    dag_one, _ = TypedDAGBuilder(profile).build([mssu_refresh, mssu_write_b, mssu_write_a], dependency_candidates=[])
    dag_two, _ = TypedDAGBuilder(profile).build([mssu_refresh, mssu_write_a, mssu_write_b], dependency_candidates=[])

    target_one = next(edge.dst_mssu for edge in dag_one.hard_edges if edge.src_mssu == "r")
    target_two = next(edge.dst_mssu for edge in dag_two.hard_edges if edge.src_mssu == "r")
    assert target_one == "write_a"
    assert target_two == "write_a"


def test_candidate_lifecycle_pairing_tokens_stay_hard_without_cleanup_type() -> None:
    mssu_connect = MSSU(mssu_id="connect", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"subscribe"})
    mssu_disconnect = MSSU(mssu_id="disconnect", mssu_type="ACT", phase="TEARDOWN", node_ids=["n2"], side_effect_sig={"unsubscribe"})

    dag, _ = TypedDAGBuilder(_profile()).build(
        [mssu_connect, mssu_disconnect],
        dependency_candidates=[("connect", "disconnect", "LIFECYCLE_DEP")],
    )

    assert not dag.hard_edges
    assert any(item.kind == "SOFT_ORDER" and item.scope == ["connect", "disconnect"] for item in dag.soft_constraints)


def test_template_pair_key_without_scope_tokens_demotes_to_soft_order() -> None:
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
                title="host paired template",
                category="lifecycle",
                hard_edge_templates=[
                    {
                        "src": "coord_refresh",
                        "dst": "state_write",
                        "kind": "HARD_LIFECYCLE",
                        "params": {"pair_key": "host"},
                    }
                ],
                evidence_ids=["DOC_x"],
            )
        ],
    )
    mssu_refresh = MSSU(mssu_id="r", mssu_type="SYNC", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"coord_refresh"})
    mssu_write = MSSU(mssu_id="w", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n2"], side_effect_sig={"state_write"})

    dag, diagnostics = TypedDAGBuilder(profile).build([mssu_refresh, mssu_write], dependency_candidates=[])

    assert not dag.hard_edges
    assert any(constraint.kind == "SOFT_ORDER" and constraint.scope == ["r", "w"] for constraint in dag.soft_constraints)
    assert diagnostics.warnings


def test_template_guard_and_fallback_override_rule_defaults() -> None:
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
                title="cloud pacing",
                category="protocol",
                guard="rule_guard",
                fallback="rule_fallback",
                soft_constraint_templates=[
                    {
                        "kind": "BACKOFF_WINDOW",
                        "scope": ["CLOUD_OP"],
                        "guard": "tpl_guard",
                        "fallback": "tpl_fallback",
                    }
                ],
                evidence_ids=["DOC_x"],
            )
        ],
    )
    mssu_cloud = MSSU(mssu_id="cloud", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"cloud_http_call"})

    dag, _ = TypedDAGBuilder(profile).build([mssu_cloud], dependency_candidates=[])
    constraint = next(item for item in dag.soft_constraints if item.kind == "BACKOFF_WINDOW")
    assert constraint.guard == "tpl_guard"
    assert constraint.fallback == "tpl_fallback"


def test_explicit_soft_constraint_scope_without_match_is_not_widened_to_critical_graph() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_local",
                title="local api budget",
                category="protocol",
                marker_hints=["LOCAL_API_READ"],
                soft_constraint_templates=[
                    {
                        "kind": "SAME_SESSION_GROUP",
                        "scope": ["LOCAL_API_READ"],
                        "params": {"group_key": "endpoint"},
                    }
                ],
                evidence_ids=["CODE_local"],
            )
        ],
    )
    mssu_cloud = MSSU(
        mssu_id="cloud",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"cloud_http_call"},
        critical=True,
    )
    mssu_write = MSSU(
        mssu_id="write",
        mssu_type="UPDATE",
        phase="RUNTIME",
        node_ids=["n2"],
        side_effect_sig={"state_write"},
        critical=True,
    )

    dag, _ = TypedDAGBuilder(profile).build([mssu_cloud, mssu_write], dependency_candidates=[])

    assert not any(item.kind == "SAME_SESSION_GROUP" for item in dag.soft_constraints)


def test_explicit_soft_constraint_scope_still_binds_matching_mssus() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_local",
                title="local api budget",
                category="protocol",
                marker_hints=["LOCAL_API_READ"],
                soft_constraint_templates=[
                    {
                        "kind": "SAME_SESSION_GROUP",
                        "scope": ["LOCAL_API_READ"],
                        "params": {"group_key": "endpoint"},
                    }
                ],
                evidence_ids=["CODE_local"],
            )
        ],
    )
    mssu_local = MSSU(
        mssu_id="local",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"local_api_read"},
        critical=True,
    )
    mssu_cloud = MSSU(
        mssu_id="cloud",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n2"],
        side_effect_sig={"cloud_http_call"},
        critical=True,
    )

    dag, _ = TypedDAGBuilder(profile).build([mssu_local, mssu_cloud], dependency_candidates=[])
    constraint = next(item for item in dag.soft_constraints if item.kind == "SAME_SESSION_GROUP")
    assert constraint.scope == ["local"]


def test_max_concurrency_budget_scope_is_filtered_by_resource() -> None:
    mssu_ble = MSSU(mssu_id="ble", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"ble_gatt_op"}, critical=True)
    mssu_cloud = MSSU(mssu_id="cloud", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], side_effect_sig={"cloud_http_call"}, critical=True)
    mssu_ha = MSSU(mssu_id="ha", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n3"], side_effect_sig={"state_write"}, critical=True)

    target = OptimizationTarget(
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        constraints={"optimization_knobs": {"max_concurrency": {"ble": 1, "cloud": 2, "ha": 1}}},
    )

    dag, _ = TypedDAGBuilder(_profile()).build([mssu_ble, mssu_cloud, mssu_ha], dependency_candidates=[], optimization_target=target)
    budget_constraints = [item for item in dag.soft_constraints if item.kind == "BUDGET_K"]
    ble_budget = next(item for item in budget_constraints if item.params.get("resource") == "BLE")
    cloud_budget = next(item for item in budget_constraints if item.params.get("resource") == "CLOUD")
    ha_budget = next(item for item in budget_constraints if item.params.get("resource") == "HA")

    assert ble_budget.scope == ["ble"]
    assert cloud_budget.scope == ["cloud"]
    assert ha_budget.scope == ["ha"]


def test_cross_action_io_data_edge_is_filtered_by_lane_and_resource() -> None:
    mssu_ble = MSSU(
        mssu_id="ble_prepare",
        mssu_type="PREPARE",
        phase="RUNTIME",
        node_ids=["n1"],
        outputs={"manager"},
        primary_action_ref="A1",
        action_refs=["A1"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:device:one",
    )
    mssu_cloud = MSSU(
        mssu_id="cloud_act",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n2"],
        inputs={"manager"},
        primary_action_ref="A2",
        action_refs=["A2"],
        lane_tag="CLOUD",
        resource_instance_tag="tuya:device:one",
    )

    dag, _ = TypedDAGBuilder(_profile()).build([mssu_ble, mssu_cloud], dependency_candidates=[])
    assert not any(edge.kind == "HARD_DATA" for edge in dag.hard_edges)


def test_same_action_generic_io_data_edge_is_filtered() -> None:
    mssu_a = MSSU(
        mssu_id="setup",
        mssu_type="INIT",
        phase="SETUP",
        node_ids=["n1"],
        outputs={"entry"},
        primary_action_ref="A1",
        action_refs=["A1"],
    )
    mssu_b = MSSU(
        mssu_id="use_entry",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n2"],
        inputs={"entry"},
        primary_action_ref="A1",
        action_refs=["A1"],
    )

    dag, _ = TypedDAGBuilder(_profile()).build([mssu_a, mssu_b], dependency_candidates=[])
    assert not any(edge.kind == "HARD_DATA" for edge in dag.hard_edges)


def test_candidate_lifecycle_dep_with_non_allowlisted_pair_is_softened() -> None:
    mssu_sub = MSSU(
        mssu_id="sub",
        mssu_type="PREPARE",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"subscribe"},
        primary_action_ref="A1",
        action_refs=["A1"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:relay",
    )
    mssu_init = MSSU(
        mssu_id="init",
        mssu_type="INIT",
        phase="SETUP",
        node_ids=["n2"],
        side_effect_sig={"entry_setup"},
    )

    dag, _ = TypedDAGBuilder(_profile()).build([mssu_sub, mssu_init], dependency_candidates=[("sub", "init", "LIFECYCLE_DEP")])
    assert not dag.hard_edges
    assert any(item.kind == "SOFT_ORDER" and item.scope == ["sub", "init"] for item in dag.soft_constraints)


def test_template_hard_edge_is_softened_when_cross_action_scope_mismatches() -> None:
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
                title="subscribe pair",
                category="lifecycle",
                hard_edge_templates=[{"src": "subscribe", "dst": "unsubscribe", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["DOC_x"],
            )
        ],
    )
    mssu_sub = MSSU(
        mssu_id="sub",
        mssu_type="PREPARE",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"subscribe"},
        primary_action_ref="A_SUB",
        action_refs=["A_SUB"],
        lane_tag="BLE_LOCAL",
        resource_instance_tag="ble:relay",
        is_shared_infra=True,
    )
    mssu_unsub = MSSU(
        mssu_id="unsub",
        mssu_type="CLEANUP",
        phase="TEARDOWN",
        node_ids=["n2"],
        side_effect_sig={"unsubscribe"},
        primary_action_ref="A_OTHER",
        action_refs=["A_OTHER"],
        lane_tag="CLOUD",
        resource_instance_tag="tuya:light",
        is_shared_infra=True,
    )

    dag, _ = TypedDAGBuilder(profile).build([mssu_sub, mssu_unsub], dependency_candidates=[])
    assert not dag.hard_edges
    assert any(
        item.kind == "SOFT_ORDER" and item.scope == ["sub", "unsub"]
        for item in dag.soft_constraints
    )


def test_unsubscribe_template_requires_cleanup_or_prepare_source_with_unsubscribe_token() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_unsub_unload",
                title="unsubscribe before unload",
                category="lifecycle",
                hard_edge_templates=[{"src": "UNSUBSCRIBE", "dst": "ENTRY_UNLOAD", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["DOC_x"],
            )
        ],
    )
    mssu_src = MSSU(
        mssu_id="src_init",
        mssu_type="INIT",
        phase="SETUP",
        node_ids=["n1"],
        side_effect_sig={"unsubscribe"},
        primary_action_ref="A1",
        action_refs=["A1"],
    )
    mssu_dst = MSSU(
        mssu_id="dst_unload",
        mssu_type="CLEANUP",
        phase="TEARDOWN",
        node_ids=["n2"],
        side_effect_sig={"entry_unload"},
        primary_action_ref="A1",
        action_refs=["A1"],
    )

    dag, _ = TypedDAGBuilder(profile).build([mssu_src, mssu_dst], dependency_candidates=[])
    assert not dag.hard_edges
    assert any(item.kind == "SOFT_ORDER" and item.scope == ["src_init", "dst_unload"] for item in dag.soft_constraints)


def test_entry_setup_to_entry_unload_cross_action_template_is_never_hard() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=DEFAULT_MARKER_DETECTORS,
        lifecycle_templates=DEFAULT_LIFECYCLE_TEMPLATES,
        rules=[
            Rule(
                rule_id="r_entry_pair",
                title="entry setup before unload",
                category="lifecycle",
                hard_edge_templates=[{"src": "ENTRY_SETUP", "dst": "ENTRY_UNLOAD", "kind": "HARD_LIFECYCLE"}],
                evidence_ids=["DOC_x"],
            )
        ],
    )
    mssu_setup = MSSU(
        mssu_id="setup_a1",
        mssu_type="INIT",
        phase="SETUP",
        node_ids=["n1"],
        side_effect_sig={"entry_setup"},
        primary_action_ref="A1",
        action_refs=["A1"],
    )
    mssu_unload = MSSU(
        mssu_id="unload_a2",
        mssu_type="CLEANUP",
        phase="TEARDOWN",
        node_ids=["n2"],
        side_effect_sig={"entry_unload"},
        primary_action_ref="A2",
        action_refs=["A2"],
    )

    dag, _ = TypedDAGBuilder(profile).build([mssu_setup, mssu_unload], dependency_candidates=[])
    assert not dag.hard_edges
    assert any(item.kind == "SOFT_ORDER" and item.scope == ["setup_a1", "unload_a2"] for item in dag.soft_constraints)


def test_effective_action_refs_preserve_generalized_cluster_scope_for_nonshared_mssu() -> None:
    mssu = MSSU(
        mssu_id="cluster_read",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n1"],
        primary_action_ref="A7",
        secondary_action_refs=["A8"],
        action_refs=["A7", "A8"],
        side_effect_sig={"cloud_http_call"},
    )

    assert TypedDAGBuilder._effective_action_refs(mssu) == ["A7", "A8"]


def test_representative_mssus_include_generalized_cluster_bound_mssu_for_secondary_action() -> None:
    builder = TypedDAGBuilder(_profile())
    nodes = {
        "cluster_read": MSSU(
            mssu_id="cluster_read",
            mssu_type="ACT",
            phase="RUNTIME",
            node_ids=["n1"],
            primary_action_ref="A7",
            secondary_action_refs=["A8"],
            action_refs=["A7", "A8"],
            side_effect_sig={"cloud_http_call"},
        )
    }
    action_index = {
        "A7": {"action_id": "A7", "protocol": "CLOUD", "target": {"endpoint": "https://api.demo.local/climate.a"}},
        "A8": {"action_id": "A8", "protocol": "CLOUD", "target": {"endpoint": "https://api.demo.local/climate.b"}},
    }

    assert builder._representative_mssus_for_action("A8", nodes, action_index) == ["cluster_read"]
