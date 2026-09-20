

from __future__ import annotations

from functools import partial
from typing import Any

from aioesphomeapi import EntityInfo, ValveInfo, ValveOperation, ValveState

from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.core import callback
from homeassistant.util.enum import try_parse_enum

from .entity import (
    EsphomeEntity,
    convert_api_error_ha_error,
    esphome_state_property,
    platform_async_setup_entry,
)

PARALLEL_UPDATES = 0


class EsphomeValve(EsphomeEntity[ValveInfo, ValveState], ValveEntity):


    @callback
    def _on_static_info_update(self, static_info: EntityInfo) -> None:

        super()._on_static_info_update(static_info)
        static_info = self._static_info
        flags = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        if static_info.supports_stop:
            flags |= ValveEntityFeature.STOP
        if static_info.supports_position:
            flags |= ValveEntityFeature.SET_POSITION
        self._attr_supported_features = flags
        self._attr_device_class = try_parse_enum(
            ValveDeviceClass, static_info.device_class
        )
        self._attr_assumed_state = static_info.assumed_state
        self._attr_reports_position = static_info.supports_position

    @property
    @esphome_state_property
    def is_closed(self) -> bool:

        return self._state.position == 0.0

    @property
    @esphome_state_property
    def is_opening(self) -> bool:

        return self._state.current_operation is ValveOperation.IS_OPENING

    @property
    @esphome_state_property
    def is_closing(self) -> bool:

        return self._state.current_operation is ValveOperation.IS_CLOSING

    @property
    @esphome_state_property
    def current_valve_position(self) -> int:

        return round(self._state.position * 100.0)

    @convert_api_error_ha_error
    async def async_open_valve(self, **kwargs: Any) -> None:

        self._client.valve_command(
            key=self._key, position=1.0, device_id=self._static_info.device_id
        )

    @convert_api_error_ha_error
    async def async_close_valve(self, **kwargs: Any) -> None:

        self._client.valve_command(
            key=self._key, position=0.0, device_id=self._static_info.device_id
        )

    @convert_api_error_ha_error
    async def async_stop_valve(self, **kwargs: Any) -> None:

        self._client.valve_command(
            key=self._key, stop=True, device_id=self._static_info.device_id
        )

    @convert_api_error_ha_error
    async def async_set_valve_position(self, position: float) -> None:

        self._client.valve_command(
            key=self._key,
            position=position / 100,
            device_id=self._static_info.device_id,
        )


async_setup_entry = partial(
    platform_async_setup_entry,
    info_type=ValveInfo,
    entity_type=EsphomeValve,
    state_type=ValveState,
)
