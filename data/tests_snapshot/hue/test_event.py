

from unittest.mock import Mock

from homeassistant.components.event import ATTR_EVENT_TYPE, ATTR_EVENT_TYPES
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.util.json import JsonArrayType

from .conftest import setup_platform
from .const import FAKE_DEVICE, FAKE_ROTARY, FAKE_ZIGBEE_CONNECTIVITY


async def test_event(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)
    await setup_platform(hass, mock_bridge_v2, Platform.EVENT)

    assert len(hass.states.async_all()) == 8


    state = hass.states.get("event.hue_dimmer_switch_with_4_controls_button_1")
    assert state
    assert state.state == "unknown"
    assert state.name == "Hue Dimmer switch with 4 controls Button 1"

    assert state.attributes[ATTR_EVENT_TYPES] == [
        "initial_press",
        "repeat",
        "short_release",
        "long_press",
        "long_release",
    ]

    btn_event = {
        "button": {
            "button_report": {
                "event": "initial_press",
                "updated": "2023-09-27T10:06:41.822Z",
            }
        },
        "id": "f92aa267-1387-4f02-9950-210fb7ca1f5a",
        "metadata": {"control_id": 1},
        "type": "button",
    }
    mock_bridge_v2.api.emit_event("update", btn_event)
    await hass.async_block_till_done()
    state = hass.states.get("event.hue_dimmer_switch_with_4_controls_button_1")
    assert state.attributes[ATTR_EVENT_TYPE] == "initial_press"

    btn_event = {
        "button": {
            "button_report": {
                "event": "long_release",
                "updated": "2023-09-27T10:06:41.822Z",
            }
        },
        "id": "f92aa267-1387-4f02-9950-210fb7ca1f5a",
        "metadata": {"control_id": 1},
        "type": "button",
    }
    mock_bridge_v2.api.emit_event("update", btn_event)
    await hass.async_block_till_done()
    state = hass.states.get("event.hue_dimmer_switch_with_4_controls_button_1")
    assert state.attributes[ATTR_EVENT_TYPE] == "long_release"


async def test_sensor_add_update(hass: HomeAssistant, mock_bridge_v2: Mock) -> None:

    await mock_bridge_v2.api.load_test_data([FAKE_DEVICE, FAKE_ZIGBEE_CONNECTIVITY])
    await setup_platform(hass, mock_bridge_v2, Platform.EVENT)

    test_entity_id = "event.hue_mocked_device_rotary"


    assert hass.states.get(test_entity_id) is None


    mock_bridge_v2.api.emit_event("add", FAKE_ROTARY)
    await hass.async_block_till_done()


    state = hass.states.get(test_entity_id)
    assert state is not None
    assert state.state == "unknown"
    assert state.name == "Hue mocked device Rotary"

    assert state.attributes[ATTR_EVENT_TYPES] == ["clock_wise", "counter_clock_wise"]


    btn_event = {
        "id": "fake_relative_rotary",
        "relative_rotary": {
            "rotary_report": {
                "action": "repeat",
                "rotation": {
                    "direction": "counter_clock_wise",
                    "steps": 60,
                    "duration": 400,
                },
                "updated": "2023-09-27T10:06:41.822Z",
            }
        },
        "type": "relative_rotary",
    }
    mock_bridge_v2.api.emit_event("update", btn_event)
    await hass.async_block_till_done()
    state = hass.states.get(test_entity_id)
    assert state.attributes[ATTR_EVENT_TYPE] == "counter_clock_wise"
    assert state.attributes["action"] == "repeat"
    assert state.attributes["steps"] == 60
    assert state.attributes["duration"] == 400
