

from unittest.mock import Mock

import pytest
from roborock import RoborockException
from roborock.exceptions import RoborockTimeout
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import FakeDevice

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture
def get_scenes_failure_fixture(fake_vacuum: FakeDevice) -> None:

    fake_vacuum.v1_properties.routines.get_routines.side_effect = RoborockException


@pytest.fixture
def platforms() -> list[Platform]:

    return [Platform.BUTTON]


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_buttons(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:

    await snapshot_platform(hass, entity_registry, snapshot, setup_entry.entry_id)


@pytest.fixture(name="consumeables_trait", autouse=True)
def consumeables_trait_fixture(fake_vacuum: FakeDevice) -> Mock:

    assert fake_vacuum.v1_properties is not None
    return fake_vacuum.v1_properties.consumables


@pytest.mark.parametrize(
    ("entity_id"),
    [
        ("button.roborock_s7_maxv_reset_sensor_consumable"),
        ("button.roborock_s7_maxv_reset_air_filter_consumable"),
        ("button.roborock_s7_maxv_reset_side_brush_consumable"),
        ("button.roborock_s7_maxv_reset_main_brush_consumable"),
    ],
)
@pytest.mark.freeze_time("2023-10-30 08:50:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_update_success(
    hass: HomeAssistant,
    bypass_api_client_fixture: None,
    setup_entry: MockConfigEntry,
    entity_id: str,
    consumeables_trait: Mock,
) -> None:


    assert hass.states.get(entity_id).state == "unknown"
    await hass.services.async_call(
        "button",
        SERVICE_PRESS,
        blocking=True,
        target={"entity_id": entity_id},
    )
    assert consumeables_trait.reset_consumable.assert_called_once
    assert hass.states.get(entity_id).state == "2023-10-30T08:50:00+00:00"


@pytest.mark.parametrize(
    ("entity_id"),
    [
        ("button.roborock_s7_maxv_reset_air_filter_consumable"),
    ],
)
@pytest.mark.freeze_time("2023-10-30 08:50:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_update_failure(
    hass: HomeAssistant,
    bypass_api_client_fixture: None,
    setup_entry: MockConfigEntry,
    entity_id: str,
    consumeables_trait: Mock,
) -> None:

    consumeables_trait.reset_consumable.side_effect = RoborockTimeout


    assert hass.states.get(entity_id).state == "unknown"
    with pytest.raises(
        HomeAssistantError, match="Error while calling RESET_CONSUMABLE"
    ):
        await hass.services.async_call(
            "button",
            SERVICE_PRESS,
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert consumeables_trait.reset_consumable.assert_called_once
    assert hass.states.get(entity_id).state == "2023-10-30T08:50:00+00:00"


@pytest.mark.parametrize(
    ("entity_id"),
    [
        ("button.roborock_s7_maxv_sc1"),
        ("button.roborock_s7_maxv_sc2"),
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_get_button_routines_failure(
    hass: HomeAssistant,
    get_scenes_failure_fixture: None,
    setup_entry: MockConfigEntry,
    entity_id: str,
    fake_vacuum: FakeDevice,
) -> None:


    assert hass.states.get(entity_id) is None


@pytest.mark.parametrize(
    ("entity_id", "routine_id"),
    [
        ("button.roborock_s7_maxv_sc1", 12),
        ("button.roborock_s7_maxv_sc2", 24),
    ],
)
@pytest.mark.freeze_time("2023-10-30 08:50:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_press_routine_button_success(
    hass: HomeAssistant,
    bypass_api_client_fixture: None,
    setup_entry: MockConfigEntry,
    entity_id: str,
    routine_id: int,
    fake_vacuum: FakeDevice,
) -> None:

    await hass.services.async_call(
        "button",
        SERVICE_PRESS,
        blocking=True,
        target={"entity_id": entity_id},
    )

    fake_vacuum.v1_properties.routines.execute_routine.assert_called_once_with(
        routine_id
    )
    assert hass.states.get(entity_id).state == "2023-10-30T08:50:00+00:00"


@pytest.mark.parametrize(
    ("entity_id", "routine_id"),
    [
        ("button.roborock_s7_maxv_sc1", 12),
    ],
)
@pytest.mark.freeze_time("2023-10-30 08:50:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_press_routine_button_failure(
    hass: HomeAssistant,
    bypass_api_client_fixture: None,
    setup_entry: MockConfigEntry,
    entity_id: str,
    routine_id: int,
    fake_vacuum: FakeDevice,
) -> None:

    fake_vacuum.v1_properties.routines.execute_routine.side_effect = RoborockException
    with pytest.raises(HomeAssistantError, match="Error while calling execute_scene"):
        await hass.services.async_call(
            "button",
            SERVICE_PRESS,
            blocking=True,
            target={"entity_id": entity_id},
        )
    fake_vacuum.v1_properties.routines.execute_routine.assert_called_once_with(
        routine_id
    )
    assert hass.states.get(entity_id).state == "2023-10-30T08:50:00+00:00"


@pytest.mark.parametrize(
    ("entity_id", "data_protocol"),
    [
        ("button.zeo_one_start", "START"),
        ("button.zeo_one_pause", "PAUSE"),
        ("button.zeo_one_shut_down", "SHUTDOWN"),
    ],
)
@pytest.mark.freeze_time("2023-10-30 08:50:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_press_a01_button_success(
    hass: HomeAssistant,
    bypass_api_client_fixture: None,
    setup_entry: MockConfigEntry,
    entity_id: str,
    data_protocol: str,
    fake_devices: list[FakeDevice],
) -> None:


    washing_machine = next(
        device
        for device in fake_devices
        if hasattr(device, "zeo") and device.zeo is not None
    )


    assert hass.states.get(entity_id) is not None

    await hass.services.async_call(
        "button",
        SERVICE_PRESS,
        blocking=True,
        target={"entity_id": entity_id},
    )


    washing_machine.zeo.set_value.assert_called_once()
    assert hass.states.get(entity_id).state == "2023-10-30T08:50:00+00:00"


@pytest.mark.parametrize(
    ("entity_id"),
    [
        ("button.zeo_one_start"),
    ],
)
@pytest.mark.freeze_time("2023-10-30 08:50:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_press_a01_button_failure(
    hass: HomeAssistant,
    bypass_api_client_fixture: None,
    setup_entry: MockConfigEntry,
    entity_id: str,
    fake_devices: list[FakeDevice],
) -> None:


    washing_machine = next(
        device
        for device in fake_devices
        if hasattr(device, "zeo") and device.zeo is not None
    )
    washing_machine.zeo.set_value.side_effect = RoborockException


    assert hass.states.get(entity_id) is not None

    with pytest.raises(HomeAssistantError, match="Failed to press button"):
        await hass.services.async_call(
            "button",
            SERVICE_PRESS,
            blocking=True,
            target={"entity_id": entity_id},
        )

    washing_machine.zeo.set_value.assert_called_once()
    assert hass.states.get(entity_id).state == "2023-10-30T08:50:00+00:00"


@pytest.mark.freeze_time("2023-10-30 08:50:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_press_q10_empty_dustbin_button_success(
    hass: HomeAssistant,
    bypass_api_client_fixture: None,
    setup_entry: MockConfigEntry,
    fake_q10_vacuum: FakeDevice,
) -> None:

    entity_id = "button.roborock_q10_s5_empty_dustbin"

    assert hass.states.get(entity_id) is not None
    await hass.services.async_call(
        "button",
        SERVICE_PRESS,
        blocking=True,
        target={"entity_id": entity_id},
    )

    assert fake_q10_vacuum.b01_q10_properties is not None
    fake_q10_vacuum.b01_q10_properties.vacuum.empty_dustbin.assert_called_once()
    assert hass.states.get(entity_id).state == "2023-10-30T08:50:00+00:00"


@pytest.mark.freeze_time("2023-10-30 08:50:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_press_q10_empty_dustbin_button_failure(
    hass: HomeAssistant,
    bypass_api_client_fixture: None,
    setup_entry: MockConfigEntry,
    fake_q10_vacuum: FakeDevice,
) -> None:

    entity_id = "button.roborock_q10_s5_empty_dustbin"
    assert fake_q10_vacuum.b01_q10_properties is not None
    fake_q10_vacuum.b01_q10_properties.vacuum.empty_dustbin.side_effect = (
        RoborockException
    )

    assert hass.states.get(entity_id) is not None
    with pytest.raises(HomeAssistantError, match="Error while calling empty_dustbin"):
        await hass.services.async_call(
            "button",
            SERVICE_PRESS,
            blocking=True,
            target={"entity_id": entity_id},
        )

    fake_q10_vacuum.b01_q10_properties.vacuum.empty_dustbin.assert_called_once()
    assert hass.states.get(entity_id).state == "2023-10-30T08:50:00+00:00"
