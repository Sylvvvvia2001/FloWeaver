

from __future__ import annotations

from typing import Any

from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.services import Service, ServicesTypes

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_BATTERY_LEVEL, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KNOWN_DEVICES
from .connection import HKDevice
from .entity import HomeKitEntity

CURRENT_STATE_MAP = {
    0: AlarmControlPanelState.ARMED_HOME,
    1: AlarmControlPanelState.ARMED_AWAY,
    2: AlarmControlPanelState.ARMED_NIGHT,
    3: AlarmControlPanelState.DISARMED,
    4: AlarmControlPanelState.TRIGGERED,
}

TARGET_STATE_MAP = {
    AlarmControlPanelState.ARMED_HOME: 0,
    AlarmControlPanelState.ARMED_AWAY: 1,
    AlarmControlPanelState.ARMED_NIGHT: 2,
    AlarmControlPanelState.DISARMED: 3,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    hkid: str = config_entry.data["AccessoryPairingID"]
    conn: HKDevice = hass.data[KNOWN_DEVICES][hkid]

    @callback
    def async_add_service(service: Service) -> bool:
        if service.type != ServicesTypes.SECURITY_SYSTEM:
            return False
        info = {"aid": service.accessory.aid, "iid": service.iid}
        entity = HomeKitAlarmControlPanelEntity(conn, info)
        conn.async_migrate_unique_id(
            entity.old_unique_id, entity.unique_id, Platform.ALARM_CONTROL_PANEL
        )
        async_add_entities([entity])
        return True

    conn.add_listener(async_add_service)


class HomeKitAlarmControlPanelEntity(HomeKitEntity, AlarmControlPanelEntity):


    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )
    _attr_code_arm_required = False

    def get_characteristic_types(self) -> list[str]:

        return [
            CharacteristicsTypes.SECURITY_SYSTEM_STATE_CURRENT,
            CharacteristicsTypes.SECURITY_SYSTEM_STATE_TARGET,
            CharacteristicsTypes.BATTERY_LEVEL,
        ]

    @property
    def alarm_state(self) -> AlarmControlPanelState:

        return CURRENT_STATE_MAP[
            self.service.value(CharacteristicsTypes.SECURITY_SYSTEM_STATE_CURRENT)
        ]

    async def async_alarm_disarm(self, code: str | None = None) -> None:

        await self.set_alarm_state(AlarmControlPanelState.DISARMED, code)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:

        await self.set_alarm_state(AlarmControlPanelState.ARMED_AWAY, code)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:

        await self.set_alarm_state(AlarmControlPanelState.ARMED_HOME, code)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:

        await self.set_alarm_state(AlarmControlPanelState.ARMED_NIGHT, code)

    async def set_alarm_state(
        self, state: AlarmControlPanelState, code: str | None = None
    ) -> None:

        await self.async_put_characteristics(
            {CharacteristicsTypes.SECURITY_SYSTEM_STATE_TARGET: TARGET_STATE_MAP[state]}
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:

        battery_level = self.service.value(CharacteristicsTypes.BATTERY_LEVEL)

        if not battery_level:
            return {}
        return {ATTR_BATTERY_LEVEL: battery_level}
