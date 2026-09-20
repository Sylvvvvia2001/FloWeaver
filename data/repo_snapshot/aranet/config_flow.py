

from __future__ import annotations

from typing import Any

from aranet4.client import Aranet4Advertisement, Version as AranetVersion
from bluetooth_data_tools import human_readable_name
import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import AbortFlow

from .const import DOMAIN

MIN_VERSION = AranetVersion(1, 2, 0)


def _title(discovery_info: BluetoothServiceInfoBleak) -> str:
    return discovery_info.device.name or human_readable_name(
        None, "Aranet", discovery_info.address
    )


class AranetConfigFlow(ConfigFlow, domain=DOMAIN):


    VERSION = 1

    def __init__(self) -> None:

        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: Aranet4Advertisement | None = None
        self._discovered_devices: dict[str, tuple[str, Aranet4Advertisement]] = {}

    def _raise_for_advertisement_errors(self, adv: Aranet4Advertisement) -> None:


        if not adv.manufacturer_data or adv.manufacturer_data.version < MIN_VERSION:
            raise AbortFlow("outdated_version")


        if not adv.manufacturer_data.integrations:
            raise AbortFlow("integrations_disabled")

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        adv = Aranet4Advertisement(discovery_info.device, discovery_info.advertisement)
        self._raise_for_advertisement_errors(adv)

        self._discovery_info = discovery_info
        self._discovered_device = adv
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:

        assert self._discovery_info is not None
        title = _title(self._discovery_info)
        if user_input is not None:
            return self.async_create_entry(title=title, data={})

        self._set_confirm_only()
        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders=placeholders
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            adv = self._discovered_devices[address][1]
            self._raise_for_advertisement_errors(adv)

            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._discovered_devices[address][0], data={}
            )

        current_addresses = self._async_current_ids(include_ignore=False)
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue

            adv = Aranet4Advertisement(
                discovery_info.device, discovery_info.advertisement
            )
            if adv.manufacturer_data:
                self._discovered_devices[address] = (_title(discovery_info), adv)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            addr: dev[0]
                            for (addr, dev) in self._discovered_devices.items()
                        }
                    )
                }
            ),
        )
