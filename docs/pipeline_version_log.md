# Pipeline Version Log

This file records traceable pipeline-level changes that affect benchmark latency or validation behavior.

## 2026-07-01-paper-module-name-alignment

- Date: 2026-07-01 Asia/Shanghai
- Scope: Module naming and ablation switches only.
- Change:
  - Aligned optimizer module switches with the paper framework: `routine_interpreter`, `primitive_extractor`, `constraint_aware_orchestrator`, and `equivalence_validator`.
  - Exposed paper submodules in `module_switches.json`: `semantic_marker`, `semantic_primitive_extractor`, `dependency_graph_builder`, `macro_level_scheduler`, `micro_level_scheduler`, and `component_assembler`.
  - Added paper-name facade modules and routed `optimizer/pipeline.py` imports through them: `routine_interpreter`, `semantic_marker`, `semantic_primitive_extractor`, `dependency_graph_builder`, `macro_level_scheduler`, `micro_level_scheduler`, `generated_routine_assembler`, and `equivalence_validator`.
  - Merged the former reduction/MSSU-builder switches under `semantic_primitive_extractor`, matching the paper's Action-Grounded Semantic Primitive Extractor.
  - Kept legacy switch aliases such as `m1_grounding`, `m5_macro_scheduler`, and `m6_trust_validator` so existing targets still run.
  - Added paper-name class aliases: `DependencyGraphBuilder`, `MacroLevelScheduler`, `MicroLevelScheduler`, and `EquivalenceValidator`.
- Validation commands:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m compileall optimizer profile_builder runtime dsl alignment_layer counterexample_layer tests scripts floweaver_cli.py`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest tests/test_end_to_end.py tests/test_m6_trust.py tests/test_m5_scheduler.py tests/test_combined_micro_refinement.py --tb=short`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest --tb=short`
- Validation results:
  - Compile check: passed.
  - Targeted tests: 104 passed.
  - Full tests: 358 passed.
  - Smoke pipeline: completed with paper-name `module_switches.json`; Micro-level Scheduler validation passed; Equivalence Validator strict/tolerant pass `6/6`.
  - Ablation smoke: disabling `primitive_extractor`, `constraint_aware_orchestrator`, `component_assembler`, and `equivalence_validator` produced a serial fallback plan and skipped validation as expected.

## 2026-07-01-floweaver-mssu-micro-pipeline-switches

- Date: 2026-07-01 Asia/Shanghai
- Scope: Project naming, M3 unit naming, optimizer pipeline orchestration.
- Change:
  - Standardized user-facing project references as `FloWeaver`.
  - Standardized M3 semantic units as `MSSU` across contracts, M3 builder, M4 DAG, M5 scheduler, M6 certificate/trust paths, templates, tests, and CLI outputs.
  - Added `micro_level_scheduler` to the main optimizer path between M5 macro scheduling and M6 Trust Validator.
  - Added per-module ablation switches under `validation.modules` or `constraints.optimization_knobs.enable_* / disable_*`.
  - Preserved default behavior by enabling all modules unless a target explicitly disables one.
- Code paths changed:
  - `dsl/contracts.py`
  - `dsl/certificate_schema.py`
  - `optimizer/pipeline.py`
  - `optimizer/m3_mssu.py`
  - `optimizer/m4_typed_dag.py`
  - `optimizer/m5_scheduler.py`
  - `optimizer/m6_trust.py`
  - `floweaver_cli.py`
  - `tests/test_m3_mssu.py`
- Validation commands:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m compileall optimizer profile_builder runtime dsl alignment_layer counterexample_layer tests scripts floweaver_cli.py`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest tests/test_m3_mssu.py tests/test_m4_typed_dag.py tests/test_m5_scheduler.py tests/test_combined_micro_refinement.py tests/test_end_to_end.py --tb=short`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest --tb=short`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python floweaver_cli.py optimize --integration-name smoke --profile-path data/profiles/default/ha_profile.json --optimization-target /tmp/floweaver_smoke_target.json --out-dir /tmp/floweaver_pipeline_smoke`
- Validation results:
  - Compile check: passed.
  - Targeted tests: 138 passed.
  - Full tests: 357 passed.
  - Smoke pipeline: M1-M7/M6 completed; `micro_level_scheduler_result.json` was emitted; micro validation passed; Trust Validator strict/tolerant pass `6/6`.
- Caveat:
  - Benchmark target JSON files may still contain the physical workspace path if they are executable inputs. Those paths should only be rewritten after the repository directory is actually moved.

## 2026-04-13-m5-ble-api-frontier-packing

- Date: 2026-04-13 15:24 Asia/Shanghai
- Scope: M5 scheduler only, focused on bounded coarse frontier packing for weak mixed BLE/API snapshot cases.
- Problem: Several mixed snapshot/readiness cases had low coarse-plan gain because the scheduler treated a long BLE prefix as a hard practical frontier and delayed ready cloud/local reads until after the BLE lane.
- Change:
  - Added a conservative `ble_api_frontier` window in `optimizer/m5_scheduler.py`.
  - The new window only anchors on one ready BLE action and only admits ready `CLOUD`/`LOCAL` read-safe API actions in `pre_control_acquisition`.
  - It does not admit a second BLE action and does not cross a later BLE action before the API frontier, because current M6 trace comparison cannot prove API reads moved ahead of visible BLE ops without a wider equivalence rule.
  - Cloud reads admitted by this path require explicit bucket/session metadata, so unaffinitized cloud reads keep the previous conservative behavior.
- Code paths changed:
  - `optimizer/m5_scheduler.py`
  - `tests/test_m5_scheduler.py`
- Regression tests added:
  - Normal cloud/local frontier extraction still refuses to skip a ready BLE barrier.
  - `ble_api_frontier` can pack API reads with a single BLE anchor when no later BLE action is crossed.
  - Legacy M5 conservative grouping behavior remains unchanged outside the explicit `ble_api_frontier` optimizer path.
- Validation commands:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest tests/test_m5_scheduler.py --tb=short`
  - `FLOWEAVER_LLM_API_BASE_URL='http://127.0.0.1:9' FLOWEAVER_LLM_API_KEY='cache-only' FLOWEAVER_LLM_MODEL='gpt-5' FLOWEAVER_LLM_TIMEOUT_S='1' PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python scripts/run_vdev_benchmarks.py --workers 1 --cases vdev_holiday_vacation_mode_full_audit_01 vdev_vacation_departure_final_audit_01 vdev_weekend_whole_home_snapshot_profile_01 vdev_morning_wakeup_readiness_profile_01 vdev_ble_safety_sweep_routine_01`
- Validation results:
  - M5 unit tests: 61 passed.
  - Targeted rerun M5 execution-plan latency:
    - `vdev_holiday_vacation_mode_full_audit_01`: 15420 ms -> 13920 ms.
    - `vdev_vacation_departure_final_audit_01`: 11670 ms -> 11100 ms.
    - `vdev_weekend_whole_home_snapshot_profile_01`: 9570 ms -> 8070 ms.
    - `vdev_morning_wakeup_readiness_profile_01`: 6800 ms -> 6350 ms.
    - `vdev_ble_safety_sweep_routine_01`: unchanged at 11600 ms, as expected for a BLE-only case under the current BLE atomic coarse model.
  - M6 status on targeted rerun: all five cases strict `6`, tolerant `6`, counterexamples `0`.
  - Important caveat: `vdev_holiday_vacation_mode_full_audit_01`, `vdev_vacation_departure_final_audit_01`, and `vdev_weekend_whole_home_snapshot_profile_01` still require M6 rollback iterations and their final `m5_trust_plan` falls back to serial timing. This is a validator/model boundary, not an M5 packing failure: current M6 does not treat API reads moved across independent but visible non-group actions as commutable unless those actions are represented in the same parallel action scope.
- Traceable artifacts:
  - Targeted run root: `<repo>/data/optimizer_runs/vdev_benchmarks`
  - Updated M5 plans: `<repo>/data/optimizer_runs/vdev_benchmarks/*/m5_execution_plan.json`
  - M6 rollback/progress files: `<repo>/data/optimizer_runs/vdev_benchmarks/*/m6_progress.json`

## 2026-04-12-m1-m2-m3-grounding-generalization-fix

- Date: 2026-04-12 21:54 Asia/Shanghai
- Scope: Coarse pipeline grounding/reduction only, focused on M1 runtime carrier discovery, M1 grounding-profile emission, M2 seed retention, and M3 generalized secondary binding.
- Problem: After adding broader integration/profile coverage, 16 benchmark cases failed before M6: 12 at M1 and 5 at M3. These were not schedule-equivalence failures; they were grounding/reduction failures before the coarse plan could be validated.
- Root causes:
  - `optimizer/pipeline.py`: runtime carrier expansion stopped scanning sibling files whenever the currently bound platform file had any positive support score, so weak platform matches such as `async_migrate` or media control methods could hide real `coordinator.py::_async_update_data` carriers.
  - `optimizer/m1_detector_builder.py`: generated read rules could include `forbidden_runtime_roles: helper` even when the selected positive carrier was the private HA coordinator update method `_async_update_data`, making the emitted rule self-contradictory.
  - `optimizer/m1_markers.py`: duplicate grounding-profile markers at the same code location were dropped by a location-only dedupe key, so two rules for the same BLE runtime path but different action sets could lose the later action set.
  - `optimizer/m2_reduction.py`: generic `CLOUD_OP` target seeds were removed when a specific `CLOUD_HTTP_CALL` peer covered only the primary action, causing generalized secondary actions to disappear before M3.
  - `optimizer/m3_mssu.py`: generic protocol markers with generalized secondary bindings could still be treated as shared infra or yield to incomplete specific peers.
- Code paths changed:
  - `optimizer/pipeline.py`
  - `optimizer/m1_detector_builder.py`
  - `optimizer/m1_markers.py`
  - `optimizer/m2_reduction.py`
  - `optimizer/m3_mssu.py`
  - `tests/test_end_to_end.py`
  - `tests/test_m1_detector_builder.py`
  - `tests/test_m1_markers.py`
  - `tests/test_m2_reduction.py`
  - `tests/test_m3_mssu.py`
- Regression tests added:
  - Weak platform read binding expands to coordinator runtime carrier even when the platform file has misleading positive support.
  - Private coordinator update carrier `_async_update_data` does not get blocked by `helper` in generated read rules.
  - Duplicate profile-generated markers at the same code location merge distinct action sets instead of dropping later refs.
  - M2 keeps generalized generic protocol seeds when the specific peer does not cover the full action set.
  - M3 keeps generalized secondary refs and does not mark them as shared infra when a specific peer is incomplete.
- Validation commands:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest tests/test_m1_markers.py tests/test_end_to_end.py tests/test_m1_detector_builder.py tests/test_m2_reduction.py tests/test_m3_mssu.py tests/test_m4_typed_dag.py --tb=short`
  - `FLOWEAVER_LLM_API_BASE_URL='http://127.0.0.1:9' FLOWEAVER_LLM_API_KEY='cache-only' FLOWEAVER_LLM_MODEL='gpt-5' FLOWEAVER_LLM_TIMEOUT_S='1' PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python scripts/run_vdev_benchmarks.py --workers 4 --cases vdev_party_scene_activation_01 vdev_morning_wakeup_ramp_01 vdev_workday_focus_mode_01 vdev_guest_suite_welcome_01 vdev_storm_lockdown_safety_01 vdev_whole_family_morning_comfort_snapshot_01 vdev_bad_air_morning_recovery_01 vdev_leave_home_safety_sweep_profile_01 vdev_vacation_departure_final_audit_01 vdev_late_night_entertainment_shutdown_01 vdev_overnight_quiet_hours_snapshot_01 vdev_weekend_whole_home_snapshot_profile_01 vdev_indoor_air_climate_audit_01 vdev_party_preparation_full_sweep_01 vdev_holiday_vacation_mode_full_audit_01 vdev_ble_safety_sweep_routine_01`
  - `FLOWEAVER_LLM_API_BASE_URL='http://127.0.0.1:9' FLOWEAVER_LLM_API_KEY='cache-only' FLOWEAVER_LLM_MODEL='gpt-5' FLOWEAVER_LLM_TIMEOUT_S='1' PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python scripts/run_vdev_benchmarks.py --workers 1 --cases vdev_ble_safety_sweep_routine_01`
- Validation results:
  - Unit/regression tests: 150 passed.
  - Targeted benchmark rerun: all 16 previously failing cases are now `status=ok` with M3 build `OK` and no missing critical actions.
  - Final single-case verification for `vdev_ble_safety_sweep_routine_01`: M6 strict `6`, tolerant `6`, counterexamples `0`, rollback iterations `0`.
- Traceable artifacts:
  - 16-case rerun report: `<repo>/data/targets/vdev_benchmarks/benchmark_run_e0c56f9c024d4c4cb082c2c7b04fba7e.md`
  - Final BLE safety rerun report: `<repo>/data/targets/vdev_benchmarks/benchmark_run_e2c99671d1ab4a96a7d7475df166b550.md`
  - Final BLE safety run dir: `<repo>/data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01`

## 2026-04-12-coarse-m4-m5-scope-fallback-fix

- Date: 2026-04-12 16:57 Asia/Shanghai
- Scope: Coarse pipeline only, focused on M4 soft-constraint scoping and M5 scheduler policy derivation/frontier packing.
- Problem: Old benchmark cases regressed to 0% coarse gain after profile/rule updates because a local API fallback was widened into global serialization.
- Root causes:
  - `optimizer/m4_typed_dag.py`: explicit soft-constraint scope hints such as `LOCAL_API_READ` fell back to the full critical graph when they did not match any MSSU.
  - `optimizer/m5_scheduler.py`: `serialize_local_api_reads` was matched by the generic `serialize` substring check and set `derived_policy.total_limit = 1`.
  - `optimizer/m5_scheduler.py`: frontier-window blocking treated an earlier incompatible cloud singleton as a blocker for later legal cloud batch candidates.
- Code paths changed:
  - `optimizer/m4_typed_dag.py`
  - `optimizer/m5_scheduler.py`
  - `tests/test_m4_typed_dag.py`
  - `tests/test_m5_scheduler.py`
- Regression tests added:
  - Explicit scoped soft constraints do not widen to the critical graph when the scope hint has no match.
  - Explicit scoped soft constraints still bind when matching MSSUs exist.
  - `serialize_local_api_reads` remains local-lane scoped and does not serialize cloud batching.
  - Frontier-window packing keeps a legal cloud batch bucket even when an earlier cloud action is incompatible with that bucket.
- Validation commands:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest tests/test_m4_typed_dag.py tests/test_m5_scheduler.py --tb=short`
  - `FLOWEAVER_LLM_API_BASE_URL='http://127.0.0.1:9' FLOWEAVER_LLM_API_KEY='cache-only' FLOWEAVER_LLM_MODEL='gpt-5' FLOWEAVER_LLM_TIMEOUT_S='1' PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python scripts/run_vdev_benchmarks.py --workers 4`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python scripts/run_combined_micro_refinement.py --cases $(tr '\n' ' ' < /tmp/floweaver_ok_cases_after_coarse_fix.txt)`
- Validation results:
  - M4/M5 unit tests: 86 passed.
  - Benchmark: 56 total cases, 40 coarse/M6 ok, 16 failed before coarse validation.
  - Coarse total over ok cases: GT 238950 ms -> coarse 196980 ms, saved 41970 ms, 17.6%.
  - Combined micro total over ok cases: GT 238950 ms -> micro 180136 ms, saved 58814 ms, 24.6%.
  - Combined micro additional saving over coarse: 16844 ms, 8.6% over coarse.
  - Coarse zero-gain ok cases: `vdev_ble_safety_sweep_stress_01`, `vdev_whole_home_ble_safety_sweep_01`; both are BLE-only and expected under the current conservative BLE atomic coarse model.
- Traceable artifacts:
  - Benchmark report: `<repo>/data/targets/vdev_benchmarks/benchmark_run_28a76fe6a26b4035bb294da0c1c85f93.md`
  - Combined micro report: `<repo>/data/targets/vdev_benchmarks/COMBINED_MICRO_REFINEMENT_REPORT.md`
  - Latency comparison report: `<repo>/data/targets/vdev_benchmarks/LATENCY_COMPARISON_AFTER_COARSE_FIX.md`
  - Machine-readable latency comparison: `<repo>/data/targets/vdev_benchmarks/latency_comparison_after_coarse_fix.json`

## 2026-04-15-profile-builder-llm-discovery

- Date: 2026-04-15 Asia/Shanghai
- Scope: Profile Builder only.
- Goal: Add an optional LLM candidate-discovery layer without weakening the deterministic profile trust boundary.
- Design:
  - LLM output is treated as candidate data, not ground truth.
  - Accepted candidates must pass local AST/source verification: resolvable source refs, valid line ranges, optional symbol existence, observed call attrs, supported marker/family type, and plausible protocol context.
  - Default Profile Builder behavior remains deterministic because LLM discovery is disabled unless explicitly requested.
- Code paths changed:
  - `profile_builder/llm_discovery.py`
  - `profile_builder/pipeline.py`
  - `floweaver_cli.py`
  - `tests/test_profile_builder.py`
  - `docs/profile_builder_llm_discovery.md`
- New artifacts when enabled:
  - `llm_candidate_request.json`
  - `llm_candidate_report.json`
  - `llm_candidate_verification.json`
  - `llm_grounding_profiles_auto/*.json`
- Validation commands:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest tests/test_profile_builder.py --tb=short`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python floweaver_cli.py build-profile --docs-root data/docs_snapshot --repo-root data/repo_snapshot --tests-root data/tests_snapshot --out-dir /tmp/floweaver_profile_builder_llm_smoke --profile-id smoke_llm_discovery --enable-llm-discovery`
  - `FLOWEAVER_LLM_API_BASE_URL='http://127.0.0.1:9' FLOWEAVER_LLM_API_KEY='cache-only' FLOWEAVER_LLM_MODEL='gpt-5' FLOWEAVER_LLM_TIMEOUT_S='1' PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python scripts/run_vdev_benchmarks.py --workers 1 --cases vdev_homecoming_security_ambience_merge_01`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python scripts/run_combined_micro_refinement.py --cases vdev_homecoming_security_ambience_merge_01`
- Validation results:
  - Profile Builder tests: 52 passed.
  - Real snapshot Profile Builder smoke: built `/tmp/floweaver_profile_builder_llm_smoke/ha_profile.json`; LLM discovery enabled with empty candidates, deterministic profile built with 13 rules and 20 detectors.
  - Random smoke benchmark `vdev_homecoming_security_ambience_merge_01`: coarse/M6 status `ok`, strict `6`, tolerant `6`, counterexamples `0`.
  - Combined micro refinement on the same case: validator passed, conflict count `0`, estimated `1900 ms -> 1875 ms`.

### 2026-04-15-profile-builder-evidence-layering

- Scope: Profile Builder evidence admission policy.
- Problem: After adding LLM candidate discovery, deterministic extraction should not remain responsible for exhaustive integration-specific semantic classification.
- Change:
  - Added a raw/semantic/facts split.
  - `evidence_bank_raw.json` preserves all deterministic extracted evidence and verified LLM synthetic evidence.
  - `profile_facts.json` records AST file/function/import/call facts for LLM candidate verification and audit.
  - `evidence_bank.json` now contains the semantic evidence admitted into clustering, normalization, gate, hardening, and final profile synthesis.
  - Added `evidence_policy_report.json` with kept/dropped counts and examples.
  - Default policy is `core_plus_verified`; `legacy` is available through `--evidence-semantic-policy legacy`.
- Code paths changed:
  - `profile_builder/evidence_policy.py`
  - `profile_builder/pipeline.py`
  - `floweaver_cli.py`
  - `tests/test_profile_builder.py`
  - `docs/profile_builder_llm_discovery.md`
- Validation commands:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m pytest tests/test_profile_builder.py --tb=short`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python floweaver_cli.py build-profile --docs-root data/docs_snapshot --repo-root data/repo_snapshot --tests-root data/tests_snapshot --out-dir /tmp/floweaver_profile_builder_policy_smoke --profile-id smoke_policy`
  - `FLOWEAVER_LLM_API_BASE_URL='http://127.0.0.1:9' FLOWEAVER_LLM_API_KEY='cache-only' FLOWEAVER_LLM_MODEL='gpt-5' FLOWEAVER_LLM_TIMEOUT_S='1' PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python floweaver_cli.py optimize --integration-name vdev_homecoming_security_ambience_merge_01 --profile-path /tmp/floweaver_profile_builder_policy_smoke/ha_profile.json --optimization-target data/targets/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01.json --out-dir /tmp/floweaver_policy_optimizer_smoke --rollback-max-steps 6`
- Validation results:
  - Profile Builder tests: 54 passed.
  - Snapshot profile smoke: raw evidence `1663`, semantic evidence `1623`, filtered weak/extended hint evidence `40`, facts `1007` files / `10131` functions.
  - Optimizer smoke with the newly built profile: strict `6`, tolerant `6`, counterexamples `0`, rollback iterations `4`.
