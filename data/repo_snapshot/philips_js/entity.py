

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PhilipsTVDataUpdateCoordinator


class PhilipsJsEntity(CoordinatorEntity[PhilipsTVDataUpdateCoordinator]):


    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PhilipsTVDataUpdateCoordinator,
    ) -> None:

        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
