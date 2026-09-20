

import asyncio
from dataclasses import asdict
from typing import Any
from unittest.mock import AsyncMock

from aioesphomeapi import (
    APIClient,
    BinarySensorInfo,
    BinarySensorState,
    DeviceInfo,
    SensorInfo,
    SensorState,
    SubDeviceInfo,
    build_unique_id,
)
import pytest

from homeassistant.components.esphome import DOMAIN
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_RESTORED,
    EVENT_HOMEASSISTANT_STOP,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

from .conftest import (
    MockESPHomeDevice,
    MockESPHomeDeviceType,
    MockGenericDeviceEntryType,
)


async def test_entities_removed(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_client: APIClient,
    hass_storage: dict[str, Any],
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
        ),
        BinarySensorInfo(
            object_id="mybinary_sensor_to_be_removed",
            key=2,
            name="my binary_sensor to be removed",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
        BinarySensorState(key=2, state=True, missing_state=False),
    ]
    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
    )
    entry = mock_device.entry
    entry_id = entry.entry_id
    storage_key = f"esphome.{entry_id}"
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is not None
    assert state.state == STATE_ON

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass_storage[storage_key]["data"]["binary_sensor"]) == 2

    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.attributes[ATTR_RESTORED] is True
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is not None
    reg_entry = entity_registry.async_get(
        "binary_sensor.test_my_binary_sensor_to_be_removed"
    )
    assert reg_entry is not None
    assert state.attributes[ATTR_RESTORED] is True

    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]
    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
        entry=entry,
    )
    assert mock_device.entry.entry_id == entry_id
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is None
    reg_entry = entity_registry.async_get(
        "binary_sensor.test_my_binary_sensor_to_be_removed"
    )
    assert reg_entry is None
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(hass_storage[storage_key]["data"]["binary_sensor"]) == 1


async def test_entities_removed_after_reload(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_client: APIClient,
    hass_storage: dict[str, Any],
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
        ),
        BinarySensorInfo(
            object_id="mybinary_sensor_to_be_removed",
            key=2,
            name="my binary_sensor to be removed",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
        BinarySensorState(key=2, state=True, missing_state=False),
    ]
    mock_device: MockESPHomeDevice = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
    )
    entry = mock_device.entry
    entry_id = entry.entry_id
    storage_key = f"esphome.{entry_id}"
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is not None
    assert state.state == STATE_ON

    reg_entry = entity_registry.async_get(
        "binary_sensor.test_my_binary_sensor_to_be_removed"
    )
    assert reg_entry is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass_storage[storage_key]["data"]["binary_sensor"]) == 2

    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.attributes[ATTR_RESTORED] is True
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is not None
    assert state.attributes[ATTR_RESTORED] is True

    reg_entry = entity_registry.async_get(
        "binary_sensor.test_my_binary_sensor_to_be_removed"
    )
    assert reg_entry is not None

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass_storage[storage_key]["data"]["binary_sensor"]) == 2

    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert ATTR_RESTORED not in state.attributes
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is not None
    assert ATTR_RESTORED not in state.attributes
    reg_entry = entity_registry.async_get(
        "binary_sensor.test_my_binary_sensor_to_be_removed"
    )
    assert reg_entry is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
        ),
    ]
    mock_device.client.list_entities_services = AsyncMock(
        return_value=(entity_info, [])
    )
    mock_device.client.device_info_and_list_entities = AsyncMock(
        return_value=(mock_device.device_info, entity_info, [])
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    on_future = hass.loop.create_future()

    @callback
    def _async_wait_for_on(event: Event[EventStateChangedData]) -> None:
        if event.data["new_state"].state == STATE_ON:
            on_future.set_result(None)

    async_track_state_change_event(
        hass, ["binary_sensor.test_my_binary_sensor"], _async_wait_for_on
    )
    await hass.async_block_till_done()
    async with asyncio.timeout(2):
        await on_future

    assert mock_device.entry.entry_id == entry_id
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is None

    await hass.async_block_till_done()

    reg_entry = entity_registry.async_get(
        "binary_sensor.test_my_binary_sensor_to_be_removed"
    )
    assert reg_entry is None
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(hass_storage[storage_key]["data"]["binary_sensor"]) == 1


async def test_entities_for_entire_platform_removed(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_client: APIClient,
    hass_storage: dict[str, Any],
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor_to_be_removed",
            key=1,
            name="my binary_sensor to be removed",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]
    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
    )
    entry = mock_device.entry
    entry_id = entry.entry_id
    storage_key = f"esphome.{entry_id}"
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is not None
    assert state.state == STATE_ON

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass_storage[storage_key]["data"]["binary_sensor"]) == 1

    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is not None
    reg_entry = entity_registry.async_get(
        "binary_sensor.test_my_binary_sensor_to_be_removed"
    )
    assert reg_entry is not None
    assert state.attributes[ATTR_RESTORED] is True

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entry=entry,
    )
    assert mock_device.entry.entry_id == entry_id
    state = hass.states.get("binary_sensor.test_my_binary_sensor_to_be_removed")
    assert state is None
    reg_entry = entity_registry.async_get(
        "binary_sensor.test_my_binary_sensor_to_be_removed"
    )
    assert reg_entry is None
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(hass_storage[storage_key]["data"]["binary_sensor"]) == 0


async def test_entity_info_object_ids(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="object_id_is_used",
            key=1,
            name="my binary_sensor",
        )
    ]
    states = []
    await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
    )
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None


async def test_deep_sleep_device(
    hass: HomeAssistant,
    mock_client: APIClient,
    hass_storage: dict[str, Any],
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
        ),
        SensorInfo(
            object_id="my_sensor",
            key=3,
            name="my sensor",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
        BinarySensorState(key=2, state=True, missing_state=False),
        SensorState(key=3, state=123.0, missing_state=False),
    ]
    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
        device_info={"has_deep_sleep": True},
    )
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON
    state = hass.states.get("sensor.test_my_sensor")
    assert state is not None
    assert state.state == "123.0"

    await mock_device.mock_disconnect(False)
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE
    state = hass.states.get("sensor.test_my_sensor")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    await mock_device.mock_connect()
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON
    state = hass.states.get("sensor.test_my_sensor")
    assert state is not None
    assert state.state == "123.0"

    await mock_device.mock_disconnect(True)
    await hass.async_block_till_done()
    await mock_device.mock_connect()
    await hass.async_block_till_done()
    mock_device.set_state(BinarySensorState(key=1, state=False, missing_state=False))
    mock_device.set_state(SensorState(key=3, state=56, missing_state=False))
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_OFF
    state = hass.states.get("sensor.test_my_sensor")
    assert state is not None
    assert state.state == "56"

    await mock_device.mock_disconnect(True)
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_OFF
    state = hass.states.get("sensor.test_my_sensor")
    assert state is not None
    assert state.state == "56"

    await mock_device.mock_connect()
    await hass.async_block_till_done()
    await mock_device.mock_disconnect(False)
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE
    state = hass.states.get("sensor.test_my_sensor")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    await mock_device.mock_connect()
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()


    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON


async def test_esphome_device_without_friendly_name(
    hass: HomeAssistant,
    mock_client: APIClient,
    hass_storage: dict[str, Any],
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
        BinarySensorState(key=2, state=True, missing_state=False),
    ]
    await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
        device_info={"friendly_name": None},
    )
    state = hass.states.get("binary_sensor.test_my_binary_sensor")
    assert state is not None
    assert state.state == STATE_ON


async def test_entity_without_name_device_with_friendly_name(
    hass: HomeAssistant,
    mock_client: APIClient,
    hass_storage: dict[str, Any],
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]
    await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
        device_info={"friendly_name": "The Best Mixer", "name": "mixer"},
    )
    state = hass.states.get("binary_sensor.the_best_mixer")
    assert state is not None
    assert state.state == STATE_ON


    assert state.attributes[ATTR_FRIENDLY_NAME] == "The Best Mixer"


@pytest.mark.usefixtures("hass_storage")
async def test_entity_id_preserved_on_upgrade(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    entity_registry: er.EntityRegistry,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="my",
            key=1,
            name="my",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]
    assert (
        build_unique_id("11:22:33:44:55:AA", entity_info[0])
        == "11:22:33:44:55:AA-binary_sensor-my"
    )

    entry = entity_registry.async_get_or_create(
        Platform.BINARY_SENSOR,
        DOMAIN,
        "11:22:33:44:55:AA-binary_sensor-my",
        suggested_object_id="should_not_change",
    )
    assert entry.entity_id == "binary_sensor.should_not_change"
    await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
        device_info={"friendly_name": "The Best Mixer", "name": "mixer"},
    )
    state = hass.states.get("binary_sensor.should_not_change")
    assert state is not None


@pytest.mark.usefixtures("hass_storage")
async def test_entity_id_preserved_on_upgrade_old_format_entity_id(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
    entity_registry: er.EntityRegistry,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="my",
            key=1,
            name="my",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]
    assert (
        build_unique_id("11:22:33:44:55:AA", entity_info[0])
        == "11:22:33:44:55:AA-binary_sensor-my"
    )

    entry = entity_registry.async_get_or_create(
        Platform.BINARY_SENSOR,
        DOMAIN,
        "11:22:33:44:55:AA-binary_sensor-my",
        suggested_object_id="my",
    )
    assert entry.entity_id == "binary_sensor.my"
    await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
        device_info={"name": "mixer"},
    )
    state = hass.states.get("binary_sensor.my")
    assert state is not None


async def test_entity_id_preserved_on_upgrade_when_in_storage(
    hass: HomeAssistant,
    mock_client: APIClient,
    hass_storage: dict[str, Any],
    mock_esphome_device: MockESPHomeDeviceType,
    entity_registry: er.EntityRegistry,
) -> None:

    entity_info = [
        BinarySensorInfo(
            object_id="my",
            key=1,
            name="my",
        ),
    ]
    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]
    device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
        device_info={"friendly_name": "The Best Mixer", "name": "mixer"},
    )
    state = hass.states.get("binary_sensor.the_best_mixer_my")
    assert state is not None

    ent_reg_entry = entity_registry.async_get_or_create(
        Platform.BINARY_SENSOR,
        DOMAIN,
        "11:22:33:44:55:AA-binary_sensor-my",
    )
    entity_registry.async_update_entity(
        ent_reg_entry.entity_id,
        new_entity_id="binary_sensor.user_named",
    )
    await hass.config_entries.async_unload(device.entry.entry_id)
    await hass.async_block_till_done()
    entry = device.entry
    entry_id = entry.entry_id
    storage_key = f"esphome.{entry_id}"
    assert len(hass_storage[storage_key]["data"]["binary_sensor"]) == 1
    binary_sensor_data: dict[str, Any] = hass_storage[storage_key]["data"][
        "binary_sensor"
    ][0]
    assert binary_sensor_data["name"] == "my"
    assert binary_sensor_data["object_id"] == "my"
    device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
        entry=entry,
        device_info={"friendly_name": "The Best Mixer", "name": "mixer"},
    )
    state = hass.states.get("binary_sensor.user_named")
    assert state is not None


async def test_deep_sleep_added_after_setup(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=[
            BinarySensorInfo(
                object_id="test",
                key=1,
                name="test",
            ),
        ],
        states=[
            BinarySensorState(key=1, state=True, missing_state=False),
        ],
        device_info={"has_deep_sleep": False},
    )

    entity_id = "binary_sensor.test_test"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON

    await mock_device.mock_disconnect(expected_disconnect=True)


    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    await mock_device.mock_connect()


    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON

    await mock_device.mock_disconnect(expected_disconnect=True)
    new_device_info = DeviceInfo(
        **{**asdict(mock_device.device_info), "has_deep_sleep": True}
    )
    mock_device.client.device_info = AsyncMock(return_value=new_device_info)
    mock_device.client.device_info_and_list_entities = AsyncMock(
        return_value=(
            new_device_info,
            mock_device.client.list_entities_services.return_value[0],
            mock_device.client.list_entities_services.return_value[1],
        )
    )
    mock_device.device_info = new_device_info

    await mock_device.mock_connect()


    await mock_device.mock_disconnect(expected_disconnect=True)


    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON


async def test_entity_assignment_to_sub_device(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:

    device_registry = dr.async_get(hass)


    sub_devices = [
        SubDeviceInfo(device_id=11111111, name="Motion Sensor", area_id=0),
        SubDeviceInfo(device_id=22222222, name="Door Sensor", area_id=0),
    ]

    device_info = {
        "devices": sub_devices,
    }


    entity_info = [

        BinarySensorInfo(
            object_id="main_sensor",
            key=1,
            name="Main Sensor",
            device_id=0,
        ),

        BinarySensorInfo(
            object_id="motion",
            key=2,
            name="Motion",
            device_id=11111111,
        ),

        BinarySensorInfo(
            object_id="door",
            key=3,
            name="Door",
            device_id=22222222,
        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False, device_id=0),
        BinarySensorState(key=2, state=False, missing_state=False, device_id=11111111),
        BinarySensorState(key=3, state=True, missing_state=False, device_id=22222222),
    ]

    device = await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )


    main_device = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, device.device_info.mac_address)}
    )
    assert main_device is not None


    main_sensor = entity_registry.async_get("binary_sensor.test_main_sensor")
    assert main_sensor is not None
    assert main_sensor.device_id == main_device.id


    sub_device_1 = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{device.device_info.mac_address}_11111111")}
    )
    assert sub_device_1 is not None

    motion_sensor = entity_registry.async_get("binary_sensor.motion_sensor_motion")
    assert motion_sensor is not None
    assert motion_sensor.device_id == sub_device_1.id


    sub_device_2 = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{device.device_info.mac_address}_22222222")}
    )
    assert sub_device_2 is not None

    door_sensor = entity_registry.async_get("binary_sensor.door_sensor_door")
    assert door_sensor is not None
    assert door_sensor.device_id == sub_device_2.id


    assert hass.states.get("binary_sensor.test_main_sensor").state == STATE_ON
    assert hass.states.get("binary_sensor.motion_sensor_motion").state == STATE_OFF
    assert hass.states.get("binary_sensor.door_sensor_door").state == STATE_ON



    main_sensor_state = hass.states.get("binary_sensor.test_main_sensor")
    assert main_sensor_state.attributes[ATTR_FRIENDLY_NAME] == "Test Main Sensor"


    motion_sensor_state = hass.states.get("binary_sensor.motion_sensor_motion")
    assert motion_sensor_state.attributes[ATTR_FRIENDLY_NAME] == "Motion Sensor Motion"


    door_sensor_state = hass.states.get("binary_sensor.door_sensor_door")
    assert door_sensor_state.attributes[ATTR_FRIENDLY_NAME] == "Door Sensor Door"


async def test_entity_friendly_names_with_empty_device_names(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    sub_devices = [
        SubDeviceInfo(device_id=11111111, name="", area_id=0),
        SubDeviceInfo(
            device_id=22222222, name="Kitchen Light", area_id=0
        ),
    ]

    device_info = {
        "devices": sub_devices,
        "friendly_name": "Main Device",
    }


    entity_info = [
        BinarySensorInfo(
            object_id="motion",
            key=1,
            name="Motion Detected",
            device_id=11111111,
        ),

        BinarySensorInfo(
            object_id="status",
            key=2,
            name="Status",
            device_id=22222222,
        ),

        BinarySensorInfo(
            object_id="sensor",
            key=3,
            name="",
            device_id=22222222,
        ),

        BinarySensorInfo(
            object_id="main_status",
            key=4,
            name="Main Status",
            device_id=0,
        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
        BinarySensorState(key=2, state=False, missing_state=False),
        BinarySensorState(key=3, state=True, missing_state=False),
        BinarySensorState(key=4, state=True, missing_state=False),
    ]

    await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )



    state_1 = hass.states.get("binary_sensor.main_device_motion_detected")
    assert state_1 is not None


    assert state_1.attributes[ATTR_FRIENDLY_NAME] == "Main Device Motion Detected"


    state_2 = hass.states.get("binary_sensor.kitchen_light_status")
    assert state_2 is not None

    assert state_2.attributes[ATTR_FRIENDLY_NAME] == "Kitchen Light Status"


    state_3 = hass.states.get("binary_sensor.kitchen_light")
    assert state_3 is not None

    assert state_3.attributes[ATTR_FRIENDLY_NAME] == "Kitchen Light"


    state_4 = hass.states.get("binary_sensor.main_device_main_status")
    assert state_4 is not None
    assert state_4.attributes[ATTR_FRIENDLY_NAME] == "Main Device Main Status"


async def test_entity_switches_between_devices(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    sub_devices = [
        SubDeviceInfo(device_id=11111111, name="Sub Device 1", area_id=0),
        SubDeviceInfo(device_id=22222222, name="Sub Device 2", area_id=0),
    ]

    device_info = {
        "devices": sub_devices,
    }


    entity_info = [
        BinarySensorInfo(
            object_id="sensor",
            key=1,
            name="Test Sensor",

        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False, device_id=0),
    ]

    device = await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )


    main_device = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, device.device_info.mac_address)}
    )
    assert main_device is not None

    sensor_entity = entity_registry.async_get("binary_sensor.test_test_sensor")
    assert sensor_entity is not None
    assert sensor_entity.device_id == main_device.id


    updated_entity_info = [
        BinarySensorInfo(
            object_id="sensor",
            key=1,
            name="Test Sensor",
            device_id=11111111,
        ),
    ]


    mock_client.list_entities_services = AsyncMock(
        return_value=(updated_entity_info, [])
    )
    mock_client.device_info_and_list_entities = AsyncMock(
        return_value=(device.device_info, updated_entity_info, [])
    )

    await device.mock_disconnect(expected_disconnect=False)
    await device.mock_connect()


    sub_device_1 = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{device.device_info.mac_address}_11111111")}
    )
    assert sub_device_1 is not None

    sensor_entity = entity_registry.async_get("binary_sensor.test_test_sensor")
    assert sensor_entity is not None
    assert sensor_entity.device_id == sub_device_1.id


    updated_entity_info = [
        BinarySensorInfo(
            object_id="sensor",
            key=1,
            name="Test Sensor",
            device_id=22222222,
        ),
    ]

    mock_client.list_entities_services = AsyncMock(
        return_value=(updated_entity_info, [])
    )
    mock_client.device_info_and_list_entities = AsyncMock(
        return_value=(device.device_info, updated_entity_info, [])
    )
    await device.mock_disconnect(expected_disconnect=False)
    await device.mock_connect()


    sub_device_2 = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{device.device_info.mac_address}_22222222")}
    )
    assert sub_device_2 is not None

    sensor_entity = entity_registry.async_get("binary_sensor.test_test_sensor")
    assert sensor_entity is not None
    assert sensor_entity.device_id == sub_device_2.id


    updated_entity_info = [
        BinarySensorInfo(
            object_id="sensor",
            key=1,
            name="Test Sensor",

        ),
    ]

    mock_client.list_entities_services = AsyncMock(
        return_value=(updated_entity_info, [])
    )
    mock_client.device_info_and_list_entities = AsyncMock(
        return_value=(device.device_info, updated_entity_info, [])
    )
    await device.mock_disconnect(expected_disconnect=False)
    await device.mock_connect()


    sensor_entity = entity_registry.async_get("binary_sensor.test_test_sensor")
    assert sensor_entity is not None
    assert sensor_entity.device_id == main_device.id


async def test_entity_id_uses_sub_device_name(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    sub_devices = [
        SubDeviceInfo(device_id=11111111, name="motion_sensor", area_id=0),
        SubDeviceInfo(device_id=22222222, name="door_sensor", area_id=0),
    ]

    device_info = {
        "devices": sub_devices,
        "name": "main_device",
        "friendly_name": "Main Device",
    }


    entity_info = [

        BinarySensorInfo(
            object_id="main_sensor",
            key=1,
            name="Main Sensor",
            device_id=0,
        ),

        BinarySensorInfo(
            object_id="motion",
            key=2,
            name="Motion",
            device_id=11111111,
        ),

        BinarySensorInfo(
            object_id="door",
            key=3,
            name="Door",
            device_id=22222222,
        ),

        BinarySensorInfo(
            object_id="sensor_no_name",
            key=4,
            name="",
            device_id=11111111,
        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
        BinarySensorState(key=2, state=False, missing_state=False),
        BinarySensorState(key=3, state=True, missing_state=False),
        BinarySensorState(key=4, state=True, missing_state=False),
    ]

    await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )



    assert hass.states.get("binary_sensor.main_device_main_sensor") is not None



    assert hass.states.get("binary_sensor.motion_sensor_motion") is not None



    assert hass.states.get("binary_sensor.door_sensor_door") is not None



    assert hass.states.get("binary_sensor.motion_sensor") is not None


async def test_entity_id_with_empty_sub_device_name(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    sub_devices = [
        SubDeviceInfo(device_id=11111111, name="", area_id=0),
    ]

    device_info = {
        "devices": sub_devices,
        "name": "main_device",
        "friendly_name": "Main Device",
    }


    entity_info = [
        BinarySensorInfo(
            object_id="sensor",
            key=1,
            name="Sensor",
            device_id=11111111,
        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]

    await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )



    assert hass.states.get("binary_sensor.main_device_sensor") is not None


async def test_unique_id_migration_when_entity_moves_between_devices(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    device_info = {
        "name": "test",
        "devices": [],
    }


    entity_info = [
        BinarySensorInfo(
            object_id="temperature",
            key=1,
            name="Temperature",
            device_id=0,
        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]

    device = await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )


    state = hass.states.get("binary_sensor.test_temperature")
    assert state is not None


    entity_entry = entity_registry.async_get("binary_sensor.test_temperature")
    assert entity_entry is not None
    initial_unique_id = entity_entry.unique_id

    assert "@" not in initial_unique_id


    sub_devices = [
        SubDeviceInfo(device_id=22222222, name="kitchen_controller", area_id=0),
    ]


    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]


    entry_data = entry.runtime_data
    entry_data.device_id_to_name = {
        sub_device.device_id: sub_device.name for sub_device in sub_devices
    }



    current_device_info = mock_client.device_info.return_value
    device_info_dict = asdict(current_device_info)


    device_info_dict["devices"] = sub_devices


    new_device_info = DeviceInfo(**device_info_dict)


    mock_client.device_info.return_value = new_device_info


    new_entity_info = [
        BinarySensorInfo(
            object_id="temperature",
            key=1,
            name="Temperature",
            device_id=22222222,
        ),
    ]


    mock_client.list_entities_services = AsyncMock(return_value=(new_entity_info, []))
    mock_client.device_info_and_list_entities = AsyncMock(
        return_value=(device.device_info, new_entity_info, [])
    )


    await device.mock_disconnect(expected_disconnect=False)
    await device.mock_connect()


    await hass.async_block_till_done()



    state = hass.states.get("binary_sensor.test_temperature")
    assert state is not None


    entity_entry = entity_registry.async_get("binary_sensor.test_temperature")
    assert entity_entry is not None



    expected_unique_id = f"{initial_unique_id}@22222222"
    assert entity_entry.unique_id == expected_unique_id


    sub_device = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{device.device_info.mac_address}_22222222")}
    )
    assert sub_device is not None
    assert entity_entry.device_id == sub_device.id


async def test_unique_id_migration_sub_device_to_main_device(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    sub_devices = [
        SubDeviceInfo(device_id=22222222, name="kitchen_controller", area_id=0),
    ]

    device_info = {
        "name": "test",
        "devices": sub_devices,
    }


    entity_info = [
        BinarySensorInfo(
            object_id="temperature",
            key=1,
            name="Temperature",
            device_id=22222222,
        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]

    device = await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )


    state = hass.states.get("binary_sensor.kitchen_controller_temperature")
    assert state is not None


    entity_entry = entity_registry.async_get(
        "binary_sensor.kitchen_controller_temperature"
    )
    assert entity_entry is not None
    initial_unique_id = entity_entry.unique_id

    assert "@22222222" in initial_unique_id


    new_entity_info = [
        BinarySensorInfo(
            object_id="temperature",
            key=1,
            name="Temperature",
            device_id=0,
        ),
    ]


    mock_client.list_entities_services = AsyncMock(return_value=(new_entity_info, []))
    mock_client.device_info_and_list_entities = AsyncMock(
        return_value=(device.device_info, new_entity_info, [])
    )


    await device.mock_disconnect(expected_disconnect=False)
    await device.mock_connect()
    await hass.async_block_till_done()


    state = hass.states.get("binary_sensor.kitchen_controller_temperature")
    assert state is not None


    entity_entry = entity_registry.async_get(
        "binary_sensor.kitchen_controller_temperature"
    )
    assert entity_entry is not None


    expected_unique_id = initial_unique_id.replace("@22222222", "")
    assert entity_entry.unique_id == expected_unique_id


    main_device = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, device.device_info.mac_address)}
    )
    assert main_device is not None
    assert entity_entry.device_id == main_device.id


async def test_unique_id_migration_between_sub_devices(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    sub_devices = [
        SubDeviceInfo(device_id=22222222, name="kitchen_controller", area_id=0),
        SubDeviceInfo(device_id=33333333, name="bedroom_controller", area_id=0),
    ]

    device_info = {
        "name": "test",
        "devices": sub_devices,
    }


    entity_info = [
        BinarySensorInfo(
            object_id="temperature",
            key=1,
            name="Temperature",
            device_id=22222222,
        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False),
    ]

    device = await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )


    state = hass.states.get("binary_sensor.kitchen_controller_temperature")
    assert state is not None


    entity_entry = entity_registry.async_get(
        "binary_sensor.kitchen_controller_temperature"
    )
    assert entity_entry is not None
    initial_unique_id = entity_entry.unique_id

    assert "@22222222" in initial_unique_id


    new_entity_info = [
        BinarySensorInfo(
            object_id="temperature",
            key=1,
            name="Temperature",
            device_id=33333333,
        ),
    ]


    mock_client.list_entities_services = AsyncMock(return_value=(new_entity_info, []))
    mock_client.device_info_and_list_entities = AsyncMock(
        return_value=(device.device_info, new_entity_info, [])
    )


    await device.mock_disconnect(expected_disconnect=False)
    await device.mock_connect()
    await hass.async_block_till_done()


    state = hass.states.get("binary_sensor.kitchen_controller_temperature")
    assert state is not None


    entity_entry = entity_registry.async_get(
        "binary_sensor.kitchen_controller_temperature"
    )
    assert entity_entry is not None


    expected_unique_id = initial_unique_id.replace("@22222222", "@33333333")
    assert entity_entry.unique_id == expected_unique_id


    bedroom_device = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{device.device_info.mac_address}_33333333")}
    )
    assert bedroom_device is not None
    assert entity_entry.device_id == bedroom_device.id


async def test_entity_device_id_rename_in_yaml(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:


    sub_devices = [
        SubDeviceInfo(device_id=11111111, name="old_device", area_id=0),
    ]

    device_info = {
        "name": "test",
        "devices": sub_devices,
    }


    entity_info = [
        BinarySensorInfo(
            object_id="sensor",
            key=1,
            name="Sensor",
            device_id=11111111,
        ),
    ]

    states = [
        BinarySensorState(key=1, state=True, missing_state=False, device_id=11111111),
    ]

    device = await mock_esphome_device(
        mock_client=mock_client,
        device_info=device_info,
        entity_info=entity_info,
        states=states,
    )


    state = hass.states.get("binary_sensor.old_device_sensor")
    assert state is not None
    assert state.state == STATE_ON


    await hass.async_block_till_done()


    entity_entry = entity_registry.async_get("binary_sensor.old_device_sensor")
    assert entity_entry is not None
    initial_unique_id = entity_entry.unique_id

    assert "@11111111" in initial_unique_id




    renamed_sub_devices = [
        SubDeviceInfo(device_id=99999999, name="renamed_device", area_id=0),
    ]


    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]


    entry_data = entry.runtime_data
    entry_data.device_id_to_name = {
        sub_device.device_id: sub_device.name for sub_device in renamed_sub_devices
    }


    current_device_info = mock_client.device_info.return_value
    device_info_dict = asdict(current_device_info)
    device_info_dict["devices"] = renamed_sub_devices
    new_device_info = DeviceInfo(**device_info_dict)
    mock_client.device_info.return_value = new_device_info


    new_entity_info = [
        BinarySensorInfo(
            object_id="sensor",
            key=1,
            name="Sensor",
            device_id=99999999,
        ),
    ]


    mock_client.list_entities_services = AsyncMock(return_value=(new_entity_info, []))
    mock_client.device_info_and_list_entities = AsyncMock(
        return_value=(new_device_info, new_entity_info, [])
    )


    await device.mock_disconnect(expected_disconnect=False)
    await device.mock_connect()
    await hass.async_block_till_done()


    state = hass.states.get("binary_sensor.old_device_sensor")
    assert state is None



    state = hass.states.get("binary_sensor.renamed_device_sensor")
    assert state is not None
    assert state.state == STATE_ON


    entity_entry = entity_registry.async_get("binary_sensor.renamed_device_sensor")
    assert entity_entry is not None


    base_unique_id = initial_unique_id.replace("@11111111", "")
    expected_unique_id = f"{base_unique_id}@99999999"
    assert entity_entry.unique_id == expected_unique_id


    renamed_device = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{device.device_info.mac_address}_99999999")}
    )
    assert renamed_device is not None
    assert entity_entry.device_id == renamed_device.id


@pytest.mark.parametrize(
    ("unicode_name", "expected_entity_id"),
    [
        ("Árvíztűrő tükörfúrógép", "binary_sensor.test_arvizturo_tukorfurogep"),
        ("Teplota venku °C", "binary_sensor.test_teplota_venku_degc"),
        ("Влажность %", "binary_sensor.test_vlazhnost"),
        ("Chinese sensor", "binary_sensor.test_chinese_sensor"),
        ("Sensor à côté", "binary_sensor.test_sensor_a_cote"),
        ("τιμή αισθητήρα", "binary_sensor.test_time_aisthetera"),
    ],
)
async def test_entity_with_unicode_name(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
    unicode_name: str,
    expected_entity_id: str,
) -> None:









    sanitized_object_id = "_".join("_" * len(word) for word in unicode_name.split())

    entity_info = [
        BinarySensorInfo(
            object_id=sanitized_object_id,
            key=1,
            name=unicode_name,
        )
    ]
    states = [BinarySensorState(key=1, state=True)]

    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
    )


    state = hass.states.get(expected_entity_id)
    assert state is not None, f"Entity with ID {expected_entity_id} should exist"
    assert state.state == STATE_ON


    assert state.attributes["friendly_name"] == f"Test {unicode_name}"



    wrong_entity_id = f"binary_sensor.test_{sanitized_object_id}"
    wrong_state = hass.states.get(wrong_entity_id)
    assert wrong_state is None, f"Entity should NOT be found at {wrong_entity_id}"


async def test_entity_without_name_uses_device_name_only(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:





    entity_info = [
        BinarySensorInfo(
            object_id="some_sanitized_id",
            key=1,
            name="",
        )
    ]
    states = [BinarySensorState(key=1, state=True)]

    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
    )


    expected_entity_id = "binary_sensor.test"
    state = hass.states.get(expected_entity_id)
    assert state is not None, f"Entity {expected_entity_id} should exist"
    assert state.state == STATE_ON
