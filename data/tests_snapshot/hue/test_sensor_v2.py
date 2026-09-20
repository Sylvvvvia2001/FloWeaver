

from unittest.mock import Mock

from homeassistant.components import hue
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util.json import JsonArrayType

from .conftest import setup_bridge, setup_platform
from .const import FAKE_DEVICE, FAKE_SENSOR, FAKE_ZIGBEE_CONNECTIVITY

from tests.common import MockConfigEntry


async def test_sensors(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_bridge_v2: Mock,
    v2_resources_test_data: JsonArrayType,
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)

    await setup_platform(hass, mock_bridge_v2, Platform.SENSOR)

    assert len(mock_bridge_v2.mock_requests) == 0

    assert len(hass.states.async_all()) == 7


    sensor = hass.states.get("sensor.hue_motion_sensor_temperature")
    assert sensor is not None
    assert sensor.state == "18.1"
    assert sensor.attributes["friendly_name"] == "Hue motion sensor Temperature"
    assert sensor.attributes["device_class"] == "temperature"
    assert sensor.attributes["state_class"] == "measurement"
    assert sensor.attributes["unit_of_measurement"] == "°C"


    sensor = hass.states.get("sensor.hue_motion_sensor_illuminance")
    assert sensor is not None
    assert sensor.state == "63"
    assert sensor.attributes["friendly_name"] == "Hue motion sensor Illuminance"
    assert sensor.attributes["device_class"] == "illuminance"
    assert sensor.attributes["state_class"] == "measurement"
    assert sensor.attributes["unit_of_measurement"] == "lx"
    assert sensor.attributes["light_level"] == 18027


    sensor = hass.states.get("sensor.wall_switch_with_2_controls_battery")
    assert sensor is not None
    assert sensor.state == "100"
    assert sensor.attributes["friendly_name"] == "Wall switch with 2 controls Battery"
    assert sensor.attributes["device_class"] == "battery"
    assert sensor.attributes["state_class"] == "measurement"
    assert sensor.attributes["unit_of_measurement"] == "%"
    assert sensor.attributes["battery_state"] == "normal"


    sensor = hass.states.get("sensor.sensor_group_illuminance")
    assert sensor is not None
    assert sensor.state == "0"
    assert sensor.attributes["friendly_name"] == "Sensor group Illuminance"
    assert sensor.attributes["device_class"] == "illuminance"
    assert sensor.attributes["state_class"] == "measurement"
    assert sensor.attributes["unit_of_measurement"] == "lx"
    assert sensor.attributes["light_level"] == 0


    entity_id = "sensor.wall_switch_with_2_controls_zigbee_connectivity"
    entity_entry = entity_registry.async_get(entity_id)

    assert entity_entry
    assert entity_entry.disabled
    assert entity_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_enable_sensor(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_bridge_v2: Mock,
    v2_resources_test_data: JsonArrayType,
    mock_config_entry_v2: MockConfigEntry,
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)
    await setup_bridge(hass, mock_bridge_v2, mock_config_entry_v2)

    assert await async_setup_component(hass, hue.DOMAIN, {}) is True
    await hass.async_block_till_done()
    await hass.config_entries.async_forward_entry_setups(
        mock_config_entry_v2, [Platform.SENSOR]
    )

    entity_id = "sensor.wall_switch_with_2_controls_zigbee_connectivity"
    entity_entry = entity_registry.async_get(entity_id)

    assert entity_entry
    assert entity_entry.disabled
    assert entity_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


    updated_entry = entity_registry.async_update_entity(
        entity_entry.entity_id, disabled_by=None
    )
    assert updated_entry != entity_entry
    assert updated_entry.disabled is False


    await hass.config_entries.async_forward_entry_unload(
        mock_config_entry_v2, Platform.SENSOR
    )
    await hass.config_entries.async_forward_entry_setups(
        mock_config_entry_v2, [Platform.SENSOR]
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == "connected"
    assert state.attributes["mac_address"] == "00:17:88:01:0b:aa:bb:99"


async def test_sensor_add_update(hass: HomeAssistant, mock_bridge_v2: Mock) -> None:

    await mock_bridge_v2.api.load_test_data([FAKE_DEVICE, FAKE_ZIGBEE_CONNECTIVITY])
    await setup_platform(hass, mock_bridge_v2, Platform.SENSOR)

    test_entity_id = "sensor.hue_mocked_device_temperature"


    assert hass.states.get(test_entity_id) is None


    mock_bridge_v2.api.emit_event("add", FAKE_SENSOR)
    await hass.async_block_till_done()


    test_entity = hass.states.get(test_entity_id)
    assert test_entity is not None
    assert test_entity.state == "18.0"


    updated_sensor = {**FAKE_SENSOR, "temperature": {"temperature": 22.5}}
    mock_bridge_v2.api.emit_event("update", updated_sensor)
    await hass.async_block_till_done()
    test_entity = hass.states.get(test_entity_id)
    assert test_entity is not None
    assert test_entity.state == "22.5"


async def test_grouped_light_level_sensor(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)
    await setup_platform(hass, mock_bridge_v2, Platform.SENSOR)


    sensor = hass.states.get("sensor.sensor_group_illuminance")
    assert sensor is not None
    assert (
        sensor.state == "0"
    )
    assert sensor.attributes["device_class"] == "illuminance"
    assert sensor.attributes["light_level"] == 0


    updated_sensor = {
        "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "type": "grouped_light_level",
        "light": {
            "light_level": 30000,
            "light_level_report": {
                "changed": "2023-09-23T08:20:51.384Z",
                "light_level": 30000,
            },
        },
    }
    mock_bridge_v2.api.emit_event("update", updated_sensor)
    await hass.async_block_till_done()
    sensor = hass.states.get("sensor.sensor_group_illuminance")
    assert (
        sensor.state == "999"
    )
