

from __future__ import annotations

from typing import Any

from tuya_device_handlers.device_wrapper import DeviceWrapper
from tuya_sharing import CustomerDevice, Manager

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, LOGGER, TUYA_HA_SIGNAL_UPDATE_ENTITY


class TuyaEntity(Entity):


    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: CustomerDevice, device_manager: Manager) -> None:

        self._attr_unique_id = f"tuya.{device.id}"

        device.set_up = True
        self.device = device
        self.device_manager = device_manager

    @property
    def device_info(self) -> DeviceInfo:

        return DeviceInfo(
            identifiers={(DOMAIN, self.device.id)},
            manufacturer="Tuya",
            name=self.device.name,
            model=self.device.product_name,
            model_id=self.device.product_id,
        )

    @property
    def available(self) -> bool:

        return self.device.online

    async def async_added_to_hass(self) -> None:

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{TUYA_HA_SIGNAL_UPDATE_ENTITY}_{self.device.id}",
                self._handle_state_update,
            )
        )

    async def _handle_state_update(
        self,
        updated_status_properties: list[str] | None,
        dp_timestamps: dict[str, int] | None,
    ) -> None:

        if (





            updated_status_properties is None


            or await self._process_device_update(
                updated_status_properties, dp_timestamps
            )
        ):
            self.async_write_ha_state()

    async def _process_device_update(
        self,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None,
    ) -> bool:





        return True

    async def _async_send_commands(self, commands: list[dict[str, Any]]) -> None:

        LOGGER.debug("Sending commands for device %s: %s", self.device.id, commands)
        if not commands:
            return
        await self.hass.async_add_executor_job(
            self.device_manager.send_commands, self.device.id, commands
        )

    def _read_wrapper[T](self, wrapper: DeviceWrapper[T] | None) -> T | None:

        if wrapper is None:
            return None
        return wrapper.read_device_status(self.device)

    async def _async_send_wrapper_updates[T](
        self, wrapper: DeviceWrapper[T] | None, value: T
    ) -> None:

        if wrapper is None:
            return
        await self._async_send_commands(
            wrapper.get_update_commands(self.device, value),
        )
