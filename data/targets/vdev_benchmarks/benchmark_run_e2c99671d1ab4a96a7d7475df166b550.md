# VDev Benchmark Run Report

- Run ID: `e2c99671d1ab4a96a7d7475df166b550`
- Case Count: `1`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_ble_safety_sweep_routine_01 | Profile Coverage - Realistic Stress Routines | ok | 17 | 6 | 0 | yes |

## Case Details

### BLE Safety Sweep Routine (`vdev_ble_safety_sweep_routine_01`)

- Story: At a fixed time, the routine performs a whole-home BLE safety sweep over curtains, doors, windows, motion sensors, bedside lamps, environmental sensors, and ESPHome transport state.
- Protocol Mix: BLE 15 / HA 2
- Main Action Types: read_sensor x8, refresh_cover x3, read_status x2, write x2, connect x1
- Final Schedule: `17` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01`

**Schedule Interpretation**

The first 15 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_015 -> batch_016. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `5` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, esphome:3, ruuvitag_ble:1, switchbot:4, xiaomi_ble:8` | `vdev_vdev_ble_safety_sweep_routine_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/airthings_ble/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 5 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_ble_safety_sweep_routine_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`
