

from __future__ import annotations

import logging
from typing import Any

from pysmartthings import Attribute, Command, SmartThings
from pysmartthings.capability import Capability

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FullDevice, SmartThingsConfigEntry
from .const import MAIN
from .entity import SmartThingsEntity

_LOGGER = logging.getLogger(__name__)

TURBO_MODE_TO_FAN_SPEED = {
    "silence": "normal",
    "on": "maximum",
    "off": "smart",
    "extraSilence": "quiet",
}

FAN_SPEED_TO_TURBO_MODE = {v: k for k, v in TURBO_MODE_TO_FAN_SPEED.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartThingsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    entry_data = entry.runtime_data
    async_add_entities(
        SamsungJetBotVacuum(entry_data.client, device)
        for device in entry_data.devices.values()
        if Capability.SAMSUNG_CE_ROBOT_CLEANER_OPERATING_STATE in device.status[MAIN]
    )


class SamsungJetBotVacuum(SmartThingsEntity, StateVacuumEntity):


    _attr_name = None
    _attr_translation_key = "vacuum"

    def __init__(self, client: SmartThings, device: FullDevice) -> None:

        super().__init__(
            client,
            device,
            {
                Capability.SAMSUNG_CE_ROBOT_CLEANER_OPERATING_STATE,
                Capability.ROBOT_CLEANER_TURBO_MODE,
            },
        )
        self._attr_supported_features = (
            VacuumEntityFeature.START
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.STATE
        )
        if self.supports_capability(Capability.ROBOT_CLEANER_TURBO_MODE):
            self._attr_supported_features |= VacuumEntityFeature.FAN_SPEED

    @property
    def activity(self) -> VacuumActivity | None:

        status = self.get_attribute_value(
            Capability.SAMSUNG_CE_ROBOT_CLEANER_OPERATING_STATE,
            Attribute.OPERATING_STATE,
        )

        return {
            "cleaning": VacuumActivity.CLEANING,
            "homing": VacuumActivity.RETURNING,
            "idle": VacuumActivity.IDLE,
            "paused": VacuumActivity.PAUSED,
            "docked": VacuumActivity.DOCKED,
            "error": VacuumActivity.ERROR,
            "charging": VacuumActivity.DOCKED,
        }.get(status)

    @property
    def fan_speed_list(self) -> list[str]:

        if not self.supports_capability(Capability.ROBOT_CLEANER_TURBO_MODE):
            return []
        return list(TURBO_MODE_TO_FAN_SPEED.values())

    @property
    def fan_speed(self) -> str | None:

        if not self.supports_capability(Capability.ROBOT_CLEANER_TURBO_MODE):
            return None
        turbo_mode = self.get_attribute_value(
            Capability.ROBOT_CLEANER_TURBO_MODE, Attribute.ROBOT_CLEANER_TURBO_MODE
        )
        return TURBO_MODE_TO_FAN_SPEED.get(turbo_mode)

    async def async_start(self) -> None:

        await self.execute_device_command(
            Capability.SAMSUNG_CE_ROBOT_CLEANER_OPERATING_STATE,
            Command.START,
        )

    async def async_pause(self) -> None:

        await self.execute_device_command(
            Capability.SAMSUNG_CE_ROBOT_CLEANER_OPERATING_STATE, Command.PAUSE
        )

    async def async_return_to_base(self, **kwargs: Any) -> None:

        await self.execute_device_command(
            Capability.SAMSUNG_CE_ROBOT_CLEANER_OPERATING_STATE,
            Command.RETURN_TO_HOME,
        )

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:

        turbo_mode = FAN_SPEED_TO_TURBO_MODE[fan_speed]
        await self.execute_device_command(
            Capability.ROBOT_CLEANER_TURBO_MODE,
            Command.SET_ROBOT_CLEANER_TURBO_MODE,
            turbo_mode,
        )
