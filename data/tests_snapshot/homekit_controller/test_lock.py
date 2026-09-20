

from collections.abc import Callable

from aiohomekit.model import Accessory
from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.services import Service, ServicesTypes

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import setup_test_component


def create_lock_service(accessory: Accessory) -> Service:

    service = accessory.add_service(ServicesTypes.LOCK_MECHANISM)

    cur_state = service.add_char(CharacteristicsTypes.LOCK_MECHANISM_CURRENT_STATE)
    cur_state.value = 0

    targ_state = service.add_char(CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE)
    targ_state.value = 0





    targ_state = service.add_char(CharacteristicsTypes.BATTERY_LEVEL)
    targ_state.value = 50

    return service


async def test_switch_change_lock_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_lock_service)

    await hass.services.async_call(
        "lock", "lock", {"entity_id": "lock.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.LOCK_MECHANISM,
        {
            CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE: 1,
        },
    )

    await hass.services.async_call(
        "lock", "unlock", {"entity_id": "lock.testdevice"}, blocking=True
    )
    helper.async_assert_service_values(
        ServicesTypes.LOCK_MECHANISM,
        {
            CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE: 0,
        },
    )


async def test_switch_read_lock_state(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:

    helper = await setup_test_component(hass, get_next_aid(), create_lock_service)

    state = await helper.async_update(
        ServicesTypes.LOCK_MECHANISM,
        {
            CharacteristicsTypes.LOCK_MECHANISM_CURRENT_STATE: 0,
            CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE: 0,
        },
    )
    assert state.state == "unlocked"
    assert state.attributes["battery_level"] == 50

    state = await helper.async_update(
        ServicesTypes.LOCK_MECHANISM,
        {
            CharacteristicsTypes.LOCK_MECHANISM_CURRENT_STATE: 1,
            CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE: 1,
        },
    )
    assert state.state == "locked"

    await helper.async_update(
        ServicesTypes.LOCK_MECHANISM,
        {
            CharacteristicsTypes.LOCK_MECHANISM_CURRENT_STATE: 2,
            CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE: 1,
        },
    )
    state = await helper.poll_and_get_state()
    assert state.state == "jammed"

    await helper.async_update(
        ServicesTypes.LOCK_MECHANISM,
        {
            CharacteristicsTypes.LOCK_MECHANISM_CURRENT_STATE: 3,
            CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE: 1,
        },
    )
    state = await helper.poll_and_get_state()
    assert state.state == "unknown"

    await helper.async_update(
        ServicesTypes.LOCK_MECHANISM,
        {
            CharacteristicsTypes.LOCK_MECHANISM_CURRENT_STATE: 0,
            CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE: 1,
        },
    )
    state = await helper.poll_and_get_state()
    assert state.state == "locking"

    await helper.async_update(
        ServicesTypes.LOCK_MECHANISM,
        {
            CharacteristicsTypes.LOCK_MECHANISM_CURRENT_STATE: 1,
            CharacteristicsTypes.LOCK_MECHANISM_TARGET_STATE: 0,
        },
    )
    state = await helper.poll_and_get_state()
    assert state.state == "unlocking"


async def test_migrate_unique_id(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    get_next_aid: Callable[[], int],
) -> None:

    aid = get_next_aid()
    lock_entry = entity_registry.async_get_or_create(
        "lock",
        "homekit_controller",
        f"homekit-00:00:00:00:00:00-{aid}-8",
    )
    await setup_test_component(hass, aid, create_lock_service)

    assert (
        entity_registry.async_get(lock_entry.entity_id).unique_id
        == f"00:00:00:00:00:00_{aid}_8"
    )
