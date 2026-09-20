

from __future__ import annotations

import pathlib
from typing import Any
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
from tuya_sharing import (
    CustomerApi,
    CustomerDevice,
    DeviceFunction,
    DeviceStatusRange,
    Manager,
)

from homeassistant.components.tuya import DOMAIN, DeviceListener
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import json_dumps
from homeassistant.util import dt as dt_util

from tests.common import MockConfigEntry, async_load_json_object_fixture

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
DEVICE_MOCKS = sorted(
    str(path.relative_to(FIXTURES_DIR).with_suffix(""))
    for path in FIXTURES_DIR.glob("*.json")
)


class MockDeviceListener(DeviceListener):


    async def _async_update_device(
        self,
        device: CustomerDevice,
        updated_status_properties: list[str] | None,
        dp_timestamps: dict[str, int] | None,
    ) -> None:

        self.update_device(device, updated_status_properties, dp_timestamps)
        await self.hass.async_block_till_done()

    async def async_mock_online(self, device: CustomerDevice) -> None:

        device.online = True
        await self._async_update_device(device, None, None)

    async def async_mock_offline(self, device: CustomerDevice) -> None:

        device.online = False
        await self._async_update_device(device, None, None)

    async def async_send_device_update(
        self,
        device: CustomerDevice,
        updated_status_properties: dict[str, Any] | None = None,
        dp_timestamps: dict[str, int] | None = None,
    ) -> None:

        property_list: list[str] | None = None
        if updated_status_properties is not None:
            property_list = []
            for key, value in updated_status_properties.items():
                if key not in device.status:
                    raise ValueError(
                        f"Property {key} not found in device status: {device.status}"
                    )
                device.status[key] = value
                property_list.append(key)
        await self._async_update_device(device, property_list, dp_timestamps)


async def create_device(hass: HomeAssistant, mock_device_code: str) -> CustomerDevice:

    details = await async_load_json_object_fixture(
        hass, f"{mock_device_code}.json", DOMAIN
    )
    device = MagicMock(spec=CustomerDevice)


    device.id = mock_device_code.replace("_", "")[::-1]

    device.name = details["name"]
    device.category = details["category"]
    device.product_id = details["product_id"]
    device.product_name = details["product_name"]
    device.online = details["online"]
    device.sub = details.get("sub")
    device.time_zone = details.get("time_zone")
    device.active_time = details.get("active_time")
    if device.active_time:
        device.active_time = int(dt_util.as_timestamp(device.active_time))
    device.create_time = details.get("create_time")
    if device.create_time:
        device.create_time = int(dt_util.as_timestamp(device.create_time))
    device.update_time = details.get("update_time")
    if device.update_time:
        device.update_time = int(dt_util.as_timestamp(device.update_time))
    device.support_local = details.get("support_local")
    device.local_strategy = details.get("local_strategy")
    device.mqtt_connected = details.get("mqtt_connected")

    device.function = {
        key: DeviceFunction(
            code=key,
            type=value["type"],
            values=(
                values
                if isinstance(values := value["value"], str)
                else json_dumps(values)
            ),
        )
        for key, value in details["function"].items()
    }
    device.status_range = {
        key: DeviceStatusRange(
            code=key,
            report_type=value.get("report_type"),
            type=value["type"],
            values=(
                values
                if isinstance(values := value["value"], str)
                else json_dumps(values)
            ),
        )
        for key, value in details["status_range"].items()
    }
    device.status = details["status"]
    for key, value in device.status.items():


        if ((dp_type := device.status_range.get(key)) and dp_type.type == "Json") or (
            (dp_type := device.function.get(key)) and dp_type.type == "Json"
        ):
            device.status[key] = json_dumps(value)
        if value == "**REDACTED**":

            device.status[key] = ""
    return device


def create_listener(hass: HomeAssistant, manager: Manager) -> MockDeviceListener:

    listener = MockDeviceListener(hass, manager)
    manager.add_device_listener(listener)
    return listener


def create_manager(
    terminal_id: str = "7cd96aff-6ec8-4006-b093-3dbff7947591",
) -> Manager:

    manager = MagicMock(spec=Manager)
    manager.device_map = {}
    manager.mq = MagicMock()
    manager.mq.client = MagicMock()
    manager.mq.client.is_connected = MagicMock(return_value=True)
    manager.customer_api = MagicMock(spec=CustomerApi)

    manager.customer_api.endpoint = "https://apigw.tuyaeu.com"
    manager.terminal_id = terminal_id
    return manager


async def initialize_entry(
    hass: HomeAssistant,
    mock_manager: Manager,
    mock_config_entry: MockConfigEntry,
    mock_devices: CustomerDevice | list[CustomerDevice],
) -> None:

    if not isinstance(mock_devices, list):
        mock_devices = [mock_devices]
    mock_manager.device_map = {device.id: device for device in mock_devices}


    mock_config_entry.add_to_hass(hass)


    with patch("homeassistant.components.tuya.Manager", return_value=mock_manager):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


async def check_selective_state_update(
    hass: HomeAssistant,
    mock_device: CustomerDevice,
    mock_listener: MockDeviceListener,
    freezer: FrozenDateTimeFactory,
    *,
    entity_id: str,
    dpcode: str,
    initial_state: str,
    updates: dict[str, Any],
    expected_state: str,
    last_reported: str,
) -> None:






    initial_reported = "2024-01-01T00:00:00+00:00"
    unavailable_reported = "2024-01-01T00:00:10+00:00"
    available_reported = "2024-01-01T00:00:20+00:00"
    assert hass.states.get(entity_id).state == initial_state
    assert hass.states.get(entity_id).last_reported.isoformat() == initial_reported


    freezer.tick(10)
    await mock_listener.async_mock_offline(mock_device)
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    assert hass.states.get(entity_id).last_reported.isoformat() == unavailable_reported


    freezer.tick(10)
    await mock_listener.async_mock_online(mock_device)
    assert hass.states.get(entity_id).state == initial_state
    assert hass.states.get(entity_id).last_reported.isoformat() == available_reported



    freezer.tick(10)
    mock_device.status[dpcode] = None
    await mock_listener.async_send_device_update(mock_device, {})
    assert hass.states.get(entity_id).state == initial_state
    assert hass.states.get(entity_id).last_reported.isoformat() == available_reported


    freezer.tick(30)
    await mock_listener.async_send_device_update(mock_device, updates)
    assert hass.states.get(entity_id).state == expected_state
    assert hass.states.get(entity_id).last_reported.isoformat() == last_reported
