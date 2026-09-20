

from unittest.mock import Mock

from homeassistant.components.light import (
    ATTR_EFFECT,
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.util import color as color_util
from homeassistant.util.json import JsonArrayType

from .conftest import setup_platform
from .const import FAKE_DEVICE, FAKE_LIGHT, FAKE_ZIGBEE_CONNECTIVITY


async def test_lights(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)

    await setup_platform(hass, mock_bridge_v2, Platform.LIGHT)

    assert len(mock_bridge_v2.mock_requests) == 0

    assert len(hass.states.async_all()) == 8


    light_1 = hass.states.get("light.hue_light_with_color_and_color_temperature_1")
    assert light_1 is not None
    assert (
        light_1.attributes["friendly_name"]
        == "Hue light with color and color temperature 1"
    )
    assert light_1.state == "on"
    assert light_1.attributes["brightness"] == int(46.85 / 100 * 255)
    assert light_1.attributes["mode"] == "normal"
    assert light_1.attributes["color_mode"] == ColorMode.XY
    assert set(light_1.attributes["supported_color_modes"]) == {
        ColorMode.COLOR_TEMP,
        ColorMode.XY,
    }
    assert light_1.attributes["xy_color"] == (0.5614, 0.4058)
    assert light_1.attributes["max_color_temp_kelvin"] == 6535
    assert light_1.attributes["min_color_temp_kelvin"] == 2000
    assert light_1.attributes["dynamics"] == "dynamic_palette"
    assert light_1.attributes["effect_list"] == ["off", "candle", "fire"]
    assert light_1.attributes["effect"] == "off"


    light_2 = hass.states.get("light.hue_light_with_color_temperature_only")
    assert light_2 is not None
    assert (
        light_2.attributes["friendly_name"] == "Hue light with color temperature only"
    )
    assert light_2.state == "off"
    assert light_2.attributes["mode"] == "normal"
    assert light_2.attributes["supported_color_modes"] == [ColorMode.COLOR_TEMP]
    assert light_2.attributes["max_color_temp_kelvin"] == 6535
    assert light_2.attributes["min_color_temp_kelvin"] == 2202
    assert light_2.attributes["dynamics"] == "none"
    assert light_2.attributes["effect_list"] == ["off", "candle", "sunrise"]


    light_3 = hass.states.get("light.hue_light_with_color_only")
    assert light_3 is not None
    assert light_3.attributes["friendly_name"] == "Hue light with color only"
    assert light_3.state == "on"
    assert light_3.attributes["brightness"] == 128
    assert light_3.attributes["mode"] == "normal"
    assert light_3.attributes["supported_color_modes"] == [ColorMode.XY]
    assert light_3.attributes["color_mode"] == ColorMode.XY
    assert light_3.attributes["dynamics"] == "dynamic_palette"


    light_4 = hass.states.get("light.hue_on_off_light")
    assert light_4 is not None
    assert light_4.attributes["friendly_name"] == "Hue on/off light"
    assert light_4.state == "off"
    assert light_4.attributes["mode"] == "normal"
    assert light_4.attributes["supported_color_modes"] == [ColorMode.ONOFF]


async def test_light_turn_on_service(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)

    await setup_platform(hass, mock_bridge_v2, Platform.LIGHT)

    test_light_id = "light.hue_light_with_color_temperature_only"


    assert hass.states.get(test_light_id).state == "off"


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "brightness_pct": 100, "color_temp_kelvin": 3333},
        blocking=True,
    )


    assert len(mock_bridge_v2.mock_requests) == 1
    assert mock_bridge_v2.mock_requests[0]["method"] == "put"
    assert mock_bridge_v2.mock_requests[0]["json"]["on"]["on"] is True
    assert mock_bridge_v2.mock_requests[0]["json"]["dimming"]["brightness"] == 100
    assert mock_bridge_v2.mock_requests[0]["json"]["color_temperature"]["mirek"] == 300


    event = {
        "id": "3a6710fa-4474-4eba-b533-5e6e72968feb",
        "type": "light",
        **mock_bridge_v2.mock_requests[0]["json"],
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()


    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["mode"] == "normal"
    assert test_light.attributes["supported_color_modes"] == [ColorMode.COLOR_TEMP]
    assert test_light.attributes["color_mode"] == ColorMode.COLOR_TEMP
    assert test_light.attributes["brightness"] == 255


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "brightness_pct": 50, "transition": 0.25},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 2
    assert mock_bridge_v2.mock_requests[1]["json"]["on"]["on"] is True
    assert mock_bridge_v2.mock_requests[1]["json"]["dynamics"]["duration"] == 200


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "flash": "long"},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 3
    assert mock_bridge_v2.mock_requests[2]["json"]["alert"]["action"] == "breathe"


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "flash": "short"},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 4
    assert mock_bridge_v2.mock_requests[3]["json"]["identify"]["action"] == "identify"



    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "color_temp_kelvin": 20000},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 5
    assert mock_bridge_v2.mock_requests[4]["json"]["color_temperature"]["mirek"] == 153
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "color_temp_kelvin": 1818},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 6
    assert mock_bridge_v2.mock_requests[5]["json"]["color_temperature"]["mirek"] == 454


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "effect": "candle"},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 7
    assert mock_bridge_v2.mock_requests[6]["json"]["effects"]["effect"] == "candle"

    event = {
        "id": "3a6710fa-4474-4eba-b533-5e6e72968feb",
        "type": "light",
        "effects": {"status": "candle"},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()
    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.attributes["effect"] == "candle"



    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "effect": "off"},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 8
    assert mock_bridge_v2.mock_requests[7]["json"]["effects"]["effect"] == "no_effect"

    event = {
        "id": "3a6710fa-4474-4eba-b533-5e6e72968feb",
        "type": "light",
        "effects": {"status": "no_effect"},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()
    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.attributes["effect"] == "off"



    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "effect": "off"},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 9
    assert "effects" not in mock_bridge_v2.mock_requests[8]["json"]


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "effect": "sunrise", "transition": 6},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 10
    assert (
        mock_bridge_v2.mock_requests[9]["json"]["timed_effects"]["effect"] == "sunrise"
    )
    assert mock_bridge_v2.mock_requests[9]["json"]["timed_effects"]["duration"] == 6000


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "effect": "candle", "color_temp_kelvin": 2000},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 11
    assert mock_bridge_v2.mock_requests[10]["json"]["effects"]["effect"] == "candle"
    assert "color_temperature" not in mock_bridge_v2.mock_requests[10]["json"]


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id, "effect": "candle", "xy_color": [0.123, 0.123]},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 12
    assert mock_bridge_v2.mock_requests[11]["json"]["effects"]["effect"] == "candle"
    assert "xy_color" not in mock_bridge_v2.mock_requests[11]["json"]


async def test_light_turn_off_service(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)

    await setup_platform(hass, mock_bridge_v2, Platform.LIGHT)

    test_light_id = "light.hue_light_with_color_and_color_temperature_1"


    assert hass.states.get(test_light_id).state == "on"
    brightness_pct = hass.states.get(test_light_id).attributes["brightness"] / 255 * 100


    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": test_light_id},
        blocking=True,
    )


    assert len(mock_bridge_v2.mock_requests) == 1
    assert mock_bridge_v2.mock_requests[0]["method"] == "put"
    assert mock_bridge_v2.mock_requests[0]["json"]["on"]["on"] is False


    event = {
        "id": "02cba059-9c2c-4d45-97e4-4f79b1bfbaa1",
        "type": "light",
        **mock_bridge_v2.mock_requests[0]["json"],
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()


    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "off"


    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": test_light_id, "transition": 0.25},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 2
    assert mock_bridge_v2.mock_requests[1]["json"]["on"]["on"] is False
    assert mock_bridge_v2.mock_requests[1]["json"]["dynamics"]["duration"] == 200


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 3
    assert mock_bridge_v2.mock_requests[2]["json"]["on"]["on"] is True
    assert (
        round(
            mock_bridge_v2.mock_requests[2]["json"]["dimming"]["brightness"]
            - brightness_pct
        )
        == 0
    )


    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": test_light_id, "flash": "long"},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 4
    assert mock_bridge_v2.mock_requests[3]["json"]["alert"]["action"] == "breathe"


    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": test_light_id, "flash": "short"},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 5
    assert mock_bridge_v2.mock_requests[4]["json"]["identify"]["action"] == "identify"


async def test_light_added(hass: HomeAssistant, mock_bridge_v2: Mock) -> None:

    await mock_bridge_v2.api.load_test_data([FAKE_DEVICE, FAKE_ZIGBEE_CONNECTIVITY])

    await setup_platform(hass, mock_bridge_v2, Platform.LIGHT)

    test_entity_id = "light.hue_mocked_device"


    assert hass.states.get(test_entity_id) is None


    mock_bridge_v2.api.emit_event("add", FAKE_LIGHT)
    await hass.async_block_till_done()


    test_entity = hass.states.get(test_entity_id)
    assert test_entity is not None
    assert test_entity.state == "off"
    assert test_entity.attributes["friendly_name"] == FAKE_DEVICE["metadata"]["name"]


async def test_light_availability(
    hass: HomeAssistant, mock_bridge_v2: Mock, v2_resources_test_data: JsonArrayType
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)

    await setup_platform(hass, mock_bridge_v2, Platform.LIGHT)

    test_light_id = "light.hue_light_with_color_and_color_temperature_1"


    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"


    for status in ("connectivity_issue", "disconnected", "connected"):
        mock_bridge_v2.api.emit_event(
            "update",
            {
                "id": "1987ba66-c21d-48d0-98fb-121d939a71f3",
                "status": status,
                "type": "zigbee_connectivity",
            },
        )
        await hass.async_block_till_done()


        test_light = hass.states.get(test_light_id)
        assert test_light.state == "on" if status == "connected" else "unavailable"


async def test_grouped_lights(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_bridge_v2: Mock,
    v2_resources_test_data: JsonArrayType,
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)

    await setup_platform(hass, mock_bridge_v2, Platform.LIGHT)


    for entity_id in ("light.test_zone", "light.test_room"):
        entity_entry = entity_registry.async_get(entity_id)

        assert entity_entry

        assert entity_entry.device_id is not None


    test_entity = hass.states.get("light.test_zone")
    assert test_entity is not None
    assert test_entity.attributes["friendly_name"] == "Test Zone"
    assert test_entity.state == "on"
    assert test_entity.attributes["brightness"] == 119
    assert test_entity.attributes["color_mode"] == ColorMode.XY
    assert set(test_entity.attributes["supported_color_modes"]) == {
        ColorMode.COLOR_TEMP,
        ColorMode.XY,
    }
    assert test_entity.attributes["max_color_temp_kelvin"] == 6535
    assert test_entity.attributes["min_color_temp_kelvin"] == 2000
    assert test_entity.attributes["is_hue_group"] is True
    assert test_entity.attributes["hue_scenes"] == {"Dynamic Test Scene"}
    assert test_entity.attributes["hue_type"] == "zone"
    assert test_entity.attributes["lights"] == {
        "Hue light with color and color temperature 1",
        "Hue light with color and color temperature gradient",
        "Hue light with color and color temperature 2",
    }
    assert test_entity.attributes["entity_id"] == {
        "light.hue_light_with_color_and_color_temperature_gradient",
        "light.hue_light_with_color_and_color_temperature_2",
        "light.hue_light_with_color_and_color_temperature_1",
    }


    test_entity = hass.states.get("light.test_room")
    assert test_entity is not None
    assert test_entity.attributes["friendly_name"] == "Test Room"
    assert test_entity.state == "off"
    assert test_entity.attributes["supported_color_modes"] == [ColorMode.COLOR_TEMP]
    assert test_entity.attributes["max_color_temp_kelvin"] == 6535
    assert test_entity.attributes["min_color_temp_kelvin"] == 2202
    assert test_entity.attributes["is_hue_group"] is True
    assert test_entity.attributes["hue_scenes"] == {
        "Regular Test Scene",
        "Smart Test Scene",
    }
    assert test_entity.attributes["hue_type"] == "room"
    assert test_entity.attributes["lights"] == {
        "Hue on/off light",
        "Hue light with color temperature only",
    }
    assert test_entity.attributes["entity_id"] == {
        "light.hue_light_with_color_temperature_only",
        "light.hue_on_off_light",
    }


    test_light_id = "light.test_zone"
    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": test_light_id,
            "brightness_pct": 100,
            "xy_color": (0.123, 0.123),
            "transition": 0.25,
        },
        blocking=True,
    )


    assert len(mock_bridge_v2.mock_requests) == 1
    assert mock_bridge_v2.mock_requests[0]["json"]["on"]["on"] is True
    assert mock_bridge_v2.mock_requests[0]["json"]["dimming"]["brightness"] == 100
    assert mock_bridge_v2.mock_requests[0]["json"]["color"]["xy"]["x"] == 0.123
    assert mock_bridge_v2.mock_requests[0]["json"]["color"]["xy"]["y"] == 0.123
    assert mock_bridge_v2.mock_requests[0]["json"]["dynamics"]["duration"] == 200


    for light_id in (
        "02cba059-9c2c-4d45-97e4-4f79b1bfbaa1",
        "b3fe71ef-d0ef-48de-9355-d9e604377df0",
        "8015b17f-8336-415b-966a-b364bd082397",
    ):
        event = {
            "id": light_id,
            "type": "light",
            **mock_bridge_v2.mock_requests[0]["json"],
        }
        mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()


    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["color_mode"] == ColorMode.XY
    assert test_light.attributes["brightness"] == 255
    assert test_light.attributes["xy_color"] == (0.123, 0.123)





    mock_bridge_v2.mock_requests.clear()
    single_light_id = "light.hue_light_with_color_and_color_temperature_1"
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": single_light_id},
        blocking=True,
    )
    event = {
        "id": "02cba059-9c2c-4d45-97e4-4f79b1bfbaa1",
        "type": "light",
        "on": {"on": False},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()


    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["xy_color"] == (0.123, 0.123)


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": single_light_id, "xy_color": [0.3127, 0.3290]},
        blocking=True,
    )
    event = {
        "id": "02cba059-9c2c-4d45-97e4-4f79b1bfbaa1",
        "type": "light",
        "on": {"on": True},
        "color": {"xy": {"x": 0.3127, "y": 0.3290}},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()







    expected_x = round((0.3127 + 0.123 + 0.123) / 3, 4)
    expected_y = round((0.3290 + 0.123 + 0.123) / 3, 4)


    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    group_x, group_y = test_light.attributes["xy_color"]
    assert abs(group_x - expected_x) < 0.001
    assert abs(group_y - expected_y) < 0.001



    second_light_id = "light.hue_light_with_color_and_color_temperature_2"
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": second_light_id},
        blocking=True,
    )


    event = {
        "id": "b3fe71ef-d0ef-48de-9355-d9e604377df0",
        "type": "light",
        "on": {"on": False},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()





    expected_x_two_lights = round((0.3127 + 0.123) / 2, 4)
    expected_y_two_lights = round((0.3290 + 0.123) / 2, 4)

    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"

    group_x, group_y = test_light.attributes["xy_color"]
    assert abs(group_x - expected_x_two_lights) < 0.001
    assert abs(group_y - expected_y_two_lights) < 0.001



    for mirek, light_name, light_id in zip(
        [300, 250, 200],
        [
            "light.hue_light_with_color_and_color_temperature_1",
            "light.hue_light_with_color_and_color_temperature_2",
            "light.hue_light_with_color_and_color_temperature_gradient",
        ],
        [
            "02cba059-9c2c-4d45-97e4-4f79b1bfbaa1",
            "b3fe71ef-d0ef-48de-9355-d9e604377df0",
            "8015b17f-8336-415b-966a-b364bd082397",
        ],
        strict=True,
    ):
        await hass.services.async_call(
            "light",
            "turn_on",
            {
                "entity_id": light_name,
                "color_temp_kelvin": color_util.color_temperature_mired_to_kelvin(
                    mirek
                ),
            },
            blocking=True,
        )

        mock_bridge_v2.api.emit_event(
            "update",
            {
                "id": light_id,
                "type": "light",
                "on": {"on": True},
                "color_temperature": {"mirek": mirek, "mirek_valid": True},
            },
        )
    await hass.async_block_till_done()

    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["color_mode"] == ColorMode.COLOR_TEMP



    expected_avg_kelvin = round((3333 + 4000 + 5000) / 3)
    assert abs(test_light.attributes["color_temp_kelvin"] - expected_avg_kelvin) <= 5


    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": "light.hue_light_with_color_and_color_temperature_gradient"},
        blocking=True,
    )
    event = {
        "id": "8015b17f-8336-415b-966a-b364bd082397",
        "type": "light",
        "on": {"on": False},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()

    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["color_mode"] == ColorMode.COLOR_TEMP



    expected_avg_kelvin = round((3333 + 4000) / 2)
    assert abs(test_light.attributes["color_temp_kelvin"] - expected_avg_kelvin) <= 5


    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.hue_light_with_color_and_color_temperature_gradient",
            "xy_color": [0.123, 0.123],
        },
        blocking=True,
    )
    mock_bridge_v2.api.emit_event(
        "update",
        {
            "id": "8015b17f-8336-415b-966a-b364bd082397",
            "type": "light",
            "on": {"on": True},
            "color": {"xy": {"x": 0.123, "y": 0.123}},
            "color_temperature": {
                "mirek": None,
                "mirek_valid": False,
            },
        },
    )
    await hass.async_block_till_done()

    test_light = hass.states.get(test_light_id)
    assert test_light.attributes["color_mode"] == ColorMode.COLOR_TEMP


    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.hue_light_with_color_and_color_temperature_2",
            "xy_color": [0.321, 0.321],
        },
        blocking=True,
    )
    mock_bridge_v2.api.emit_event(
        "update",
        {
            "id": "b3fe71ef-d0ef-48de-9355-d9e604377df0",
            "type": "light",
            "on": {"on": True},
            "color": {"xy": {"x": 0.321, "y": 0.321}},
            "color_temperature": {
                "mirek": None,
                "mirek_valid": False,
            },
        },
    )
    await hass.async_block_till_done()

    test_light = hass.states.get(test_light_id)
    assert test_light.attributes["color_mode"] == ColorMode.XY


    mock_bridge_v2.mock_requests.clear()


    for brightness, light_name, light_id in zip(
        [90.0, 60.0, 30.0],
        [
            "light.hue_light_with_color_and_color_temperature_1",
            "light.hue_light_with_color_and_color_temperature_2",
            "light.hue_light_with_color_and_color_temperature_gradient",
        ],
        [
            "02cba059-9c2c-4d45-97e4-4f79b1bfbaa1",
            "b3fe71ef-d0ef-48de-9355-d9e604377df0",
            "8015b17f-8336-415b-966a-b364bd082397",
        ],
        strict=True,
    ):
        await hass.services.async_call(
            "light",
            "turn_on",
            {
                "entity_id": light_name,
                "brightness": brightness,
            },
            blocking=True,
        )

        mock_bridge_v2.api.emit_event(
            "update",
            {
                "id": light_id,
                "type": "light",
                "on": {"on": True},
                "dimming": {"brightness": brightness},
            },
        )
    await hass.async_block_till_done()



    expected_brightness = round(((90 + 60 + 30) / 3 / 100) * 255)

    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["brightness"] == expected_brightness


    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": "light.hue_light_with_color_and_color_temperature_gradient"},
        blocking=True,
    )
    event = {
        "id": "8015b17f-8336-415b-966a-b364bd082397",
        "type": "light",
        "on": {"on": False},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()



    expected_brightness_two_lights = round(((90 + 60) / 2 / 100) * 255)

    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["brightness"] == expected_brightness_two_lights


    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": "light.hue_light_with_color_and_color_temperature_2"},
        blocking=True,
    )
    event = {
        "id": "b3fe71ef-d0ef-48de-9355-d9e604377df0",
        "type": "light",
        "on": {"on": False},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()



    expected_brightness_one_light = round((90 / 100) * 255)

    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["brightness"] == expected_brightness_one_light


    for light_name, light_id in zip(
        [
            "light.hue_light_with_color_and_color_temperature_1",
            "light.hue_light_with_color_and_color_temperature_2",
            "light.hue_light_with_color_and_color_temperature_gradient",
        ],
        [
            "02cba059-9c2c-4d45-97e4-4f79b1bfbaa1",
            "b3fe71ef-d0ef-48de-9355-d9e604377df0",
            "8015b17f-8336-415b-966a-b364bd082397",
        ],
        strict=True,
    ):
        await hass.services.async_call(
            "light",
            "turn_on",
            {
                "entity_id": light_name,
                "brightness": 100.0,
            },
            blocking=True,
        )

        mock_bridge_v2.api.emit_event(
            "update",
            {
                "id": light_id,
                "type": "light",
                "on": {"on": True},
                "dimming": {"brightness": 100.0},
            },
        )
    await hass.async_block_till_done()


    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "on"
    assert test_light.attributes["brightness"] == 255


    mock_bridge_v2.mock_requests.clear()
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": test_light_id},
        blocking=True,
    )


    assert len(mock_bridge_v2.mock_requests) == 1
    assert mock_bridge_v2.mock_requests[0]["method"] == "put"
    assert mock_bridge_v2.mock_requests[0]["json"]["on"]["on"] is False


    event = {
        "id": "f2416154-9607-43ab-a684-4453108a200e",
        "type": "grouped_light",
        **mock_bridge_v2.mock_requests[0]["json"],
    }
    mock_bridge_v2.api.emit_event("update", event)
    mock_bridge_v2.api.emit_event("update", mock_bridge_v2.mock_requests[0]["json"])
    await hass.async_block_till_done()


    test_light = hass.states.get(test_light_id)
    assert test_light is not None
    assert test_light.state == "off"


    mock_bridge_v2.mock_requests.clear()
    test_light_id = "light.test_zone"
    await hass.services.async_call(
        "light",
        "turn_off",
        {
            "entity_id": test_light_id,
            "transition": 0.25,
        },
        blocking=True,
    )


    assert len(mock_bridge_v2.mock_requests) == 1
    assert mock_bridge_v2.mock_requests[0]["json"]["on"]["on"] is False
    assert mock_bridge_v2.mock_requests[0]["json"]["dynamics"]["duration"] == 200


    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": test_light_id},
        blocking=True,
    )
    assert len(mock_bridge_v2.mock_requests) == 2
    assert mock_bridge_v2.mock_requests[1]["json"]["on"]["on"] is True
    assert mock_bridge_v2.mock_requests[1]["json"]["dimming"]["brightness"] == 100


    mock_bridge_v2.mock_requests.clear()
    test_light_id = "light.test_zone"
    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": test_light_id,
            "flash": "short",
        },
        blocking=True,
    )


    assert len(mock_bridge_v2.mock_requests) == 3
    for index in range(3):
        assert (
            mock_bridge_v2.mock_requests[index]["json"]["identify"]["action"]
            == "identify"
        )


    mock_bridge_v2.mock_requests.clear()
    test_light_id = "light.test_zone"
    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": test_light_id,
            "flash": "long",
        },
        blocking=True,
    )


    assert len(mock_bridge_v2.mock_requests) == 1
    assert mock_bridge_v2.mock_requests[0]["json"]["alert"]["action"] == "breathe"


    mock_bridge_v2.mock_requests.clear()
    test_light_id = "light.test_zone"
    await hass.services.async_call(
        "light",
        "turn_off",
        {
            "entity_id": test_light_id,
            "flash": "short",
        },
        blocking=True,
    )


    assert len(mock_bridge_v2.mock_requests) == 3
    for index in range(3):
        assert (
            mock_bridge_v2.mock_requests[index]["json"]["identify"]["action"]
            == "identify"
        )


async def test_light_turn_on_service_deprecation(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    v2_resources_test_data: JsonArrayType,
    issue_registry: ir.IssueRegistry,
) -> None:

    await mock_bridge_v2.api.load_test_data(v2_resources_test_data)

    test_light_id = "light.hue_light_with_color_temperature_only"

    await setup_platform(hass, mock_bridge_v2, Platform.LIGHT)

    event = {
        "id": "3a6710fa-4474-4eba-b533-5e6e72968feb",
        "type": "light",
        "effects": {"status": "candle"},
    }
    mock_bridge_v2.api.emit_event("update", event)
    await hass.async_block_till_done()



    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: test_light_id,
            ATTR_EFFECT: "None",
        },
        blocking=True,
    )
    assert mock_bridge_v2.mock_requests[0]["json"]["effects"]["effect"] == "no_effect"
