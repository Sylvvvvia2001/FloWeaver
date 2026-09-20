# Install Generated VDev Component

1. Copy the generated `custom_components/` folder into your Home Assistant config directory.
2. Restart Home Assistant.
3. Call service `vdev_vdev_indoor_air_climate_audit_01.run_indoor_air_climate_audit_01` from Developer Tools -> Services.
4. Check runtime trace in `hass.data[DOMAIN]["runtime"]["event_trace"]` for debugging.
5. Optionally pass `export_trace: true` or `trace_path: ...` to persist a run trace for offline diffing.

Generated at: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01`
