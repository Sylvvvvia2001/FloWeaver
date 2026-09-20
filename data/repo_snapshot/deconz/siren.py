

from __future__ import annotations

from typing import Any

from pydeconz.models.event import EventType
from pydeconz.models.light.siren import Siren

from homeassistant.components.siren import (
    ATTR_DURATION,
    DOMAIN as SIREN_DOMAIN,
    SirenEntity,
    SirenEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DeconzConfigEntry
from .entity import DeconzDevice


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DeconzConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    hub = config_entry.runtime_data
    hub.entities[SIREN_DOMAIN] = set()

    @callback
    def async_add_siren(_: EventType, siren_id: str) -> None:

        siren = hub.api.lights.sirens[siren_id]
        async_add_entities([DeconzSiren(siren, hub)])

    hub.register_platform_add_device_callback(
        async_add_siren,
        hub.api.lights.sirens,
    )


class DeconzSiren(DeconzDevice[Siren], SirenEntity):


    TYPE = SIREN_DOMAIN
    _attr_supported_features = (
        SirenEntityFeature.TURN_ON
        | SirenEntityFeature.TURN_OFF
        | SirenEntityFeature.DURATION
    )

    @property
    def is_on(self) -> bool:

        return self._device.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:

        if (duration := kwargs.get(ATTR_DURATION)) is not None:
            duration *= 10
        await self.hub.api.lights.sirens.set_state(
            id=self._device.resource_id,
            on=True,
            duration=duration,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:

        await self.hub.api.lights.sirens.set_state(
            id=self._device.resource_id,
            on=False,
        )
