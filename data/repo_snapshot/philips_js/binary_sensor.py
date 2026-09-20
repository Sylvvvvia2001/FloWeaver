

from __future__ import annotations

from dataclasses import dataclass

from haphilipsjs import PhilipsTV

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PhilipsTVConfigEntry, PhilipsTVDataUpdateCoordinator
from .entity import PhilipsJsEntity


@dataclass(frozen=True, kw_only=True)
class PhilipsTVBinarySensorEntityDescription(BinarySensorEntityDescription):


    recording_value: str


DESCRIPTIONS = (
    PhilipsTVBinarySensorEntityDescription(
        key="recording_ongoing",
        translation_key="recording_ongoing",
        recording_value="RECORDING_ONGOING",
    ),
    PhilipsTVBinarySensorEntityDescription(
        key="recording_new",
        translation_key="recording_new",
        recording_value="RECORDING_NEW",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: PhilipsTVConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    coordinator = config_entry.runtime_data

    if (
        coordinator.api.json_feature_supported("recordings", "List")
        and coordinator.api.api_version == 6
    ):
        async_add_entities(
            PhilipsTVBinarySensorEntityRecordingType(coordinator, description)
            for description in DESCRIPTIONS
        )


def _check_for_recording_entry(api: PhilipsTV, entry: str, value: str) -> bool:

    if api.recordings_list is None:
        return False
    return any(rec.get(entry) == value for rec in api.recordings_list["recordings"])


class PhilipsTVBinarySensorEntityRecordingType(PhilipsJsEntity, BinarySensorEntity):


    entity_description: PhilipsTVBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: PhilipsTVDataUpdateCoordinator,
        description: PhilipsTVBinarySensorEntityDescription,
    ) -> None:

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_is_on = _check_for_recording_entry(
            coordinator.api,
            "RecordingType",
            description.recording_value,
        )

        super().__init__(coordinator)

    @callback
    def _handle_coordinator_update(self) -> None:

        self._attr_is_on = _check_for_recording_entry(
            self.coordinator.api,
            "RecordingType",
            self.entity_description.recording_value,
        )
        super()._handle_coordinator_update()
