from __future__ import annotations

import argparse
import os
from pathlib import Path

from dsl.io import load_json
from optimizer.m_minus1_scoping import build_optimization_target
from optimizer.pipeline import FloWeaverOptimizer
from profile_builder.llm_discovery import make_chat_completion_discovery_adapter
from profile_builder.pipeline import HAPProfileBuilder


def _load_optional_json(path: str | None) -> object | None:
    if not path:
        return None
    return load_json(path)


def _llm_discovery_adapter_from_args(args: argparse.Namespace):
    if not bool(getattr(args, "enable_llm_discovery", False)):
        return None
    base_url = str(getattr(args, "llm_discovery_api_base_url", "") or "").strip()
    api_key = str(getattr(args, "llm_discovery_api_key", "") or "").strip()
    api_key_env = str(getattr(args, "llm_discovery_api_key_env", "FLOWEAVER_LLM_API_KEY") or "FLOWEAVER_LLM_API_KEY").strip()
    if not api_key and api_key_env:
        api_key = os.environ.get(api_key_env, "")
    if not base_url and not api_key:
        return None
    return make_chat_completion_discovery_adapter(
        api_base_url=base_url,
        api_key=api_key,
        model=str(getattr(args, "llm_discovery_model", "gpt-5") or "gpt-5"),
        timeout_s=int(getattr(args, "llm_discovery_timeout_s", 120) or 120),
    )


def cmd_build_profile(args: argparse.Namespace) -> None:
    builder = HAPProfileBuilder(args.docs_root, args.repo_root, args.out_dir, args.tests_root)
    llm_payload = _load_optional_json(args.llm_discovery_candidates_path)
    llm_adapter = _llm_discovery_adapter_from_args(args)
    artifacts = builder.run(
        profile_id=args.profile_id,
        validation_stats_path=args.validation_stats,
        enable_llm_discovery=bool(args.enable_llm_discovery or llm_payload is not None or llm_adapter is not None),
        llm_discovery_adapter=llm_adapter,
        llm_discovery_payload=llm_payload,
        evidence_semantic_policy=args.evidence_semantic_policy,
    )
    print(f"Profile built: {artifacts.profile.profile_id}")
    print(f"Output: {Path(args.out_dir).resolve() / 'ha_profile.json'}")


def cmd_build_target(args: argparse.Namespace) -> None:
    target = build_optimization_target(
        vdev_spec_path=args.vdev_spec,
        source_spec_path=args.source_spec,
        run_spec_path=args.run_spec,
        out_path=args.out_path,
    )
    print(f"Optimization target built: {Path(args.out_path).resolve()}")
    print(f"Source files: {len(target.source_scope.get('files', []))}")
    print(f"Actions: {len(target.vdev_actions)}")


def cmd_optimize(args: argparse.Namespace) -> None:
    optimizer = FloWeaverOptimizer(
        integration_name=args.integration_name,
        integration_path=args.integration_path,
        profile_path=args.profile_path,
        out_dir=args.out_dir,
        vdev_spec_path=args.vdev_spec,
        source_spec_path=args.source_spec,
        run_spec_path=args.run_spec,
        optimization_target_path=args.optimization_target,
        rollback_max_steps=args.rollback_max_steps,
        hardening_min_pass_rate=args.hardening_min_pass_rate,
        hardening_min_coverage=args.hardening_min_coverage,
    )
    artifacts = optimizer.run()
    print(f"Optimization done for {args.integration_name}")
    print(f"Source files: {len(artifacts.optimization_target.source_scope.get('files', []))}")
    print(f"Markers: {len(artifacts.marker_set.markers)}")
    print(f"MSSUs: {len(artifacts.mssu_result.mssus)}")
    print(f"M7 component: {artifacts.component_assembly.custom_component_dir}")
    print(f"Trust summary: {artifacts.trust_summary}")


def cmd_all(args: argparse.Namespace) -> None:
    profile_out = Path(args.profile_out)
    builder = HAPProfileBuilder(args.docs_root, args.repo_root, profile_out, args.tests_root)
    llm_payload = _load_optional_json(args.llm_discovery_candidates_path)
    llm_adapter = _llm_discovery_adapter_from_args(args)
    artifacts = builder.run(
        profile_id=args.profile_id,
        validation_stats_path=args.validation_stats,
        enable_llm_discovery=bool(args.enable_llm_discovery or llm_payload is not None or llm_adapter is not None),
        llm_discovery_adapter=llm_adapter,
        llm_discovery_payload=llm_payload,
        evidence_semantic_policy=args.evidence_semantic_policy,
    )

    profile_path = profile_out / "ha_profile.json"
    optimizer = FloWeaverOptimizer(
        integration_name=args.integration_name,
        integration_path=args.integration_path,
        profile_path=profile_path,
        out_dir=args.optimize_out,
        vdev_spec_path=args.vdev_spec,
        source_spec_path=args.source_spec,
        run_spec_path=args.run_spec,
        optimization_target_path=args.optimization_target,
        rollback_max_steps=args.rollback_max_steps,
        hardening_min_pass_rate=args.hardening_min_pass_rate,
        hardening_min_coverage=args.hardening_min_coverage,
    )
    opt_artifacts = optimizer.run()

    print(f"Profile: {artifacts.profile.profile_id}")
    print(f"Profile path: {profile_path}")
    print(f"M7 component: {opt_artifacts.component_assembly.custom_component_dir}")
    print(f"Optimization summary: {opt_artifacts.trust_summary}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FloWeaver (HA version) pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_profile = sub.add_parser("build-profile", help="Run offline HA profile builder")
    p_profile.add_argument("--docs-root", default="data/docs_snapshot")
    p_profile.add_argument("--repo-root", default="data/repo_snapshot")
    p_profile.add_argument("--tests-root", default="data/tests_snapshot")
    p_profile.add_argument("--out-dir", default="data/profiles/default")
    p_profile.add_argument("--profile-id", default="ha_profile_default")
    p_profile.add_argument("--validation-stats")
    p_profile.add_argument("--evidence-semantic-policy", choices=("core_plus_verified", "legacy"), default="core_plus_verified")
    p_profile.add_argument("--enable-llm-discovery", action="store_true")
    p_profile.add_argument("--llm-discovery-candidates-path")
    p_profile.add_argument("--llm-discovery-api-base-url", default=os.environ.get("FLOWEAVER_LLM_API_BASE_URL", ""))
    p_profile.add_argument("--llm-discovery-api-key", default="")
    p_profile.add_argument("--llm-discovery-api-key-env", default="FLOWEAVER_LLM_API_KEY")
    p_profile.add_argument("--llm-discovery-model", default=os.environ.get("FLOWEAVER_LLM_MODEL", "gpt-5"))
    p_profile.add_argument("--llm-discovery-timeout-s", type=int, default=int(os.environ.get("FLOWEAVER_LLM_TIMEOUT_S", "120")))
    p_profile.set_defaults(func=cmd_build_profile)

    p_target = sub.add_parser("build-target", help="Run M-1 VDevSpec ingestion")
    p_target.add_argument("--vdev-spec", required=True)
    p_target.add_argument("--source-spec", required=True)
    p_target.add_argument("--run-spec")
    p_target.add_argument("--out-path", default="data/targets/default_optimization_target.json")
    p_target.set_defaults(func=cmd_build_target)

    p_opt = sub.add_parser("optimize", help="Run FloWeaver optimizer pipeline")
    p_opt.add_argument("--integration-name", required=True)
    p_opt.add_argument("--profile-path", required=True)
    p_opt.add_argument("--integration-path")
    p_opt.add_argument("--vdev-spec")
    p_opt.add_argument("--source-spec")
    p_opt.add_argument("--run-spec")
    p_opt.add_argument("--optimization-target")
    p_opt.add_argument("--out-dir", default="data/optimizer_runs/default")
    p_opt.add_argument("--rollback-max-steps", type=int, default=6)
    p_opt.add_argument("--hardening-min-pass-rate", type=float, default=0.98)
    p_opt.add_argument("--hardening-min-coverage", type=float, default=0.85)
    p_opt.set_defaults(func=cmd_optimize)

    p_all = sub.add_parser("all", help="Build profile then optimize")
    p_all.add_argument("--docs-root", default="data/docs_snapshot")
    p_all.add_argument("--repo-root", default="data/repo_snapshot")
    p_all.add_argument("--tests-root", default="data/tests_snapshot")
    p_all.add_argument("--profile-out", default="data/profiles/default")
    p_all.add_argument("--profile-id", default="ha_profile_default")
    p_all.add_argument("--validation-stats")
    p_all.add_argument("--evidence-semantic-policy", choices=("core_plus_verified", "legacy"), default="core_plus_verified")
    p_all.add_argument("--enable-llm-discovery", action="store_true")
    p_all.add_argument("--llm-discovery-candidates-path")
    p_all.add_argument("--llm-discovery-api-base-url", default=os.environ.get("FLOWEAVER_LLM_API_BASE_URL", ""))
    p_all.add_argument("--llm-discovery-api-key", default="")
    p_all.add_argument("--llm-discovery-api-key-env", default="FLOWEAVER_LLM_API_KEY")
    p_all.add_argument("--llm-discovery-model", default=os.environ.get("FLOWEAVER_LLM_MODEL", "gpt-5"))
    p_all.add_argument("--llm-discovery-timeout-s", type=int, default=int(os.environ.get("FLOWEAVER_LLM_TIMEOUT_S", "120")))
    p_all.add_argument("--integration-name", required=True)
    p_all.add_argument("--integration-path")
    p_all.add_argument("--vdev-spec")
    p_all.add_argument("--source-spec")
    p_all.add_argument("--run-spec")
    p_all.add_argument("--optimization-target")
    p_all.add_argument("--optimize-out", default="data/optimizer_runs/default")
    p_all.add_argument("--rollback-max-steps", type=int, default=6)
    p_all.add_argument("--hardening-min-pass-rate", type=float, default=0.98)
    p_all.add_argument("--hardening-min-coverage", type=float, default=0.85)
    p_all.set_defaults(func=cmd_all)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
