

from __future__ import annotations

from typing import Any

from pydeconz.models.event import EventType
from pydeconz.models.light.light import Light, LightFanSpeed

from homeassistant.components.fan import (
    DOMAIN as FAN_DOMAIN,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from . import DeconzConfigEntry
from .entity import DeconzDevice
from .hub import DeconzHub

ORDERED_NAMED_FAN_SPEEDS: list[LightFanSpeed] = [
    LightFanSpeed.PERCENT_25,
    LightFanSpeed.PERCENT_50,
    LightFanSpeed.PERCENT_75,
    LightFanSpeed.PERCENT_100,
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DeconzConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    hub = config_entry.runtime_data
    hub.entities[FAN_DOMAIN] = set()

    @callback
    def async_add_fan(_: EventType, fan_id: str) -> None:

        fan = hub.api.lights.lights[fan_id]
        if not fan.supports_fan_speed:
            return
        async_add_entities([DeconzFan(fan, hub)])

    hub.register_platform_add_device_callback(
        async_add_fan,
        hub.api.lights.lights,
    )


class DeconzFan(DeconzDevice[Light], FanEntity):


    TYPE = FAN_DOMAIN
    _default_on_speed = LightFanSpeed.PERCENT_50

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, device: Light, hub: DeconzHub) -> None:

        super().__init__(device, hub)
        if device.fan_speed in ORDERED_NAMED_FAN_SPEEDS:
            self._default_on_speed = device.fan_speed

    @property
    def is_on(self) -> bool:

        return self._device.fan_speed != LightFanSpeed.OFF

    @property
    def percentage(self) -> int | None:

        if self._device.fan_speed == LightFanSpeed.OFF:
            return 0
        if self._device.fan_speed not in ORDERED_NAMED_FAN_SPEEDS:
            return None
        return ordered_list_item_to_percentage(
            ORDERED_NAMED_FAN_SPEEDS, self._device.fan_speed
        )

    @callback
    def async_update_callback(self) -> None:

        if self._device.fan_speed in ORDERED_NAMED_FAN_SPEEDS:
            self._default_on_speed = self._device.fan_speed
        super().async_update_callback()

    async def async_set_percentage(self, percentage: int) -> None:

        if percentage == 0:
            await self.async_turn_off()
            return
        await self.hub.api.lights.lights.set_state(
            id=self._device.resource_id,
            fan_speed=percentage_to_ordered_list_item(
                ORDERED_NAMED_FAN_SPEEDS, percentage
            ),
        )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:

        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        await self.hub.api.lights.lights.set_state(
            id=self._device.resource_id,
            fan_speed=self._default_on_speed,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:

        await self.hub.api.lights.lights.set_state(
            id=self._device.resource_id,
            fan_speed=LightFanSpeed.OFF,
        )
