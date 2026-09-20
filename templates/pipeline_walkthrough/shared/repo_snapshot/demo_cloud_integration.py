from __future__ import annotations


async def async_setup_entry(hass, entry):
    result = await cloud_client.call_api("tuya:device.control")
    entity = DemoCloudEntity()
    entity.async_write_ha_state()
    return result


async def async_unload_entry(hass, entry):
    data = hass.data.get(entry.entry_id, {})
    unsub = data.get("unsub")
    if unsub:
        unsub()
    return True


class DemoCloudEntity:
    def async_write_ha_state(self):
        return None
