# Latency Comparison After Coarse Pipeline Fix

- Generated at: `2026-04-12T08:57:32.804711+00:00`
- Benchmark report: `data/targets/vdev_benchmarks/benchmark_run_28a76fe6a26b4035bb294da0c1c85f93.md`
- Combined micro report: `data/targets/vdev_benchmarks/COMBINED_MICRO_REFINEMENT_REPORT.md`
- Combined micro summary: `data/optimizer_runs/vdev_benchmarks_combined_micro_refined/summary.json`
- Cases: `56` total, `40` coarse/M6 ok, `16` failed before M6 or M5, `40` combined micro validator pass.
- Coarse avg gain over ok cases: `18.7%`; total GT `238950` ms -> coarse `196980` ms, saved `41970` ms (`17.6%`).
- Micro avg total gain over ok cases: `25.5%`; total GT `238950` ms -> micro `180136` ms, saved `58814` ms (`24.6%`).
- Combined micro additional saving over coarse: `16844` ms (`8.6%` over coarse).
- Coarse zero-gain ok cases: `vdev_ble_safety_sweep_stress_01`, `vdev_whole_home_ble_safety_sweep_01`

## Full Table

| # | Case | Status | GT ms | Coarse ms | Coarse gain | Coarse gain % | Micro ms | Micro gain | Micro gain % | Micro add vs coarse | Micro add % | M6 | Micro validator |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | `vdev_morning_wakeup_readiness_01` | ok | 6850 | 6070 | 780 | 11.4% | 5686 | 1164 | 17.0% | 384 | 6.3% | pass | pass |
| 2 | `vdev_leaving_home_safety_check_01` | ok | 6000 | 4870 | 1130 | 18.8% | 4510 | 1490 | 24.8% | 360 | 7.4% | pass | pass |
| 3 | `vdev_arrival_comfort_preparation_01` | ok | 6730 | 5500 | 1230 | 18.3% | 5170 | 1560 | 23.2% | 330 | 6.0% | pass | pass |
| 4 | `vdev_dinner_home_mode_01` | ok | 5430 | 4300 | 1130 | 20.8% | 4018 | 1412 | 26.0% | 282 | 6.6% | pass | pass |
| 5 | `vdev_night_shutdown_01` | ok | 6650 | 5520 | 1130 | 17.0% | 5082 | 1568 | 23.6% | 438 | 7.9% | pass | pass |
| 6 | `vdev_overnight_health_safety_monitoring_01` | ok | 5660 | 4020 | 1640 | 29.0% | 3750 | 1910 | 33.7% | 270 | 6.7% | pass | pass |
| 7 | `vdev_weekend_whole_home_snapshot_01` | ok | 9480 | 8000 | 1480 | 15.6% | 7382 | 2098 | 22.1% | 618 | 7.7% | pass | pass |
| 8 | `vdev_party_preparation_01` | ok | 5780 | 4300 | 1480 | 25.6% | 4018 | 1762 | 30.5% | 282 | 6.6% | pass | pass |
| 9 | `vdev_party_scene_activation_01` | error: GroundingCoverageError('GROUNDING_FAILED:M3 critical actions not grounded into MSSUs: A7, A8, A9') | - | - | - | - | - | - | - | - | - | - | - |
| 10 | `vdev_movie_night_blackout_01` | ok | 10780 | 8940 | 1840 | 17.1% | 8056 | 2724 | 25.3% | 884 | 9.9% | pass | pass |
| 11 | `vdev_morning_wakeup_ramp_01` | error: GroundingCoverageError('GROUNDING_FAILED:M3 critical actions not grounded into MSSUs: A7, A8, A9') | - | - | - | - | - | - | - | - | - | - | - |
| 12 | `vdev_workday_focus_mode_01` | error: GroundingCoverageError('GROUNDING_FAILED:M3 critical actions not grounded into MSSUs: A8, A9') | - | - | - | - | - | - | - | - | - | - | - |
| 13 | `vdev_guest_suite_welcome_01` | error: GroundingCoverageError('GROUNDING_FAILED:M3 critical actions not grounded into MSSUs: A8, A9') | - | - | - | - | - | - | - | - | - | - | - |
| 14 | `vdev_storm_lockdown_safety_01` | error: GroundingCoverageError('GROUNDING_FAILED:M3 critical actions not grounded into MSSUs: A9') | - | - | - | - | - | - | - | - | - | - | - |
| 15 | `vdev_ble_safety_sweep_stress_01` | ok | 7300 | 7300 | 0 | 0.0% | 6700 | 600 | 8.2% | 600 | 8.2% | pass | pass |
| 16 | `vdev_energy_hvac_audit_01` | ok | 3800 | 2870 | 930 | 24.5% | 2330 | 1470 | 38.7% | 540 | 18.8% | pass | pass |
| 17 | `vdev_arrive_home_lighting_climate_prep_01` | ok | 6950 | 5820 | 1130 | 16.3% | 5427 | 1523 | 21.9% | 393 | 6.8% | pass | pass |
| 18 | `vdev_leave_home_safety_energy_sweep_01` | ok | 7400 | 5920 | 1480 | 20.0% | 5408 | 1992 | 26.9% | 512 | 8.6% | pass | pass |
| 19 | `vdev_good_morning_whole_floor_readiness_01` | ok | 6750 | 5620 | 1130 | 16.7% | 5182 | 1568 | 23.2% | 438 | 7.8% | pass | pass |
| 20 | `vdev_bedtime_lockdown_routine_01` | ok | 7100 | 5620 | 1480 | 20.8% | 5157 | 1943 | 27.4% | 463 | 8.2% | pass | pass |
| 21 | `vdev_rain_coming_indoor_adjustment_01` | ok | 4430 | 3200 | 1230 | 27.8% | 3008 | 1422 | 32.1% | 192 | 6.0% | pass | pass |
| 22 | `vdev_weekend_whole_home_snapshot_extended_01` | ok | 9580 | 8550 | 1030 | 10.8% | 7716 | 1864 | 19.5% | 834 | 9.8% | pass | pass |
| 23 | `vdev_dinner_preparation_readiness_01` | ok | 4580 | 3450 | 1130 | 24.7% | 3270 | 1310 | 28.6% | 180 | 5.2% | pass | pass |
| 24 | `vdev_party_preparation_ambience_check_01` | ok | 5800 | 4320 | 1480 | 25.5% | 4000 | 1800 | 31.0% | 320 | 7.4% | pass | pass |
| 25 | `vdev_workday_departure_office_zone_shutdown_01` | ok | 2900 | 2470 | 430 | 14.8% | 2330 | 570 | 19.7% | 140 | 5.7% | pass | pass |
| 26 | `vdev_kids_room_comfort_safety_snapshot_01` | ok | 5030 | 4600 | 430 | 8.5% | 4228 | 802 | 15.9% | 372 | 8.1% | pass | pass |
| 27 | `vdev_elderly_care_daily_check_01` | ok | 3980 | 3550 | 430 | 10.8% | 3358 | 622 | 15.6% | 192 | 5.4% | pass | pass |
| 28 | `vdev_laundry_utility_room_sweep_01` | ok | 2680 | 2250 | 430 | 16.0% | 2160 | 520 | 19.4% | 90 | 4.0% | pass | pass |
| 29 | `vdev_air_quality_recovery_routine_01` | ok | 3010 | 2330 | 680 | 22.6% | 2215 | 795 | 26.4% | 115 | 4.9% | pass | pass |
| 30 | `vdev_vacation_mode_house_sweep_01` | ok | 10150 | 8670 | 1480 | 14.6% | 7717 | 2433 | 24.0% | 953 | 11.0% | pass | pass |
| 31 | `vdev_homecoming_security_ambience_merge_01` | ok | 3600 | 2370 | 1230 | 34.2% | 2243 | 1357 | 37.7% | 127 | 5.4% | pass | pass |
| 32 | `vdev_school_night_quiet_hours_01` | ok | 5300 | 4640 | 660 | 12.5% | 4267 | 1033 | 19.5% | 373 | 8.0% | pass | pass |
| 33 | `vdev_rainy_commute_preparation_01` | ok | 2700 | 2270 | 430 | 15.9% | 2180 | 520 | 19.3% | 90 | 4.0% | pass | pass |
| 34 | `vdev_energy_hvac_audit_expanded_01` | ok | 4050 | 1820 | 2230 | 55.1% | 1654 | 2396 | 59.2% | 166 | 9.1% | pass | pass |
| 35 | `vdev_whole_home_ble_safety_sweep_01` | ok | 10300 | 10300 | 0 | 0.0% | 9340 | 960 | 9.3% | 960 | 9.3% | pass | pass |
| 36 | `vdev_cloud_burst_living_conditions_snapshot_01` | ok | 4500 | 3570 | 930 | 20.7% | 2864 | 1636 | 36.4% | 706 | 19.8% | pass | pass |
| 37 | `vdev_morning_wakeup_readiness_profile_01` | ok | 7350 | 6800 | 550 | 7.5% | 6362 | 988 | 13.4% | 438 | 6.4% | pass | pass |
| 38 | `vdev_whole_family_morning_comfort_snapshot_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A1') | - | - | - | - | - | - | - | - | - | - | - |
| 39 | `vdev_school_day_quiet_start_check_01` | ok | 4100 | 3450 | 650 | 15.9% | 3233 | 867 | 21.1% | 217 | 6.3% | pass | pass |
| 40 | `vdev_bad_air_morning_recovery_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A1') | - | - | - | - | - | - | - | - | - | - | - |
| 41 | `vdev_leave_home_safety_sweep_profile_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A19') | - | - | - | - | - | - | - | - | - | - | - |
| 42 | `vdev_arrival_home_preparation_profile_01` | ok | 6000 | 4770 | 1230 | 20.5% | 4566 | 1434 | 23.9% | 204 | 4.3% | pass | pass |
| 43 | `vdev_vacation_departure_final_audit_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A28') | - | - | - | - | - | - | - | - | - | - | - |
| 44 | `vdev_come_home_security_comfort_merge_01` | ok | 3800 | 3250 | 550 | 14.5% | 3015 | 785 | 20.7% | 235 | 7.2% | pass | pass |
| 45 | `vdev_bedtime_lockdown_profile_01` | ok | 7600 | 6470 | 1130 | 14.9% | 5917 | 1683 | 22.1% | 553 | 8.5% | pass | pass |
| 46 | `vdev_kids_room_night_safety_check_01` | ok | 4550 | 3670 | 880 | 19.3% | 3388 | 1162 | 25.5% | 282 | 7.7% | pass | pass |
| 47 | `vdev_late_night_entertainment_shutdown_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A7') | - | - | - | - | - | - | - | - | - | - | - |
| 48 | `vdev_overnight_quiet_hours_snapshot_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A1') | - | - | - | - | - | - | - | - | - | - | - |
| 49 | `vdev_weekend_whole_home_snapshot_profile_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A24') | - | - | - | - | - | - | - | - | - | - | - |
| 50 | `vdev_whole_home_energy_hvac_audit_profile_01` | ok | 5500 | 4520 | 980 | 17.8% | 3610 | 1890 | 34.4% | 910 | 20.1% | pass | pass |
| 51 | `vdev_indoor_air_climate_audit_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A1') | - | - | - | - | - | - | - | - | - | - | - |
| 52 | `vdev_security_presence_fabric_snapshot_01` | ok | 8100 | 6750 | 1350 | 16.7% | 6096 | 2004 | 24.7% | 654 | 9.7% | pass | pass |
| 53 | `vdev_party_preparation_full_sweep_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A17, A4') | - | - | - | - | - | - | - | - | - | - | - |
| 54 | `vdev_holiday_vacation_mode_full_audit_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A34') | - | - | - | - | - | - | - | - | - | - | - |
| 55 | `vdev_ble_safety_sweep_routine_01` | error: GroundingCoverageError('GROUNDING_FAILED:M1 critical actions not grounded into code markers: A12') | - | - | - | - | - | - | - | - | - | - | - |
| 56 | `vdev_cloud_burst_living_conditions_snapshot_profile_01` | ok | 6700 | 4270 | 2430 | 36.3% | 3523 | 3177 | 47.4% | 747 | 17.5% | pass | pass |

