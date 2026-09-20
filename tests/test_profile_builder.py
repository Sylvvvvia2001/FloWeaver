from pathlib import Path
import json

from dsl.contracts import CodeEvidence, DocEvidence, TestEvidence as TestEvidenceContract
from dsl.contracts import Rule, RuleStatus
from profile_builder.cluster import ClusterPack, cluster_evidence
from profile_builder.evidence import EvidenceBank, build_evidence_bank, extract_test_evidence
from profile_builder.evidence_policy import select_semantic_evidence_bank
from profile_builder.hardening import auto_harden_rules
from profile_builder.llm_norm import normalize_rules
from profile_builder.pipeline import HAPProfileBuilder


def test_profile_builder_cold_start_keeps_rules_soft(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text("The integration must complete setup and should clean up listeners on unload.", encoding="utf-8")
    (repo / "demo.py").write_text(
        "async def async_setup_entry(hass, entry):\n    await coordinator.async_config_entry_first_refresh()\n    return True\n",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out).run(profile_id="p")
    assert artifacts.profile.rules
    assert all(rule.status == "SOFT" for rule in artifacts.profile.rules)

    decisions = (out / "hardening_decisions.json").read_text(encoding="utf-8")
    assert "cold_start_no_validation_stats" in decisions


def test_test_evidence_is_collected_as_separate_category(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_demo.py").write_text(
        """
import pytest

async def test_flow(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)

async def test_not_ready():
    with pytest.raises(ConfigEntryNotReady):
        raise ConfigEntryNotReady
""",
        encoding="utf-8",
    )

    evidence = extract_test_evidence(tests_root)
    assert evidence
    assert all(isinstance(item, TestEvidenceContract) for item in evidence)
    patterns = {item.pattern for item in evidence}
    assert "TEST_ENTRY_SETUP" in patterns
    assert "TEST_CONFIG_ENTRY_NOT_READY" in patterns


def test_test_evidence_extracts_cloud_patterns(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_cloud.py").write_text(
        """
import asyncio

async def test_cloud_flow(session):
    assert 429 == 429
    await asyncio.sleep(0.2)
    session.batch_update()
    session.assert_called_once_with("reuse")
""",
        encoding="utf-8",
    )

    evidence = extract_test_evidence(tests_root)
    patterns = {item.pattern for item in evidence}
    assert "TEST_RATE_LIMIT" in patterns
    assert "TEST_BACKOFF_SLEEP" in patterns
    assert "TEST_BATCH_CALL" in patterns
    assert "TEST_NO_REDUNDANT_CALL" in patterns


def test_test_evidence_keeps_setup_and_state_write_as_test_level_anchors(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_demo.py").write_text(
        """
async def test_flow(hass, entry, entity):
    assert await hass.config_entries.async_setup(entry.entry_id)
    entity.async_write_ha_state()
""",
        encoding="utf-8",
    )

    evidence = extract_test_evidence(tests_root)
    typed = {item.typed_anchor for item in evidence}
    assert "TEST_ENTRY_SETUP" in typed
    assert "TEST_STATE_WRITE" in typed
    assert "ENTRY_SETUP" not in typed
    assert "STATE_WRITE" not in typed


def test_build_evidence_bank_records_tests_separately(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    tests_root = tmp_path / "tests"
    out = tmp_path / "evidence_bank.json"
    docs.mkdir()
    repo.mkdir()
    tests_root.mkdir()

    (docs / "guide.md").write_text("The integration must set up the config entry before updates begin.", encoding="utf-8")
    (repo / "demo.py").write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")
    (tests_root / "test_demo.py").write_text(
        "async def test_flow(hass, entry):\n    assert await hass.config_entries.async_remove(entry.entry_id)\n",
        encoding="utf-8",
    )

    bank = build_evidence_bank(docs, repo, tests_root=tests_root, output_path=out)

    assert bank.docs
    assert bank.code
    assert bank.tests
    payload = out.read_text(encoding="utf-8")
    assert "\"tests\"" in payload
    assert any(item.pattern == "TEST_ENTRY_UNLOAD" for item in bank.tests)


def test_doc_evidence_filters_out_code_blocks_tables_and_comment_style_lines(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        """
# Entity

| attr | type | required |
| --- | --- | --- |
| name | str | required |

```python
# Grab active context variables required to be fetched from API
```

Entities must unsubscribe on unload.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(docs, tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].text == "Entities must unsubscribe on unload."
    assert bank.docs[0].section_title == "Entity"
    assert bank.docs[0].doc_kind == "LIFECYCLE_SENTENCE"
    assert bank.docs[0].normative_strength == "MUST"


def test_doc_evidence_fuses_same_section_and_typed_anchor(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        """
# Config Entry

The config entry must complete setup before coordinator refresh.
The config entry should complete setup before coordinator refresh.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(docs, tmp_path / "repo")
    assert len(bank.docs) == 1
    doc = bank.docs[0]
    assert doc.normative_strength == "MUST"
    assert doc.typed_anchor == "DOC_ENTRY_SETUP_POLICY"
    assert "typed_anchor:DOC_ENTRY_SETUP_POLICY" in doc.normalization_flags
    assert "runtime_hypothesis:ENTRY_SETUP" in doc.normalization_flags
    assert "candidate_fused:2" in doc.normalization_flags


def test_doc_evidence_demotes_state_update_guidance_to_policy_anchor(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "entity.md").write_text(
        """
# Entity

Entity properties should only return information from memory and updates should be handled inside async_update().
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(docs, tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor == "DOC_STATE_UPDATE_POLICY"
    assert bank.docs[0].semantic_level == "POLICY"
    assert "runtime_hypothesis:STATE_WRITE" in bank.docs[0].normalization_flags


def test_doc_evidence_demotes_ble_connection_guidance_to_policy_anchor(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "bluetooth"
    docs.mkdir(parents=True)
    (docs / "bluetooth.md").write_text(
        """
# Bluetooth

Bluetooth integrations with some devices need a connection to be established and should use a connection timeout to avoid hanging forever.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor == "DOC_BLE_CONNECTION_POLICY"
    assert bank.docs[0].semantic_level == "POLICY"
    assert "runtime_hypothesis:BLE_CONNECT" in bank.docs[0].normalization_flags


def test_doc_evidence_does_not_misclassify_bluetooth_api_text_as_cloud_http_call(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "bluetooth"
    docs.mkdir(parents=True)
    (docs / "api.md").write_text(
        """
# Bluetooth API

Integrations that need an instance of a BleakScanner should call the bluetooth.async_get_scanner API. This API returns a wrapper around a single BleakScanner that allows integrations to share without overloading the system.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    flags = set(bank.docs[0].normalization_flags)
    assert "typed_anchor:CLOUD_HTTP_CALL" not in flags
    assert "typed_anchor:DOC_SHARED_RESOURCE" in flags


def test_doc_evidence_still_classifies_cloud_backoff_guidance_as_cloud_anchor(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "integration_runtime"
    docs.mkdir(parents=True)
    (docs / "docs-data-update.md").write_text(
        """
# Runtime Data

Cloud integrations should back off after 429 responses before issuing another HTTP request.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor == "DOC_RETRY_BACKOFF_POLICY"


def test_doc_evidence_manifest_branding_sentence_is_not_misclassified_as_cloud_call(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "quality_ops"
    docs.mkdir(parents=True)
    (docs / "creating_integration_manifest.md").write_text(
        """
# Virtual integration

The logo for the domain of this virtual integration must be added to our brands repository.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    flags = set(bank.docs[0].normalization_flags)
    assert "typed_anchor:CLOUD_HTTP_CALL" not in flags
    assert "typed_anchor:DOC_MANIFEST_META" in flags


def test_doc_evidence_manifest_metadata_path_blocks_protocol_runtime_anchor(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "quality_ops"
    docs.mkdir(parents=True)
    (docs / "creating_integration_manifest.md").write_text(
        """
# Manifest

The integration should include website and documentation fields that point to the public API documentation.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor == "DOC_MANIFEST_META"
    assert "typed_anchor:CLOUD_HTTP_CALL" not in set(bank.docs[0].normalization_flags)


def test_doc_evidence_availability_policy_is_framework_specificity(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "entities_devices"
    docs.mkdir(parents=True)
    (docs / "entity-unavailable.md").write_text(
        """
# Entity unavailable

An entity should become unavailable or remain in standby when the secondary control channel is not responsive.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor == "DOC_AVAILABILITY_POLICY"
    assert bank.docs[0].specificity == "FRAMEWORK"


def test_doc_evidence_system_health_policy_is_framework_specificity(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "quality_ops"
    docs.mkdir(parents=True)
    (docs / "integration_system_health.md").write_text(
        """
# System health

The update callback should be a coroutine so the frontend can refresh after the callback completes.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].specificity == "FRAMEWORK"


def test_doc_evidence_classifies_unique_id_guidance_more_specifically(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "config_entries"
    docs.mkdir(parents=True)
    (docs / "config_entries.md").write_text(
        """
# Unique IDs

A unique ID is used to match a config entry to the underlying device or API. The unique ID must be stable and should not be changed by the user.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor == "DOC_UNIQUE_ID_POLICY"


def test_doc_evidence_classifies_shared_ble_resource_guidance_more_specifically(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "bluetooth"
    docs.mkdir(parents=True)
    (docs / "api.md").write_text(
        """
# Fetch the shared BleakScanner instance

Integrations that need an instance of a BleakScanner should call the bluetooth.async_get_scanner API. This API returns a wrapper around a single BleakScanner that allows integrations to share without overloading the system.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor == "DOC_SHARED_RESOURCE"


def test_doc_evidence_does_not_treat_connection_data_as_ble_connect(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "config_entries"
    docs.mkdir(parents=True)
    (docs / "config_flow_handler.md").write_text(
        """
# Reconfigure

All user input is saved in the options dictionary. Therefore it's not suitable to use in integrations which use connection data, API keys, or other information that should be stored in config entry data.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor != "BLE_CONNECT"


def test_doc_evidence_does_not_treat_callback_as_cloud_http_call(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "quality_ops"
    docs.mkdir(parents=True)
    (docs / "integration_system_health.md").write_text(
        """
# System health

The info callback should return a dictionary whose values can be coroutines. The frontend updates once the coroutine finishes and provides a result.
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    assert len(bank.docs) == 1
    assert bank.docs[0].typed_anchor != "CLOUD_HTTP_CALL"


def test_code_evidence_fuses_same_pattern_bucket_and_accumulates_frequency(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "cloud.py").write_text(
        """
async def update(response):
    if response.status == 429:
        raise TooManyRequests
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", repo)
    cloud_429 = [item for item in bank.code if item.pattern == "CLOUD_429_CHECK"]
    assert len(cloud_429) == 1
    assert cloud_429[0].frequency >= 2
    assert cloud_429[0].typed_anchor == "CLOUD_429_CHECK"
    assert "typed_anchor:CLOUD_429_CHECK" in cloud_429[0].normalization_flags


def test_code_evidence_ids_are_unique_per_final_evidence_entity(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "entity.py").write_text(
        """
class Demo:
    def a(self):
        self.async_write_ha_state()

    def b(self):
        self.async_write_ha_state()
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", repo)
    state_rows = [item for item in bank.code if item.pattern == "STATE_WRITE"]
    assert len(state_rows) == 2
    assert len({item.evidence_id for item in state_rows}) == 2


def test_test_evidence_downgrades_generic_mock_client_assertions_from_session_reuse(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_client_calls.py").write_text(
        """
async def test_client_event_is_suppressed(mock_client):
    mock_client.send_voice_assistant_event.assert_not_called()
""",
        encoding="utf-8",
    )

    evidence = extract_test_evidence(tests_root)
    patterns = {item.pattern for item in evidence}
    assert "TEST_SESSION_REUSE" not in patterns
    assert "TEST_CALL_SUPPRESSION" in patterns
    assert {item.typed_anchor for item in evidence} == {"TEST_CALL_SUPPRESSION"}


def test_test_evidence_upgrades_connect_disconnect_and_config_calls(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_client_ops.py").write_text(
        """
async def test_client_ops(mock_client):
    mock_client.connect.assert_called_once()
    mock_client.disconnect.assert_called_once()
    mock_client.set_voice_assistant_configuration.assert_called_once_with("x")
""",
        encoding="utf-8",
    )

    evidence = extract_test_evidence(tests_root)
    pattern_set = {item.pattern for item in evidence}
    typed_anchors = {item.typed_anchor for item in evidence}
    assert "TEST_CLIENT_CONNECT" in pattern_set
    assert "TEST_CLIENT_DISCONNECT" in pattern_set
    assert "TEST_CLIENT_CONFIG_UPDATE" in pattern_set
    assert {"TEST_EXPECTED_SINGLE_CALL"} <= typed_anchors


def test_test_evidence_uses_expected_client_idle_for_explicit_session_not_called(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_session_idle.py").write_text(
        """
async def test_session_idle(session):
    session.request.assert_not_called()
""",
        encoding="utf-8",
    )

    evidence = extract_test_evidence(tests_root)
    patterns = {item.pattern for item in evidence}
    anchors = {item.typed_anchor for item in evidence}
    assert "TEST_EXPECTED_CLIENT_IDLE" in patterns
    assert "TEST_EXPECTED_CLIENT_IDLE" in anchors
    assert evidence[0].protocol_hypothesis == "CLOUD_SESSION_REUSE"
    assert "protocol_hypothesis:CLOUD_SESSION_REUSE" in evidence[0].normalization_flags


def test_code_evidence_records_signal_strength(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "cloud.py").write_text(
        """
import aiohttp

async def run(session, response):
    await session.request("GET", "https://api.example.com")
    if response.status == 429:
        raise RuntimeError("429")

MANAGER = "manager"
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", repo)
    by_pattern = {item.pattern: item for item in bank.code}
    assert by_pattern["CLOUD_HTTP_CALL"].signal_strength == "CALL_CHAIN_STRONG"
    assert by_pattern["CLOUD_429_CHECK"].signal_strength == "AST_STRONG"


def test_code_evidence_uses_manifest_iot_class_to_split_local_and_cloud_api(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    local = repo / "local_demo"
    cloud = repo / "cloud_demo"
    local.mkdir(parents=True)
    cloud.mkdir(parents=True)
    (local / "manifest.json").write_text(json.dumps({"iot_class": "local_polling"}), encoding="utf-8")
    (cloud / "manifest.json").write_text(json.dumps({"iot_class": "cloud_polling"}), encoding="utf-8")
    source = """
import aiohttp

async def _async_update_data(session):
    return await session.request("GET", "/status")
"""
    (local / "sensor.py").write_text(source, encoding="utf-8")
    (cloud / "sensor.py").write_text(source, encoding="utf-8")

    bank = build_evidence_bank(tmp_path / "docs", repo)
    by_file = {}
    for item in bank.code:
        by_file.setdefault(Path(item.source_path).parts[-2], set()).add(item.pattern)

    assert "LOCAL_API_READ" in by_file["local_demo"]
    assert "CLOUD_HTTP_CALL" not in by_file["local_demo"]
    assert "CLOUD_HTTP_CALL" in by_file["cloud_demo"]


def test_code_evidence_downgrades_text_only_protocol_anchor_confidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "cloud_text.py").write_text(
        """
def explain():
    details = "persistent session manager closes idle session and batch requests are grouped"
    return details
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", repo)
    sessionish = [item for item in bank.code if item.pattern in {"CLOUD_BATCH_CALL", "CLOUD_SESSION_CLOSE"}]
    assert sessionish
    assert all(item.signal_strength == "TEXT_WEAK" for item in sessionish)
    assert all(item.confidence <= 0.55 for item in sessionish)
    assert any("protocol_anchor_downgraded:text_only" in item.normalization_flags for item in sessionish)
    assert any(item.effective_typed_anchor in {"CLOUD_BATCH_HINT", "CLOUD_SESSION_HINT"} for item in sessionish)


def test_code_evidence_downgrades_assignment_plus_text_protocol_anchor_confidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "cloud_assign.py").write_text(
        """
import aiohttp

class Demo:
    def __init__(self):
        self.manager = aiohttp.ClientSession()
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", repo)
    store_rows = [item for item in bank.code if item.pattern == "CLOUD_SESSION_STORE"]
    assert store_rows
    assert any(item.confidence <= 0.62 for item in store_rows)
    assert any("protocol_anchor_downgraded:assignment_plus_text" in item.normalization_flags for item in store_rows)
    assert any(item.effective_typed_anchor == "CLOUD_SESSION_HINT" for item in store_rows)


def test_code_evidence_downgrades_text_only_backoff_protocol_anchor_to_hint(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "text_protocols.py").write_text(
        """
def explain():
    notes = "429 responses should trigger backoff retry_after delay with jitter"
    return notes
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", repo)
    rows = {(item.pattern, item.effective_typed_anchor, item.semantic_level) for item in bank.code}
    assert ("CLOUD_BACKOFF_SLEEP", "CLOUD_BACKOFF_HINT", "HINT") in rows


def test_code_evidence_does_not_emit_cloud_hints_for_non_cloud_bluetooth_text(tmp_path: Path) -> None:
    repo = tmp_path / "repo" / "bluetooth"
    repo.mkdir(parents=True)
    (repo / "__init__.py").write_text(
        """
class BluetoothManager:
    def __init__(self):
        self.manager = "device manager listener"
        self.notes = "use backoff jitter when reconnecting bluetooth devices"
""",
        encoding="utf-8",
    )

    bank = build_evidence_bank(tmp_path / "docs", tmp_path / "repo")
    cloudish = [
        item
        for item in bank.code
        if item.pattern in {"CLOUD_SESSION_STORE", "CLOUD_SESSION_CLOSE", "CLOUD_BACKOFF_SLEEP", "CLOUD_HTTP_CALL"}
        or item.effective_typed_anchor in {"CLOUD_SESSION_HINT", "CLOUD_BACKOFF_HINT", "CLOUD_API_HINT"}
    ]
    assert cloudish == []


def test_evidence_bank_by_id_exposes_typed_anchor() -> None:
    bank = EvidenceBank(
        docs=[DocEvidence("DOC_1", "docs/a.md", 1, "MUST", "Entry setup must run first", typed_anchor="ENTRY_SETUP", semantic_level="POLICY", semantic_anchor="ENTRY_SETUP")],
        code=[CodeEvidence("CODE_1", "repo/a.py", "STATE_WRITE", 20, 1, typed_anchor="STATE_WRITE", effective_typed_anchor="STATE_WRITE", semantic_level="RUNTIME", semantic_anchor="STATE_WRITE")],
        tests=[TestEvidenceContract("TEST_1", "tests/test_a.py", "TEST_BATCH_CALL", "test_batch", 12, "assert", frequency=1, typed_anchor="TEST_BATCH_CALL", protocol_hypothesis="CLOUD_BATCH_CALL", semantic_level="BEHAVIOR", semantic_anchor="TEST_BATCH_CALL", behavior_category="BATCH_BEHAVIOR")],
    )

    rows = bank.by_id()
    assert rows["DOC_1"]["typed_anchor"] == "ENTRY_SETUP"
    assert rows["DOC_1"]["semantic_level"] == "POLICY"
    assert rows["DOC_1"]["semantic_anchor"] == "ENTRY_SETUP"
    assert rows["CODE_1"]["typed_anchor"] == "STATE_WRITE"
    assert rows["CODE_1"]["effective_typed_anchor"] == "STATE_WRITE"
    assert rows["CODE_1"]["semantic_level"] == "RUNTIME"
    assert rows["CODE_1"]["semantic_anchor"] == "STATE_WRITE"
    assert rows["TEST_1"]["typed_anchor"] == "TEST_BATCH_CALL"
    assert rows["TEST_1"]["protocol_hypothesis"] == "CLOUD_BATCH_CALL"
    assert rows["TEST_1"]["semantic_level"] == "BEHAVIOR"
    assert rows["TEST_1"]["semantic_anchor"] == "TEST_BATCH_CALL"
    assert rows["TEST_1"]["behavior_category"] == "BATCH_BEHAVIOR"


def test_extracted_evidence_emits_semantic_levels(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    tests_root = tmp_path / "tests"
    docs.mkdir()
    repo.mkdir()
    tests_root.mkdir()

    (docs / "guide.md").write_text(
        "# Runtime Data\nCloud integrations should back off after 429 responses before issuing another HTTP request.\n",
        encoding="utf-8",
    )
    (repo / "demo.py").write_text(
        """
def explain():
    details = "persistent session manager closes idle session and batch requests are grouped"
    return details
""",
        encoding="utf-8",
    )
    (tests_root / "test_demo.py").write_text(
        "def test_idle(mock_session):\n    mock_session.request.assert_not_called()\n",
        encoding="utf-8",
    )

    bank = build_evidence_bank(docs, repo, tests_root=tests_root)
    assert bank.docs[0].semantic_level == "POLICY"
    assert any(item.semantic_level == "HINT" for item in bank.code if item.effective_typed_anchor)
    assert any(item.semantic_level == "BEHAVIOR" for item in bank.tests)
    assert any(item.semantic_anchor.endswith("_HINT") for item in bank.code if item.semantic_level == "HINT")
    assert any(item.behavior_category == "CLIENT_IDLE" for item in bank.tests)


def test_cluster_prefers_typed_anchor_for_doc_topic_routing() -> None:
    bank = EvidenceBank(
        docs=[
            DocEvidence(
                evidence_id="DOC_1",
                source_path="docs/quality_ops/creating_integration_manifest.md",
                line_no=10,
                modality="MUST",
                text="The logo for the domain must be added to the brands repository.",
                typed_anchor="DOC_MANIFEST_META",
                doc_kind="NORMATIVE_SENTENCE",
            )
        ]
    )

    packs = cluster_evidence(bank)
    assert len(packs) == 1
    assert packs[0].topic == "manifest_meta"


def test_llm_payload_prefers_typed_anchor_for_test_dominant_pattern() -> None:
    bank = EvidenceBank(
        tests=[
            TestEvidenceContract(
                evidence_id="TEST_1",
                source_path="tests/test_cloud.py",
                pattern="TEST_429_RETRY",
                test_name="test_cloud_rate_limit",
                line_no=12,
                assertion_kind="assert",
                frequency=2,
                typed_anchor="TEST_RETRY_CALL",
                protocol_hypothesis="CLOUD_429_CHECK",
            )
        ]
    )
    packs = [ClusterPack(cluster_id="cluster:protocol_cloud", topic="protocol_cloud", evidence_ids=["TEST_1"])]
    captured = {}

    def llm_adapter(payload):
        captured["payload"] = payload
        return []

    normalize_rules(bank, packs, llm_adapter=llm_adapter)
    cluster_row = captured["payload"]["clusters"][0]
    assert cluster_row["dominant_pattern_candidate"] == "CLOUD_429_CHECK"
    assert cluster_row["evidence"][0]["typed_anchor"] == "TEST_RETRY_CALL"
    assert cluster_row["evidence"][0]["protocol_hypothesis"] == "CLOUD_429_CHECK"


def test_protocol_rule_kept_soft_when_validation_fails() -> None:
    rule = Rule(
        rule_id="rp",
        title="protocol guard",
        category="protocol",
        status=RuleStatus.SOFT.value,
        guard="true",
        evidence_ids=["DOC_x"],
    )
    hardened, decisions = auto_harden_rules(
        [rule],
        validation_stats={"rp": {"n_matched": 1, "n_counterexamples": 1, "trace_preserved_rate": 0.2, "resource_protocol_preserved_rate": 0.2}},
    )
    assert hardened[0].status == RuleStatus.SOFT.value
    assert decisions["rp"]["hardening_state"] == "SOFT"
    assert decisions["rp"]["hardening_reason"] in {"insufficient_coverage", "counterexample_seen", "validation_below_threshold"}
    assert hardened[0].hardening_reason == decisions["rp"]["hardening_reason"]


def test_llm_payload_contains_evidence_summary_and_pattern_stats() -> None:
    bank = EvidenceBank(
        docs=[
            DocEvidence(
                evidence_id="DOC_1",
                source_path="docs/guide.md",
                line_no=12,
                modality="MUST",
                text="integration must refresh token before cloud call",
            )
        ],
        code=[
            CodeEvidence(
                evidence_id="CODE_1",
                source_path="repo/integration.py",
                pattern="CLOUD_HTTP_CALL",
                line_no=20,
                frequency=3,
            )
        ],
    )
    packs = [ClusterPack(cluster_id="cluster:protocol_cloud", topic="protocol_cloud", evidence_ids=["DOC_1", "CODE_1"])]
    captured = {}

    def llm_adapter(payload):
        captured["payload"] = payload
        return []

    normalize_rules(bank, packs, llm_adapter=llm_adapter)
    payload = captured["payload"]
    assert payload["clusters"]
    assert payload["clusters"][0]["pattern_stats"]["CLOUD_HTTP_CALL"] == 3
    assert payload["clusters"][0]["dominant_pattern_candidate"] == "CLOUD_HTTP_CALL"
    assert payload["clusters"][0]["evidence"][0]["kind"] == "doc"
    assert payload["clusters"][0]["evidence"][1]["kind"] == "code"


def test_profile_provenance_records_rule_hints_and_derived_templates(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text("The integration must set up the coordinator refresh before the entity update runs.", encoding="utf-8")
    (repo / "demo.py").write_text(
        """
async def async_setup_entry(hass, entry):
    await coordinator.async_config_entry_first_refresh()
    return True
""",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out).run(profile_id="p")
    enhancements = artifacts.profile.provenance.get("profile_enhancements", {})
    assert "ENTRY_SETUP" in enhancements.get("rule_marker_hints", [])
    derived = enhancements.get("derived_lifecycle_templates", [])
    assert any(item.get("src") == "ENTRY_SETUP" and item.get("dst") == "COORD_REFRESH" for item in derived)


def test_profile_provenance_records_tests_root_and_count(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    tests_root = tmp_path / "tests"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()
    tests_root.mkdir()

    (docs / "guide.md").write_text("The integration must set up the config entry before runtime actions.", encoding="utf-8")
    (repo / "demo.py").write_text("async def async_setup_entry(hass, entry):\n    return True\n", encoding="utf-8")
    (tests_root / "test_demo.py").write_text(
        "async def test_flow(hass, entry):\n    assert await hass.config_entries.async_setup(entry.entry_id)\n",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out, tests_root).run(profile_id="p")
    provenance = artifacts.profile.provenance
    assert provenance.get("tests_root") == str(tests_root)
    assert provenance.get("evidence_count", {}).get("tests", 0) >= 1
    assert provenance.get("profile_quality", {}).get("policy") == "manifest_iot_class_plus_protocol_signal_v1"
    assert "rule_evidence_policy" in provenance.get("profile_enhancements", {})


def test_profile_adds_protocol_marker_detectors_when_protocol_rules_present(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text("Cloud API requests should use backoff, and BLE connect operations should be serialized.", encoding="utf-8")
    (repo / "proto.py").write_text(
        """
import aiohttp
from bleak import BleakClient

async def run(client, session):
    await client.connect()
    await client.read_gatt_char("abc")
    await session.request("GET", "https://api.example.com/dev")
""",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out).run(profile_id="p")
    detector_types = {str(item.get("type", "")) for item in artifacts.profile.marker_detectors}
    assert "BLE_CONNECT" in detector_types
    assert "BLE_GATT_OP" in detector_types
    assert "CLOUD_HTTP_CALL" in detector_types
    enhancements = artifacts.profile.provenance.get("profile_enhancements", {})
    assert enhancements.get("protocol_detectors_added_count", 0) >= 1


def test_profile_adds_local_api_detector_from_manifest_scoped_evidence(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    local = repo / "local_demo"
    docs.mkdir()
    local.mkdir(parents=True)
    (local / "manifest.json").write_text(json.dumps({"iot_class": "local_polling"}), encoding="utf-8")
    (local / "sensor.py").write_text(
        """
import aiohttp

async def _async_update_data(session):
    await session.request("GET", "/a")
    await session.get("/b")
    await session.get("/c")
    await session.get("/d")
""",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out).run(profile_id="p")
    detector_types = {str(item.get("type", "")) for item in artifacts.profile.marker_detectors}
    rule_ids = {rule.rule_id for rule in artifacts.profile.rules}
    assert "LOCAL_API_READ" in detector_types
    assert "rule_protocol_local_api_budget" in rule_ids


def test_profile_adds_cloud_protocol_detectors_with_code_and_test_support(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    tests_root = tmp_path / "tests"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()
    tests_root.mkdir()

    (docs / "guide.md").write_text(
        "Cloud integrations must back off after 429 responses and should reuse session objects for grouped updates.",
        encoding="utf-8",
    )
    (repo / "cloud.py").write_text(
        """
import aiohttp
import asyncio

class Manager:
    async def setup(self):
        self.session = aiohttp.ClientSession()

    async def update(self, response):
        if response.status == 429:
            await asyncio.sleep(0.5)
        await self.session.request("GET", "https://api.example.com/dev")
        await self.batch_update()
""",
        encoding="utf-8",
    )
    (tests_root / "test_cloud.py").write_text(
        """
import asyncio

async def test_cloud_retry(session):
    assert 429 == 429
    await asyncio.sleep(0.5)
    session.batch_update()
    session.assert_called_once_with("reuse")
""",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out, tests_root).run(profile_id="p")
    detector_types = {str(item.get("type", "")) for item in artifacts.profile.marker_detectors}
    assert "CLOUD_429_CHECK" in detector_types
    assert "CLOUD_BACKOFF_SLEEP" in detector_types
    assert "CLOUD_BATCH_CALL" in detector_types
    assert "CLOUD_SESSION_REUSE" in detector_types


def test_cloud_session_reuse_detector_requires_store_and_use_chain(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text("Cloud integrations should reuse clients across grouped requests.", encoding="utf-8")
    (repo / "cloud.py").write_text(
        """
import aiohttp

async def run():
    session = aiohttp.ClientSession()
    await session.request("GET", "https://api.example.com/dev")
""",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out).run(profile_id="p")
    detector_types = {str(item.get("type", "")) for item in artifacts.profile.marker_detectors}
    assert "CLOUD_HTTP_CALL" in detector_types
    assert "CLOUD_SESSION_REUSE" not in detector_types


def test_hardening_promotes_rule_to_hard_with_strong_stats() -> None:
    rule = Rule(
        rule_id="r1",
        title="State write is observable",
        category="observable",
        status=RuleStatus.SOFT.value,
        evidence_ids=["DOC_x"],
    )
    hardened, decisions = auto_harden_rules(
        [rule],
        validation_stats={
            "r1": {
                "n_matched": 8,
                "n_applied": 8,
                "n_success": 8,
                "n_counterexamples": 0,
                "trace_preserved_rate": 1.0,
                "final_state_preserved_rate": 1.0,
                "resource_protocol_preserved_rate": 1.0,
            }
        },
    )
    assert decisions["r1"]["hardening_state"] == "HARD"
    assert decisions["r1"]["hardening_reason"] == "promoted_by_validation"
    assert hardened[0].hardening_state == "HARD"
    assert hardened[0].status == RuleStatus.HARD.value


def test_hardening_marks_rule_as_hard_candidate_with_mid_confidence_stats() -> None:
    rule = Rule(
        rule_id="r1",
        title="State write is observable",
        category="observable",
        status=RuleStatus.SOFT.value,
        evidence_ids=["DOC_x"],
    )
    hardened, decisions = auto_harden_rules(
        [rule],
        validation_stats={
            "r1": {
                "n_matched": 8,
                "n_applied": 8,
                "n_success": 7,
                "n_counterexamples": 0,
                "trace_preserved_rate": 0.90,
                "final_state_preserved_rate": 0.90,
                "resource_protocol_preserved_rate": 0.90,
            }
        },
    )
    assert decisions["r1"]["hardening_state"] == "HARD_CANDIDATE"
    assert decisions["r1"]["hardening_reason"] == "promoted_candidate_by_validation"
    assert hardened[0].hardening_state == "HARD_CANDIDATE"
    assert hardened[0].status == RuleStatus.SOFT.value


def test_profile_builder_loads_validation_stats_from_json(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    stats_path = tmp_path / "validation_stats.json"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text("The integration must write entity state after refresh.", encoding="utf-8")
    (repo / "demo.py").write_text(
        """
async def async_setup_entry(hass, entry):
    await coordinator.async_config_entry_first_refresh()
    entity.async_write_ha_state()
    return True
""",
        encoding="utf-8",
    )

    cold = HAPProfileBuilder(docs, repo, out).run(profile_id="p-cold")
    state_rule_id = next(rule.rule_id for rule in cold.profile.rules if rule.title == "State write is observable")

    stats_payload = {
        "rules": [
            {
                "rule_id": state_rule_id,
                "n_matched": 6,
                "n_applied": 6,
                "n_success": 6,
                "n_counterexamples": 0,
                "trace_preserved_rate": 1.0,
                "final_state_preserved_rate": 1.0,
                "resource_protocol_preserved_rate": 1.0,
                "last_updated_at": "2026-03-24T00:00:00Z",
            }
        ]
    }
    stats_path.write_text(json.dumps(stats_payload), encoding="utf-8")

    artifacts = HAPProfileBuilder(docs, repo, out).run(profile_id="p", validation_stats_path=stats_path)
    state_rule = next(rule for rule in artifacts.profile.rules if rule.title == "State write is observable")
    assert state_rule.hardening_state == "HARD"
    assert state_rule.hardening_reason == "promoted_by_validation"
    assert artifacts.profile.provenance.get("validation_stats_path") == str(stats_path)


def test_gate_reports_structured_matchability_reasons() -> None:
    bank = EvidenceBank(
        docs=[],
        code=[CodeEvidence("c1", "a.py", "BLE_DISCONNECT", 10, 1)],
    )
    rules = normalize_rules(bank, packs=[])
    target_rule = next(rule for rule in rules if rule.rule_id == "rule_protocol_ble_budget_overlap")
    from profile_builder.gate import run_deterministic_gate

    gate = run_deterministic_gate([target_rule], bank)
    reasons = gate.reasons[target_rule.rule_id]
    assert "matchability:false" in reasons
    assert "missing_marker:BLE_CONNECT" in reasons
    assert "missing_marker:BLE_GATT_OP" in reasons


def test_gate_accepts_protocol_rule_with_bank_level_cross_modal_support() -> None:
    from profile_builder.gate import run_deterministic_gate

    bank = EvidenceBank(
        docs=[
            DocEvidence(
                "DOC_1",
                "docs/bluetooth/api.md",
                10,
                "SHOULD",
                "Bluetooth integrations should use a connection timeout.",
                typed_anchor="DOC_BLE_CONNECTION_POLICY",
                specificity="PROTOCOL",
                semantic_anchor="DOC_BLE_CONNECTION_POLICY",
            )
        ],
        code=[
            CodeEvidence("CODE_1", "repo/bluetooth.py", "BLE_CONNECT", 10, typed_anchor="BLE_CONNECT", effective_typed_anchor="BLE_CONNECT", semantic_anchor="BLE_CONNECT"),
            CodeEvidence("CODE_2", "repo/bluetooth.py", "BLE_GATT_OP", 12, typed_anchor="BLE_GATT_OP", effective_typed_anchor="BLE_GATT_OP", semantic_anchor="BLE_GATT_OP"),
            CodeEvidence("CODE_3", "repo/bluetooth.py", "BLE_DISCONNECT", 14, typed_anchor="BLE_DISCONNECT", effective_typed_anchor="BLE_DISCONNECT", semantic_anchor="BLE_DISCONNECT"),
            CodeEvidence("CODE_4", "repo/bluetooth.py", "BLE_OP", 15, typed_anchor="BLE_OP", effective_typed_anchor="BLE_OP", semantic_anchor="BLE_OP"),
        ],
    )
    rule = Rule(
        rule_id="rp_ble",
        title="BLE connect precedes op",
        category="protocol",
        evidence_ids=["CODE_1", "CODE_2", "CODE_3", "CODE_4"],
        marker_hints=["BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT", "BLE_OP"],
        match_pattern={"dominant_pattern": "BLE_CONNECT", "topic": "protocol_ble"},
        effect={"kind": "ordering_or_constraint", "scope": "protocol_ble"},
    )

    gate = run_deterministic_gate([rule], bank)
    assert [row.rule_id for row in gate.enabled] == ["rp_ble"]
    assert gate.disabled == []


def test_gate_accepts_strong_code_only_protocol_rule() -> None:
    from profile_builder.gate import run_deterministic_gate

    bank = EvidenceBank(
        code=[
            CodeEvidence("CODE_1", "repo/cloud.py", "CLOUD_HTTP_CALL", 10, typed_anchor="CLOUD_HTTP_CALL", effective_typed_anchor="CLOUD_HTTP_CALL", semantic_anchor="CLOUD_HTTP_CALL", signal_strength="CALL_CHAIN_STRONG"),
            CodeEvidence("CODE_2", "repo/cloud.py", "CLOUD_HTTP_CALL", 14, typed_anchor="CLOUD_HTTP_CALL", effective_typed_anchor="CLOUD_HTTP_CALL", semantic_anchor="CLOUD_HTTP_CALL", signal_strength="CALL_CHAIN_STRONG"),
            CodeEvidence("CODE_3", "repo/cloud.py", "CLOUD_HTTP_CALL", 20, typed_anchor="CLOUD_HTTP_CALL", effective_typed_anchor="CLOUD_HTTP_CALL", semantic_anchor="CLOUD_HTTP_CALL", signal_strength="AST_STRONG"),
            CodeEvidence("CODE_4", "repo/cloud.py", "CLOUD_HTTP_CALL", 28, typed_anchor="CLOUD_HTTP_CALL", effective_typed_anchor="CLOUD_HTTP_CALL", semantic_anchor="CLOUD_HTTP_CALL", signal_strength="AST_STRONG"),
        ]
    )
    rule = Rule(
        rule_id="rp_cloud",
        title="Cloud budget rate",
        category="protocol",
        evidence_ids=["CODE_1", "CODE_2", "CODE_3", "CODE_4"],
        marker_hints=["CLOUD_HTTP_CALL"],
        match_pattern={"dominant_pattern": "CLOUD_HTTP_CALL", "topic": "protocol_cloud"},
        effect={"kind": "ordering_or_constraint", "scope": "protocol_cloud"},
    )

    gate = run_deterministic_gate([rule], bank)
    assert [row.rule_id for row in gate.enabled] == ["rp_cloud"]
    assert gate.disabled == []


def test_rule_canonicalization_deduplicates_entry_setup_rules() -> None:
    bank = EvidenceBank(
        docs=[
            DocEvidence("DOC_1", "docs/a.md", 1, "MUST", "Config entry must setup coordinator refresh", doc_kind="LIFECYCLE_SENTENCE"),
            DocEvidence("DOC_2", "docs/b.md", 1, "SHOULD", "Config entry should setup coordinator refresh", doc_kind="LIFECYCLE_SENTENCE"),
        ],
        code=[
            CodeEvidence("CODE_1", "repo/a.py", "ENTRY_SETUP", 10, 1),
            CodeEvidence("CODE_2", "repo/b.py", "ENTRY_SETUP", 20, 1),
            CodeEvidence("CODE_3", "repo/a.py", "COORD_REFRESH", 11, 1),
        ],
    )
    packs = [
        ClusterPack(cluster_id="cluster:lifecycle", topic="lifecycle", evidence_ids=["DOC_1", "CODE_1", "CODE_3"]),
        ClusterPack(cluster_id="cluster:lifecycle:1", topic="lifecycle", evidence_ids=["DOC_2", "CODE_2", "CODE_3"]),
    ]
    rules = normalize_rules(bank, packs=packs)
    setup_rules = [rule for rule in rules if rule.title == "Entry setup precedes first refresh"]
    assert len(setup_rules) == 1
    assert set(setup_rules[0].evidence_ids) == {"DOC_1", "DOC_2", "CODE_1", "CODE_2", "CODE_3"}


def test_profile_preserves_template_params_in_derived_lifecycle_templates(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()

    (docs / "guide.md").write_text("A token refresh should precede the cloud API call for this config entry.", encoding="utf-8")
    (repo / "cloud.py").write_text(
        """
import aiohttp

async def run(session):
    await session.login()
    await session.request("GET", "https://api.example.com/dev")
""",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out).run(profile_id="p")
    target_rows = [
        row
        for row in artifacts.profile.lifecycle_templates
        if row.get("requires_order") == ["CLOUD_TOKEN_REFRESH", "CLOUD_HTTP_CALL"]
    ]
    assert target_rows
    assert target_rows[0].get("params", {}).get("pair_key") == "host"


def test_profile_builder_accepts_verified_llm_discovery_candidates(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    demo = repo / "demo"
    out = tmp_path / "out"
    docs.mkdir()
    demo.mkdir(parents=True)

    (docs / "guide.md").write_text("Cloud integrations should batch compatible API reads.", encoding="utf-8")
    (demo / "manifest.json").write_text(json.dumps({"iot_class": "cloud_polling"}), encoding="utf-8")
    (demo / "api.py").write_text(
        """
import aiohttp

class DemoClient:
    async def async_update_data(self):
        await self.session.bulk_status()
        return await self.session.request("GET", "https://api.example.com/devices")
""",
        encoding="utf-8",
    )
    captured = {}

    def llm_adapter(payload):
        captured["payload"] = payload
        return {
            "schema_version": "profile_builder_llm_discovery/response/v1",
            "candidates": [
                {
                    "kind": "marker_detector",
                    "marker_type": "CLOUD_BATCH_CALL",
                    "protocol_family": "CLOUD",
                    "match": {"call_attrs": ["bulk_status"], "module_hints": ["aiohttp"]},
                    "source_refs": [{"path": "demo/api.py", "line": 6, "symbol": "DemoClient.async_update_data"}],
                    "confidence": 0.82,
                },
                {
                    "kind": "runtime_carrier",
                    "marker_type": "CLOUD_HTTP_CALL",
                    "protocol_family": "CLOUD",
                    "runtime_role": "status",
                    "symbol": "DemoClient.async_update_data",
                    "match": {"call_attrs": ["request"], "module_hints": ["aiohttp"]},
                    "source_refs": [{"path": "demo/api.py", "line": 7, "symbol": "DemoClient.async_update_data"}],
                    "confidence": 0.8,
                },
            ],
        }

    artifacts = HAPProfileBuilder(docs, repo, out).run(
        profile_id="p",
        enable_llm_discovery=True,
        llm_discovery_adapter=llm_adapter,
    )

    assert captured["payload"]["schema_version"] == "profile_builder_llm_discovery/request/v1"
    enhancements = artifacts.profile.provenance.get("profile_enhancements", {})
    llm_summary = enhancements.get("llm_discovery", {})
    assert llm_summary.get("candidate_count") == 2
    assert llm_summary.get("verified_count") == 2
    assert llm_summary.get("marker_detector_count") == 1
    assert any(str(item.get("id", "")).startswith("llm:detector:cloud_batch_call") for item in artifacts.profile.marker_detectors)
    assert any(item.extractor_version == "profile_builder_llm_discovery/v1" for item in artifacts.evidence_bank.code)
    assert (out / "llm_candidate_verification.json").exists()
    assert (out / "llm_grounding_profiles_auto" / "demo.json").exists()


def test_profile_builder_rejects_ungrounded_llm_discovery_candidates(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()
    (docs / "guide.md").write_text("Cloud integrations should handle API calls.", encoding="utf-8")
    (repo / "demo.py").write_text("async def run():\n    return None\n", encoding="utf-8")

    payload = {
        "candidates": [
            {
                "kind": "marker_detector",
                "marker_type": "CLOUD_BATCH_CALL",
                "protocol_family": "CLOUD",
                "match": {"call_attrs": ["batch_status"]},
                "source_refs": [{"path": "missing.py", "line": 1}],
                "confidence": 0.9,
            }
        ]
    }

    artifacts = HAPProfileBuilder(docs, repo, out).run(
        profile_id="p",
        enable_llm_discovery=True,
        llm_discovery_payload=payload,
    )

    llm_summary = artifacts.profile.provenance["profile_enhancements"]["llm_discovery"]
    assert llm_summary["candidate_count"] == 1
    assert llm_summary["verified_count"] == 0
    assert llm_summary["rejected_count"] == 1
    assert not any(str(item.get("id", "")).startswith("llm:detector:") for item in artifacts.profile.marker_detectors)


def test_evidence_policy_keeps_core_and_llm_verified_but_filters_hint_rows() -> None:
    bank = EvidenceBank(
        code=[
            CodeEvidence(
                "CODE_CORE",
                "repo/cloud.py",
                "CLOUD_HTTP_CALL",
                10,
                typed_anchor="CLOUD_HTTP_CALL",
                effective_typed_anchor="CLOUD_HTTP_CALL",
                signal_strength="AST_STRONG",
            ),
            CodeEvidence(
                "CODE_HINT",
                "repo/cloud.py",
                "CLOUD_API_HINT",
                12,
                typed_anchor="CLOUD_API_HINT",
                effective_typed_anchor="CLOUD_API_HINT",
                signal_strength="TEXT_WEAK",
            ),
            CodeEvidence(
                "CODE_LLM",
                "repo/cloud.py",
                "CUSTOM_RUNTIME",
                14,
                typed_anchor="CUSTOM_RUNTIME",
                extractor_version="profile_builder_llm_discovery/v1",
                normalization_flags=["llm_candidate_verified:source_ref"],
            ),
        ]
    )

    result = select_semantic_evidence_bank(bank, policy="core_plus_verified")
    kept_ids = {item.evidence_id for item in result.semantic_bank.code}

    assert kept_ids == {"CODE_CORE", "CODE_LLM"}
    assert result.report["dropped_count"] == 1
    assert result.report["class_counts"]["llm_verified_semantic"] == 1


def test_profile_builder_writes_raw_semantic_and_fact_artifacts(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    docs.mkdir()
    repo.mkdir()
    (docs / "guide.md").write_text("Cloud integrations should fetch state with an API request.", encoding="utf-8")
    (repo / "cloud.py").write_text(
        """
import aiohttp

async def async_update_data(session):
    return await session.request("GET", "https://api.example.com/devices")
""",
        encoding="utf-8",
    )

    artifacts = HAPProfileBuilder(docs, repo, out).run(profile_id="p")

    assert (out / "evidence_bank_raw.json").exists()
    assert (out / "evidence_bank.json").exists()
    assert (out / "evidence_policy_report.json").exists()
    assert (out / "profile_facts.json").exists()
    assert artifacts.raw_evidence_bank is not None
    assert artifacts.evidence_policy_report is not None
    assert artifacts.profile.provenance["semantic_evidence_policy"] == "core_plus_verified"
    assert artifacts.profile.provenance["raw_evidence_count"]["code"] >= artifacts.profile.provenance["evidence_count"]["code"]
