

from __future__ import annotations

from typing import Any

import switchbot
from switchbot import SwitchbotModel

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SwitchbotConfigEntry, SwitchbotDataUpdateCoordinator
from .entity import SwitchbotEntity

PARALLEL_UPDATES = 0

DEVICE_SUPPORT_PROTOCOL_VERSION_1 = [
    SwitchbotModel.K10_VACUUM,
    SwitchbotModel.K10_PRO_VACUUM,
]

PROTOCOL_VERSION_1_STATE_TO_HA_STATE: dict[int, VacuumActivity] = {
    0: VacuumActivity.CLEANING,
    1: VacuumActivity.DOCKED,
}

PROTOCOL_VERSION_2_STATE_TO_HA_STATE: dict[int, VacuumActivity] = {
    1: VacuumActivity.IDLE,
    2: VacuumActivity.DOCKED,
    3: VacuumActivity.DOCKED,
    4: VacuumActivity.IDLE,
    5: VacuumActivity.IDLE,
    6: VacuumActivity.CLEANING,
    7: VacuumActivity.CLEANING,
    8: VacuumActivity.CLEANING,
    9: VacuumActivity.CLEANING,
    10: VacuumActivity.CLEANING,
    11: VacuumActivity.PAUSED,
    12: VacuumActivity.CLEANING,
    13: VacuumActivity.ERROR,
    14: VacuumActivity.CLEANING,
    15: VacuumActivity.RETURNING,
    16: VacuumActivity.CLEANING,
    17: VacuumActivity.CLEANING,
    18: VacuumActivity.CLEANING,
    19: VacuumActivity.CLEANING,
    20: VacuumActivity.CLEANING,
    21: VacuumActivity.IDLE,
    22: VacuumActivity.IDLE,
    23: VacuumActivity.CLEANING,
    24: VacuumActivity.RETURNING,
    25: VacuumActivity.IDLE,
    26: VacuumActivity.IDLE,
    27: VacuumActivity.IDLE,
    28: VacuumActivity.IDLE,
    29: VacuumActivity.IDLE,
    30: VacuumActivity.IDLE,
    31: VacuumActivity.IDLE,
    32: VacuumActivity.PAUSED,
    33: VacuumActivity.IDLE,
    34: VacuumActivity.CLEANING,
}

SWITCHBOT_VACUUM_STATE_MAP: dict[int, dict[int, VacuumActivity]] = {
    1: PROTOCOL_VERSION_1_STATE_TO_HA_STATE,
    2: PROTOCOL_VERSION_2_STATE_TO_HA_STATE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    async_add_entities([SwitchbotVacuumEntity(entry.runtime_data)])


class SwitchbotVacuumEntity(SwitchbotEntity, StateVacuumEntity):


    _device: switchbot.SwitchbotVacuum
    _attr_supported_features = (
        VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.START
        | VacuumEntityFeature.STATE
    )
    _attr_translation_key = "vacuum"
    _attr_name = None

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:

        super().__init__(coordinator)
        self.protocol_version = (
            1 if coordinator.model in DEVICE_SUPPORT_PROTOCOL_VERSION_1 else 2
        )

    @property
    def activity(self) -> VacuumActivity | None:

        status_code = self._device.get_work_status()
        return SWITCHBOT_VACUUM_STATE_MAP[self.protocol_version].get(status_code)

    async def async_start(self) -> None:

        self._last_run_success = bool(
            await self._device.clean_up(self.protocol_version)
        )

    async def async_return_to_base(self, **kwargs: Any) -> None:

        self._last_run_success = bool(
            await self._device.return_to_dock(self.protocol_version)
        )
