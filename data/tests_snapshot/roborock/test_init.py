

import datetime
import pathlib
from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from roborock import (
    RoborockInvalidCredentials,
    RoborockInvalidUserAgreement,
    RoborockNoUserAgreement,
)
from roborock.exceptions import RoborockException
from roborock.mqtt.session import MqttSessionUnauthorized

from homeassistant.components.homeassistant import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from homeassistant.components.roborock.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.setup import async_setup_component

from .conftest import FakeDevice
from .mock_data import ROBOROCK_RRUID, USER_EMAIL

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.typing import ClientSessionGenerator


async def test_unload_entry(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    device_manager: AsyncMock,
) -> None:

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert setup_entry.state is ConfigEntryState.LOADED

    assert device_manager.get_devices.called
    assert not device_manager.close.called


    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert setup_entry.state is ConfigEntryState.NOT_LOADED

    assert device_manager.close.called


async def test_home_assistant_stop(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    device_manager: AsyncMock,
) -> None:

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert setup_entry.state is ConfigEntryState.LOADED

    assert not device_manager.close.called


    await hass.async_stop()

    assert device_manager.close.called


@pytest.mark.parametrize(
    "side_effect", [RoborockInvalidCredentials(), MqttSessionUnauthorized()]
)
async def test_reauth_started(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    side_effect: Exception,
) -> None:

    with patch(
        "homeassistant.components.roborock.create_device_manager",
        side_effect=side_effect,
    ):
        await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        assert mock_roborock_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"


async def test_mqtt_session_unauthorized_hook_called(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    device_manager: AsyncMock,
) -> None:

    device_manager_kwargs = {}

    def create_device_manager(*args: Any, **kwargs: Any) -> AsyncMock:
        nonlocal device_manager_kwargs
        device_manager_kwargs = kwargs
        return device_manager

    with patch(
        "homeassistant.components.roborock.create_device_manager",
        side_effect=create_device_manager,
    ):
        await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_roborock_entry.state is ConfigEntryState.LOADED

    flows = hass.config_entries.flow.async_progress()
    assert not flows


    assert device_manager_kwargs
    mqtt_session_unauthorized_hook = device_manager_kwargs.get(
        "mqtt_session_unauthorized_hook"
    )
    assert mqtt_session_unauthorized_hook
    mqtt_session_unauthorized_hook()


    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"


@pytest.mark.parametrize("platforms", [[Platform.IMAGE]])
@pytest.mark.parametrize(
    ("exists", "is_dir", "rmtree_called"),
    [
        (True, True, True),
        (False, False, False),
        (True, False, False),
    ],
    ids=[
        "old_storage_removed",
        "new_storage_ignored",
        "no_existing_storage",
    ],
)
async def test_remove_old_storage_directory(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    storage_path: pathlib.Path,
    hass_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
    exists: bool,
    is_dir: bool,
    rmtree_called: bool,
) -> None:

    with (
        patch(
            "homeassistant.components.roborock.roborock_storage.Path.exists",
            return_value=exists,
        ),
        patch(
            "homeassistant.components.roborock.roborock_storage.Path.is_dir",
            return_value=is_dir,
        ),
        patch(
            "homeassistant.components.roborock.roborock_storage.shutil.rmtree",
        ) as mock_rmtree,
    ):
        await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_roborock_entry.state is ConfigEntryState.LOADED

    assert mock_rmtree.called == rmtree_called


@pytest.mark.parametrize("platforms", [[Platform.IMAGE]])
async def test_oserror_remove_storage_directory(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    storage_path: pathlib.Path,
    hass_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:

    with (
        patch(
            "homeassistant.components.roborock.roborock_storage.Path.exists",
            return_value=True,
        ),
        patch(
            "homeassistant.components.roborock.roborock_storage.Path.is_dir",
            return_value=True,
        ),
        patch(
            "homeassistant.components.roborock.roborock_storage.shutil.rmtree",
            side_effect=OSError,
        ) as mock_rmtree,
    ):
        await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_roborock_entry.state is ConfigEntryState.LOADED

    assert mock_rmtree.called
    assert "Unable to remove map files" in caplog.text


async def test_not_supported_protocol(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    fake_devices: list[FakeDevice],
) -> None:

    fake_devices[0].v1_properties = None
    fake_devices[0].zeo = None
    fake_devices[0].dyad = None
    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    await hass.async_block_till_done()
    assert "because its protocol version " in caplog.text


async def test_invalid_user_agreement(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
) -> None:

    with patch(
        "homeassistant.components.roborock.create_device_manager",
        side_effect=RoborockInvalidUserAgreement(),
    ):
        await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
        assert mock_roborock_entry.state is ConfigEntryState.SETUP_RETRY
        assert (
            mock_roborock_entry.error_reason_translation_key == "invalid_user_agreement"
        )


async def test_no_user_agreement(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
) -> None:

    with patch(
        "homeassistant.components.roborock.create_device_manager",
        side_effect=RoborockNoUserAgreement(),
    ):
        await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
        assert mock_roborock_entry.state is ConfigEntryState.SETUP_RETRY
        assert mock_roborock_entry.error_reason_translation_key == "no_user_agreement"


@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
async def test_stale_device(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    device_registry: DeviceRegistry,
    fake_devices: list[FakeDevice],
) -> None:

    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    assert mock_roborock_entry.state is ConfigEntryState.LOADED
    existing_devices = device_registry.devices.get_devices_for_config_entry_id(
        mock_roborock_entry.entry_id
    )
    assert {device.name for device in existing_devices} == {
        "Roborock S7 MaxV",
        "Roborock S7 MaxV Dock",
        "Roborock S7 2",
        "Roborock S7 2 Dock",
        "Dyad Pro",
        "Zeo One",
        "Roborock Q7",
        "Roborock Q10 S5+",
    }
    fake_devices.pop(0)

    await hass.config_entries.async_reload(mock_roborock_entry.entry_id)
    await hass.async_block_till_done()
    new_devices = device_registry.devices.get_devices_for_config_entry_id(
        mock_roborock_entry.entry_id
    )
    assert {device.name for device in new_devices} == {
        "Roborock S7 2",
        "Roborock S7 2 Dock",
        "Dyad Pro",
        "Zeo One",
        "Roborock Q7",
        "Roborock Q10 S5+",
    }


@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
async def test_no_stale_device(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    device_registry: DeviceRegistry,
    fake_devices: list[FakeDevice],
) -> None:

    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    assert mock_roborock_entry.state is ConfigEntryState.LOADED
    existing_devices = device_registry.devices.get_devices_for_config_entry_id(
        mock_roborock_entry.entry_id
    )
    assert {device.name for device in existing_devices} == {
        "Roborock S7 MaxV",
        "Roborock S7 MaxV Dock",
        "Roborock S7 2",
        "Roborock S7 2 Dock",
        "Dyad Pro",
        "Zeo One",
        "Roborock Q7",
        "Roborock Q10 S5+",
    }

    await hass.config_entries.async_reload(mock_roborock_entry.entry_id)
    await hass.async_block_till_done()
    new_devices = device_registry.devices.get_devices_for_config_entry_id(
        mock_roborock_entry.entry_id
    )
    assert {device.name for device in new_devices} == {
        "Roborock S7 MaxV",
        "Roborock S7 MaxV Dock",
        "Roborock S7 2",
        "Roborock S7 2 Dock",
        "Dyad Pro",
        "Zeo One",
        "Roborock Q7",
        "Roborock Q10 S5+",
    }


async def test_migrate_config_entry_unique_id(
    hass: HomeAssistant,
    config_entry_data: dict[str, Any],
) -> None:

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USER_EMAIL,
        data=config_entry_data,
        version=1,
        minor_version=1,
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.unique_id == ROBOROCK_RRUID


@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
async def test_update_unavailability_threshold(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_entry: MockConfigEntry,
    fake_vacuum: FakeDevice,
) -> None:

    await async_setup_component(hass, HA_DOMAIN, {})
    assert setup_entry.state is ConfigEntryState.LOADED


    sensor_entity_id = "sensor.roborock_s7_maxv_battery"
    expected_state = "100"
    state = hass.states.get(sensor_entity_id)
    assert state is not None
    assert state.state == expected_state


    assert fake_vacuum.v1_properties is not None
    fake_vacuum.v1_properties.status.refresh.side_effect = RoborockException(
        "Simulated update failure"
    )


    freezer.tick(datetime.timedelta(seconds=90))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


    await hass.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: sensor_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()


    state = hass.states.get(sensor_entity_id)
    assert state is not None
    assert state.state == expected_state


    freezer.tick(datetime.timedelta(minutes=3))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


    state = hass.states.get(sensor_entity_id)
    assert state is not None
    assert state.state == "unavailable"


    fake_vacuum.v1_properties.status.refresh.side_effect = None

    freezer.tick(datetime.timedelta(seconds=45))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


    state = hass.states.get(sensor_entity_id)
    assert state is not None
    assert state.state == expected_state


async def test_cloud_api_repair(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    fake_vacuum: FakeDevice,
) -> None:



    fake_vacuum.is_connected = True
    fake_vacuum.is_local_connected = False

    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    await hass.async_block_till_done()

    issue_registry = ir.async_get(hass)
    assert len(issue_registry.issues) == 1

    assert all(
        issue.translation_key == "cloud_api_used"
        for issue in issue_registry.issues.values()
    )
    names = {
        issue.translation_placeholders["device_name"]
        for issue in issue_registry.issues.values()
    }
    assert names == {"Roborock S7 MaxV"}
    await hass.config_entries.async_unload(mock_roborock_entry.entry_id)


    fake_vacuum.is_local_connected = True


    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    await hass.async_block_till_done()

    assert len(issue_registry.issues) == 0


@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
async def test_cloud_api_repair_cleared_on_update(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    fake_vacuum: FakeDevice,
    freezer: FrozenDateTimeFactory,
) -> None:



    fake_vacuum.is_connected = True
    fake_vacuum.is_local_connected = False


    await async_setup_component(hass, HA_DOMAIN, {})
    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_roborock_entry.state is ConfigEntryState.LOADED

    issue_registry = ir.async_get(hass)
    assert len(issue_registry.issues) == 1


    fake_vacuum.is_local_connected = True



    sensor_entity_id = "sensor.roborock_s7_maxv_battery"
    await hass.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: sensor_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()


    issue_registry = ir.async_get(hass)
    assert len(issue_registry.issues) == 0



    fake_vacuum.is_local_connected = False

    await hass.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: sensor_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()


    issue_registry = ir.async_get(hass)
    assert len(issue_registry.issues) == 0


@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
async def test_zeo_device_fails_setup(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    device_registry: DeviceRegistry,
    entity_registry: EntityRegistry,
    fake_devices: list[FakeDevice],
) -> None:


    zeo_device = next(
        (device for device in fake_devices if device.zeo is not None),
        None,
    )
    assert zeo_device is not None
    zeo_device.zeo.query_values.side_effect = RoborockException("Simulated Zeo failure")

    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    assert mock_roborock_entry.state is ConfigEntryState.LOADED



    zeo_device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, zeo_device.duid)}
    )
    assert zeo_device_entry is not None
    zeo_entities = er.async_entries_for_device(
        entity_registry, zeo_device_entry.id, include_disabled_entities=True
    )
    assert len(zeo_entities) == 0


    all_entities = er.async_entries_for_config_entry(
        entity_registry, mock_roborock_entry.entry_id
    )
    devices_with_entities = {
        device_registry.async_get(entity.device_id).name
        for entity in all_entities
        if entity.device_id is not None
    }
    assert devices_with_entities == {
        "Roborock S7 MaxV",
        "Roborock S7 MaxV Dock",
        "Roborock S7 2",
        "Roborock S7 2 Dock",
        "Dyad Pro",
        "Roborock Q7",
        "Roborock Q10 S5+",

    }


@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
async def test_dyad_device_fails_setup(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    device_registry: DeviceRegistry,
    entity_registry: EntityRegistry,
    fake_devices: list[FakeDevice],
) -> None:


    dyad_device = next(
        (device for device in fake_devices if device.dyad is not None),
        None,
    )
    assert dyad_device is not None
    dyad_device.dyad.query_values.side_effect = RoborockException(
        "Simulated Dyad failure"
    )

    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    assert mock_roborock_entry.state is ConfigEntryState.LOADED



    dyad_device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, dyad_device.duid)}
    )
    assert dyad_device_entry is not None
    dyad_entities = er.async_entries_for_device(
        entity_registry, dyad_device_entry.id, include_disabled_entities=True
    )
    assert len(dyad_entities) == 0


    all_entities = er.async_entries_for_config_entry(
        entity_registry, mock_roborock_entry.entry_id
    )
    devices_with_entities = {
        device_registry.async_get(entity.device_id).name
        for entity in all_entities
        if entity.device_id is not None
    }
    assert devices_with_entities == {
        "Roborock S7 MaxV",
        "Roborock S7 MaxV Dock",
        "Roborock S7 2",
        "Roborock S7 2 Dock",

        "Zeo One",
        "Roborock Q7",
        "Roborock Q10 S5+",
    }


@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
async def test_disabled_device_no_coordinator(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    device_registry: DeviceRegistry,
    fake_devices: list[FakeDevice],
) -> None:



    first_device = fake_devices[0]
    device_registry.async_get_or_create(
        config_entry_id=mock_roborock_entry.entry_id,
        identifiers={(DOMAIN, first_device.duid)},
        name=first_device.device_info.name,
        manufacturer="Roborock",
        disabled_by=dr.DeviceEntryDisabler.USER,
    )

    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_roborock_entry.state is ConfigEntryState.LOADED


    disabled_device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, first_device.duid)}
    )
    assert disabled_device_entry is not None
    assert disabled_device_entry.disabled



    coordinators = mock_roborock_entry.runtime_data
    assert all(coord.duid != first_device.duid for coord in coordinators.v1)


    found_devices = device_registry.devices.get_devices_for_config_entry_id(
        mock_roborock_entry.entry_id
    )
    enabled_device_names = {
        device.name for device in found_devices if not device.disabled
    }
    assert "Roborock S7 MaxV" not in enabled_device_names
    assert "Roborock S7 2" in enabled_device_names


@pytest.mark.parametrize("platforms", [[Platform.SENSOR]])
async def test_all_devices_disabled(
    hass: HomeAssistant,
    mock_roborock_entry: MockConfigEntry,
    device_registry: DeviceRegistry,
    entity_registry: EntityRegistry,
    fake_devices: list[FakeDevice],
) -> None:


    for fake_device in fake_devices:
        device_registry.async_get_or_create(
            config_entry_id=mock_roborock_entry.entry_id,
            identifiers={(DOMAIN, fake_device.duid)},
            name=fake_device.device_info.name,
            manufacturer="Roborock",
            disabled_by=dr.DeviceEntryDisabler.USER,
        )

    await hass.config_entries.async_setup(mock_roborock_entry.entry_id)
    await hass.async_block_till_done()


    assert mock_roborock_entry.state is ConfigEntryState.LOADED


    all_entities = er.async_entries_for_config_entry(
        entity_registry, mock_roborock_entry.entry_id
    )
    assert len(all_entities) == 0


    for fake_device in fake_devices:
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, fake_device.duid)}
        )
        assert device_entry is not None
        assert device_entry.disabled
