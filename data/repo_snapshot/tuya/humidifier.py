

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tuya_device_handlers.device_wrapper.base import DeviceWrapper
from tuya_device_handlers.device_wrapper.common import (
    DPCodeBooleanWrapper,
    DPCodeEnumWrapper,
)
from tuya_device_handlers.device_wrapper.extended import DPCodeRoundedIntegerWrapper
from tuya_sharing import CustomerDevice, Manager

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityDescription,
    HumidifierEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TuyaConfigEntry
from .const import TUYA_DISCOVERY_NEW, DeviceCategory, DPCode
from .entity import TuyaEntity
from .util import ActionDPCodeNotFoundError, get_dpcode


@dataclass(frozen=True)
class TuyaHumidifierEntityDescription(HumidifierEntityDescription):



    dpcode: DPCode | tuple[DPCode, ...] | None = None

    current_humidity: DPCode | None = None
    humidity: DPCode | None = None


def _has_a_valid_dpcode(
    device: CustomerDevice, description: TuyaHumidifierEntityDescription
) -> bool:

    properties_to_check: list[str | tuple[str, ...] | None] = [

        description.dpcode or description.key,

        description.current_humidity,
        description.humidity,
    ]
    return any(get_dpcode(device, code) for code in properties_to_check)


HUMIDIFIERS: dict[DeviceCategory, TuyaHumidifierEntityDescription] = {
    DeviceCategory.CS: TuyaHumidifierEntityDescription(
        key=DPCode.SWITCH,
        dpcode=(DPCode.SWITCH, DPCode.SWITCH_SPRAY),
        current_humidity=DPCode.HUMIDITY_INDOOR,
        humidity=DPCode.DEHUMIDITY_SET_VALUE,
        device_class=HumidifierDeviceClass.DEHUMIDIFIER,
    ),
    DeviceCategory.JSQ: TuyaHumidifierEntityDescription(
        key=DPCode.SWITCH,
        dpcode=(DPCode.SWITCH, DPCode.SWITCH_SPRAY),
        current_humidity=DPCode.HUMIDITY_CURRENT,
        humidity=DPCode.HUMIDITY_SET,
        device_class=HumidifierDeviceClass.HUMIDIFIER,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    manager = entry.runtime_data.manager

    @callback
    def async_discover_device(device_ids: list[str]) -> None:

        entities: list[TuyaHumidifierEntity] = []
        for device_id in device_ids:
            device = manager.device_map[device_id]
            if (
                description := HUMIDIFIERS.get(device.category)
            ) and _has_a_valid_dpcode(device, description):
                entities.append(
                    TuyaHumidifierEntity(
                        device,
                        manager,
                        description,
                        current_humidity_wrapper=DPCodeRoundedIntegerWrapper.find_dpcode(
                            device, description.current_humidity
                        ),
                        mode_wrapper=DPCodeEnumWrapper.find_dpcode(
                            device, DPCode.MODE, prefer_function=True
                        ),
                        switch_wrapper=DPCodeBooleanWrapper.find_dpcode(
                            device,
                            description.dpcode or description.key,
                            prefer_function=True,
                        ),
                        target_humidity_wrapper=DPCodeRoundedIntegerWrapper.find_dpcode(
                            device, description.humidity, prefer_function=True
                        ),
                    )
                )
        async_add_entities(entities)

    async_discover_device([*manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, TUYA_DISCOVERY_NEW, async_discover_device)
    )


class TuyaHumidifierEntity(TuyaEntity, HumidifierEntity):


    entity_description: TuyaHumidifierEntityDescription
    _attr_name = None

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: TuyaHumidifierEntityDescription,
        *,
        current_humidity_wrapper: DeviceWrapper[int] | None = None,
        mode_wrapper: DeviceWrapper[str] | None = None,
        switch_wrapper: DeviceWrapper[bool] | None = None,
        target_humidity_wrapper: DeviceWrapper[int] | None = None,
    ) -> None:

        super().__init__(device, device_manager)
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}{description.key}"

        self._current_humidity_wrapper = current_humidity_wrapper
        self._mode_wrapper = mode_wrapper
        self._switch_wrapper = switch_wrapper
        self._target_humidity_wrapper = target_humidity_wrapper


        if target_humidity_wrapper:
            self._attr_min_humidity = round(target_humidity_wrapper.min_value)
            self._attr_max_humidity = round(target_humidity_wrapper.max_value)


        if mode_wrapper:
            self._attr_supported_features |= HumidifierEntityFeature.MODES
            self._attr_available_modes = mode_wrapper.options

    @property
    def is_on(self) -> bool | None:

        return self._read_wrapper(self._switch_wrapper)

    @property
    def mode(self) -> str | None:

        return self._read_wrapper(self._mode_wrapper)

    @property
    def target_humidity(self) -> int | None:

        return self._read_wrapper(self._target_humidity_wrapper)

    @property
    def current_humidity(self) -> int | None:

        return self._read_wrapper(self._current_humidity_wrapper)

    async def async_turn_on(self, **kwargs: Any) -> None:

        if self._switch_wrapper is None:
            raise ActionDPCodeNotFoundError(
                self.device,
                self.entity_description.dpcode or self.entity_description.key,
            )
        await self._async_send_wrapper_updates(self._switch_wrapper, True)

    async def async_turn_off(self, **kwargs: Any) -> None:

        if self._switch_wrapper is None:
            raise ActionDPCodeNotFoundError(
                self.device,
                self.entity_description.dpcode or self.entity_description.key,
            )
        await self._async_send_wrapper_updates(self._switch_wrapper, False)

    async def async_set_humidity(self, humidity: int) -> None:

        if self._target_humidity_wrapper is None:
            raise ActionDPCodeNotFoundError(
                self.device,
                self.entity_description.humidity,
            )
        await self._async_send_wrapper_updates(self._target_humidity_wrapper, humidity)

    async def async_set_mode(self, mode: str) -> None:

        await self._async_send_wrapper_updates(self._mode_wrapper, mode)
