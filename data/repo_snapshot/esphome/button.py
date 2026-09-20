

from __future__ import annotations

from functools import partial

from aioesphomeapi import ButtonInfo, EntityInfo, EntityState

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import callback
from homeassistant.util.enum import try_parse_enum

from .entity import (
    EsphomeEntity,
    convert_api_error_ha_error,
    platform_async_setup_entry,
)

PARALLEL_UPDATES = 0


class EsphomeButton(EsphomeEntity[ButtonInfo, EntityState], ButtonEntity):


    @callback
    def _on_static_info_update(self, static_info: EntityInfo) -> None:

        super()._on_static_info_update(static_info)
        self._attr_device_class = try_parse_enum(
            ButtonDeviceClass, self._static_info.device_class
        )

    @callback
    def _on_device_update(self) -> None:










        self._on_entry_data_changed()
        self.async_write_ha_state()

    @convert_api_error_ha_error
    async def async_press(self) -> None:

        self._client.button_command(self._key, device_id=self._static_info.device_id)


async_setup_entry = partial(
    platform_async_setup_entry,
    info_type=ButtonInfo,
    entity_type=EsphomeButton,
    state_type=EntityState,
)
