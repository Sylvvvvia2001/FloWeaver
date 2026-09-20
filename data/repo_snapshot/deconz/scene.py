

from __future__ import annotations

from typing import Any

from pydeconz.models.event import EventType

from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN, Scene
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DeconzConfigEntry
from .entity import DeconzSceneMixin


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DeconzConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    hub = config_entry.runtime_data
    hub.entities[SCENE_DOMAIN] = set()

    @callback
    def async_add_scene(_: EventType, scene_id: str) -> None:

        scene = hub.api.scenes[scene_id]
        async_add_entities([DeconzScene(scene, hub)])

    hub.register_platform_add_device_callback(
        async_add_scene,
        hub.api.scenes,
    )


class DeconzScene(DeconzSceneMixin, Scene):


    TYPE = SCENE_DOMAIN

    async def async_activate(self, **kwargs: Any) -> None:

        await self.hub.api.scenes.recall(
            self._device.group_id,
            self._device.id,
        )
