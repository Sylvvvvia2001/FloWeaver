from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from profile_builder.evidence import EvidenceBank


_TEST_TOPIC_MAP = {
    "TEST_ENTRY_SETUP": "entry_setup",
    "TEST_ENTRY_UNLOAD": "entry_unload",
    "TEST_CONFIG_ENTRY_NOT_READY": "entry_setup",
    "TEST_AUTH_FAILED": "entry_setup",
    "TEST_SUBSCRIBE_CLEANUP": "subscription",
    "TEST_STATE_WRITE": "state_write",
    "TEST_MANAGER_STOP": "unload_cleanup",
    "TEST_429_RETRY": "protocol_cloud",
    "TEST_BACKOFF_SLEEP": "protocol_cloud",
    "TEST_BATCH_CALL": "protocol_cloud",
    "TEST_BATCH_UPDATE": "protocol_cloud",
    "TEST_NO_REDUNDANT_CALL": "call_constraint",
    "TEST_EXPECTED_CLIENT_IDLE": "call_constraint",
    "TEST_CALL_SUPPRESSION": "call_constraint",
    "TEST_CLIENT_CONNECT": "call_constraint",
    "TEST_CLIENT_DISCONNECT": "call_constraint",
    "TEST_CLIENT_CONFIG_UPDATE": "call_constraint",
    "TEST_CLIENT_EMIT": "call_constraint",
    "TEST_CLIENT_CALL_CONSTRAINT": "call_constraint",
    "TEST_RATE_LIMIT": "protocol_cloud",
    "TEST_HTTP_ERROR_RECOVERY": "protocol_cloud",
}

_TYPED_ANCHOR_TOPIC_MAP = {
    "ENTRY_SETUP": "entry_setup",
    "ENTRY_UNLOAD": "entry_unload",
    "COORD_REFRESH": "coordinator",
    "STATE_WRITE": "state_write",
    "SUBSCRIBE": "subscription",
    "UNSUBSCRIBE": "subscription",
    "SUBSCRIBE_PAIRING": "subscription",
    "BLE_OP": "protocol_ble",
    "BLE_CONNECT": "protocol_ble",
    "BLE_GATT_OP": "protocol_ble",
    "BLE_DISCONNECT": "protocol_ble",
    "BLE_SCAN": "protocol_ble",
    "BLE_RETRY_OR_TIMEOUT": "protocol_ble",
    "BLE_REUSE_CONTEXT": "protocol_ble",
    "LOCAL_API_READ": "protocol_local",
    "CLOUD_HTTP_CALL": "protocol_cloud",
    "CLOUD_TOKEN_REFRESH": "protocol_cloud",
    "CLOUD_429_CHECK": "protocol_cloud",
    "CLOUD_BACKOFF_SLEEP": "protocol_cloud",
    "CLOUD_BATCH_CALL": "protocol_cloud",
    "CLOUD_SESSION_CREATE": "protocol_cloud",
    "CLOUD_SESSION_STORE": "protocol_cloud",
    "CLOUD_SESSION_USE": "protocol_cloud",
    "CLOUD_SESSION_CLOSE": "protocol_cloud",
    "CLOUD_SESSION_REUSE": "protocol_cloud",
    "CLIENT_CONNECT": "call_constraint",
    "CLIENT_DISCONNECT": "call_constraint",
    "CLIENT_CONFIG_UPDATE": "call_constraint",
    "CLIENT_EMIT": "call_constraint",
    "NO_REDUNDANT_CALL": "call_constraint",
    "EXPECTED_CLIENT_IDLE": "call_constraint",
    "CALL_SUPPRESSION": "call_constraint",
    "CLIENT_CALL_CONSTRAINT": "call_constraint",
    "TEST_SUBSCRIBE_CLEANUP": "subscription",
    "TEST_RETRY_CALL": "protocol_cloud",
    "TEST_BACKOFF_CALL": "protocol_cloud",
    "TEST_BATCH_CALL": "protocol_cloud",
    "TEST_EXPECTED_SINGLE_CALL": "call_constraint",
    "TEST_NO_REDUNDANT_CALL": "call_constraint",
    "TEST_EXPECTED_CLIENT_IDLE": "call_constraint",
    "TEST_CALL_SUPPRESSION": "call_constraint",
    "TEST_CLIENT_CALL_CONSTRAINT": "call_constraint",
    "DOC_BLE_CONNECTION_POLICY": "protocol_ble_policy",
    "DOC_BLE_GATT_POLICY": "protocol_ble_policy",
    "DOC_BLE_DISCONNECT_POLICY": "protocol_ble_policy",
    "DOC_CLOUD_API_POLICY": "protocol_cloud_policy",
    "DOC_CLOUD_BATCH_POLICY": "protocol_cloud_policy",
    "DOC_RETRY_BACKOFF_POLICY": "protocol_cloud_policy",
    "DOC_CLOUD_SESSION_POLICY": "protocol_cloud_policy",
    "DOC_CLOUD_AUTH_POLICY": "protocol_cloud_policy",
    "DOC_ENTRY_SETUP_POLICY": "entry_setup",
    "DOC_ENTRY_UNLOAD_POLICY": "entry_unload",
    "DOC_COORD_REFRESH_POLICY": "coordinator",
    "DOC_SUBSCRIBE_PAIRING_POLICY": "subscription_policy",
    "DOC_STATE_UPDATE_POLICY": "state_write",
    "DOC_UNIQUE_ID_POLICY": "identity_policy",
    "DOC_DISCOVERY_POLICY": "discovery_policy",
    "DOC_SHARED_RESOURCE": "shared_resource_policy",
    "DOC_SUBSCRIPTION_POLICY": "subscription_policy",
    "DOC_CONFIG_ENTRY_MUTATION": "config_entry_policy",
    "DOC_RETRY_POLICY": "retry_policy",
    "DOC_AVAILABILITY_POLICY": "availability_policy",
    "DOC_ENTITY_PROPERTY_POLICY": "entity_property_policy",
    "DOC_ENTITY_NAMING_POLICY": "entity_naming_policy",
    "DOC_TRANSLATION_POLICY": "translation_policy",
    "DOC_DIAGNOSTICS_POLICY": "diagnostics_policy",
    "DOC_REAUTH_FLOW": "reauth_flow",
    "DOC_RECONFIGURE_FLOW": "reconfigure_flow",
    "DOC_MIGRATION": "migration",
    "DOC_MANIFEST_META": "manifest_meta",
    "DOC_NORMATIVE": "general",
}


@dataclass
class ClusterPack:
    cluster_id: str
    topic: str
    evidence_ids: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)


def _tokenize(text: str) -> Set[str]:
    return {t.lower() for t in text.replace("_", " ").replace("-", " ").split() if t}


def _doc_topic(text: str) -> str:
    tokens = _tokenize(text)
    if tokens & {"ble", "bluetooth", "gatt", "characteristic"}:
        return "protocol_ble"
    if tokens & {"cloud", "http", "api", "token", "oauth", "429", "ratelimit", "backoff"}:
        return "protocol_cloud"
    if tokens & {"coordinator", "refresh", "first_refresh", "update_data"}:
        return "coordinator"
    if tokens & {"state_write", "state", "entity", "write", "async_write_ha_state"}:
        return "state_write"
    if tokens & {"subscribe", "unsubscribe", "listener", "dispatcher"}:
        return "subscription"
    if tokens & {"unload", "remove", "teardown", "cleanup", "close"}:
        return "unload_cleanup"
    if tokens & {"setup", "unload", "refresh", "lifecycle", "configentry"}:
        return "lifecycle"
    if tokens & {"cleanup", "teardown", "remove", "unsubscribe", "close"}:
        return "cleanup"
    return "general"


def _typed_anchor_topic(typed_anchor: str | None) -> str:
    anchor = str(typed_anchor or "").strip().upper()
    return _TYPED_ANCHOR_TOPIC_MAP.get(anchor, "")


def cluster_evidence(bank: EvidenceBank, max_pack_size: int = 12) -> List[ClusterPack]:
    buckets: Dict[str, ClusterPack] = {}

    for doc in bank.docs:
        if getattr(doc, "doc_kind", "NORMATIVE_SENTENCE") not in {"NORMATIVE_SENTENCE", "LIFECYCLE_SENTENCE"}:
            continue
        key = _typed_anchor_topic(getattr(doc, "typed_anchor", "")) or _doc_topic(doc.text)
        pack = buckets.setdefault(key, ClusterPack(cluster_id=f"cluster:{key}", topic=key))
        pack.evidence_ids.append(doc.evidence_id)

    for code in bank.code:
        typed_anchor = str(getattr(code, "effective_typed_anchor", "") or getattr(code, "typed_anchor", "")).strip().upper()
        key = typed_anchor.lower() if typed_anchor else code.pattern.lower()
        pack = buckets.setdefault(key, ClusterPack(cluster_id=f"cluster:{key}", topic=key))
        pack.evidence_ids.append(code.evidence_id)

    for test in bank.tests:
        key = _typed_anchor_topic(getattr(test, "typed_anchor", "")) or _TEST_TOPIC_MAP.get(test.pattern)
        if not key:
            continue
        pack = buckets.setdefault(key, ClusterPack(cluster_id=f"cluster:{key}", topic=key))
        pack.evidence_ids.append(test.evidence_id)

    expanded: List[ClusterPack] = []
    for pack in buckets.values():
        ids = pack.evidence_ids
        for idx in range(0, len(ids), max_pack_size):
            subset = ids[idx : idx + max_pack_size]
            suffix = f":{idx // max_pack_size}" if len(ids) > max_pack_size else ""
            expanded.append(
                ClusterPack(
                    cluster_id=f"{pack.cluster_id}{suffix}",
                    topic=pack.topic,
                    evidence_ids=subset,
                    stats={"count": len(subset)},
                )
            )

    return expanded


def evidence_feature_summary(bank: EvidenceBank) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for item in bank.code:
        summary[item.pattern] = summary.get(item.pattern, 0) + item.frequency
    return dict(sorted(summary.items(), key=lambda kv: (-kv[1], kv[0])))
