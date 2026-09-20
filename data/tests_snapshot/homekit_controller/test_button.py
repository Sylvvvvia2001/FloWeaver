

from collections.abc import Callable

from aiohomekit.model import Accessory
from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.services import Service, ServicesTypes

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import Helper, setup_test_component


def create_switch_with_setup_button(accessory: Accessory) -> Service:

    service = accessory.add_service(ServicesTypes.OUTLET)

    setup = service.add_char(CharacteristicsTypes.VENDOR_HAA_SETUP)

    setup.value = ""
    setup.format = "string"

    cur_state = service.add_char(CharacteristicsTypes.ON)
    cur_state.value = True

    return service


def create_switch_with_ecobee_clear_hold_button(accessory: Accessory) -> Service:

    service = accessory.add_service(ServicesTypes.OUTLET)

    setup = service.add_char(CharacteristicsTypes.VENDOR_ECOBEE_CLEAR_HOLD)

    setup.value = ""
    setup.format = "string"

    cur_state = service.add_char(CharacteristicsTypes.ON)
    cur_state.value = True

    return service


async def test_press_button(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_switch_with_setup_button
    )


    button = Helper(
        hass,
        "button.testdevice_setup",
        helper.pairing,
        helper.accessory,
        helper.config_entry,
    )

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.testdevice_setup"},
        blocking=True,
    )
    button.async_assert_service_values(
        ServicesTypes.OUTLET,
        {
            CharacteristicsTypes.VENDOR_HAA_SETUP: "#HAA@trcmd",
        },
    )


async def test_ecobee_clear_hold_press_button(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_switch_with_ecobee_clear_hold_button
    )


    clear_hold = Helper(
        hass,
        "button.testdevice_clear_hold",
        helper.pairing,
        helper.accessory,
        helper.config_entry,
    )

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.testdevice_clear_hold"},
        blocking=True,
    )
    clear_hold.async_assert_service_values(
        ServicesTypes.OUTLET,
        {
            CharacteristicsTypes.VENDOR_ECOBEE_CLEAR_HOLD: True,
        },
    )


async def test_migrate_unique_id(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    get_next_aid: Callable[[], int],
) -> None:

    aid = get_next_aid()
    button_entry = entity_registry.async_get_or_create(
        "button",
        "homekit_controller",
        f"homekit-0001-aid:{aid}-sid:1-cid:2",
    )
    await setup_test_component(hass, aid, create_switch_with_ecobee_clear_hold_button)
    assert (
        entity_registry.async_get(button_entry.entity_id).unique_id
        == f"00:00:00:00:00:00_{aid}_1_2"
    )
