# BLE Micro-Refinement

The BLE refiner processes serial BLE segments in the macro execution plan. It models transport preparation and transfer phases, proposes bounded overlap, and validates the resulting schedule.

## Phase Model

Each action follows `PREPARE_ADV_SIDE -> PREPARE_CONNECT_SIDE -> BLE_XFER -> BLE_SETTLE`:

- `PREPARE_ADV_SIDE`: shared-scanner discovery and advertisement preparation.
- `PREPARE_CONNECT_SIDE`: controller, backend, and connection-context preparation.
- `BLE_XFER`: data transfer.
- `BLE_SETTLE`: completion, confirmation, and release.

These phases form a scheduling model. Their durations are estimates supplied to the refiner.

## Selection and Constraints

Eligible segments consist of consecutive single-action BLE batches. Actions are grouped by capability (`read_like`, `control_like`, `session_chain`, or `generic`) and must meet the configured length, duration, and overlap-admission thresholds.

The default policy permits the next action's advertisement preparation to overlap the current action's transfer or settling phase. Transfers remain serial, action completion order is preserved, and lookahead is limited to one action. Connection preparation remains subject to controller and slot constraints.

Same-device, same-session, and subscription actions receive conservative treatment. Source-specific overrides control additional advertisement overlap and narrowly scoped connect-to-subscribe cases. Preparation must be bounded by a timeout and safe to discard.

## Configuration

Defaults are stored in `data/targets/vdev_benchmarks/ble_micro_refinement_defaults.json`. Use `--config` with `scripts/run_ble_micro_refinement.py` to supply another policy.

## Validation and Outputs

Validation checks phase order, transfer exclusivity, completion order, lookahead, scanner availability, controller capacity, device/session constraints, and preparation bounds.

The standalone script consumes the benchmark manifest, policy, and existing `m5_execution_plan.json` files. It writes per-case `ble_micro_refinement.json` and `ble_micro_refined_plan_overlay.json`, an aggregate summary, and `BLE_MICRO_REFINEMENT_REPORT.md`.

The main pipeline also invokes this refiner through the combined micro-level scheduler. Accepted refinements are represented in plan metadata and evaluated within the micro-event model.
