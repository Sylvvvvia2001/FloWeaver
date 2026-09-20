

from __future__ import annotations

from typing import Any

from tuya_device_handlers.device_wrapper.base import DeviceWrapper
from tuya_device_handlers.device_wrapper.common import (
    DPCodeBooleanWrapper,
    DPCodeEnumWrapper,
)
from tuya_device_handlers.device_wrapper.fan import (
    FanDirectionEnumWrapper,
    FanSpeedEnumWrapper,
    FanSpeedIntegerWrapper,
)
from tuya_device_handlers.helpers.homeassistant import TuyaFanDirection
from tuya_sharing import CustomerDevice, Manager

from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TuyaConfigEntry
from .const import TUYA_DISCOVERY_NEW, DeviceCategory, DPCode
from .entity import TuyaEntity
from .util import get_dpcode

_DIRECTION_DPCODES = (DPCode.FAN_DIRECTION,)
_MODE_DPCODES = (DPCode.FAN_MODE, DPCode.MODE)
_OSCILLATE_DPCODES = (DPCode.SWITCH_HORIZONTAL, DPCode.SWITCH_VERTICAL)
_SPEED_DPCODES = (
    DPCode.FAN_SPEED_PERCENT,
    DPCode.FAN_SPEED,
    DPCode.SPEED,
    DPCode.FAN_SPEED_ENUM,
)
_SWITCH_DPCODES = (DPCode.SWITCH_FAN, DPCode.FAN_SWITCH, DPCode.SWITCH)

TUYA_SUPPORT_TYPE: set[DeviceCategory] = {
    DeviceCategory.CS,
    DeviceCategory.FS,
    DeviceCategory.FSD,
    DeviceCategory.FSKG,
    DeviceCategory.KJ,
    DeviceCategory.KS,
}

_TUYA_TO_HA_DIRECTION_MAPPINGS = {
    TuyaFanDirection.FORWARD: DIRECTION_FORWARD,
    TuyaFanDirection.REVERSE: DIRECTION_REVERSE,
}
_HA_TO_TUYA_DIRECTION_MAPPINGS = {
    v: k for k, v in _TUYA_TO_HA_DIRECTION_MAPPINGS.items()
}


def _has_a_valid_dpcode(device: CustomerDevice) -> bool:

    properties_to_check: list[DPCode | tuple[DPCode, ...] | None] = [

        _SWITCH_DPCODES,

        _SPEED_DPCODES,
        _OSCILLATE_DPCODES,
        _DIRECTION_DPCODES,
    ]
    return any(get_dpcode(device, code) for code in properties_to_check)


def _get_speed_wrapper(
    device: CustomerDevice,
) -> DeviceWrapper[int] | None:

    if int_wrapper := FanSpeedIntegerWrapper.find_dpcode(
        device, _SPEED_DPCODES, prefer_function=True
    ):
        return int_wrapper
    return FanSpeedEnumWrapper.find_dpcode(device, _SPEED_DPCODES, prefer_function=True)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    manager = entry.runtime_data.manager

    @callback
    def async_discover_device(device_ids: list[str]) -> None:

        entities: list[TuyaFanEntity] = []
        for device_id in device_ids:
            device = manager.device_map[device_id]
            if device.category in TUYA_SUPPORT_TYPE and _has_a_valid_dpcode(device):
                entities.append(
                    TuyaFanEntity(
                        device,
                        manager,
                        direction_wrapper=FanDirectionEnumWrapper.find_dpcode(
                            device, _DIRECTION_DPCODES, prefer_function=True
                        ),
                        mode_wrapper=DPCodeEnumWrapper.find_dpcode(
                            device, _MODE_DPCODES, prefer_function=True
                        ),
                        oscillate_wrapper=DPCodeBooleanWrapper.find_dpcode(
                            device, _OSCILLATE_DPCODES, prefer_function=True
                        ),
                        speed_wrapper=_get_speed_wrapper(device),
                        switch_wrapper=DPCodeBooleanWrapper.find_dpcode(
                            device, _SWITCH_DPCODES, prefer_function=True
                        ),
                    )
                )
        async_add_entities(entities)

    async_discover_device([*manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, TUYA_DISCOVERY_NEW, async_discover_device)
    )


class TuyaFanEntity(TuyaEntity, FanEntity):


    _attr_name = None

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        *,
        direction_wrapper: DeviceWrapper[TuyaFanDirection] | None,
        mode_wrapper: DeviceWrapper[str] | None,
        oscillate_wrapper: DeviceWrapper[bool] | None,
        speed_wrapper: DeviceWrapper[int] | None,
        switch_wrapper: DeviceWrapper[bool] | None,
    ) -> None:

        super().__init__(device, device_manager)
        self._direction_wrapper = direction_wrapper
        self._mode_wrapper = mode_wrapper
        self._oscillate_wrapper = oscillate_wrapper
        self._speed_wrapper = speed_wrapper
        self._switch_wrapper = switch_wrapper

        if mode_wrapper:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE
            self._attr_preset_modes = mode_wrapper.options

        if speed_wrapper:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED


            if hasattr(speed_wrapper, "options"):
                self._attr_speed_count = len(speed_wrapper.options)

        if oscillate_wrapper:
            self._attr_supported_features |= FanEntityFeature.OSCILLATE

        if direction_wrapper:
            self._attr_supported_features |= FanEntityFeature.DIRECTION
        if switch_wrapper:
            self._attr_supported_features |= (
                FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:

        await self._async_send_wrapper_updates(self._mode_wrapper, preset_mode)

    async def async_set_direction(self, direction: str) -> None:

        if tuya_value := _HA_TO_TUYA_DIRECTION_MAPPINGS.get(direction):
            await self._async_send_wrapper_updates(self._direction_wrapper, tuya_value)

    async def async_set_percentage(self, percentage: int) -> None:

        await self._async_send_wrapper_updates(self._speed_wrapper, percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:

        await self._async_send_wrapper_updates(self._switch_wrapper, False)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:

        if self._switch_wrapper is None:
            return

        commands = self._switch_wrapper.get_update_commands(self.device, True)

        if percentage is not None and self._speed_wrapper is not None:
            commands.extend(
                self._speed_wrapper.get_update_commands(self.device, percentage)
            )

        if preset_mode is not None and self._mode_wrapper:
            commands.extend(
                self._mode_wrapper.get_update_commands(self.device, preset_mode)
            )
        await self._async_send_commands(commands)

    async def async_oscillate(self, oscillating: bool) -> None:

        await self._async_send_wrapper_updates(self._oscillate_wrapper, oscillating)

    @property
    def is_on(self) -> bool | None:

        return self._read_wrapper(self._switch_wrapper)

    @property
    def current_direction(self) -> str | None:

        tuya_value = self._read_wrapper(self._direction_wrapper)
        return _TUYA_TO_HA_DIRECTION_MAPPINGS.get(tuya_value) if tuya_value else None

    @property
    def oscillating(self) -> bool | None:

        return self._read_wrapper(self._oscillate_wrapper)

    @property
    def preset_mode(self) -> str | None:

        return self._read_wrapper(self._mode_wrapper)

    @property
    def percentage(self) -> int | None:

        return self._read_wrapper(self._speed_wrapper)
