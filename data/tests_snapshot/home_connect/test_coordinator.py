

from collections.abc import Awaitable, Callable
from datetime import timedelta
import re
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

from aiohomeconnect.model import (
    ArrayOfEvents,
    ArrayOfHomeAppliances,
    ArrayOfPrograms,
    ArrayOfSettings,
    ArrayOfStatus,
    Event,
    EventKey,
    EventMessage,
    EventType,
    GetSetting,
    HomeAppliance,
    SettingKey,
)
from aiohomeconnect.model.error import (
    EventStreamInterruptedError,
    HomeConnectApiError,
    HomeConnectError,
    HomeConnectRequestError,
    TooManyRequestsError,
    UnauthorizedError,
)
from aiohomeconnect.model.program import Option, OptionKey, Program, ProgramKey
from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.components.home_connect.const import (
    BSH_DOOR_STATE_OPEN,
    BSH_EVENT_PRESENT_STATE_PRESENT,
    BSH_POWER_OFF,
    DOMAIN,
)
from homeassistant.components.homeassistant import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from homeassistant.config_entries import ConfigEntries, ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_STATE_REPORTED,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import (
    Event as HassEvent,
    EventStateReportedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed

INITIAL_FETCH_CLIENT_METHODS = [
    "get_settings",
    "get_status",
    "get_all_programs",
    "get_available_commands",
    "get_available_program",
]


@pytest.fixture
def platforms() -> list[str]:

    return [Platform.SENSOR, Platform.SWITCH]


@pytest.mark.parametrize("platforms", [("binary_sensor",)])
@pytest.mark.parametrize("appliance", ["Washer"], indirect=True)
async def test_coordinator_failure_refresh_and_stream(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
) -> None:

    appliance_data = (
        cast(str, appliance.to_json())
        .replace("ha_id", "haId")
        .replace("e_number", "enumber")
    )
    entity_id_1 = "binary_sensor.washer_remote_control"
    entity_id_2 = "binary_sensor.washer_remote_start"
    await async_setup_component(hass, HA_DOMAIN, {})
    await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED
    state = hass.states.get(entity_id_1)
    assert state
    assert state.state != STATE_UNAVAILABLE
    state = hass.states.get(entity_id_2)
    assert state
    assert state.state != STATE_UNAVAILABLE

    client.get_specific_appliance.side_effect = HomeConnectError()


    await hass.services.async_call(
        HA_DOMAIN, SERVICE_UPDATE_ENTITY, {ATTR_ENTITY_ID: entity_id_1}, blocking=True
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id_1)
    assert state
    assert state.state == STATE_UNAVAILABLE
    state = hass.states.get(entity_id_2)
    assert state
    assert state.state == STATE_UNAVAILABLE



    client.get_specific_appliance.side_effect = None
    client.get_specific_appliance.return_value = HomeAppliance.from_json(appliance_data)


    freezer.tick(timedelta(hours=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


    await hass.services.async_call(
        HA_DOMAIN, SERVICE_UPDATE_ENTITY, {ATTR_ENTITY_ID: entity_id_1}, blocking=True
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id_1)
    assert state
    assert state.state != STATE_UNAVAILABLE
    state = hass.states.get(entity_id_2)
    assert state
    assert state.state != STATE_UNAVAILABLE




    client.get_specific_appliance.side_effect = HomeConnectError()


    freezer.tick(timedelta(hours=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


    await hass.services.async_call(
        HA_DOMAIN, SERVICE_UPDATE_ENTITY, {ATTR_ENTITY_ID: entity_id_1}, blocking=True
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id_1)
    assert state
    assert state.state == STATE_UNAVAILABLE
    state = hass.states.get(entity_id_2)
    assert state
    assert state.state == STATE_UNAVAILABLE


    client.get_specific_appliance.side_effect = None
    client.get_specific_appliance.return_value = HomeAppliance.from_json(appliance_data)


    event_message = EventMessage(
        appliance.ha_id,
        EventType.STATUS,
        ArrayOfEvents(
            [
                Event(
                    key=EventKey.BSH_COMMON_STATUS_REMOTE_CONTROL_ACTIVE,
                    raw_key=EventKey.BSH_COMMON_STATUS_REMOTE_CONTROL_ACTIVE.value,
                    timestamp=0,
                    level="",
                    handling="",
                    value=False,
                )
            ],
        ),
    )
    await client.add_events([event_message])
    await hass.async_block_till_done()

    state = hass.states.get(entity_id_1)
    assert state
    assert state.state != STATE_UNAVAILABLE
    state = hass.states.get(entity_id_2)
    assert state
    assert state.state != STATE_UNAVAILABLE


@pytest.mark.parametrize("appliance", ["Dishwasher"], indirect=True)
async def test_coordinator_not_fetching_on_disconnected_appliance(
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
) -> None:

    appliance.connected = False

    await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    for method in INITIAL_FETCH_CLIENT_METHODS:
        assert getattr(client, method).call_count == 0


@pytest.mark.parametrize(
    "mock_method",
    INITIAL_FETCH_CLIENT_METHODS,
)
async def test_coordinator_update_failing(
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    mock_method: str,
) -> None:




    setattr(client, mock_method, AsyncMock(side_effect=HomeConnectError()))

    await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    getattr(client, mock_method).assert_called()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize("appliance", ["Dishwasher"], indirect=True)
@pytest.mark.parametrize(
    ("event_type", "event_key", "event_value", ATTR_ENTITY_ID),
    [
        (
            EventType.STATUS,
            EventKey.BSH_COMMON_STATUS_DOOR_STATE,
            BSH_DOOR_STATE_OPEN,
            "sensor.dishwasher_door",
        ),
        (
            EventType.NOTIFY,
            EventKey.BSH_COMMON_SETTING_POWER_STATE,
            BSH_POWER_OFF,
            "switch.dishwasher_power",
        ),
        (
            EventType.EVENT,
            EventKey.DISHCARE_DISHWASHER_EVENT_SALT_NEARLY_EMPTY,
            BSH_EVENT_PRESENT_STATE_PRESENT,
            "sensor.dishwasher_salt_nearly_empty",
        ),
    ],
)
async def test_event_listener(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
    event_type: EventType,
    event_key: EventKey,
    event_value: str,
    entity_id: str,
) -> None:

    await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    state = hass.states.get(entity_id)
    assert state
    event_message = EventMessage(
        appliance.ha_id,
        event_type,
        ArrayOfEvents(
            [
                Event(
                    key=event_key,
                    raw_key=event_key.value,
                    timestamp=0,
                    level="",
                    handling="",
                    value=event_value,
                )
            ],
        ),
    )
    await client.add_events([event_message])
    await hass.async_block_till_done()

    new_state = hass.states.get(entity_id)
    assert new_state
    assert new_state.state != state.state


    new_entity_id = entity_id + "_new"
    listener = MagicMock()

    @callback
    def listener_callback(event: HassEvent[EventStateReportedData]) -> None:
        listener(event.data["entity_id"])

    @callback
    def event_filter(_: EventStateReportedData) -> bool:
        return True

    hass.bus.async_listen_once(EVENT_STATE_REPORTED, listener_callback, event_filter)

    entity_registry.async_update_entity(entity_id, new_entity_id=new_entity_id)
    await hass.async_block_till_done()
    await client.add_events([event_message])
    await hass.async_block_till_done()




    listener.assert_called_once_with(new_entity_id)


@pytest.mark.parametrize("appliance", ["Washer"], indirect=True)
async def tests_receive_setting_and_status_for_first_time_at_events(
    hass: HomeAssistant,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
) -> None:

    client.get_setting = AsyncMock(return_value=ArrayOfSettings([]))
    client.get_status = AsyncMock(return_value=ArrayOfStatus([]))

    await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    await client.add_events(
        [
            EventMessage(
                appliance.ha_id,
                EventType.NOTIFY,
                ArrayOfEvents(
                    [
                        Event(
                            key=EventKey.LAUNDRY_CARE_WASHER_SETTING_I_DOS_1_BASE_LEVEL,
                            raw_key=EventKey.LAUNDRY_CARE_WASHER_SETTING_I_DOS_1_BASE_LEVEL.value,
                            timestamp=0,
                            level="",
                            handling="",
                            value="some value",
                        )
                    ],
                ),
            ),
            EventMessage(
                appliance.ha_id,
                EventType.STATUS,
                ArrayOfEvents(
                    [
                        Event(
                            key=EventKey.BSH_COMMON_STATUS_DOOR_STATE,
                            raw_key=EventKey.BSH_COMMON_STATUS_DOOR_STATE.value,
                            timestamp=0,
                            level="",
                            handling="",
                            value="some value",
                        )
                    ],
                ),
            ),
        ]
    )
    await hass.async_block_till_done()
    assert len(config_entry._background_tasks) == 1
    assert config_entry.state is ConfigEntryState.LOADED


async def test_event_listener_error(
    hass: HomeAssistant,
    client_with_exception: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
) -> None:

    client_with_exception.stream_all_events = MagicMock(
        side_effect=HomeConnectApiError("error.key", "error description")
    )

    with patch.object(
        ConfigEntries,
        "async_schedule_reload",
    ) as mock_schedule_reload:
        await integration_setup(client_with_exception)
        await hass.async_block_till_done()

    client_with_exception.stream_all_events.assert_called_once()
    mock_schedule_reload.assert_called_once_with(config_entry.entry_id)
    assert not config_entry._background_tasks


@pytest.mark.parametrize("platforms", [("sensor",)])
@pytest.mark.parametrize("appliance", ["Washer"], indirect=True)
@pytest.mark.parametrize(
    "exception",
    [HomeConnectRequestError(), EventStreamInterruptedError()],
)
@pytest.mark.parametrize(
    (
        "entity_id",
        "initial_state",
        "event_key",
        "event_value",
        "after_event_expected_state",
    ),
    [
        (
            "sensor.washer_door",
            "closed",
            EventKey.BSH_COMMON_STATUS_DOOR_STATE,
            BSH_DOOR_STATE_OPEN,
            "open",
        ),
    ],
)
async def test_event_listener_resilience(
    hass: HomeAssistant,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
    exception: HomeConnectError,
    entity_id: str,
    initial_state: str,
    event_key: EventKey,
    event_value: Any,
    after_event_expected_state: str,
) -> None:

    future = hass.loop.create_future()

    async def stream_exception():
        yield await future

    client.stream_all_events = MagicMock(
        side_effect=[stream_exception(), client.stream_all_events()]
    )

    await integration_setup(client)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert len(config_entry._background_tasks) == 1

    state = hass.states.get(entity_id)
    assert state
    assert state.state == initial_state

    future.set_exception(exception)
    await hass.async_block_till_done()

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=30))
    await hass.async_block_till_done()

    assert client.stream_all_events.call_count == 2

    await client.add_events(
        [
            EventMessage(
                appliance.ha_id,
                EventType.STATUS,
                ArrayOfEvents(
                    [
                        Event(
                            key=event_key,
                            raw_key=event_key.value,
                            timestamp=0,
                            level="",
                            handling="",
                            value=event_value,
                        )
                    ],
                ),
            ),
        ]
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert state.state == after_event_expected_state


async def test_devices_updated_on_refresh(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    platforms: list[str],
) -> None:

    appliances: list[HomeAppliance] = (
        client.get_home_appliances.return_value.homeappliances
    )
    assert len(appliances) >= 3
    client.get_home_appliances = AsyncMock(
        return_value=ArrayOfHomeAppliances(appliances[:2]),
    )

    await async_setup_component(hass, HA_DOMAIN, {})
    await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    for appliance in appliances[:2]:
        assert device_registry.async_get_device({(DOMAIN, appliance.ha_id)})
    assert not device_registry.async_get_device({(DOMAIN, appliances[2].ha_id)})

    client.get_home_appliances = AsyncMock(
        return_value=ArrayOfHomeAppliances(appliances[1:3]),
    )
    with (
        patch("homeassistant.components.home_connect.PLATFORMS", platforms),
        patch(
            "homeassistant.components.home_connect.HomeConnectClient",
            return_value=client,
        ),
    ):
        await client.add_events([HomeConnectApiError("error.key", "error description")])
        await hass.async_block_till_done()

    assert not device_registry.async_get_device({(DOMAIN, appliances[0].ha_id)})
    for appliance in appliances[2:3]:
        assert device_registry.async_get_device({(DOMAIN, appliance.ha_id)})


@pytest.mark.parametrize("appliance", ["Washer"], indirect=True)
async def test_paired_event(
    hass: HomeAssistant,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
) -> None:

    client.get_home_appliances = AsyncMock(return_value=ArrayOfHomeAppliances([]))
    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    await client.add_events(
        [
            EventMessage(
                appliance.ha_id,
                EventType.PAIRED,
                data=ArrayOfEvents([]),
            )
        ]
    )
    await hass.async_block_till_done()





    assert client.get_specific_appliance.call_count == 2
    for call in client.get_specific_appliance.call_args_list:
        assert call.args[0] == appliance.ha_id
    for method in INITIAL_FETCH_CLIENT_METHODS:
        getattr(client, method).assert_awaited_once()


@pytest.mark.parametrize("appliance", ["Washer"], indirect=True)
async def test_paired_disconnected_devices_not_fetching(
    hass: HomeAssistant,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
) -> None:

    client.get_home_appliances = AsyncMock(return_value=ArrayOfHomeAppliances([]))
    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    appliance.connected = False
    await client.add_events(
        [
            EventMessage(
                appliance.ha_id,
                EventType.PAIRED,
                data=ArrayOfEvents([]),
            )
        ]
    )
    await hass.async_block_till_done()





    assert client.get_specific_appliance.call_count == 2
    for call in client.get_specific_appliance.call_args_list:
        assert call.args[0] == appliance.ha_id
    for method in INITIAL_FETCH_CLIENT_METHODS:
        getattr(client, method).assert_not_awaited()


async def test_coordinator_disabling_updates_for_appliance(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
) -> None:





    appliance_ha_id = "SIEMENS-HCS02DWH1-6BE58C26DCC1"

    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    assert hass.states.is_state("switch.dishwasher_power", STATE_ON)

    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.CONNECTED,
                data=ArrayOfEvents([]),
            )
            for _ in range(6)
        ]
    )
    await hass.async_block_till_done()

    freezer.tick(timedelta(minutes=10))
    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.CONNECTED,
                data=ArrayOfEvents([]),
            )
            for _ in range(2)
        ]
    )
    await hass.async_block_till_done()




    get_settings_original_side_effect = client.get_settings.side_effect

    async def get_settings_side_effect(ha_id: str) -> ArrayOfSettings:
        if ha_id == appliance_ha_id:
            return ArrayOfSettings(
                [
                    GetSetting(
                        SettingKey.BSH_COMMON_POWER_STATE,
                        SettingKey.BSH_COMMON_POWER_STATE.value,
                        BSH_POWER_OFF,
                    )
                ]
            )
        return cast(ArrayOfSettings, get_settings_original_side_effect(ha_id))

    client.get_settings = AsyncMock(side_effect=get_settings_side_effect)

    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.CONNECTED,
                data=ArrayOfEvents([]),
            )
        ]
    )
    await hass.async_block_till_done()

    assert hass.states.is_state("switch.dishwasher_power", STATE_ON)




    freezer.tick(timedelta(minutes=55))
    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.CONNECTED,
                data=ArrayOfEvents([]),
            )
        ]
    )
    await hass.async_block_till_done()

    assert hass.states.is_state("switch.dishwasher_power", STATE_OFF)


    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.CONNECTED,
                data=ArrayOfEvents([]),
            )
            for _ in range(5)
        ]
    )
    await hass.async_block_till_done()
    client.get_settings = get_settings_original_side_effect
    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.CONNECTED,
                data=ArrayOfEvents([]),
            )
        ]
    )
    await hass.async_block_till_done()

    assert hass.states.is_state("switch.dishwasher_power", STATE_OFF)


async def test_coordinator_disabling_updates_for_appliance_is_gone_after_entry_reload(
    hass: HomeAssistant,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
) -> None:




    appliance_ha_id = "SIEMENS-HCS02DWH1-6BE58C26DCC1"

    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    assert hass.states.is_state("switch.dishwasher_power", STATE_ON)

    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.CONNECTED,
                data=ArrayOfEvents([]),
            )
            for _ in range(8)
        ]
    )
    await hass.async_block_till_done()

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    get_settings_original_side_effect = client.get_settings.side_effect

    async def get_settings_side_effect(ha_id: str) -> ArrayOfSettings:
        if ha_id == appliance_ha_id:
            return ArrayOfSettings(
                [
                    GetSetting(
                        SettingKey.BSH_COMMON_POWER_STATE,
                        SettingKey.BSH_COMMON_POWER_STATE.value,
                        BSH_POWER_OFF,
                    )
                ]
            )
        return cast(ArrayOfSettings, get_settings_original_side_effect(ha_id))

    client.get_settings = AsyncMock(side_effect=get_settings_side_effect)

    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.CONNECTED,
                data=ArrayOfEvents([]),
            )
        ]
    )
    await hass.async_block_till_done()

    assert hass.states.is_state("switch.dishwasher_power", STATE_OFF)


@pytest.mark.parametrize("appliance", ["Dishwasher"], indirect=True)
async def test_auth_error_while_updating_appliance(
    hass: HomeAssistant,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
) -> None:

    entity_id = "switch.dishwasher_power"

    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(entity_id)

    client.get_specific_appliance = AsyncMock(
        side_effect=UnauthorizedError("unauthorized")
    )

    await async_setup_component(hass, HA_DOMAIN, {})
    await hass.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    flows_in_progress = hass.config_entries.flow.async_progress()
    assert len(flows_in_progress) == 1
    result = flows_in_progress[0]
    assert result["step_id"] == "reauth_confirm"
    assert result["context"]["entry_id"] == config_entry.entry_id
    assert result["context"]["source"] == "reauth"


@pytest.mark.parametrize("appliance", ["Dishwasher"], indirect=True)
@pytest.mark.parametrize(
    ("side_effect", "log_level", "string_in_log"),
    [
        (
            HomeConnectError("mocked-error"),
            "ERROR",
            r".*mocked-error.*",
        ),
        (
            [
                TooManyRequestsError("rate-limit-error", retry_after=0.1),
                Exception("error-to-stop-retrying"),
            ],
            "WARNING",
            r"Rate limit exceeded, retrying in 0.1 seconds.*rate-limit-error",
        ),
    ],
)
async def test_other_errors_while_updating_appliance(
    hass: HomeAssistant,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    caplog: pytest.LogCaptureFixture,
    side_effect: HomeConnectError | list[Exception],
    log_level: str,
    string_in_log: str,
) -> None:

    entity_id = "switch.dishwasher_power"

    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(entity_id)

    client.get_specific_appliance = AsyncMock(side_effect=side_effect)

    await async_setup_component(hass, HA_DOMAIN, {})
    caplog.clear()
    await hass.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    assert any(
        record.levelname == log_level and re.search(string_in_log, record.message)
        for record in caplog.records
    )


@pytest.mark.parametrize("appliance", ["Dishwasher"], indirect=True)
@pytest.mark.parametrize("array_of_programs_param", ["active", "selected"])
async def test_fetch_base_program_options_when_active_favorite_program(
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
    array_of_programs_param: str,
) -> None:





    client.get_all_programs = AsyncMock(
        return_value=ArrayOfPrograms(
            programs=[],
            **{
                array_of_programs_param: Program(
                    key=ProgramKey.BSH_COMMON_FAVORITE_001,
                    options=[
                        Option(
                            OptionKey.BSH_COMMON_BASE_PROGRAM,
                            ProgramKey.DISHCARE_DISHWASHER_ECO_50.value,
                        )
                    ],
                ),
            },
        )
    )

    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    client.get_available_program.assert_awaited_once_with(
        appliance.ha_id, program_key=ProgramKey.DISHCARE_DISHWASHER_ECO_50
    )


@pytest.mark.parametrize("appliance", ["Dishwasher"], indirect=True)
@pytest.mark.parametrize(
    "event_key",
    [
        EventKey.BSH_COMMON_ROOT_ACTIVE_PROGRAM,
        EventKey.BSH_COMMON_ROOT_SELECTED_PROGRAM,
    ],
)
async def test_fetch_base_program_options_when_favorite_program_event(
    hass: HomeAssistant,
    client: MagicMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[MagicMock], Awaitable[bool]],
    appliance: HomeAppliance,
    event_key: EventKey,
) -> None:





    appliance_ha_id = appliance.ha_id
    assert await integration_setup(client)
    assert config_entry.state is ConfigEntryState.LOADED

    client.get_available_program.reset_mock()
    await client.add_events(
        [
            EventMessage(
                appliance_ha_id,
                EventType.NOTIFY,
                data=ArrayOfEvents(
                    [
                        Event(
                            key=event_key,
                            raw_key=event_key.value,
                            timestamp=0,
                            level="",
                            handling="",
                            value=ProgramKey.BSH_COMMON_FAVORITE_001.value,
                        ),
                        Event(
                            key=EventKey.BSH_COMMON_OPTION_BASE_PROGRAM,
                            raw_key=EventKey.BSH_COMMON_OPTION_BASE_PROGRAM.value,
                            timestamp=0,
                            level="",
                            handling="",
                            value=ProgramKey.DISHCARE_DISHWASHER_ECO_50.value,
                        ),
                    ]
                ),
            )
        ]
    )
    await hass.async_block_till_done()

    client.get_available_program.assert_awaited_once_with(
        appliance.ha_id, program_key=ProgramKey.DISHCARE_DISHWASHER_ECO_50
    )
