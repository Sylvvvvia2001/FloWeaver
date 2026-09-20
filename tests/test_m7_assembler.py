import json
from pathlib import Path

from dsl.contracts import Batch, ExecutionPlan, OptimizationTarget
from optimizer.m7_component_assembler import VDevCustomComponentAssembler


def test_generate_custom_component_from_plan(tmp_path: Path) -> None:
    target = OptimizationTarget(
        meta={"spec_version": "0.1", "vdev_id": "demo_01", "name": "Demo VDev"},
        source_scope={"files": ["/tmp/fake.py"], "domains": ["demo"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "call_api",
                "protocol": "CLOUD",
                "target": {"kind": "cloud_endpoint", "id": "tuya:device.control"},
                "exec": {
                    "kind": "ha_service_call",
                    "domain": "tuya",
                    "service": "call_api",
                    "data_template": {"endpoint": "tuya:device.control"},
                },
                "critical": True,
                "marker_hints": ["CLOUD_OP"],
            }
        ],
        target_anchors={"entities": [], "endpoints": ["tuya:device.control"], "device_ids": [], "characteristics": [], "service_entrypoints": [], "anchor_ops": ["CLOUD_OP"]},
        entrypoint={"kind": "ha_service", "service": {"domain": "floweaver", "name": "run"}},
        objectives={"primary": "minimize_tail_latency", "name": "Demo VDev"},
        constraints={"optimization_knobs": {"allow_concurrency": True}},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1"],
    )

    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1"]],
                constraints=["HARD_CONTROL"],
                guards=["true"],
                fallback={},
            )
        ],
        meta={"node_kind": "action_id"},
    )

    assembler = VDevCustomComponentAssembler(tmp_path)
    artifact = assembler.assemble(target, plan)

    component_dir = Path(artifact.custom_component_dir)
    assert (component_dir / "manifest.json").exists()
    assert (component_dir / "__init__.py").exists()
    assert (component_dir / "executor.py").exists()
    assert (component_dir / "services.yaml").exists()
    assert (component_dir / "plan.json").exists()
    assert (component_dir / "target.json").exists()
    assert Path(artifact.install_doc_path).exists()

    manifest = json.loads((component_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "integration_type" not in manifest
    assert "iot_class" not in manifest
    services_yaml = (component_dir / "services.yaml").read_text(encoding="utf-8")
    assert "runtime_metrics:" in services_yaml
    assert "export_trace:" in services_yaml
    assert "trace_path:" in services_yaml


def test_rendered_executor_is_fail_fast_and_scope_aware() -> None:
    text = VDevCustomComponentAssembler._render_executor_py()

    compile(text, "<generated_executor>", "exec")
    assert "async_track_state_change_event" in text
    assert "Missing required template token" in text
    assert "TEMPLATE_MISSING" in text
    assert "GUARD_UNKNOWN" in text
    assert "EXCEPTION_SUMMARY" in text
    assert "RATE_WAIT" in text
    assert "RATE_DOWNGRADE" in text
    assert "BATCH_COALESCE_WAIT" in text
    assert "BATCH_SHRINK_APPLIED" in text
    assert "TRACE_EXPORTED" in text
    assert "schema_version\": \"m7_trace_export/v1\"" in text or "schema_version': 'm7_trace_export/v1'" in text
    assert "def _enforced_bucket_keys" in text
    assert "def _observed_bucket_keys" in text
    assert "def _group_requires_order_preservation" in text
    assert "runtime_policy_snapshot" in text
    assert "forced_fallbacks_applied" in text
    assert "results = await asyncio.gather(*tasks.values())" in text
    assert "def _split_bool_expr" in text
    assert "def _serialize_targets" in text
    assert "if self._group_requires_order_preservation(action_ids, relevant_fallback):" in text
    assert "serial_ids = list(action_ids)" in text
    assert "class RateController" in text
    assert 'if protocol in {"LOCAL", "MQTT"}:' in text
    assert 'return "LOCAL"' in text
