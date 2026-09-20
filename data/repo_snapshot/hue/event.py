

from __future__ import annotations

from typing import Any

from aiohue.v2 import HueBridgeV2
from aiohue.v2.controllers.events import EventType
from aiohue.v2.models.bell_button import BellButton
from aiohue.v2.models.button import Button
from aiohue.v2.models.relative_rotary import RelativeRotary, RelativeRotaryDirection

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .bridge import HueConfigEntry
from .const import DEFAULT_BUTTON_EVENT_TYPES, DEVICE_SPECIFIC_EVENT_TYPES
from .v2.entity import HueBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    bridge = config_entry.runtime_data
    api: HueBridgeV2 = bridge.api

    if bridge.api_version == 1:

        raise NotImplementedError("Event support is only available for V2 bridges")


    @callback
    def async_add_entity(
        event_type: EventType,
        resource: Button | RelativeRotary | BellButton,
    ) -> None:

        if isinstance(resource, RelativeRotary):
            async_add_entities(
                [HueRotaryEventEntity(bridge, api.sensors.relative_rotary, resource)]
            )
        elif isinstance(resource, BellButton):
            async_add_entities(
                [HueBellButtonEventEntity(bridge, api.sensors.bell_button, resource)]
            )
        else:
            async_add_entities(
                [HueButtonEventEntity(bridge, api.sensors.button, resource)]
            )

    for controller in (
        api.sensors.button,
        api.sensors.relative_rotary,
        api.sensors.bell_button,
    ):

        for item in controller:
            async_add_entity(EventType.RESOURCE_ADDED, item)


        config_entry.async_on_unload(
            controller.subscribe(
                async_add_entity, event_filter=EventType.RESOURCE_ADDED
            )
        )


class HueButtonEventEntity(HueBaseEntity, EventEntity):


    resource: Button | BellButton

    entity_description = EventEntityDescription(
        key="button",
        device_class=EventDeviceClass.BUTTON,
        translation_key="button",
        has_entity_name=True,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:

        super().__init__(*args, **kwargs)

        hue_dev_id = self.controller.get_device(self.resource.id).id
        model_id = self.bridge.api.devices[hue_dev_id].product_data.product_name
        self._attr_event_types: list[str] = [
            event_type.value
            for event_type in DEVICE_SPECIFIC_EVENT_TYPES.get(
                model_id, DEFAULT_BUTTON_EVENT_TYPES
            )
        ]
        self._attr_translation_placeholders = {
            "button_id": self.resource.metadata.control_id
        }

    @callback
    def _handle_event(
        self, event_type: EventType, resource: Button | BellButton
    ) -> None:

        if event_type == EventType.RESOURCE_UPDATED and resource.id == self.resource.id:
            if resource.button is None or resource.button.button_report is None:
                return
            self._trigger_event(resource.button.button_report.event.value)
            self.async_write_ha_state()
            return
        super()._handle_event(event_type, resource)


class HueBellButtonEventEntity(HueButtonEventEntity):


    resource: Button | BellButton

    entity_description = EventEntityDescription(
        key="bell_button",
        device_class=EventDeviceClass.DOORBELL,
        has_entity_name=True,
    )


class HueRotaryEventEntity(HueBaseEntity, EventEntity):


    entity_description = EventEntityDescription(
        key="rotary",
        device_class=EventDeviceClass.BUTTON,
        translation_key="rotary",
        event_types=[
            RelativeRotaryDirection.CLOCK_WISE.value,
            RelativeRotaryDirection.COUNTER_CLOCK_WISE.value,
        ],
        has_entity_name=True,
    )

    @callback
    def _handle_event(self, event_type: EventType, resource: RelativeRotary) -> None:

        if event_type == EventType.RESOURCE_UPDATED and resource.id == self.resource.id:
            if (
                resource.relative_rotary is None
                or resource.relative_rotary.rotary_report is None
            ):
                return
            event_key = resource.relative_rotary.rotary_report.rotation.direction.value
            event_data = {
                "duration": resource.relative_rotary.rotary_report.rotation.duration,
                "steps": resource.relative_rotary.rotary_report.rotation.steps,
                "action": resource.relative_rotary.rotary_report.action.value,
            }
            self._trigger_event(event_key, event_data)
            self.async_write_ha_state()
            return
        super()._handle_event(event_type, resource)
