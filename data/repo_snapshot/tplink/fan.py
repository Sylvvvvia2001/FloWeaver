

from collections.abc import Callable
from dataclasses import dataclass
import logging
import math
from typing import Any

from kasa import Device, Module

from homeassistant.components.fan import (
    DOMAIN as FAN_DOMAIN,
    FanEntity,
    FanEntityDescription,
    FanEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)
from homeassistant.util.scaling import int_states_in_range

from . import TPLinkConfigEntry, legacy_device_id
from .coordinator import TPLinkDataUpdateCoordinator
from .entity import (
    CoordinatedTPLinkModuleEntity,
    TPLinkModuleEntityDescription,
    async_refresh_after,
)



PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TPLinkFanEntityDescription(FanEntityDescription, TPLinkModuleEntityDescription):


    unique_id_fn: Callable[[Device, TPLinkModuleEntityDescription], str] = (
        lambda device, desc: (
            legacy_device_id(device)
            if desc.key == "fan"
            else f"{legacy_device_id(device)}-{desc.key}"
        )
    )


FAN_DESCRIPTIONS: tuple[TPLinkFanEntityDescription, ...] = (
    TPLinkFanEntityDescription(
        key="fan",
        exists_fn=lambda dev, _: Module.Fan in dev.modules,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: TPLinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    data = config_entry.runtime_data
    parent_coordinator = data.parent_coordinator
    device = parent_coordinator.device

    known_child_device_ids: set[str] = set()
    first_check = True

    def _check_device() -> None:
        entities = CoordinatedTPLinkModuleEntity.entities_for_device_and_its_children(
            hass=hass,
            device=device,
            coordinator=parent_coordinator,
            entity_class=TPLinkFanEntity,
            descriptions=FAN_DESCRIPTIONS,
            platform_domain=FAN_DOMAIN,
            known_child_device_ids=known_child_device_ids,
            first_check=first_check,
        )
        async_add_entities(entities)

    _check_device()
    first_check = False
    config_entry.async_on_unload(parent_coordinator.async_add_listener(_check_device))


SPEED_RANGE = (1, 4)


class TPLinkFanEntity(CoordinatedTPLinkModuleEntity, FanEntity):


    _attr_speed_count = int_states_in_range(SPEED_RANGE)
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    entity_description: TPLinkFanEntityDescription

    def __init__(
        self,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        description: TPLinkFanEntityDescription,
        *,
        parent: Device | None = None,
    ) -> None:

        super().__init__(device, coordinator, description, parent=parent)
        self.fan_module = device.modules[Module.Fan]

    @async_refresh_after
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:

        if percentage is not None:
            value_in_range = math.ceil(
                percentage_to_ranged_value(SPEED_RANGE, percentage)
            )
        else:
            value_in_range = SPEED_RANGE[1]
        await self.fan_module.set_fan_speed_level(value_in_range)

    @async_refresh_after
    async def async_turn_off(self, **kwargs: Any) -> None:

        await self.fan_module.set_fan_speed_level(0)

    async def async_set_percentage(self, percentage: int) -> None:

        value_in_range = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self.fan_module.set_fan_speed_level(value_in_range)

    @callback
    def _async_update_attrs(self) -> bool:

        fan_speed = self.fan_module.fan_speed_level
        self._attr_is_on = fan_speed != 0
        if self._attr_is_on:
            self._attr_percentage = ranged_value_to_percentage(SPEED_RANGE, fan_speed)
        else:
            self._attr_percentage = None
        return True
