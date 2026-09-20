# vDev Benchmarks Archive Summary

- Archived at: `2026-04-01 15:52:03` (Asia/Shanghai)
- Archive root: `data/optimizer_runs/history/20260401_155203`
- Source snapshot: `data/optimizer_runs/vdev_benchmarks`

## Overall

- Total cases: `10`
- Passed end-to-end: `3`
- Failed: `7`

## Passed Cases

- `vdev_tuya_cloud_fleet_01` (strict_pass=6, counterexample_count=0)
- `vdev_mixed_curtain_air_energy_01` (strict_pass=6, counterexample_count=0)
- `vdev_cloud_burst_stress_01` (strict_pass=6, counterexample_count=0)

## Failed Cases (High-level)

All failed cases stopped at `M1` with `GroundingCoverageError`: critical actions could not be grounded into code markers.

Typical failure pattern:
- requested action exists in target, but corresponding runtime marker in current `repo_snapshot` is missing or too weak
- result is missing critical action IDs in `m1_marker_report.json`

Failed case list:
- `vdev_ble_sensor_sweep_01`: missing `A2, A5, A6`
- `vdev_ble_lighting_snapshot_01`: missing `A1, A2, A3, A4`
- `vdev_cloud_hybrid_lane_01`: missing `A3, A4`
- `vdev_presence_comfort_mixed_01`: missing `A1, A2, A6`
- `vdev_cross_transport_hue_ble_tuya_01`: missing `A1, A3, A4, A8`
- `vdev_monitoring_fabric_mqtt_ble_cloud_01`: missing `A1, A3, A4, A8`
- `vdev_ble_congestion_stress_01`: missing `A2, A4, A5, A6`

## Notes

- Cloud-heavy cases now show real batching in execution plans when action metadata includes cloud grouping keys.

## Grounding Analysis

Failures cluster by integration and source file, particularly runtime status and control paths. Lifecycle and state-write markers can still be detected while transport operations lack reliable grounding. Expanding coverage requires detectors for each integration family’s runtime functions, API conventions, and coordinator or transport structure.
