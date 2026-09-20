from __future__ import annotations

import json
from pathlib import Path

from dsl.contracts import (
    DEFAULT_LIFECYCLE_TEMPLATES,
    DEFAULT_MARKER_DETECTORS,
    HAPProfile,
    MSSU,
    OptimizationTarget,
    PROFILE_SCHEMA_VERSION,
    Rule,
    SoftConstraint,
    TypedDAG,
    now_utc_iso,
)
from optimizer.m1_markers import detect_markers
from optimizer.m5_scheduler import CrossProtocolScheduler


GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


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


def _target() -> OptimizationTarget:
    return OptimizationTarget(
        meta={"vdev_id": "sched_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
            },
            {
                "action_id": "A2",
                "protocol": "HA",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
            },
        ],
        target_anchors={},
        entrypoint={},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2"],
    )


def test_golden_m1_alias_summary(tmp_path: Path) -> None:
    source = tmp_path / "integration_alias.py"
    source.write_text(
        """
from homeassistant.helpers.dispatcher import dispatcher_connect as dc

async def async_setup_entry(hass, entry):
    state_writer = entity.async_write_ha_state
    dc(hass, "sig", state_writer)
    state_writer()
    return True
""",
        encoding="utf-8",
    )
    marker_set = detect_markers(source, _profile())
    summary = {
        "kinds": sorted({marker.marker_type for marker in marker_set.markers}),
        "direct": marker_set.diagnostics["match_counts"]["direct"],
        "alias": marker_set.diagnostics["match_counts"]["alias"],
    }
    golden = json.loads((GOLDEN_DIR / "m1_alias_summary.json").read_text(encoding="utf-8"))
    assert summary == golden


def test_golden_m5_plan_summary() -> None:
    mssu_a = MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"])
    mssu_b = MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"])
    dag = TypedDAG(
        nodes={"m1": mssu_a, "m2": mssu_b},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(kind="MIN_GAP", scope=["m1", "m2"], fallback="preserve_action_order"),
            SoftConstraint(kind="MIN_GAP", scope=["m1", "m2"], fallback="reduce_parallelism"),
        ],
        resources={},
    )
    plan = CrossProtocolScheduler().schedule(dag, optimization_target=_target())
    summary = {
        "batches": [
            [str(action_id) for group in batch.parallel_groups for action_id in group]
            for batch in plan.ordered_batches
        ],
        "fallback": plan.ordered_batches[0].fallback if plan.ordered_batches else [],
        "cycle_resolution_count": len(plan.meta.get("cycle_resolution", [])),
    }
    golden = json.loads((GOLDEN_DIR / "m5_plan_summary.json").read_text(encoding="utf-8"))
    assert summary == golden
