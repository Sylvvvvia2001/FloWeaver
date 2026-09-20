

from __future__ import annotations

import asyncio
from typing import Any

from aiohue.v2 import HueBridgeV2
from aiohue.v2.controllers.events import EventType
from aiohue.v2.controllers.groups import GroupedLight, Room, Zone
from aiohue.v2.models.feature import DynamicStatus
from aiohue.v2.models.resource import ResourceTypes

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_FLASH,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
    FLASH_SHORT,
    ColorMode,
    LightEntity,
    LightEntityDescription,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import color as color_util

from ..bridge import HueBridge, HueConfigEntry
from ..const import DOMAIN
from .entity import HueBaseEntity
from .helpers import (
    normalize_hue_brightness,
    normalize_hue_colortemp,
    normalize_hue_transition,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    bridge = config_entry.runtime_data
    api: HueBridgeV2 = bridge.api

    async def async_add_light(event_type: EventType, resource: GroupedLight) -> None:



        retries = 5
        while (
            retries
            and (group := api.groups.grouped_light.get_zone(resource.id)) is None
        ):
            retries -= 1
            await asyncio.sleep(0.5)
        if group is None:

            return
        light = GroupedHueLight(bridge, resource, group)
        async_add_entities([light])


    for item in api.groups.grouped_light.items:
        if item.owner.rtype not in [
            ResourceTypes.BRIDGE_HOME,
            ResourceTypes.PRIVATE_GROUP,
        ]:
            await async_add_light(EventType.RESOURCE_ADDED, item)


    config_entry.async_on_unload(
        api.groups.grouped_light.subscribe(
            async_add_light, event_filter=EventType.RESOURCE_ADDED
        )
    )



class GroupedHueLight(HueBaseEntity, LightEntity):


    entity_description = LightEntityDescription(
        key="hue_grouped_light",
        icon="mdi:lightbulb-group",
        has_entity_name=True,
        name=None,
    )

    def __init__(
        self, bridge: HueBridge, resource: GroupedLight, group: Room | Zone
    ) -> None:

        controller = bridge.api.groups.grouped_light
        super().__init__(bridge, controller, resource)
        self.resource = resource
        self.hue_group = group
        self.controller = controller
        self.api: HueBridgeV2 = bridge.api
        self._attr_supported_features |= LightEntityFeature.FLASH
        self._attr_supported_features |= LightEntityFeature.TRANSITION
        self._restore_brightness: float | None = None
        self._brightness_pct: float = 0


        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.hue_group.id)},
        )
        self._dynamic_mode_active = False
        self._update_values()

    async def async_added_to_hass(self) -> None:

        await super().async_added_to_hass()


        self.async_on_remove(
            self.api.groups.subscribe(self._handle_event, self.hue_group.id)
        )


        if self._attr_supported_color_modes:
            light_ids = tuple(
                x.id for x in self.controller.get_lights(self.resource.id)
            )
            self.async_on_remove(
                self.api.lights.subscribe(self._handle_event, light_ids)
            )

    @property
    def is_on(self) -> bool:

        return self.resource.on.on

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:

        scenes = {
            x.metadata.name for x in self.api.scenes if x.group.rid == self.hue_group.id
        }
        light_resource_ids = tuple(
            x.id for x in self.controller.get_lights(self.resource.id)
        )
        light_names, light_entities = self._get_names_and_entity_ids_for_resource_ids(
            light_resource_ids
        )
        return {
            "is_hue_group": True,
            "hue_scenes": scenes,
            "hue_type": self.hue_group.type.value,
            "lights": light_names,
            "entity_id": light_entities,
            "dynamics": self._dynamic_mode_active,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:

        transition = normalize_hue_transition(kwargs.get(ATTR_TRANSITION))
        xy_color = kwargs.get(ATTR_XY_COLOR)
        color_temp = normalize_hue_colortemp(
            kwargs.get(ATTR_COLOR_TEMP_KELVIN),
            color_util.color_temperature_kelvin_to_mired(self.max_color_temp_kelvin),
            color_util.color_temperature_kelvin_to_mired(self.min_color_temp_kelvin),
        )
        brightness = normalize_hue_brightness(kwargs.get(ATTR_BRIGHTNESS))
        flash = kwargs.get(ATTR_FLASH)

        if self._restore_brightness and brightness is None:








            brightness = self._restore_brightness
            self._restore_brightness = None

        if flash is not None:
            await self.async_set_flash(flash)
            return

        await self.bridge.async_request_call(
            self.controller.set_state,
            id=self.resource.id,
            on=True,
            brightness=brightness,
            color_xy=xy_color,
            color_temp=color_temp,
            transition_time=transition,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:

        transition = normalize_hue_transition(kwargs.get(ATTR_TRANSITION))
        if transition is not None:
            self._restore_brightness = self._brightness_pct
        flash = kwargs.get(ATTR_FLASH)

        if flash is not None:
            await self.async_set_flash(flash)

            return

        await self.bridge.async_request_call(
            self.controller.set_state,
            id=self.resource.id,
            on=False,
            transition_time=transition,
        )

    async def async_set_flash(self, flash: str) -> None:

        await self.bridge.async_request_call(
            self.controller.set_flash,
            id=self.resource.id,
            short=flash == FLASH_SHORT,
        )

    @callback
    def on_update(self) -> None:

        self._update_values()

    @callback
    def _update_values(self) -> None:

        supported_color_modes: set[ColorMode] = set()
        lights_with_color_support = 0
        lights_with_color_temp_support = 0
        lights_with_dimming_support = 0
        lights_on_with_dimming_support = 0
        total_brightness = 0
        all_lights = self.controller.get_lights(self.resource.id)
        lights_in_colortemp_mode = 0
        lights_in_xy_mode = 0
        lights_in_dynamic_mode = 0

        xy_total_x = 0.0
        xy_total_y = 0.0
        xy_count = 0
        temp_total = 0.0


        for light in all_lights:

            light_in_colortemp_mode = False

            if color_temp := light.color_temperature:
                lights_with_color_temp_support += 1

                self._attr_color_temp_kelvin = (
                    color_util.color_temperature_mired_to_kelvin(color_temp.mirek)
                    if color_temp.mirek
                    else None
                )
                self._attr_min_color_temp_kelvin = (
                    color_util.color_temperature_mired_to_kelvin(
                        color_temp.mirek_schema.mirek_maximum
                    )
                )
                self._attr_max_color_temp_kelvin = (
                    color_util.color_temperature_mired_to_kelvin(
                        color_temp.mirek_schema.mirek_minimum
                    )
                )

                if (
                    light.on.on
                    and color_temp.mirek is not None
                    and color_temp.mirek_valid
                ):
                    lights_in_colortemp_mode += 1
                    light_in_colortemp_mode = True
                    temp_total += color_util.color_temperature_mired_to_kelvin(
                        color_temp.mirek
                    )

            if color := light.color:
                lights_with_color_support += 1

                self._attr_xy_color = (color.xy.x, color.xy.y)

                if light.on.on:
                    xy_total_x += color.xy.x
                    xy_total_y += color.xy.y
                    xy_count += 1


                    if not light_in_colortemp_mode:
                        lights_in_xy_mode += 1

            if dimming := light.dimming:
                lights_with_dimming_support += 1

                if light.on.on:
                    total_brightness += dimming.brightness
                    lights_on_with_dimming_support += 1

            if (
                light.dynamics
                and light.dynamics.status == DynamicStatus.DYNAMIC_PALETTE
            ):
                lights_in_dynamic_mode += 1







        if lights_with_color_support > 0:
            supported_color_modes.add(ColorMode.XY)
        if lights_with_color_temp_support > 0:
            supported_color_modes.add(ColorMode.COLOR_TEMP)
        if lights_with_dimming_support > 0:
            if len(supported_color_modes) == 0:

                supported_color_modes.add(ColorMode.BRIGHTNESS)

            if lights_on_with_dimming_support > 0:
                self._brightness_pct = total_brightness / lights_on_with_dimming_support
                self._attr_brightness = round(
                    ((total_brightness / lights_on_with_dimming_support) / 100) * 255
                )
        else:
            supported_color_modes.add(ColorMode.ONOFF)
        self._dynamic_mode_active = lights_in_dynamic_mode > 0
        self._attr_supported_color_modes = supported_color_modes

        if xy_count > 0:
            self._attr_xy_color = (
                round(xy_total_x / xy_count, 5),
                round(xy_total_y / xy_count, 5),
            )
        if lights_in_colortemp_mode > 0:
            avg_temp = temp_total / lights_in_colortemp_mode
            self._attr_color_temp_kelvin = round(avg_temp)


        if lights_in_xy_mode > 0 and lights_in_xy_mode >= lights_in_colortemp_mode:
            self._attr_color_mode = ColorMode.XY
        elif (
            lights_in_colortemp_mode > 0
            and lights_in_colortemp_mode > lights_in_xy_mode
        ):
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif lights_with_color_support > 0:
            self._attr_color_mode = ColorMode.XY
        elif lights_with_color_temp_support > 0:
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif lights_with_dimming_support > 0:
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_color_mode = ColorMode.ONOFF

    @callback
    def _get_names_and_entity_ids_for_resource_ids(
        self, resource_ids: tuple[str]
    ) -> tuple[set[str], set[str]]:

        ent_reg = er.async_get(self.hass)
        light_names: set[str] = set()
        light_entities: set[str] = set()
        for resource_id in resource_ids:
            light_names.add(self.controller.get_device(resource_id).metadata.name)
            if entity_id := ent_reg.async_get_entity_id(
                self.platform.domain, DOMAIN, resource_id
            ):
                light_entities.add(entity_id)
        return light_names, light_entities
