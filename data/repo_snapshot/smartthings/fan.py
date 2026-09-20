

from __future__ import annotations

import math
from typing import Any

from pysmartthings import Attribute, Capability, Command, SmartThings

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)
from homeassistant.util.scaling import int_states_in_range

from . import FullDevice, SmartThingsConfigEntry
from .const import MAIN
from .entity import SmartThingsEntity

SPEED_RANGE = (1, 3)

SMART = 14
PRESET_SMART = "smart"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartThingsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    entry_data = entry.runtime_data
    entities: list[FanEntity] = [
        SmartThingsFan(entry_data.client, device)
        for device in entry_data.devices.values()
        if Capability.SWITCH in device.status[MAIN]
        and any(
            capability in device.status[MAIN]
            for capability in (
                Capability.FAN_SPEED,
                Capability.AIR_CONDITIONER_FAN_MODE,
            )
        )
        and Capability.THERMOSTAT_COOLING_SETPOINT not in device.status[MAIN]
    ]
    entities.extend(
        SmartThingsHood(entry_data.client, device)
        for device in entry_data.devices.values()
        if Capability.SWITCH in device.status[MAIN]
        and Capability.SAMSUNG_CE_HOOD_FAN_SPEED in device.status[MAIN]
        and (
            device.status[MAIN][Capability.SAMSUNG_CE_HOOD_FAN_SPEED][
                Attribute.SETTABLE_MIN_FAN_SPEED
            ].value
            == SMART
        )
    )
    async_add_entities(entities)


class SmartThingsFan(SmartThingsEntity, FanEntity):


    _attr_name = None
    _attr_speed_count = int_states_in_range(SPEED_RANGE)

    def __init__(self, client: SmartThings, device: FullDevice) -> None:

        super().__init__(
            client,
            device,
            {
                Capability.SWITCH,
                Capability.FAN_SPEED,
                Capability.AIR_CONDITIONER_FAN_MODE,
            },
        )
        self._attr_supported_features = self._determine_features()

    def _determine_features(self):
        flags = FanEntityFeature.TURN_OFF | FanEntityFeature.TURN_ON

        if self.supports_capability(Capability.FAN_SPEED):
            flags |= FanEntityFeature.SET_SPEED
        if self.supports_capability(Capability.AIR_CONDITIONER_FAN_MODE):
            flags |= FanEntityFeature.PRESET_MODE

        return flags

    async def async_set_percentage(self, percentage: int) -> None:

        if percentage == 0:
            await self.execute_device_command(Capability.SWITCH, Command.OFF)
        else:
            value = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
            await self.execute_device_command(
                Capability.FAN_SPEED,
                Command.SET_FAN_SPEED,
                argument=value,
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:

        await self.execute_device_command(
            Capability.AIR_CONDITIONER_FAN_MODE,
            Command.SET_FAN_MODE,
            argument=preset_mode,
        )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:

        if (
            FanEntityFeature.SET_SPEED in self._attr_supported_features
            and percentage is not None
        ):
            await self.async_set_percentage(percentage)
        else:
            await self.execute_device_command(Capability.SWITCH, Command.ON)

    async def async_turn_off(self, **kwargs: Any) -> None:

        await self.execute_device_command(Capability.SWITCH, Command.OFF)

    @property
    def is_on(self) -> bool:

        return self.get_attribute_value(Capability.SWITCH, Attribute.SWITCH) == "on"

    @property
    def percentage(self) -> int | None:

        return ranged_value_to_percentage(
            SPEED_RANGE,
            self.get_attribute_value(Capability.FAN_SPEED, Attribute.FAN_SPEED),
        )

    @property
    def preset_mode(self) -> str | None:




        if not self.supports_capability(Capability.AIR_CONDITIONER_FAN_MODE):
            return None
        return self.get_attribute_value(
            Capability.AIR_CONDITIONER_FAN_MODE, Attribute.FAN_MODE
        )

    @property
    def preset_modes(self) -> list[str] | None:




        if not self.supports_capability(Capability.AIR_CONDITIONER_FAN_MODE):
            return None
        return self.get_attribute_value(
            Capability.AIR_CONDITIONER_FAN_MODE, Attribute.SUPPORTED_AC_FAN_MODES
        )


class SmartThingsHood(SmartThingsEntity, FanEntity):


    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.SET_SPEED
    )
    _attr_preset_modes = [PRESET_SMART]
    _attr_translation_key = "hood"

    def __init__(self, client: SmartThings, device: FullDevice) -> None:

        super().__init__(
            client,
            device,
            {
                Capability.SWITCH,
                Capability.SAMSUNG_CE_HOOD_FAN_SPEED,
            },
        )

    @property
    def fan_speeds(self) -> list[int]:

        return [
            speed
            for speed in self.get_attribute_value(
                Capability.SAMSUNG_CE_HOOD_FAN_SPEED, Attribute.SUPPORTED_HOOD_FAN_SPEED
            )
            if speed != SMART
        ]

    async def async_set_preset_mode(self, preset_mode: str) -> None:

        await self.execute_device_command(
            Capability.SAMSUNG_CE_HOOD_FAN_SPEED,
            Command.SET_HOOD_FAN_SPEED,
            argument=SMART,
        )

    async def async_set_percentage(self, percentage: int) -> None:

        if percentage == 0:
            await self.execute_device_command(Capability.SWITCH, Command.OFF)
        else:
            await self.execute_device_command(
                Capability.SAMSUNG_CE_HOOD_FAN_SPEED,
                Command.SET_HOOD_FAN_SPEED,
                argument=percentage_to_ordered_list_item(self.fan_speeds, percentage),
            )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:

        await self.execute_device_command(Capability.SWITCH, Command.ON)

    async def async_turn_off(self, **kwargs: Any) -> None:

        await self.execute_device_command(Capability.SWITCH, Command.OFF)

    @property
    def is_on(self) -> bool:

        return self.get_attribute_value(Capability.SWITCH, Attribute.SWITCH) == "on"

    @property
    def preset_mode(self) -> str | None:

        if (
            self.get_attribute_value(
                Capability.SAMSUNG_CE_HOOD_FAN_SPEED, Attribute.HOOD_FAN_SPEED
            )
            == SMART
        ):
            return PRESET_SMART
        return None

    @property
    def percentage(self) -> int | None:

        fan_speed = self.get_attribute_value(
            Capability.SAMSUNG_CE_HOOD_FAN_SPEED, Attribute.HOOD_FAN_SPEED
        )
        if fan_speed == SMART:
            return None
        return ordered_list_item_to_percentage(self.fan_speeds, fan_speed)

    @property
    def speed_count(self) -> int:

        return len(self.fan_speeds)
