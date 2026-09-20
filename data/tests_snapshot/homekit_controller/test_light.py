

from collections.abc import Callable
from unittest import mock

from aiohomekit.model import Accessory
from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.services import Service, ServicesTypes
from aiohomekit.testing import FakeController

from homeassistant.components.homekit_controller.const import KNOWN_DEVICES
from homeassistant.components.light import (
    ATTR_COLOR_MODE,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import setup_test_component

LIGHT_BULB_NAME = "TestDevice"
LIGHT_BULB_ENTITY_ID = "light.testdevice"


def create_lightbulb_service(accessory: Accessory) -> Service:

    service = accessory.add_service(ServicesTypes.LIGHTBULB, name=LIGHT_BULB_NAME)

    on_char = service.add_char(CharacteristicsTypes.ON)
    on_char.value = 0

    brightness = service.add_char(CharacteristicsTypes.BRIGHTNESS)
    brightness.value = 0

    return service


def create_lightbulb_service_with_hs(accessory: Accessory) -> Service:

    service = create_lightbulb_service(accessory)

    hue = service.add_char(CharacteristicsTypes.HUE)
    hue.value = 0

    saturation = service.add_char(CharacteristicsTypes.SATURATION)
    saturation.value = 0

    return service


def create_lightbulb_service_with_color_temp(accessory: Accessory) -> Service:

    service = create_lightbulb_service(accessory)

    color_temp = service.add_char(CharacteristicsTypes.COLOR_TEMPERATURE)
    color_temp.value = 0

    return service


async def test_switch_change_light_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_lightbulb_service_with_hs
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": "light.testdevice", "brightness": 255, "hs_color": [4, 5]},
        blocking=True,
    )
    helper.async_assert_service_values(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
            CharacteristicsTypes.HUE: 4,
            CharacteristicsTypes.SATURATION: 5,
        },
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": "light.testdevice", "brightness": 255, "color_temp_kelvin": 3333},
        blocking=True,
    )
    helper.async_assert_service_values(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
            CharacteristicsTypes.HUE: 27,
            CharacteristicsTypes.SATURATION: 49,
        },
    )

    await hass.services.async_call(
        "light", "turn_off", {"entity_id": "light.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: False,
        },
    )


async def test_switch_change_light_state_color_temp(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_lightbulb_service_with_color_temp
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": "light.testdevice", "brightness": 255, "color_temp_kelvin": 2500},
        blocking=True,
    )
    helper.async_assert_service_values(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
            CharacteristicsTypes.COLOR_TEMPERATURE: 400,
        },
    )


async def test_switch_read_light_state_dimmer(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_lightbulb_service)


    state = await helper.poll_and_get_state()
    assert state.state == "off"
    assert state.attributes[ATTR_COLOR_MODE] is None
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.BRIGHTNESS]
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
        },
    )
    assert state.state == "on"
    assert state.attributes["brightness"] == 255
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.BRIGHTNESS
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.BRIGHTNESS]
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: False,
        },
    )
    assert state.state == "off"


async def test_switch_push_light_state_dimmer(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_lightbulb_service)


    state = hass.states.get(LIGHT_BULB_ENTITY_ID)
    assert state.state == "off"

    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
        },
    )
    assert state.state == "on"
    assert state.attributes["brightness"] == 255


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: False,
        },
    )
    assert state.state == "off"


async def test_switch_read_light_state_hs(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_lightbulb_service_with_hs
    )


    state = await helper.poll_and_get_state()
    assert state.state == "off"
    assert state.attributes[ATTR_COLOR_MODE] is None
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [
        ColorMode.COLOR_TEMP,
        ColorMode.HS,
    ]
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
            CharacteristicsTypes.HUE: 4,
            CharacteristicsTypes.SATURATION: 5,
        },
    )
    assert state.state == "on"
    assert state.attributes["brightness"] == 255
    assert state.attributes["hs_color"] == (4, 5)
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.HS
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [
        ColorMode.COLOR_TEMP,
        ColorMode.HS,
    ]
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: False,
        },
    )
    assert state.state == "off"


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.HUE: 6,
            CharacteristicsTypes.SATURATION: 7,
        },
    )
    assert state.state == "on"
    assert state.attributes["brightness"] == 255
    assert state.attributes["hs_color"] == (6, 7)
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.HS
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [
        ColorMode.COLOR_TEMP,
        ColorMode.HS,
    ]
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0


async def test_switch_push_light_state_hs(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_lightbulb_service_with_hs
    )


    state = hass.states.get(LIGHT_BULB_ENTITY_ID)
    assert state.state == "off"

    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
            CharacteristicsTypes.HUE: 4,
            CharacteristicsTypes.SATURATION: 5,
        },
    )
    assert state.state == "on"
    assert state.attributes["brightness"] == 255
    assert state.attributes["hs_color"] == (4, 5)


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: False,
        },
    )
    assert state.state == "off"


async def test_switch_read_light_state_color_temp(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_lightbulb_service_with_color_temp
    )


    state = await helper.poll_and_get_state()
    assert state.state == "off"
    assert state.attributes[ATTR_COLOR_MODE] is None
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.COLOR_TEMP]
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
            CharacteristicsTypes.COLOR_TEMPERATURE: 400,
        },
    )
    assert state.state == "on"
    assert state.attributes["brightness"] == 255
    assert state.attributes["color_temp_kelvin"] == 2500
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.COLOR_TEMP
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.COLOR_TEMP]
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0


async def test_switch_push_light_state_color_temp(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_lightbulb_service_with_color_temp
    )


    state = hass.states.get(LIGHT_BULB_ENTITY_ID)
    assert state.state == "off"

    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
            CharacteristicsTypes.COLOR_TEMPERATURE: 400,
        },
    )
    assert state.state == "on"
    assert state.attributes["brightness"] == 255
    assert state.attributes["color_temp_kelvin"] == 2500


async def test_light_becomes_unavailable_but_recovers(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_lightbulb_service_with_color_temp
    )


    state = await helper.poll_and_get_state()
    assert state.state == "off"


    helper.pairing.available = False
    with mock.patch.object(
        FakeController,
        "async_reachable",
        return_value=False,
    ):
        state = await helper.poll_and_get_state()
    assert state.state == "unavailable"


    helper.pairing.available = True
    state = await helper.async_update(
        ServicesTypes.LIGHTBULB,
        {
            CharacteristicsTypes.ON: True,
            CharacteristicsTypes.BRIGHTNESS: 100,
            CharacteristicsTypes.COLOR_TEMPERATURE: 400,
        },
    )
    assert state.state == "on"
    assert state.attributes["brightness"] == 255
    assert state.attributes["color_temp_kelvin"] == 2500


async def test_light_unloaded_removed(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_lightbulb_service_with_color_temp
    )


    state = await helper.poll_and_get_state()
    assert state.state == "off"

    unload_result = await hass.config_entries.async_unload(helper.config_entry.entry_id)
    assert unload_result is True


    assert hass.states.get(helper.entity_id).state == STATE_UNAVAILABLE


    conn = hass.data[KNOWN_DEVICES]["00:00:00:00:00:00"]
    assert not conn.pollable_characteristics

    await hass.config_entries.async_remove(helper.config_entry.entry_id)
    await hass.async_block_till_done()


    assert hass.states.get(helper.entity_id) is None


async def test_migrate_unique_id(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    get_next_aid: Callable[[], int],
) -> None:

    aid = get_next_aid()
    light_entry = entity_registry.async_get_or_create(
        "light",
        "homekit_controller",
        f"homekit-00:00:00:00:00:00-{aid}-8",
    )
    await setup_test_component(hass, aid, create_lightbulb_service_with_color_temp)

    assert (
        entity_registry.async_get(light_entry.entity_id).unique_id
        == f"00:00:00:00:00:00_{aid}_8"
    )


async def test_only_migrate_once(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    get_next_aid: Callable[[], int],
) -> None:

    aid = get_next_aid()
    old_light_entry = entity_registry.async_get_or_create(
        "light",
        "homekit_controller",
        f"homekit-00:00:00:00:00:00-{aid}-8",
    )
    new_light_entry = entity_registry.async_get_or_create(
        "light",
        "homekit_controller",
        f"00:00:00:00:00:00_{aid}_8",
    )
    await setup_test_component(hass, aid, create_lightbulb_service_with_color_temp)

    assert (
        entity_registry.async_get(old_light_entry.entity_id).unique_id
        == f"homekit-00:00:00:00:00:00-{aid}-8"
    )

    assert (
        entity_registry.async_get(new_light_entry.entity_id).unique_id
        == f"00:00:00:00:00:00_{aid}_8"
    )
