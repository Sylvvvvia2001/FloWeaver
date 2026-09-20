

from unittest.mock import Mock, patch

from aioesphomeapi import (
    APIClient,
    EntityCategory as ESPHomeEntityCategory,
    EntityInfo,
    SensorInfo,
    SensorState,
)
import pytest

from homeassistant.components.esphome import DOMAIN
from homeassistant.components.esphome.entry_data import RuntimeEntryData
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery_flow, entity_registry as er
from homeassistant.helpers.service_info.esphome import ESPHomeServiceInfo

from .conftest import MockGenericDeviceEntryType


async def test_migrate_entity_unique_id_downgrade_upgrade(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:

    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "my_sensor",
        suggested_object_id="old_sensor",
        disabled_by=None,
    )
    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "11:22:33:44:55:AA-sensor-mysensor",
        suggested_object_id="new_sensor",
        disabled_by=None,
    )
    entity_info = [
        SensorInfo(
            object_id="mysensor",
            key=1,
            name="my sensor",
            entity_category=ESPHomeEntityCategory.DIAGNOSTIC,
            icon="mdi:leaf",
        )
    ]
    states = [SensorState(key=1, state=50)]
    user_service = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = hass.states.get("sensor.new_sensor")
    assert state is not None
    assert state.state == "50"
    entry = entity_registry.async_get("sensor.new_sensor")
    assert entry is not None




    assert (
        entity_registry.async_get_entity_id(SENSOR_DOMAIN, DOMAIN, "my_sensor")
        is not None
    )


    assert entry.unique_id == "11:22:33:44:55:AA-sensor-mysensor"


async def test_discover_zwave() -> None:

    hass = Mock()
    entry_data = RuntimeEntryData(
        "mock-id",
        "mock-title",
        Mock(
            connected_address="mock-client-address",
            port=1234,
            noise_psk=None,
        ),
        None,
    )
    device_info = Mock(
        mac_address="mock-device-info-mac",
        zwave_proxy_feature_flags=1,
        zwave_home_id=1234,
    )
    device_info.name = "mock-device-infoname"

    with patch(
        "homeassistant.helpers.discovery_flow.async_create_flow"
    ) as mock_create_flow:
        entry_data.async_on_connect(
            hass,
            device_info,
            None,
        )
        mock_create_flow.assert_called_once_with(
            hass,
            "zwave_js",
            {"source": "esphome"},
            ESPHomeServiceInfo(
                name="mock-device-infoname",
                zwave_home_id=1234,
                ip_address="mock-client-address",
                port=1234,
                noise_psk=None,
            ),
            discovery_key=discovery_flow.DiscoveryKey(
                domain="esphome",
                key="mock-device-info-mac",
                version=1,
            ),
        )


async def test_discover_zwave_without_home_id() -> None:

    hass = Mock()
    entry_data = RuntimeEntryData(
        "mock-id",
        "mock-title",
        Mock(
            connected_address="mock-client-address",
            port=1234,
            noise_psk=None,
        ),
        None,
    )
    device_info = Mock(
        mac_address="mock-device-info-mac",
        zwave_proxy_feature_flags=1,
        zwave_home_id=0,
    )
    device_info.name = "mock-device-infoname"

    with patch(
        "homeassistant.helpers.discovery_flow.async_create_flow"
    ) as mock_create_flow:
        entry_data.async_on_connect(
            hass,
            device_info,
            None,
        )

        mock_create_flow.assert_not_called()


async def test_unknown_entity_type_skipped(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
    caplog: pytest.LogCaptureFixture,
) -> None:


    class UnknownInfo(EntityInfo):
        pass

    entity_info = [
        SensorInfo(
            object_id="mysensor",
            key=1,
            name="my sensor",
        ),
        UnknownInfo(
            object_id="unknown",
            key=2,
            name="unknown entity",
        ),
    ]
    states = [SensorState(key=1, state=42)]
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        states=states,
    )

    assert "UnknownInfo" in caplog.text
    assert "not supported in this version of Home Assistant" in caplog.text


    state = hass.states.get("sensor.test_my_sensor")
    assert state is not None
    assert state.state == "42"
