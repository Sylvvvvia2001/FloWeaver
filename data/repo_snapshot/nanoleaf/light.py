

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NanoleafConfigEntry, NanoleafCoordinator
from .entity import NanoleafEntity

RESERVED_EFFECTS = ("*Solid*", "*Static*", "*Dynamic*")
DEFAULT_NAME = "Nanoleaf"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NanoleafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    async_add_entities([NanoleafLight(entry.runtime_data)])


class NanoleafLight(NanoleafEntity, LightEntity):


    _attr_supported_color_modes = {ColorMode.COLOR_TEMP, ColorMode.HS}
    _attr_supported_features = LightEntityFeature.EFFECT | LightEntityFeature.TRANSITION
    _attr_name = None
    _attr_translation_key = "light"

    def __init__(self, coordinator: NanoleafCoordinator) -> None:

        super().__init__(coordinator)
        self._attr_unique_id = self._nanoleaf.serial_no
        self._attr_max_color_temp_kelvin = self._nanoleaf.color_temperature_max
        self._attr_min_color_temp_kelvin = self._nanoleaf.color_temperature_min

    @property
    def brightness(self) -> int:

        return int(self._nanoleaf.brightness * 2.55)

    @property
    def color_temp_kelvin(self) -> int | None:

        return self._nanoleaf.color_temperature

    @property
    def effect(self) -> str | None:





        return (
            None if self._nanoleaf.effect in RESERVED_EFFECTS else self._nanoleaf.effect
        )

    @property
    def effect_list(self) -> list[str]:

        return self._nanoleaf.effects_list

    @property
    def is_on(self) -> bool:

        return self._nanoleaf.is_on

    @property
    def hs_color(self) -> tuple[int, int]:

        return self._nanoleaf.hue, self._nanoleaf.saturation

    @property
    def color_mode(self) -> ColorMode:



        if self._nanoleaf.color_mode == "ct":
            return ColorMode.COLOR_TEMP

        return ColorMode.HS

    async def async_turn_on(self, **kwargs: Any) -> None:

        brightness = kwargs.get(ATTR_BRIGHTNESS)
        hs_color = kwargs.get(ATTR_HS_COLOR)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        effect = kwargs.get(ATTR_EFFECT)
        transition = kwargs.get(ATTR_TRANSITION)

        if effect:
            if effect not in self.effect_list:
                raise ValueError(
                    f"Attempting to apply effect not in the effect list: '{effect}'"
                )
            await self._nanoleaf.set_effect(effect)
        elif hs_color:
            hue, saturation = hs_color
            await self._nanoleaf.set_hue(int(hue))
            await self._nanoleaf.set_saturation(int(saturation))
        elif color_temp_kelvin:
            await self._nanoleaf.set_color_temperature(color_temp_kelvin)
        if transition:
            if brightness:
                await self._nanoleaf.set_brightness(
                    int(brightness / 2.55), transition=int(kwargs[ATTR_TRANSITION])
                )
            else:
                await self._nanoleaf.set_brightness(100, transition=int(transition))
        else:
            await self._nanoleaf.turn_on()
            if brightness:
                await self._nanoleaf.set_brightness(int(brightness / 2.55))
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:

        transition: float | None = kwargs.get(ATTR_TRANSITION)
        await self._nanoleaf.turn_off(None if transition is None else int(transition))
        await self.coordinator.async_refresh()
