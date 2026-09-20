# API Micro-Refinement

The API refiner processes serial cloud and local API segments in the macro execution plan. It models request preparation, transport, parsing, aggregation, and state writeback, then validates bounded pre-request overlap.

## Phase Models

The shared model follows `API_PREPARE -> API_SESSION_READY -> API_REQUEST_SEND -> API_RESPONSE_RECV -> API_PARSE_NORMALIZE -> API_AGGREGATE -> HA_STATE_WRITE`.

Cloud actions add authentication checks, rate-budget checks, backoff, and batch-commit phases. Local HTTP actions model endpoint resolution, session preparation, request/response, parsing, and cache updates. MQTT reads model cached-message access, parsing, and state writeback.

## Selection and Constraints

Eligible segments consist of consecutive runtime API batches with a consistent protocol and phase model. Capability classes distinguish cloud reads, cloud controls, local HTTP reads, local HTTP controls, and MQTT reads. Each class has configurable length and duration thresholds.

Local HTTP refinement overlaps the next endpoint/session preparation with the current request or response. Cloud refinement overlaps the next authentication, budget, and preparation phases with the current request or response. MQTT reads retain their serial model.

Request sends remain serial across actions. Completion order is preserved, lookahead is limited to one action, and parse, aggregate, commit, and writeback phases retain their ordering. Backoff cannot be bypassed. Shared-session requirements and event-loop phase budgets constrain admission. Poll frequency and refresh counts are unchanged.

## Configuration

Defaults are stored in `data/targets/vdev_benchmarks/api_micro_refinement_defaults.json`. Use `--config` with `scripts/run_api_micro_refinement.py` to supply another policy.

## Validation and Outputs

Validation checks phase order, completion order, lookahead, request exclusivity, coordinator/session constraints, backoff, and writeback ordering.

The standalone script consumes the benchmark manifest, policy, and existing `m5_execution_plan.json` files. It writes per-case `api_micro_refinement.json` and `api_micro_refined_plan_overlay.json`, an aggregate summary, and `API_MICRO_REFINEMENT_REPORT.md`.

The main pipeline invokes this refiner through the combined micro-level scheduler. Accepted refinements are represented in plan metadata and evaluated within the micro-event model.
