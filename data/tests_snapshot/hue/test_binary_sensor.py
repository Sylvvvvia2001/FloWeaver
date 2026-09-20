

from unittest.mock import Mock

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.util.json import JsonArrayType

from .conftest import setup_platform
from .const import FAKE_BINARY_SENSOR, FAKE_DEVICE, FAKE_ZIGBEE_CONNECTIVITY


async def test_binary_sensors(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)

    await setup_platform(hass, mock_bridge_v2, Platform.BINARY_SENSOR)

    assert len(mock_bridge_v2.mock_requests) == 0



    sensor = hass.states.get("binary_sensor.hue_motion_sensor_motion")
    assert sensor is not None
    assert sensor.state == "off"
    assert sensor.name == "Hue motion sensor Motion"
    assert sensor.attributes["device_class"] == "motion"


    sensor = hass.states.get("binary_sensor.philips_hue_entertainmentroom_1")
    assert sensor is not None
    assert sensor.state == "off"
    assert sensor.name == "Philips hue Entertainmentroom 1"
    assert sensor.attributes["device_class"] == "running"


    sensor = hass.states.get("binary_sensor.test_contact_sensor_opening")
    assert sensor is not None
    assert sensor.state == "off"
    assert sensor.name == "Test contact sensor Opening"
    assert sensor.attributes["device_class"] == "opening"

    mock_bridge_v2.api.emit_event(
        "update",
        {
            "enabled": False,
            "id": "18802b4a-b2f6-45dc-8813-99cde47f3a4a",
            "type": "contact",
        },
    )
    await hass.async_block_till_done()
    sensor = hass.states.get("binary_sensor.test_contact_sensor_opening")
    assert sensor.state == "unknown"


    sensor = hass.states.get("binary_sensor.test_contact_sensor_tamper")
    assert sensor is not None
    assert sensor.state == "off"
    assert sensor.name == "Test contact sensor Tamper"
    assert sensor.attributes["device_class"] == "tamper"

    mock_bridge_v2.api.emit_event(
        "update",
        {
            "id": "d7fcfab0-69e1-4afb-99df-6ed505211db4",
            "tamper_reports": [],
            "type": "tamper",
        },
    )
    await hass.async_block_till_done()
    sensor = hass.states.get("binary_sensor.test_contact_sensor_tamper")
    assert sensor.state == "off"


    sensor = hass.states.get("binary_sensor.test_camera_motion")
    assert sensor is not None
    assert sensor.state == "on"
    assert sensor.name == "Test Camera Motion"
    assert sensor.attributes["device_class"] == "motion"


    sensor = hass.states.get("binary_sensor.sensor_group_motion")
    assert sensor is not None
    assert sensor.state == "off"
    assert sensor.name == "Sensor group Motion"
    assert sensor.attributes["device_class"] == "motion"


    sensor = hass.states.get("binary_sensor.test_room_motion_aware_sensor_1")
    assert sensor is not None
    assert sensor.state == "off"
    assert sensor.name == "Test Room Motion Aware Sensor 1"
    assert sensor.attributes["device_class"] == "motion"


async def test_binary_sensor_add_update(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:

    await mock_bridge_v2.api.load_test_data([FAKE_DEVICE, FAKE_ZIGBEE_CONNECTIVITY])
    await setup_platform(hass, mock_bridge_v2, Platform.BINARY_SENSOR)

    test_entity_id = "binary_sensor.hue_mocked_device_motion"


    assert hass.states.get(test_entity_id) is None


    mock_bridge_v2.api.emit_event("add", FAKE_BINARY_SENSOR)
    await hass.async_block_till_done()


    test_entity = hass.states.get(test_entity_id)
    assert test_entity is not None
    assert test_entity.state == "off"


    updated_sensor = {**FAKE_BINARY_SENSOR, "motion": {"motion": True}}
    mock_bridge_v2.api.emit_event("update", updated_sensor)
    await hass.async_block_till_done()
    test_entity = hass.states.get(test_entity_id)
    assert test_entity is not None
    assert test_entity.state == "on"

    updated_sensor = {
        **FAKE_BINARY_SENSOR,
        "motion": {
            "motion": False,
            "motion_report": {"changed": "2025-01-01T00:00:00Z", "motion": True},
        },
    }
    mock_bridge_v2.api.emit_event("update", updated_sensor)
    await hass.async_block_till_done()
    assert hass.states.get(test_entity_id).state == "on"


    updated_sensor = {
        **FAKE_BINARY_SENSOR,
        "motion": {
            "motion": True,
            "motion_report": {"changed": "2025-01-01T00:00:01Z", "motion": False},
        },
    }
    mock_bridge_v2.api.emit_event("update", updated_sensor)
    await hass.async_block_till_done()
    assert hass.states.get(test_entity_id).state == "off"


async def test_grouped_motion_sensor(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)
    await setup_platform(hass, mock_bridge_v2, Platform.BINARY_SENSOR)


    sensor = hass.states.get("binary_sensor.sensor_group_motion")
    assert sensor is not None
    assert sensor.state == "off"
    assert sensor.attributes["device_class"] == "motion"


    updated_sensor = {
        "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
        "type": "grouped_motion",
        "motion": {
            "motion_report": {"changed": "2023-09-23T08:20:51.384Z", "motion": True}
        },
    }
    mock_bridge_v2.api.emit_event("update", updated_sensor)
    await hass.async_block_till_done()
    sensor = hass.states.get("binary_sensor.sensor_group_motion")
    assert sensor.state == "on"


    disabled_sensor = {
        "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
        "type": "grouped_motion",
        "enabled": False,
    }
    mock_bridge_v2.api.emit_event("update", disabled_sensor)
    await hass.async_block_till_done()
    sensor = hass.states.get("binary_sensor.sensor_group_motion")
    assert sensor.state == "unknown"


async def test_motion_aware_sensor(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)
    await setup_platform(hass, mock_bridge_v2, Platform.BINARY_SENSOR)


    sensor = hass.states.get("binary_sensor.test_room_motion_aware_sensor_1")
    assert sensor is not None
    assert sensor.state == "off"
    assert sensor.attributes["device_class"] == "motion"


    updated_sensor = {
        "id": "8b7e4f82-9c3d-4e1a-a5f6-8d9c7b2a3e4f",
        "type": "security_area_motion",
        "motion": {
            "motion": True,
            "motion_valid": True,
            "motion_report": {"changed": "2023-09-23T05:54:08.166Z", "motion": True},
        },
    }
    mock_bridge_v2.api.emit_event("update", updated_sensor)
    await hass.async_block_till_done()
    sensor = hass.states.get("binary_sensor.test_room_motion_aware_sensor_1")
    assert sensor.state == "on"


    updated_config = {
        "id": "5e6f7a8b-9c1d-4e2f-b3a4-5c6d7e8f9a0b",
        "type": "motion_area_configuration",
        "name": "Updated Motion Area",
    }
    mock_bridge_v2.api.emit_event("update", updated_config)
    await hass.async_block_till_done()


    sensor = hass.states.get("binary_sensor.test_room_motion_aware_sensor_1")
    assert sensor is not None
    assert sensor.name == "Test Room Updated Motion Area"
