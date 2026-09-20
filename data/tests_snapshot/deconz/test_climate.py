

from collections.abc import Callable
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE_DOMAIN,
    FAN_OFF,
    FAN_ON,
    PRESET_BOOST,
    PRESET_COMFORT,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from homeassistant.components.deconz.climate import (
    DECONZ_FAN_SMART,
    DECONZ_PRESET_AUTO,
    DECONZ_PRESET_MANUAL,
)
from homeassistant.components.deconz.const import CONF_ALLOW_CLIP_SENSOR
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, STATE_OFF, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from .conftest import ConfigEntryFactoryType, WebsocketDataType

from tests.common import snapshot_platform
from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "config": {
                "battery": 59,
                "displayflipped": None,
                "heatsetpoint": 2100,
                "locked": True,
                "mountingmode": None,
                "offset": 0,
                "on": True,
                "reachable": True,
            },
            "ep": 1,
            "etag": "6130553ac247174809bae47144ee23f8",
            "lastseen": "2020-11-29T19:31Z",
            "manufacturername": "Danfoss",
            "modelid": "eTRV0100",
            "name": "thermostat",
            "state": {
                "errorcode": None,
                "lastupdated": "2020-11-29T19:28:40.665",
                "mountingmodeactive": False,
                "on": True,
                "temperature": 2102,
                "valve": 24,
                "windowopen": "Closed",
            },
            "swversion": "01.02.0008 01.02",
            "type": "ZHAThermostat",
            "uniqueid": "14:b4:57:ff:fe:d5:4e:77-01-0201",
        }
    ],
)
async def test_simple_climate_device(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry_factory: ConfigEntryFactoryType,
    mock_put_request: Callable[[str, str], AiohttpClientMocker],
    sensor_ws_data: WebsocketDataType,
    snapshot: SnapshotAssertion,
) -> None:




    with patch("homeassistant.components.deconz.PLATFORMS", [Platform.CLIMATE]):
        config_entry = await config_entry_factory()
    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)



    await sensor_ws_data({"state": {"on": False}})
    assert hass.states.get("climate.thermostat").state == STATE_OFF
    assert (
        hass.states.get("climate.thermostat").attributes["hvac_action"]
        == HVACAction.IDLE
    )



    await sensor_ws_data({"state": {"on": True}})
    assert hass.states.get("climate.thermostat").state == HVACMode.HEAT
    assert (
        hass.states.get("climate.thermostat").attributes["hvac_action"]
        == HVACAction.HEATING
    )



    aioclient_mock = mock_put_request("/sensors/0/config")



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: "climate.thermostat", ATTR_HVAC_MODE: HVACMode.HEAT},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[1][2] == {"on": True}



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: "climate.thermostat", ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[2][2] == {"on": False}



    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: "climate.thermostat", ATTR_HVAC_MODE: HVACMode.AUTO},
            blocking=True,
        )


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "name": "Thermostat",
            "type": "ZHAThermostat",
            "state": {"on": True, "temperature": 2260, "valve": 30},
            "config": {
                "battery": 100,
                "heatsetpoint": 2200,
                "mode": "auto",
                "offset": 10,
                "reachable": True,
            },
            "uniqueid": "00:00:00:00:00:00:00:00-00",
        }
    ],
)
async def test_climate_device_without_cooling_support(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry_factory: ConfigEntryFactoryType,
    mock_put_request: Callable[[str, str], AiohttpClientMocker],
    sensor_ws_data: WebsocketDataType,
    snapshot: SnapshotAssertion,
) -> None:

    with patch("homeassistant.components.deconz.PLATFORMS", [Platform.CLIMATE]):
        config_entry = await config_entry_factory()
    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)



    await sensor_ws_data({"config": {"mode": "off"}})
    assert hass.states.get("climate.thermostat").state == STATE_OFF
    assert (
        hass.states.get("climate.thermostat").attributes["hvac_action"]
        == HVACAction.OFF
    )



    await sensor_ws_data({"config": {"mode": "other"}, "state": {"on": True}})
    assert hass.states.get("climate.thermostat").state == HVACMode.HEAT
    assert (
        hass.states.get("climate.thermostat").attributes["hvac_action"]
        == HVACAction.HEATING
    )



    await sensor_ws_data({"state": {"on": False}})
    assert hass.states.get("climate.thermostat").state == STATE_OFF
    assert (
        hass.states.get("climate.thermostat").attributes["hvac_action"]
        == HVACAction.IDLE
    )



    aioclient_mock = mock_put_request("/sensors/0/config")



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: "climate.thermostat", ATTR_HVAC_MODE: HVACMode.AUTO},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[1][2] == {"mode": "auto"}



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: "climate.thermostat", ATTR_HVAC_MODE: HVACMode.HEAT},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[2][2] == {"mode": "heat"}



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: "climate.thermostat", ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[3][2] == {"mode": "off"}



    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: "climate.thermostat", ATTR_HVAC_MODE: HVACMode.COOL},
            blocking=True,
        )



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: "climate.thermostat", ATTR_TEMPERATURE: 20},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[4][2] == {"heatsetpoint": 2000.0}



    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "climate.thermostat",
                ATTR_TARGET_TEMP_HIGH: 30,
                ATTR_TARGET_TEMP_LOW: 10,
            },
            blocking=True,
        )


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "config": {
                "battery": 25,
                "coolsetpoint": 1111,
                "fanmode": None,
                "heatsetpoint": 2222,
                "mode": "heat",
                "offset": 0,
                "on": True,
                "reachable": True,
            },
            "ep": 1,
            "etag": "074549903686a77a12ef0f06c499b1ef",
            "lastseen": "2020-11-27T13:45Z",
            "manufacturername": "Zen Within",
            "modelid": "Zen-01",
            "name": "Zen-01",
            "state": {
                "lastupdated": "2020-11-27T13:42:40.863",
                "on": False,
                "temperature": 2320,
            },
            "type": "ZHAThermostat",
            "uniqueid": "00:24:46:00:00:11:6f:56-01-0201",
        }
    ],
)
async def test_climate_device_with_cooling_support(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry_factory: ConfigEntryFactoryType,
    mock_put_request: Callable[[str, str], AiohttpClientMocker],
    sensor_ws_data: WebsocketDataType,
    snapshot: SnapshotAssertion,
) -> None:

    with patch("homeassistant.components.deconz.PLATFORMS", [Platform.CLIMATE]):
        config_entry = await config_entry_factory()
    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)



    await sensor_ws_data({"config": {"mode": "cool"}})
    assert hass.states.get("climate.zen_01").state == HVACMode.COOL
    assert hass.states.get("climate.zen_01").attributes["temperature"] == 11.1
    assert (
        hass.states.get("climate.zen_01").attributes["hvac_action"] == HVACAction.IDLE
    )



    await sensor_ws_data({"state": {"on": True}})
    assert hass.states.get("climate.zen_01").state == HVACMode.COOL
    assert (
        hass.states.get("climate.zen_01").attributes["hvac_action"]
        == HVACAction.COOLING
    )



    aioclient_mock = mock_put_request("/sensors/0/config")



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: "climate.zen_01", ATTR_TEMPERATURE: 20},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[1][2] == {"coolsetpoint": 2000.0}


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "config": {
                "battery": 25,
                "coolsetpoint": None,
                "fanmode": "auto",
                "heatsetpoint": 2222,
                "mode": "heat",
                "offset": 0,
                "on": True,
                "reachable": True,
            },
            "ep": 1,
            "etag": "074549903686a77a12ef0f06c499b1ef",
            "lastseen": "2020-11-27T13:45Z",
            "manufacturername": "Zen Within",
            "modelid": "Zen-01",
            "name": "Zen-01",
            "state": {
                "lastupdated": "2020-11-27T13:42:40.863",
                "on": False,
                "temperature": 2320,
            },
            "type": "ZHAThermostat",
            "uniqueid": "00:24:46:00:00:11:6f:56-01-0201",
        }
    ],
)
async def test_climate_device_with_fan_support(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry_factory: ConfigEntryFactoryType,
    mock_put_request: Callable[[str, str], AiohttpClientMocker],
    sensor_ws_data: WebsocketDataType,
    snapshot: SnapshotAssertion,
) -> None:

    with patch("homeassistant.components.deconz.PLATFORMS", [Platform.CLIMATE]):
        config_entry = await config_entry_factory()
    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)



    await sensor_ws_data({"config": {"fanmode": "unsupported"}})
    assert hass.states.get("climate.zen_01").attributes["fan_mode"] == FAN_OFF
    assert (
        hass.states.get("climate.zen_01").attributes["hvac_action"] == HVACAction.IDLE
    )



    await sensor_ws_data({"config": {"fanmode": "unsupported"}, "state": {"on": True}})
    assert hass.states.get("climate.zen_01").attributes["fan_mode"] == FAN_ON
    assert (
        hass.states.get("climate.zen_01").attributes["hvac_action"]
        == HVACAction.HEATING
    )



    await sensor_ws_data({"config": {"fanmode": "unsupported"}})
    assert hass.states.get("climate.zen_01").attributes["fan_mode"] == FAN_ON
    assert (
        hass.states.get("climate.zen_01").attributes["hvac_action"]
        == HVACAction.HEATING
    )



    aioclient_mock = mock_put_request("/sensors/0/config")



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: "climate.zen_01", ATTR_FAN_MODE: FAN_OFF},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[1][2] == {"fanmode": "off"}



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: "climate.zen_01", ATTR_FAN_MODE: DECONZ_FAN_SMART},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[2][2] == {"fanmode": "smart"}



    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {ATTR_ENTITY_ID: "climate.zen_01", ATTR_FAN_MODE: "unsupported"},
            blocking=True,
        )


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "config": {
                "battery": 25,
                "coolsetpoint": None,
                "fanmode": None,
                "heatsetpoint": 2222,
                "mode": "heat",
                "preset": "auto",
                "offset": 0,
                "on": True,
                "reachable": True,
            },
            "ep": 1,
            "etag": "074549903686a77a12ef0f06c499b1ef",
            "lastseen": "2020-11-27T13:45Z",
            "manufacturername": "Zen Within",
            "modelid": "Zen-01",
            "name": "Zen-01",
            "state": {
                "lastupdated": "2020-11-27T13:42:40.863",
                "on": False,
                "temperature": 2320,
            },
            "type": "ZHAThermostat",
            "uniqueid": "00:24:46:00:00:11:6f:56-01-0201",
        }
    ],
)
async def test_climate_device_with_preset(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_put_request: Callable[[str, str], AiohttpClientMocker],
    sensor_ws_data: WebsocketDataType,
    config_entry_factory: ConfigEntryFactoryType,
    snapshot: SnapshotAssertion,
) -> None:

    with patch("homeassistant.components.deconz.PLATFORMS", [Platform.CLIMATE]):
        config_entry = await config_entry_factory()
    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)



    await sensor_ws_data({"config": {"preset": "manual"}})
    assert (
        hass.states.get("climate.zen_01").attributes["preset_mode"]
        == DECONZ_PRESET_MANUAL
    )



    await sensor_ws_data({"config": {"preset": "unsupported"}})
    assert hass.states.get("climate.zen_01").attributes["preset_mode"] is None



    aioclient_mock = mock_put_request("/sensors/0/config")



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: "climate.zen_01", ATTR_PRESET_MODE: PRESET_COMFORT},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[1][2] == {"preset": "comfort"}



    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: "climate.zen_01", ATTR_PRESET_MODE: DECONZ_PRESET_MANUAL},
        blocking=True,
    )
    assert aioclient_mock.mock_calls[2][2] == {"preset": "manual"}



    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: "climate.zen_01", ATTR_PRESET_MODE: "unsupported"},
            blocking=True,
        )


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "1": {
                "name": "Thermostat",
                "type": "ZHAThermostat",
                "state": {"on": True, "temperature": 2260, "valve": 30},
                "config": {
                    "battery": 100,
                    "heatsetpoint": 2200,
                    "mode": "auto",
                    "offset": 10,
                    "reachable": True,
                },
                "uniqueid": "00:00:00:00:00:00:00:00-00",
            },
            "2": {
                "name": "CLIP thermostat",
                "type": "CLIPThermostat",
                "state": {"on": True, "temperature": 2260, "valve": 30},
                "config": {"reachable": True},
                "uniqueid": "00:00:00:00:00:00:00:02-00",
            },
        }
    ],
)
@pytest.mark.parametrize("config_entry_options", [{CONF_ALLOW_CLIP_SENSOR: True}])
async def test_clip_climate_device(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry_factory: ConfigEntryFactoryType,
    snapshot: SnapshotAssertion,
) -> None:

    with patch("homeassistant.components.deconz.PLATFORMS", [Platform.CLIMATE]):
        config_entry = await config_entry_factory()
    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)



    hass.config_entries.async_update_entry(
        config_entry, options={CONF_ALLOW_CLIP_SENSOR: False}
    )
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 1
    assert not hass.states.get("climate.clip_thermostat")



    hass.config_entries.async_update_entry(
        config_entry, options={CONF_ALLOW_CLIP_SENSOR: True}
    )
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 2
    assert hass.states.get("climate.clip_thermostat").state == HVACMode.HEAT
    assert (
        hass.states.get("climate.clip_thermostat").attributes["hvac_action"]
        == HVACAction.HEATING
    )


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "name": "Thermostat",
            "type": "ZHAThermostat",
            "state": {"on": True, "temperature": 2260, "valve": 30},
            "config": {
                "battery": 100,
                "heatsetpoint": 2200,
                "mode": "auto",
                "offset": 10,
                "reachable": True,
            },
            "uniqueid": "00:00:00:00:00:00:00:00-00",
        }
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_verify_state_update(
    hass: HomeAssistant,
    sensor_ws_data: WebsocketDataType,
) -> None:

    assert hass.states.get("climate.thermostat").state == HVACMode.AUTO
    assert (
        hass.states.get("climate.thermostat").attributes["hvac_action"]
        == HVACAction.HEATING
    )

    await sensor_ws_data({"state": {"on": False}})
    assert hass.states.get("climate.thermostat").state == HVACMode.AUTO
    assert (
        hass.states.get("climate.thermostat").attributes["hvac_action"]
        == HVACAction.IDLE
    )


@pytest.mark.usefixtures("config_entry_setup")
async def test_add_new_climate_device(
    hass: HomeAssistant,
    sensor_ws_data: WebsocketDataType,
) -> None:

    event_added_sensor = {
        "e": "added",
        "sensor": {
            "id": "Thermostat id",
            "name": "Thermostat",
            "type": "ZHAThermostat",
            "state": {"on": True, "temperature": 2260, "valve": 30},
            "config": {
                "battery": 100,
                "heatsetpoint": 2200,
                "mode": "auto",
                "offset": 10,
                "reachable": True,
            },
            "uniqueid": "00:00:00:00:00:00:00:00-00",
        },
    }

    assert len(hass.states.async_all()) == 0

    await sensor_ws_data(event_added_sensor)

    assert len(hass.states.async_all()) == 2
    assert hass.states.get("climate.thermostat").state == HVACMode.AUTO
    assert hass.states.get("sensor.thermostat_battery").state == "100"
    assert (
        hass.states.get("climate.thermostat").attributes["hvac_action"]
        == HVACAction.HEATING
    )


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "name": "CLIP thermostat sensor",
            "type": "CLIPThermostat",
            "state": {},
            "config": {},
            "uniqueid": "00:00:00:00:00:00:00:00-00",
        },
    ],
)
@pytest.mark.parametrize("config_entry_options", [{CONF_ALLOW_CLIP_SENSOR: False}])
@pytest.mark.usefixtures("config_entry_setup")
async def test_not_allow_clip_thermostat(hass: HomeAssistant) -> None:

    assert len(hass.states.async_all()) == 0


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "config": {
                "battery": 25,
                "heatsetpoint": 2222,
                "mode": None,
                "preset": "auto",
                "offset": 0,
                "on": True,
                "reachable": True,
            },
            "ep": 1,
            "etag": "074549903686a77a12ef0f06c499b1ef",
            "lastseen": "2020-11-27T13:45Z",
            "manufacturername": "Zen Within",
            "modelid": "Zen-01",
            "name": "Zen-01",
            "state": {"lastupdated": "none", "on": None, "temperature": 2290},
            "type": "ZHAThermostat",
            "uniqueid": "00:24:46:00:00:11:6f:56-01-0201",
        }
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_no_mode_no_state(hass: HomeAssistant) -> None:

    assert len(hass.states.async_all()) == 2

    climate_thermostat = hass.states.get("climate.zen_01")
    assert climate_thermostat.state is STATE_OFF
    assert climate_thermostat.attributes["preset_mode"] is DECONZ_PRESET_AUTO
    assert climate_thermostat.attributes["hvac_action"] is HVACAction.IDLE


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "config": {
                "battery": 58,
                "heatsetpoint": 2200,
                "locked": False,
                "mode": "heat",
                "offset": -200,
                "on": True,
                "preset": "manual",
                "reachable": True,
                "schedule": {},
                "schedule_on": False,
                "setvalve": False,
                "windowopen_set": False,
            },
            "ep": 1,
            "etag": "404c15db68c318ebe7832ce5aa3d1e30",
            "lastannounced": "2022-08-31T03:00:59Z",
            "lastseen": "2022-09-19T11:58Z",
            "manufacturername": "_TZE200_b6wax7g0",
            "modelid": "TS0601",
            "name": "Thermostat",
            "state": {
                "lastupdated": "2022-09-19T11:58:24.204",
                "lowbattery": False,
                "on": False,
                "temperature": 2200,
                "valve": 0,
            },
            "type": "ZHAThermostat",
            "uniqueid": "84:fd:27:ff:fe:8a:eb:89-01-0201",
        }
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_boost_mode(
    hass: HomeAssistant,
    sensor_ws_data: WebsocketDataType,
) -> None:

    assert len(hass.states.async_all()) == 3

    climate_thermostat = hass.states.get("climate.thermostat")
    assert climate_thermostat.state == HVACMode.HEAT
    assert climate_thermostat.attributes["preset_mode"] is DECONZ_PRESET_MANUAL
    assert climate_thermostat.attributes["hvac_action"] is HVACAction.IDLE



    await sensor_ws_data({"config": {"preset": "boost"}, "state": {"valve": 100}})

    climate_thermostat = hass.states.get("climate.thermostat")
    assert climate_thermostat.attributes["preset_mode"] is PRESET_BOOST
    assert climate_thermostat.attributes["hvac_action"] is HVACAction.HEATING
