# Install Generated VDev Component

1. Copy the generated `custom_components/` folder into your Home Assistant config directory.
2. Restart Home Assistant.
3. Call service `vdev_fallback_vdev.run` from Developer Tools -> Services.
4. Check runtime trace in `hass.data[DOMAIN]["runtime"]["event_trace"]` for debugging.

Generated at: `data/optimizer_runs/demo_compat_m7/reassembly/vdev_fallback_vdev`
