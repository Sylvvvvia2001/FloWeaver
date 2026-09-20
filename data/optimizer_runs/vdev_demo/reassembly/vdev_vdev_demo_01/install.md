# Install Generated VDev Component

1. Copy the generated `custom_components/` folder into your Home Assistant config directory.
2. Restart Home Assistant.
3. Call service `vdev_vdev_demo_01.run` from Developer Tools -> Services.
4. Check runtime trace in `hass.data[DOMAIN]["runtime"]["event_trace"]` for debugging.

Generated at: `data/optimizer_runs/vdev_demo/reassembly/vdev_vdev_demo_01`
