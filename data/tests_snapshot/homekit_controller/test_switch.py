

from collections.abc import Callable

from aiohomekit.model import Accessory
from aiohomekit.model.characteristics import (
    CharacteristicsTypes,
    InUseValues,
    IsConfiguredValues,
)
from aiohomekit.model.services import ServicesTypes

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import setup_test_component


def create_switch_service(accessory: Accessory) -> None:

    service = accessory.add_service(ServicesTypes.OUTLET)

    on_char = service.add_char(CharacteristicsTypes.ON)
    on_char.value = False

    outlet_in_use = service.add_char(CharacteristicsTypes.OUTLET_IN_USE)
    outlet_in_use.value = False


def create_faucet_service(accessory: Accessory) -> None:

    service = accessory.add_service(ServicesTypes.FAUCET)

    active_char = service.add_char(CharacteristicsTypes.ACTIVE)
    active_char.value = False


def create_valve_service(accessory: Accessory) -> None:

    service = accessory.add_service(ServicesTypes.VALVE)

    on_char = service.add_char(CharacteristicsTypes.ACTIVE)
    on_char.value = False

    in_use = service.add_char(CharacteristicsTypes.IN_USE)
    in_use.value = InUseValues.IN_USE

    configured = service.add_char(CharacteristicsTypes.IS_CONFIGURED)
    configured.value = IsConfiguredValues.CONFIGURED

    remaining = service.add_char(CharacteristicsTypes.REMAINING_DURATION)
    remaining.value = 99


def create_char_switch_service(accessory: Accessory) -> None:

    service = accessory.add_service(ServicesTypes.OUTLET)

    on_char = service.add_char(CharacteristicsTypes.VENDOR_AQARA_PAIRING_MODE)
    on_char.perms.append("ev")
    on_char.value = False


async def test_switch_change_outlet_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_switch_service)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.OUTLET,
        {
            CharacteristicsTypes.ON: 1,
        },
    )

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.OUTLET,
        {
            CharacteristicsTypes.ON: 0,
        },
    )


async def test_switch_read_outlet_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_switch_service)


    switch_1 = await helper.poll_and_get_state()
    assert switch_1.state == "off"
    assert switch_1.attributes["outlet_in_use"] is False


    switch_1 = await helper.async_update(
        ServicesTypes.OUTLET,
        {CharacteristicsTypes.ON: True},
    )
    assert switch_1.state == "on"
    assert switch_1.attributes["outlet_in_use"] is False


    switch_1 = await helper.async_update(
        ServicesTypes.OUTLET,
        {CharacteristicsTypes.ON: False},
    )
    assert switch_1.state == "off"


    switch_1 = await helper.async_update(
        ServicesTypes.OUTLET,
        {CharacteristicsTypes.OUTLET_IN_USE: True},
    )
    assert switch_1.state == "off"
    assert switch_1.attributes["outlet_in_use"] is True


async def test_faucet_change_active_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_faucet_service)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.FAUCET,
        {
            CharacteristicsTypes.ACTIVE: 1,
        },
    )

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.FAUCET,
        {
            CharacteristicsTypes.ACTIVE: 0,
        },
    )


async def test_faucet_read_active_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_faucet_service)


    switch_1 = await helper.poll_and_get_state()
    assert switch_1.state == "off"


    switch_1 = await helper.async_update(
        ServicesTypes.FAUCET,
        {CharacteristicsTypes.ACTIVE: True},
    )
    assert switch_1.state == "on"


    switch_1 = await helper.async_update(
        ServicesTypes.FAUCET,
        {CharacteristicsTypes.ACTIVE: False},
    )
    assert switch_1.state == "off"


async def test_valve_change_active_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_valve_service)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.VALVE,
        {
            CharacteristicsTypes.ACTIVE: 1,
        },
    )

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.VALVE,
        {
            CharacteristicsTypes.ACTIVE: 0,
        },
    )


async def test_valve_read_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_valve_service)


    switch_1 = await helper.poll_and_get_state()
    assert switch_1.state == "off"
    assert switch_1.attributes["in_use"] is True
    assert switch_1.attributes["is_configured"] is True
    assert switch_1.attributes["remaining_duration"] == 99


    switch_1 = await helper.async_update(
        ServicesTypes.VALVE,
        {CharacteristicsTypes.ACTIVE: True},
    )
    assert switch_1.state == "on"


    switch_1 = await helper.async_update(
        ServicesTypes.VALVE,
        {CharacteristicsTypes.IS_CONFIGURED: IsConfiguredValues.NOT_CONFIGURED},
    )
    assert switch_1.attributes["is_configured"] is False


    switch_1 = await helper.async_update(
        ServicesTypes.VALVE,
        {CharacteristicsTypes.IN_USE: InUseValues.NOT_IN_USE},
    )
    assert switch_1.attributes["in_use"] is False


async def test_char_switch_change_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_char_switch_service, suffix="pairing_mode"
    )

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.testdevice_pairing_mode"},
        blocking=True,
    )
    helper.async_assert_service_values(
        ServicesTypes.OUTLET,
        {
            CharacteristicsTypes.VENDOR_AQARA_PAIRING_MODE: True,
        },
    )

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.testdevice_pairing_mode"},
        blocking=True,
    )
    helper.async_assert_service_values(
        ServicesTypes.OUTLET,
        {
            CharacteristicsTypes.VENDOR_AQARA_PAIRING_MODE: False,
        },
    )


async def test_char_switch_read_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(
        hass, get_next_aid(), create_char_switch_service, suffix="pairing_mode"
    )


    switch_1 = await helper.async_update(
        ServicesTypes.OUTLET,
        {CharacteristicsTypes.VENDOR_AQARA_PAIRING_MODE: True},
    )
    assert switch_1.state == "on"


    switch_1 = await helper.async_update(
        ServicesTypes.OUTLET,
        {CharacteristicsTypes.VENDOR_AQARA_PAIRING_MODE: False},
    )
    assert switch_1.state == "off"


async def test_migrate_unique_id(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    get_next_aid: Callable[[], int],
) -> None:

    aid = get_next_aid()
    switch_entry = entity_registry.async_get_or_create(
        "switch",
        "homekit_controller",
        f"homekit-00:00:00:00:00:00-{aid}-8",
    )
    switch_entry_2 = entity_registry.async_get_or_create(
        "switch",
        "homekit_controller",
        f"homekit-0001-aid:{aid}-sid:8-cid:9",
    )
    await setup_test_component(
        hass, aid, create_char_switch_service, suffix="pairing_mode"
    )

    assert (
        entity_registry.async_get(switch_entry.entity_id).unique_id
        == f"00:00:00:00:00:00_{aid}_8"
    )

    assert (
        entity_registry.async_get(switch_entry_2.entity_id).unique_id
        == f"00:00:00:00:00:00_{aid}_8_9"
    )
