from pathlib import Path

from dsl.contracts import CodeEvidence, HAPProfile, MSSU, PROFILE_SCHEMA_VERSION, Rule, SoftConstraint, TypedDAG, now_utc_iso
from optimizer.m4_typed_dag import TypedDAGBuilder
from optimizer.m5_scheduler import CrossProtocolScheduler
from profile_builder.evidence import EvidenceBank, extract_code_evidence
from profile_builder.llm_norm import normalize_rules


def test_protocol_evidence_patterns_extracted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "integration.py"
    source.write_text(
        """
import aiohttp
from bleak import BleakClient
import asyncio

async def run(client, session, resp):
    await client.connect()
    await client.read_gatt_char("abc")
    if resp.status == 429:
        raise RuntimeError("429")
    try:
        await session.request("GET", "https://api.example.com/dev")
    except Exception:
        await asyncio.sleep(0.2)
""",
        encoding="utf-8",
    )

    evidence = extract_code_evidence(repo)
    patterns = {item.pattern for item in evidence}
    assert "BLE_CONNECT" in patterns
    assert "BLE_GATT_OP" in patterns
    assert "CLOUD_HTTP_CALL" in patterns
    assert "CLOUD_429_CHECK" in patterns
    assert "CLOUD_BACKOFF_SLEEP" in patterns


def test_protocol_evidence_generic_connect_without_context_is_not_ble(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "integration.py"
    source.write_text(
        """
async def run(client, foo):
    await client.connect()
    await foo.get("/local")
""",
        encoding="utf-8",
    )

    evidence = extract_code_evidence(repo)
    patterns = {item.pattern for item in evidence}
    assert "BLE_CONNECT" not in patterns
    assert "BLE_GATT_OP" not in patterns
    assert "CLOUD_HTTP_CALL" not in patterns


def test_protocol_rules_synthesized_as_soft() -> None:
    bank = EvidenceBank(
        docs=[],
        code=[
            CodeEvidence("c1", "a.py", "BLE_CONNECT", 10, 2),
            CodeEvidence("c2", "a.py", "BLE_GATT_OP", 11, 2),
            CodeEvidence("c3", "a.py", "BLE_DISCONNECT", 12, 1),
            CodeEvidence("c4", "a.py", "CLOUD_HTTP_CALL", 20, 3),
            CodeEvidence("c5", "a.py", "CLOUD_429_CHECK", 21, 1),
            CodeEvidence("c6", "a.py", "CLOUD_TOKEN_REFRESH", 22, 1),
        ],
    )
    rules = normalize_rules(bank, packs=[])
    protocol_rule_ids = {rule.rule_id for rule in rules if rule.category == "protocol"}
    assert "rule_protocol_ble_budget_overlap" in protocol_rule_ids
    assert "rule_protocol_cloud_budget_rate" in protocol_rule_ids
    assert all(rule.status == "SOFT" for rule in rules if rule.category == "protocol")


def test_protocol_rule_evidence_selection_covers_multiple_patterns() -> None:
    bank = EvidenceBank(
        docs=[],
        code=[
            CodeEvidence("e1", "a.py", "BLE_CONNECT", 10, 5),
            CodeEvidence("e2", "a.py", "BLE_GATT_OP", 11, 4),
            CodeEvidence("e3", "a.py", "BLE_DISCONNECT", 12, 3),
            CodeEvidence("e4", "a.py", "BLE_RETRY_OR_TIMEOUT", 13, 2),
            CodeEvidence("e5", "a.py", "CLOUD_HTTP_CALL", 20, 5),
        ],
    )
    rules = normalize_rules(bank, packs=[])
    by_id = {row.evidence_id: row.pattern for row in bank.code}
    ble_rule = next(rule for rule in rules if rule.rule_id == "rule_protocol_ble_budget_overlap")
    covered = {by_id[eid] for eid in ble_rule.evidence_ids}
    assert {"BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT", "BLE_RETRY_OR_TIMEOUT"} <= covered


def test_m4_has_no_builtin_protocol_heuristics() -> None:
    profile = HAPProfile(
        profile_id="p",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=[],
        rules=[Rule(rule_id="r1", title="t", category="lifecycle", evidence_ids=["DOC_x"])],
    )
    mssu_ble = MSSU(mssu_id="ble", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], side_effect_sig={"ble_op"})
    mssu_cloud = MSSU(mssu_id="cloud", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], side_effect_sig={"cloud_op"})
    dag, _ = TypedDAGBuilder(profile).build([mssu_ble, mssu_cloud], dependency_candidates=[])

    kinds = {constraint.kind for constraint in dag.soft_constraints}
    assert "NO_OVERLAP" not in kinds
    assert "BACKOFF_WINDOW" not in kinds


def test_m5_budget_constraint_changes_batching_behavior() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BUDGET_K",
                scope=["m1", "m2"],
                params={"resource": "CLOUD_PARALLEL", "limit": 1},
                guard="true",
                fallback="reduce_parallelism",
            )
        ],
        resources={},
    )
    target = {
        "meta": {"vdev_id": "sched"},
        "source_scope": {"files": ["/tmp/fake.py"]},
        "vdev_actions": [
            {"action_id": "A1", "protocol": "CLOUD", "exec": {"kind": "ha_service_call", "domain": "d", "service": "s"}, "critical": True},
            {"action_id": "A2", "protocol": "CLOUD", "exec": {"kind": "ha_service_call", "domain": "d", "service": "s"}, "critical": True},
        ],
        "target_anchors": {},
        "entrypoint": {},
        "objectives": {},
        "constraints": {},
        "validation": {},
        "hard_dependencies": [],
        "soft_dependencies": [],
        "critical_action_ids": [],
    }

    from dsl.contracts import OptimizationTarget

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=OptimizationTarget(**target))
    assert len(plan.ordered_batches) == 2
