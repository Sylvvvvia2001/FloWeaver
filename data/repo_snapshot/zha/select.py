

from __future__ import annotations

import functools
import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import ZHAEntity
from .helpers import (
    SIGNAL_ADD_ENTITIES,
    EntityData,
    async_add_entities as zha_async_add_entities,
    convert_zha_error_to_ha_error,
    get_zha_data,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    zha_data = get_zha_data(hass)
    entities_to_create = zha_data.platforms[Platform.SELECT]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            zha_async_add_entities,
            async_add_entities,
            ZHAEnumSelectEntity,
            entities_to_create,
        ),
    )
    config_entry.async_on_unload(unsub)


class ZHAEnumSelectEntity(ZHAEntity, SelectEntity):


    def __init__(self, entity_data: EntityData, **kwargs: Any) -> None:

        super().__init__(entity_data, **kwargs)
        self._attr_options = self.entity_data.entity.info_object.options

    @property
    def current_option(self) -> str | None:

        return self.entity_data.entity.current_option

    @convert_zha_error_to_ha_error
    async def async_select_option(self, option: str) -> None:

        await self.entity_data.entity.async_select_option(option=option)
        self.async_write_ha_state()

    @callback
    def restore_external_state_attributes(self, state: State) -> None:

        if state.state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self.entity_data.entity.restore_external_state_attributes(
                state=state.state,
            )
