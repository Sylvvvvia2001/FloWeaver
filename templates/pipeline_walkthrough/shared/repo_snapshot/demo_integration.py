from __future__ import annotations


async def async_setup_entry(hass, entry):
    coordinator = DemoCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()
    entity = DemoEntity(coordinator)
    entity.async_write_ha_state()
    unsub = dispatcher_connect(hass, "demo_signal", entity.async_write_ha_state)
    hass.data[entry.entry_id] = {"coordinator": coordinator, "unsub": unsub}
    return True


async def async_unload_entry(hass, entry):
    data = hass.data.get(entry.entry_id, {})
    unsub = data.get("unsub")
    if unsub:
        unsub()
    return True


class DemoCoordinator:
    def __init__(self, hass):
        self.hass = hass

    async def async_config_entry_first_refresh(self):
        await self._async_update_data()

    async def _async_update_data(self):
        client = self.hass.data.get("client")
        if client:
            await client.connect()
            await client.read_gatt_char("temp")
            await client.disconnect()


class DemoEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def async_write_ha_state(self):
        return None


def dispatcher_connect(hass, signal, callback):
    def _unsub():
        return None

    return _unsub
