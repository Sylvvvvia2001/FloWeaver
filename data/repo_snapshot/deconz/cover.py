

from __future__ import annotations

from typing import Any, cast

from pydeconz.interfaces.lights import CoverAction
from pydeconz.models import ResourceType
from pydeconz.models.event import EventType
from pydeconz.models.light.cover import Cover

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as COVER_DOMAIN,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DeconzConfigEntry
from .entity import DeconzDevice
from .hub import DeconzHub

DECONZ_TYPE_TO_DEVICE_CLASS = {
    ResourceType.LEVEL_CONTROLLABLE_OUTPUT.value: CoverDeviceClass.DAMPER,
    ResourceType.WINDOW_COVERING_CONTROLLER.value: CoverDeviceClass.SHADE,
    ResourceType.WINDOW_COVERING_DEVICE.value: CoverDeviceClass.SHADE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DeconzConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    hub = config_entry.runtime_data
    hub.entities[COVER_DOMAIN] = set()

    @callback
    def async_add_cover(_: EventType, cover_id: str) -> None:

        async_add_entities([DeconzCover(cover_id, hub)])

    hub.register_platform_add_device_callback(
        async_add_cover,
        hub.api.lights.covers,
    )


class DeconzCover(DeconzDevice[Cover], CoverEntity):


    TYPE = COVER_DOMAIN

    def __init__(self, cover_id: str, hub: DeconzHub) -> None:

        super().__init__(cover := hub.api.lights.covers[cover_id], hub)

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

        if self._device.tilt is not None:
            self._attr_supported_features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.STOP_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )

        self._attr_device_class = DECONZ_TYPE_TO_DEVICE_CLASS.get(cover.type)

        self.legacy_mode = cover.type == ResourceType.LEVEL_CONTROLLABLE_OUTPUT.value

    @property
    def current_cover_position(self) -> int:

        return 100 - self._device.lift

    @property
    def is_closed(self) -> bool:

        return not self._device.is_open

    async def async_set_cover_position(self, **kwargs: Any) -> None:

        position = 100 - cast(int, kwargs[ATTR_POSITION])
        await self.hub.api.lights.covers.set_state(
            id=self._device.resource_id,
            lift=position,
            legacy_mode=self.legacy_mode,
        )

    async def async_open_cover(self, **kwargs: Any) -> None:

        await self.hub.api.lights.covers.set_state(
            id=self._device.resource_id,
            action=CoverAction.OPEN,
            legacy_mode=self.legacy_mode,
        )

    async def async_close_cover(self, **kwargs: Any) -> None:

        await self.hub.api.lights.covers.set_state(
            id=self._device.resource_id,
            action=CoverAction.CLOSE,
            legacy_mode=self.legacy_mode,
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:

        await self.hub.api.lights.covers.set_state(
            id=self._device.resource_id,
            action=CoverAction.STOP,
            legacy_mode=self.legacy_mode,
        )

    @property
    def current_cover_tilt_position(self) -> int | None:

        if self._device.tilt is not None:
            return 100 - self._device.tilt
        return None

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:

        position = 100 - cast(int, kwargs[ATTR_TILT_POSITION])
        await self.hub.api.lights.covers.set_state(
            id=self._device.resource_id,
            tilt=position,
            legacy_mode=self.legacy_mode,
        )

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:

        await self.hub.api.lights.covers.set_state(
            id=self._device.resource_id,
            tilt=0,
            legacy_mode=self.legacy_mode,
        )

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:

        await self.hub.api.lights.covers.set_state(
            id=self._device.resource_id,
            tilt=100,
            legacy_mode=self.legacy_mode,
        )

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:

        await self.hub.api.lights.covers.set_state(
            id=self._device.resource_id,
            action=CoverAction.STOP,
            legacy_mode=self.legacy_mode,
        )
