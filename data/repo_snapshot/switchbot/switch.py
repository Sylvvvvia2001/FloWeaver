

from __future__ import annotations

import logging
from typing import Any

import switchbot

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import SwitchbotConfigEntry, SwitchbotDataUpdateCoordinator
from .entity import SwitchbotSwitchedEntity, exception_handler

PARALLEL_UPDATES = 0
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    coordinator = entry.runtime_data

    if isinstance(coordinator.device, switchbot.SwitchbotRelaySwitch2PM):
        entries = [
            SwitchbotMultiChannelSwitch(coordinator, channel)
            for channel in range(1, coordinator.device.channel + 1)
        ]
        async_add_entities(entries)
    else:
        async_add_entities([SwitchBotSwitch(coordinator)])


class SwitchBotSwitch(SwitchbotSwitchedEntity, SwitchEntity, RestoreEntity):


    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_translation_key = "bot"
    _attr_name = None
    _device: switchbot.Switchbot

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:

        super().__init__(coordinator)
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:

        await super().async_added_to_hass()
        if not (last_state := await self.async_get_last_state()):
            return
        self._attr_is_on = last_state.state == STATE_ON
        self._last_run_success = last_state.attributes.get("last_run_success")

    @property
    def assumed_state(self) -> bool:

        return not self._device.switch_mode()

    @property
    def is_on(self) -> bool | None:

        if not self._device.switch_mode():
            return self._attr_is_on
        return self._device.is_on()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:

        return {
            **super().extra_state_attributes,
            "switch_mode": self._device.switch_mode(),
        }


class SwitchbotMultiChannelSwitch(SwitchbotSwitchedEntity, SwitchEntity):


    _attr_device_class = SwitchDeviceClass.SWITCH
    _device: switchbot.Switchbot
    _attr_name = None

    def __init__(
        self, coordinator: SwitchbotDataUpdateCoordinator, channel: int
    ) -> None:

        super().__init__(coordinator)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.base_unique_id}-{channel}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.base_unique_id}-channel-{channel}")},
            manufacturer="SwitchBot",
            model_id="RelaySwitch2PM",
            name=f"{coordinator.device_name} Channel {channel}",
        )

    @property
    def is_on(self) -> bool | None:

        return self._device.is_on(self._channel)

    @exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:

        _LOGGER.debug(
            "Turn Switchbot device on %s, channel %d", self._address, self._channel
        )
        await self._device.turn_on(self._channel)
        self.async_write_ha_state()

    @exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:

        _LOGGER.debug(
            "Turn Switchbot device off %s, channel %d", self._address, self._channel
        )
        await self._device.turn_off(self._channel)
        self.async_write_ha_state()
