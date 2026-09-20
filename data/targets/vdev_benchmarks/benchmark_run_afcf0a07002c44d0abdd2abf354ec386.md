# VDev Benchmark Run Report

- Run ID: `afcf0a07002c44d0abdd2abf354ec386`
- Case Count: `3`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_morning_wakeup_readiness_01 | Morning and Leaving Home Routines | ok | 13 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_01 | Night and Energy Monitoring Routines | ok | 20 | 6 | 0 | yes |
| vdev_energy_hvac_audit_01 | Household Stress and Abnormality Routines | ok | 9 | 6 | 0 | yes |

## Case Details

### Morning Wake-Up Readiness Routine (`vdev_morning_wakeup_readiness_01`)

- Story: Before residents wake up, the system collects bedroom and hallway readiness signals to decide whether the home is already in a comfortable morning state.
- Protocol Mix: BLE 7 / CLOUD 3 / LOCAL 2 / HA 4
- Main Action Types: write x4, status x3, get_state x2, read_status x2, refresh_cover x2
- Final Schedule: `13` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01`

**Schedule Interpretation**

The first 7 BLE actions run serially to avoid shared-radio conflicts. Local reads overlap other reads in batch_009. Writeback follows lane updates and then the overall update: batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `5` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:3, switchbot:3, tuya:4, xiaomi_ble:3` | `vdev_vdev_morning_wakeup_readiness_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/xiaomi_ble/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 5 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_morning_wakeup_readiness_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Weekend Whole-Home Snapshot Routine (`vdev_weekend_whole_home_snapshot_01`)

- Story: During a weekend whole-home snapshot, the routine checks several curtains, rooms, sensors, climate endpoints, lights, plugs, and a few local monitoring sources to generate one house-wide summary.
- Protocol Mix: BLE 8 / CLOUD 7 / LOCAL 4 / HA 4
- Main Action Types: status x7, write x4, get_state x3, read_sensor x3, refresh_cover x3
- Final Schedule: `20` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Local reads overlap other reads in batch_014. Writeback follows lane updates and then the overall update: batch_018 -> batch_019. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `14` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:2, mqtt:1, switchbot:4, tplink:2, tuya:8, xiaomi_ble:3` | `vdev_vdev_weekend_whole_home_snapshot_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/esphome/__init__.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 14 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Cloud Burst Energy & HVAC Audit Routine (`vdev_energy_hvac_audit_01`)

- Story: At a fixed audit time, the routine gathers multiple Tuya lights, energy strips, climate states, and two Ecobee runtime reads to generate one energy and HVAC audit summary.
- Protocol Mix: CLOUD 10 / HA 2
- Main Action Types: status x8, read_runtime x2, write x2
- Final Schedule: `9` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01`

**Schedule Interpretation**

Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `3` integrations / `7` files | `1` generated custom component |
| Main Source Integrations | `ecobee:2, esphome:1, tuya:9` | `vdev_vdev_energy_hvac_audit_01` |
| Main Source Files | `data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py; data/repo_snapshot/tuya/climate.py; data/repo_snapshot/ecobee/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 3 integrations and approximately 7 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_energy_hvac_audit_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`
