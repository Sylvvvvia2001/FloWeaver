

from datetime import timedelta
import time
from typing import Any
from unittest.mock import patch

from bleak.backends.scanner import AdvertisementData, BLEDevice
from bluetooth_adapters import AdvertisementHistory
from freezegun import freeze_time
from habluetooth import BluetoothScanningMode, HaScanner


from habluetooth.advertisement_tracker import TRACKER_BUFFERING_WOBBLE_SECONDS
import pytest

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
    MONOTONIC_TIME,
    BaseHaRemoteScanner,
    BluetoothChange,
    BluetoothServiceInfo,
    BluetoothServiceInfoBleak,
    HaBluetoothConnector,
    async_ble_device_from_address,
    async_get_fallback_availability_interval,
    async_get_learned_advertising_interval,
    async_scanner_count,
    async_set_fallback_availability_interval,
    async_track_unavailable,
    storage,
)
from homeassistant.components.bluetooth.const import (
    SOURCE_LOCAL,
    UNAVAILABLE_TRACK_SECONDS,
)
from homeassistant.components.bluetooth.manager import HomeAssistantBluetoothManager
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.discovery_flow import DiscoveryKey
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.dt import utcnow
from homeassistant.util.json import json_loads

from . import (
    HCI0_SOURCE_ADDRESS,
    HCI1_SOURCE_ADDRESS,
    FakeRemoteScanner,
    FakeScanner,
    MockBleakClient,
    _get_manager,
    generate_advertisement_data,
    generate_ble_device,
    inject_advertisement_with_source,
    inject_advertisement_with_time_and_source,
    inject_advertisement_with_time_and_source_connectable,
    patch_bluetooth_time,
)

from tests.common import (
    MockConfigEntry,
    MockModule,
    async_call_logger_set_level,
    async_fire_time_changed,
    async_load_fixture,
    mock_integration,
)


@pytest.mark.usefixtures("enable_bluetooth")
async def test_advertisements_do_not_switch_adapters_for_no_reason(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
) -> None:


    address = "44:44:33:11:23:12"

    switchbot_device_signal_100 = generate_ble_device(address, "wohand_signal_100")
    switchbot_adv_signal_100 = generate_advertisement_data(
        local_name="wohand_signal_100", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_source(
        hass, switchbot_device_signal_100, switchbot_adv_signal_100, HCI0_SOURCE_ADDRESS
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_signal_100
    )

    switchbot_device_signal_99 = generate_ble_device(address, "wohand_signal_99")
    switchbot_adv_signal_99 = generate_advertisement_data(
        local_name="wohand_signal_99", service_uuids=[], rssi=-99
    )
    inject_advertisement_with_source(
        hass, switchbot_device_signal_99, switchbot_adv_signal_99, HCI0_SOURCE_ADDRESS
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_signal_99
    )

    switchbot_device_signal_98 = generate_ble_device(address, "wohand_good_signal")
    switchbot_adv_signal_98 = generate_advertisement_data(
        local_name="wohand_good_signal", service_uuids=[], rssi=-98
    )
    inject_advertisement_with_source(
        hass, switchbot_device_signal_98, switchbot_adv_signal_98, HCI1_SOURCE_ADDRESS
    )


    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_signal_99
    )


@pytest.mark.usefixtures("enable_bluetooth")
async def test_switching_adapters_based_on_rssi(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
) -> None:


    address = "44:44:33:11:23:45"

    switchbot_device_poor_signal = generate_ble_device(address, "wohand_poor_signal")
    switchbot_adv_poor_signal = generate_advertisement_data(
        local_name="wohand_poor_signal", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_source(
        hass,
        switchbot_device_poor_signal,
        switchbot_adv_poor_signal,
        HCI0_SOURCE_ADDRESS,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal
    )

    switchbot_device_good_signal = generate_ble_device(address, "wohand_good_signal")
    switchbot_adv_good_signal = generate_advertisement_data(
        local_name="wohand_good_signal", service_uuids=[], rssi=-60
    )
    inject_advertisement_with_source(
        hass,
        switchbot_device_good_signal,
        switchbot_adv_good_signal,
        HCI1_SOURCE_ADDRESS,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )

    inject_advertisement_with_source(
        hass,
        switchbot_device_good_signal,
        switchbot_adv_poor_signal,
        HCI0_SOURCE_ADDRESS,
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )


    switchbot_device_similar_signal = generate_ble_device(
        address, "wohand_similar_signal"
    )
    switchbot_adv_similar_signal = generate_advertisement_data(
        local_name="wohand_similar_signal", service_uuids=[], rssi=-62
    )

    inject_advertisement_with_source(
        hass,
        switchbot_device_similar_signal,
        switchbot_adv_similar_signal,
        HCI0_SOURCE_ADDRESS,
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )


@pytest.mark.usefixtures("enable_bluetooth")
async def test_switching_adapters_based_on_zero_rssi(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
) -> None:


    address = "44:44:33:11:23:45"

    switchbot_device_no_rssi = generate_ble_device(address, "wohand_poor_signal")
    switchbot_adv_no_rssi = generate_advertisement_data(
        local_name="wohand_no_rssi", service_uuids=[], rssi=0
    )
    inject_advertisement_with_source(
        hass, switchbot_device_no_rssi, switchbot_adv_no_rssi, HCI0_SOURCE_ADDRESS
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_no_rssi
    )

    switchbot_device_good_signal = generate_ble_device(address, "wohand_good_signal")
    switchbot_adv_good_signal = generate_advertisement_data(
        local_name="wohand_good_signal", service_uuids=[], rssi=-60
    )
    inject_advertisement_with_source(
        hass,
        switchbot_device_good_signal,
        switchbot_adv_good_signal,
        HCI1_SOURCE_ADDRESS,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )

    inject_advertisement_with_source(
        hass, switchbot_device_good_signal, switchbot_adv_no_rssi, HCI0_SOURCE_ADDRESS
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )


    switchbot_device_similar_signal = generate_ble_device(
        address, "wohand_similar_signal"
    )
    switchbot_adv_similar_signal = generate_advertisement_data(
        local_name="wohand_similar_signal", service_uuids=[], rssi=-62
    )

    inject_advertisement_with_source(
        hass,
        switchbot_device_similar_signal,
        switchbot_adv_similar_signal,
        HCI0_SOURCE_ADDRESS,
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )


@pytest.mark.usefixtures("enable_bluetooth")
async def test_switching_adapters_based_on_stale(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
) -> None:


    address = "44:44:33:11:23:41"
    start_time_monotonic = 50.0

    switchbot_device_poor_signal_hci0 = generate_ble_device(
        address, "wohand_poor_signal_hci0"
    )
    switchbot_adv_poor_signal_hci0 = generate_advertisement_data(
        local_name="wohand_poor_signal_hci0", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device_poor_signal_hci0,
        switchbot_adv_poor_signal_hci0,
        start_time_monotonic,
        HCI0_SOURCE_ADDRESS,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal_hci0
    )

    switchbot_device_poor_signal_hci1 = generate_ble_device(
        address, "wohand_poor_signal_hci1"
    )
    switchbot_adv_poor_signal_hci1 = generate_advertisement_data(
        local_name="wohand_poor_signal_hci1", service_uuids=[], rssi=-99
    )
    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device_poor_signal_hci1,
        switchbot_adv_poor_signal_hci1,
        start_time_monotonic,
        HCI1_SOURCE_ADDRESS,
    )


    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal_hci0
    )




    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device_poor_signal_hci1,
        switchbot_adv_poor_signal_hci1,
        start_time_monotonic + FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 1,
        "hci1",
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal_hci1
    )


@pytest.mark.usefixtures("enable_bluetooth")
async def test_switching_adapters_based_on_stale_with_discovered_interval(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
) -> None:


    address = "44:44:33:11:23:41"
    start_time_monotonic = 50.0

    switchbot_device_poor_signal_hci0 = generate_ble_device(
        address, "wohand_poor_signal_hci0"
    )
    switchbot_adv_poor_signal_hci0 = generate_advertisement_data(
        local_name="wohand_poor_signal_hci0", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device_poor_signal_hci0,
        switchbot_adv_poor_signal_hci0,
        start_time_monotonic,
        HCI0_SOURCE_ADDRESS,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal_hci0
    )

    bluetooth.async_set_fallback_availability_interval(hass, address, 10)

    switchbot_device_poor_signal_hci1 = generate_ble_device(
        address, "wohand_poor_signal_hci1"
    )
    switchbot_adv_poor_signal_hci1 = generate_advertisement_data(
        local_name="wohand_poor_signal_hci1", service_uuids=[], rssi=-99
    )
    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device_poor_signal_hci1,
        switchbot_adv_poor_signal_hci1,
        start_time_monotonic,
        HCI1_SOURCE_ADDRESS,
    )


    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal_hci0
    )

    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device_poor_signal_hci1,
        switchbot_adv_poor_signal_hci1,
        start_time_monotonic + 10 + 1,
        HCI1_SOURCE_ADDRESS,
    )



    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal_hci0
    )

    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device_poor_signal_hci1,
        switchbot_adv_poor_signal_hci1,
        start_time_monotonic + 10 + TRACKER_BUFFERING_WOBBLE_SECONDS + 1,
        HCI1_SOURCE_ADDRESS,
    )



    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal_hci1
    )


@pytest.mark.usefixtures("one_adapter")
async def test_restore_history_from_dbus(
    hass: HomeAssistant, disable_new_discovery_flows
) -> None:

    address = "AA:BB:CC:CC:CC:FF"

    ble_device = generate_ble_device(address, "name")
    history = {
        address: AdvertisementHistory(
            ble_device,
            generate_advertisement_data(local_name="name"),
            "hci0",
        )
    }

    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        history,
    ):
        assert await async_setup_component(hass, bluetooth.DOMAIN, {})
        await hass.async_block_till_done()

    assert bluetooth.async_ble_device_from_address(hass, address) is ble_device
    info = bluetooth.async_last_service_info(hass, address, False)
    assert info.source == "00:00:00:00:00:01"


@pytest.mark.usefixtures("one_adapter")
async def test_restore_history_from_dbus_and_remote_adapters(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    disable_new_discovery_flows,
) -> None:

    address = "AA:BB:CC:CC:CC:FF"

    data = hass_storage[storage.REMOTE_SCANNER_STORAGE_KEY] = json_loads(
        await async_load_fixture(hass, "bluetooth.remote_scanners", bluetooth.DOMAIN)
    )
    now = time.time()
    timestamps = data["data"]["atom-bluetooth-proxy-ceaac4"][
        "discovered_device_timestamps"
    ]
    for address in timestamps:
        timestamps[address] = now

    ble_device = generate_ble_device(address, "name")
    history = {
        address: AdvertisementHistory(
            ble_device,
            generate_advertisement_data(local_name="name"),
            HCI0_SOURCE_ADDRESS,
        )
    }

    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        history,
    ):
        assert await async_setup_component(hass, bluetooth.DOMAIN, {})
        await hass.async_block_till_done()

    assert bluetooth.async_ble_device_from_address(hass, address) is not None
    assert (
        bluetooth.async_ble_device_from_address(hass, "EB:0B:36:35:6F:A4") is not None
    )
    assert disable_new_discovery_flows.call_count > 1


@pytest.mark.usefixtures("one_adapter")
async def test_restore_history_from_dbus_and_corrupted_remote_adapters(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    disable_new_discovery_flows,
) -> None:

    address = "AA:BB:CC:CC:CC:FF"

    data = hass_storage[storage.REMOTE_SCANNER_STORAGE_KEY] = json_loads(
        await async_load_fixture(
            hass, "bluetooth.remote_scanners.corrupt", bluetooth.DOMAIN
        )
    )
    now = time.time()
    timestamps = data["data"]["atom-bluetooth-proxy-ceaac4"][
        "discovered_device_timestamps"
    ]
    for address in timestamps:
        timestamps[address] = now

    ble_device = generate_ble_device(address, "name")
    history = {
        address: AdvertisementHistory(
            ble_device,
            generate_advertisement_data(local_name="name"),
            HCI0_SOURCE_ADDRESS,
        )
    }

    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        history,
    ):
        assert await async_setup_component(hass, bluetooth.DOMAIN, {})
        await hass.async_block_till_done()

    assert bluetooth.async_ble_device_from_address(hass, address) is not None
    assert bluetooth.async_ble_device_from_address(hass, "EB:0B:36:35:6F:A4") is None
    assert disable_new_discovery_flows.call_count >= 1


@pytest.mark.usefixtures("enable_bluetooth")
async def test_switching_adapters_based_on_rssi_connectable_to_non_connectable(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
) -> None:


    address = "44:44:33:11:23:45"
    now = time.monotonic()
    switchbot_device_poor_signal = generate_ble_device(address, "wohand_poor_signal")
    switchbot_adv_poor_signal = generate_advertisement_data(
        local_name="wohand_poor_signal", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_time_and_source_connectable(
        hass,
        switchbot_device_poor_signal,
        switchbot_adv_poor_signal,
        now,
        HCI0_SOURCE_ADDRESS,
        True,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address, False)
        is switchbot_device_poor_signal
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address, True)
        is switchbot_device_poor_signal
    )
    switchbot_device_good_signal = generate_ble_device(address, "wohand_good_signal")
    switchbot_adv_good_signal = generate_advertisement_data(
        local_name="wohand_good_signal", service_uuids=[], rssi=-60
    )
    inject_advertisement_with_time_and_source_connectable(
        hass,
        switchbot_device_good_signal,
        switchbot_adv_good_signal,
        now,
        "hci1",
        False,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address, False)
        is switchbot_device_good_signal
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address, True)
        is switchbot_device_poor_signal
    )
    inject_advertisement_with_time_and_source_connectable(
        hass,
        switchbot_device_good_signal,
        switchbot_adv_poor_signal,
        now,
        "hci0",
        False,
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address, False)
        is switchbot_device_good_signal
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address, True)
        is switchbot_device_poor_signal
    )
    switchbot_device_excellent_signal = generate_ble_device(
        address, "wohand_excellent_signal"
    )
    switchbot_adv_excellent_signal = generate_advertisement_data(
        local_name="wohand_excellent_signal", service_uuids=[], rssi=-25
    )

    inject_advertisement_with_time_and_source_connectable(
        hass,
        switchbot_device_excellent_signal,
        switchbot_adv_excellent_signal,
        now,
        "hci2",
        False,
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address, False)
        is switchbot_device_excellent_signal
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address, True)
        is switchbot_device_poor_signal
    )


@pytest.mark.usefixtures("enable_bluetooth")
async def test_connectable_advertisement_can_be_retrieved_with_best_path_is_non_connectable(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
) -> None:






    address = "44:44:33:11:23:45"
    now = time.monotonic()
    switchbot_device_good_signal = generate_ble_device(address, "wohand_good_signal")
    switchbot_adv_good_signal = generate_advertisement_data(
        local_name="wohand_good_signal", service_uuids=[], rssi=-60
    )
    inject_advertisement_with_time_and_source_connectable(
        hass,
        switchbot_device_good_signal,
        switchbot_adv_good_signal,
        now,
        HCI1_SOURCE_ADDRESS,
        False,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address, False)
        is switchbot_device_good_signal
    )
    assert bluetooth.async_ble_device_from_address(hass, address, True) is None

    switchbot_device_poor_signal = generate_ble_device(address, "wohand_poor_signal")
    switchbot_adv_poor_signal = generate_advertisement_data(
        local_name="wohand_poor_signal", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_time_and_source_connectable(
        hass,
        switchbot_device_poor_signal,
        switchbot_adv_poor_signal,
        now,
        HCI0_SOURCE_ADDRESS,
        True,
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address, False)
        is switchbot_device_good_signal
    )
    assert (
        bluetooth.async_ble_device_from_address(hass, address, True)
        is switchbot_device_poor_signal
    )


@pytest.mark.usefixtures("enable_bluetooth")
async def test_switching_adapters_when_one_goes_away(
    hass: HomeAssistant, register_hci0_scanner: None
) -> None:

    cancel_hci2 = bluetooth.async_register_scanner(hass, FakeScanner("hci2", "hci2"))

    address = "44:44:33:11:23:45"

    switchbot_device_good_signal = generate_ble_device(address, "wohand_good_signal")
    switchbot_adv_good_signal = generate_advertisement_data(
        local_name="wohand_good_signal", service_uuids=[], rssi=-60
    )
    inject_advertisement_with_source(
        hass, switchbot_device_good_signal, switchbot_adv_good_signal, "hci2"
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )

    switchbot_device_poor_signal = generate_ble_device(address, "wohand_poor_signal")
    switchbot_adv_poor_signal = generate_advertisement_data(
        local_name="wohand_poor_signal", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_source(
        hass,
        switchbot_device_poor_signal,
        switchbot_adv_poor_signal,
        HCI0_SOURCE_ADDRESS,
    )


    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )

    cancel_hci2()

    inject_advertisement_with_source(
        hass,
        switchbot_device_poor_signal,
        switchbot_adv_poor_signal,
        HCI0_SOURCE_ADDRESS,
    )



    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal
    )


@pytest.mark.usefixtures("enable_bluetooth")
async def test_switching_adapters_when_one_stop_scanning(
    hass: HomeAssistant, register_hci0_scanner: None
) -> None:

    hci2_scanner = FakeScanner("hci2", "hci2")
    cancel_hci2 = bluetooth.async_register_scanner(hass, hci2_scanner)

    address = "44:44:33:11:23:45"

    switchbot_device_good_signal = generate_ble_device(address, "wohand_good_signal")
    switchbot_adv_good_signal = generate_advertisement_data(
        local_name="wohand_good_signal", service_uuids=[], rssi=-60
    )
    inject_advertisement_with_source(
        hass, switchbot_device_good_signal, switchbot_adv_good_signal, "hci2"
    )

    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )

    switchbot_device_poor_signal = generate_ble_device(address, "wohand_poor_signal")
    switchbot_adv_poor_signal = generate_advertisement_data(
        local_name="wohand_poor_signal", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_source(
        hass,
        switchbot_device_poor_signal,
        switchbot_adv_poor_signal,
        HCI0_SOURCE_ADDRESS,
    )


    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_good_signal
    )

    hci2_scanner.scanning = False

    inject_advertisement_with_source(
        hass,
        switchbot_device_poor_signal,
        switchbot_adv_poor_signal,
        HCI0_SOURCE_ADDRESS,
    )



    assert (
        bluetooth.async_ble_device_from_address(hass, address)
        is switchbot_device_poor_signal
    )

    cancel_hci2()


@pytest.mark.usefixtures("mock_bluetooth_adapters")
async def test_goes_unavailable_connectable_only_and_recovers(
    hass: HomeAssistant,
) -> None:

    assert await async_setup_component(hass, bluetooth.DOMAIN, {})
    await hass.async_block_till_done()

    assert async_scanner_count(hass, connectable=True) == 0
    assert async_scanner_count(hass, connectable=False) == 0
    switchbot_device_connectable = generate_ble_device(
        "44:44:33:11:23:45",
        "wohand",
        {},
    )
    switchbot_device_non_connectable = generate_ble_device(
        "44:44:33:11:23:45",
        "wohand",
        {},
    )
    switchbot_device_adv = generate_advertisement_data(
        local_name="wohand",
        service_uuids=["050a021a-0000-1000-8000-00805f9b34fb"],
        service_data={"050a021a-0000-1000-8000-00805f9b34fb": b"\n\xff"},
        manufacturer_data={1: b"\x01"},
        rssi=-100,
    )
    callbacks = []

    def _fake_subscriber(
        service_info: BluetoothServiceInfo,
        change: BluetoothChange,
    ) -> None:

        callbacks.append((service_info, change))

    cancel = bluetooth.async_register_callback(
        hass,
        _fake_subscriber,
        {"address": "44:44:33:11:23:45", "connectable": True},
        BluetoothScanningMode.ACTIVE,
    )

    class FakeScanner(BaseHaRemoteScanner):
        def inject_advertisement(
            self, device: BLEDevice, advertisement_data: AdvertisementData
        ) -> None:

            self._async_on_advertisement(
                device.address,
                advertisement_data.rssi,
                device.name,
                advertisement_data.service_uuids,
                advertisement_data.service_data,
                advertisement_data.manufacturer_data,
                advertisement_data.tx_power,
                {"scanner_specific_data": "test"},
                MONOTONIC_TIME(),
            )

    connector = (
        HaBluetoothConnector(MockBleakClient, "mock_bleak_client", lambda: False),
    )
    connectable_scanner = FakeScanner(
        "connectable",
        "connectable",
        connector,
        True,
    )
    unsetup_connectable_scanner = connectable_scanner.async_setup()
    cancel_connectable_scanner = _get_manager().async_register_scanner(
        connectable_scanner
    )
    connectable_scanner.inject_advertisement(
        switchbot_device_connectable, switchbot_device_adv
    )
    assert async_ble_device_from_address(hass, "44:44:33:11:23:45") is not None
    assert async_scanner_count(hass, connectable=True) == 1
    assert len(callbacks) == 1

    assert (
        "44:44:33:11:23:45"
        in connectable_scanner.discovered_devices_and_advertisement_data
    )

    not_connectable_scanner = FakeScanner(
        "not_connectable",
        "not_connectable",
        connector,
        False,
    )
    unsetup_not_connectable_scanner = not_connectable_scanner.async_setup()
    cancel_not_connectable_scanner = _get_manager().async_register_scanner(
        not_connectable_scanner
    )
    not_connectable_scanner.inject_advertisement(
        switchbot_device_non_connectable, switchbot_device_adv
    )
    assert async_scanner_count(hass, connectable=True) == 1
    assert async_scanner_count(hass, connectable=False) == 2

    assert (
        "44:44:33:11:23:45"
        in not_connectable_scanner.discovered_devices_and_advertisement_data
    )

    unavailable_callbacks: list[BluetoothServiceInfoBleak] = []

    @callback
    def _unavailable_callback(service_info: BluetoothServiceInfoBleak) -> None:

        nonlocal unavailable_callbacks
        unavailable_callbacks.append(service_info.address)

    cancel_unavailable = async_track_unavailable(
        hass,
        _unavailable_callback,
        switchbot_device_connectable.address,
        connectable=True,
    )

    assert async_scanner_count(hass, connectable=True) == 1
    cancel_connectable_scanner()
    unsetup_connectable_scanner()
    assert async_scanner_count(hass, connectable=True) == 0
    assert async_scanner_count(hass, connectable=False) == 1

    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=UNAVAILABLE_TRACK_SECONDS)
    )
    await hass.async_block_till_done()
    assert "44:44:33:11:23:45" in unavailable_callbacks
    cancel_unavailable()

    connectable_scanner_2 = FakeScanner(
        "connectable",
        "connectable",
        connector,
        True,
    )
    unsetup_connectable_scanner_2 = connectable_scanner_2.async_setup()
    cancel_connectable_scanner_2 = _get_manager().async_register_scanner(
        connectable_scanner
    )
    connectable_scanner_2.inject_advertisement(
        switchbot_device_connectable, switchbot_device_adv
    )
    assert (
        "44:44:33:11:23:45"
        in connectable_scanner_2.discovered_devices_and_advertisement_data
    )


    assert len(callbacks) == 2

    cancel()
    cancel_connectable_scanner_2()
    unsetup_connectable_scanner_2()
    cancel_not_connectable_scanner()
    unsetup_not_connectable_scanner()


@pytest.mark.usefixtures("mock_bluetooth_adapters")
async def test_goes_unavailable_dismisses_discovery_and_makes_discoverable(
    hass: HomeAssistant,
) -> None:

    mock_bt = [
        {
            "domain": "switchbot",
            "service_data_uuid": "050a021a-0000-1000-8000-00805f9b34fb",
            "connectable": False,
        },
    ]
    with patch(
        "homeassistant.components.bluetooth.async_get_bluetooth", return_value=mock_bt
    ):
        assert await async_setup_component(hass, bluetooth.DOMAIN, {})
        await hass.async_block_till_done()

    assert async_scanner_count(hass, connectable=False) == 0
    switchbot_device_non_connectable = generate_ble_device(
        "44:44:33:11:23:45",
        "wohand",
        {},
    )
    switchbot_device_adv = generate_advertisement_data(
        local_name="wohand",
        service_uuids=["050a021a-0000-1000-8000-00805f9b34fb"],
        service_data={"050a021a-0000-1000-8000-00805f9b34fb": b"\n\xff"},
        manufacturer_data={1: b"\x01"},
        rssi=-100,
    )
    callbacks = []

    def _fake_subscriber(
        service_info: BluetoothServiceInfo,
        change: BluetoothChange,
    ) -> None:

        callbacks.append((service_info, change))

    cancel = bluetooth.async_register_callback(
        hass,
        _fake_subscriber,
        {"address": "44:44:33:11:23:45", "connectable": False},
        BluetoothScanningMode.ACTIVE,
    )

    class FakeScanner(BaseHaRemoteScanner):
        def inject_advertisement(
            self, device: BLEDevice, advertisement_data: AdvertisementData
        ) -> None:

            self._async_on_advertisement(
                device.address,
                advertisement_data.rssi,
                device.name,
                advertisement_data.service_uuids,
                advertisement_data.service_data,
                advertisement_data.manufacturer_data,
                advertisement_data.tx_power,
                {"scanner_specific_data": "test"},
                MONOTONIC_TIME(),
            )

        def clear_all_devices(self) -> None:

            self._previous_service_info.clear()

    connector = (
        HaBluetoothConnector(MockBleakClient, "mock_bleak_client", lambda: False),
    )
    non_connectable_scanner = FakeScanner(
        "connectable",
        "connectable",
        connector,
        False,
    )
    unsetup_connectable_scanner = non_connectable_scanner.async_setup()
    cancel_connectable_scanner = _get_manager().async_register_scanner(
        non_connectable_scanner
    )
    with patch.object(hass.config_entries.flow, "async_init") as mock_config_flow:
        non_connectable_scanner.inject_advertisement(
            switchbot_device_non_connectable, switchbot_device_adv
        )
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 1
    assert mock_config_flow.mock_calls[0][1][0] == "switchbot"
    assert mock_config_flow.mock_calls[0][2]["context"] == {
        "discovery_key": DiscoveryKey(
            domain="bluetooth", key="44:44:33:11:23:45", version=1
        ),
        "source": "bluetooth",
    }

    assert async_ble_device_from_address(hass, "44:44:33:11:23:45", False) is not None
    assert async_scanner_count(hass, connectable=False) == 1
    assert len(callbacks) == 1

    assert (
        "44:44:33:11:23:45"
        in non_connectable_scanner.discovered_devices_and_advertisement_data
    )

    unavailable_callbacks: list[BluetoothServiceInfoBleak] = []

    @callback
    def _unavailable_callback(service_info: BluetoothServiceInfoBleak) -> None:

        nonlocal unavailable_callbacks
        unavailable_callbacks.append(service_info.address)

    cancel_unavailable = async_track_unavailable(
        hass,
        _unavailable_callback,
        switchbot_device_non_connectable.address,
        connectable=False,
    )

    assert async_scanner_count(hass, connectable=False) == 1

    non_connectable_scanner.clear_all_devices()
    assert (
        "44:44:33:11:23:45"
        not in non_connectable_scanner.discovered_devices_and_advertisement_data
    )
    monotonic_now = time.monotonic()
    with (
        patch.object(
            hass.config_entries.flow,
            "async_progress_by_init_data_type",
            return_value=[{"flow_id": "mock_flow_id"}],
        ) as mock_async_progress_by_init_data_type,
        patch.object(hass.config_entries.flow, "async_abort") as mock_async_abort,
        patch_bluetooth_time(
            monotonic_now + FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
        ),
    ):
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=UNAVAILABLE_TRACK_SECONDS)
        )
    await hass.async_block_till_done()
    assert "44:44:33:11:23:45" in unavailable_callbacks

    assert len(mock_async_progress_by_init_data_type.mock_calls) == 1
    assert mock_async_abort.mock_calls[0][1][0] == "mock_flow_id"


    with patch.object(hass.config_entries.flow, "async_init") as mock_config_flow:
        new_switchbot_device_adv = generate_advertisement_data(
            local_name="wohand",
            service_uuids=["050a021a-0000-1000-8000-00805f9b34fb"],
            service_data={"050a021a-0000-1000-8000-00805f9b34fb": b"\n\xff"},
            manufacturer_data={1: b"\x01"},
            rssi=-60,
        )
        non_connectable_scanner.inject_advertisement(
            switchbot_device_non_connectable, new_switchbot_device_adv
        )
        await hass.async_block_till_done()

    assert (
        "44:44:33:11:23:45"
        in non_connectable_scanner.discovered_devices_and_advertisement_data
    )
    assert len(mock_config_flow.mock_calls) == 1
    assert mock_config_flow.mock_calls[0][1][0] == "switchbot"
    assert mock_config_flow.mock_calls[0][2]["context"] == {
        "discovery_key": DiscoveryKey(
            domain="bluetooth", key="44:44:33:11:23:45", version=1
        ),
        "source": "bluetooth",
    }

    cancel_unavailable()

    cancel()
    unsetup_connectable_scanner()
    cancel_connectable_scanner()


@pytest.mark.usefixtures("enable_bluetooth")
async def test_debug_logging(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
    caplog: pytest.LogCaptureFixture,
) -> None:

    assert await async_setup_component(hass, "logger", {"logger": {}})
    async with async_call_logger_set_level(
        "homeassistant.components.bluetooth", "DEBUG", hass=hass, caplog=caplog
    ):
        address = "44:44:33:11:23:41"
        start_time_monotonic = 50.0

        switchbot_device_poor_signal_hci0 = generate_ble_device(
            address, "wohand_poor_signal_hci0"
        )
        switchbot_adv_poor_signal_hci0 = generate_advertisement_data(
            local_name="wohand_poor_signal_hci0", service_uuids=[], rssi=-100
        )
        inject_advertisement_with_time_and_source(
            hass,
            switchbot_device_poor_signal_hci0,
            switchbot_adv_poor_signal_hci0,
            start_time_monotonic,
            "hci0",
        )
        assert "wohand_poor_signal_hci0" in caplog.text
        caplog.clear()

    async with async_call_logger_set_level(
        "homeassistant.components.bluetooth", "WARNING", hass=hass, caplog=caplog
    ):
        switchbot_device_good_signal_hci0 = generate_ble_device(
            address, "wohand_good_signal_hci0"
        )
        switchbot_adv_good_signal_hci0 = generate_advertisement_data(
            local_name="wohand_good_signal_hci0", service_uuids=[], rssi=-33
        )
        inject_advertisement_with_time_and_source(
            hass,
            switchbot_device_good_signal_hci0,
            switchbot_adv_good_signal_hci0,
            start_time_monotonic,
            "hci0",
        )
        assert "wohand_good_signal_hci0" not in caplog.text


@pytest.mark.usefixtures("enable_bluetooth", "macos_adapter")
async def test_set_fallback_interval_small(hass: HomeAssistant) -> None:

    assert async_get_fallback_availability_interval(hass, "44:44:33:11:23:12") is None

    async_set_fallback_availability_interval(hass, "44:44:33:11:23:12", 2.0)
    assert async_get_fallback_availability_interval(hass, "44:44:33:11:23:12") == 2.0

    start_monotonic_time = time.monotonic()
    switchbot_device = generate_ble_device("44:44:33:11:23:12", "wohand")
    switchbot_adv = generate_advertisement_data(
        local_name="wohand", service_uuids=["cba20d00-224d-11e6-9fb8-0002a5d5c51b"]
    )
    switchbot_device_went_unavailable = False

    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device,
        switchbot_adv,
        start_monotonic_time,
        SOURCE_LOCAL,
    )

    @callback
    def _switchbot_device_unavailable_callback(_address: str) -> None:

        nonlocal switchbot_device_went_unavailable
        switchbot_device_went_unavailable = True

    assert async_get_learned_advertising_interval(hass, "44:44:33:11:23:12") is None

    switchbot_device_unavailable_cancel = async_track_unavailable(
        hass,
        _switchbot_device_unavailable_callback,
        switchbot_device.address,
        connectable=False,
    )

    monotonic_now = start_monotonic_time + 2
    with patch_bluetooth_time(
        monotonic_now + UNAVAILABLE_TRACK_SECONDS,
    ):
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=UNAVAILABLE_TRACK_SECONDS)
        )
        await hass.async_block_till_done()

    assert switchbot_device_went_unavailable is True
    switchbot_device_unavailable_cancel()


    assert async_get_fallback_availability_interval(hass, "44:44:33:11:23:12") is None


@pytest.mark.usefixtures("enable_bluetooth", "macos_adapter")
async def test_set_fallback_interval_big(hass: HomeAssistant) -> None:

    assert async_get_fallback_availability_interval(hass, "44:44:33:11:23:12") is None



    async_set_fallback_availability_interval(hass, "44:44:33:11:23:12", 604800.0)
    assert (
        async_get_fallback_availability_interval(hass, "44:44:33:11:23:12") == 604800.0
    )

    start_monotonic_time = time.monotonic()
    switchbot_device = generate_ble_device("44:44:33:11:23:12", "wohand")
    switchbot_adv = generate_advertisement_data(
        local_name="wohand", service_uuids=["cba20d00-224d-11e6-9fb8-0002a5d5c51b"]
    )
    switchbot_device_went_unavailable = False

    inject_advertisement_with_time_and_source(
        hass,
        switchbot_device,
        switchbot_adv,
        start_monotonic_time,
        SOURCE_LOCAL,
    )

    @callback
    def _switchbot_device_unavailable_callback(_address: str) -> None:

        nonlocal switchbot_device_went_unavailable
        switchbot_device_went_unavailable = True

    assert async_get_learned_advertising_interval(hass, "44:44:33:11:23:12") is None

    switchbot_device_unavailable_cancel = async_track_unavailable(
        hass,
        _switchbot_device_unavailable_callback,
        switchbot_device.address,
        connectable=False,
    )



    monotonic_now = start_monotonic_time + 86400
    with patch_bluetooth_time(
        monotonic_now + UNAVAILABLE_TRACK_SECONDS,
    ):
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=UNAVAILABLE_TRACK_SECONDS)
        )
        await hass.async_block_till_done()

    assert switchbot_device_went_unavailable is False



    monotonic_now = start_monotonic_time + 604800
    with patch_bluetooth_time(
        monotonic_now + UNAVAILABLE_TRACK_SECONDS,
    ):
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=UNAVAILABLE_TRACK_SECONDS)
        )
        await hass.async_block_till_done()

    assert switchbot_device_went_unavailable is True

    switchbot_device_unavailable_cancel()


    assert async_get_fallback_availability_interval(hass, "44:44:33:11:23:12") is None


@pytest.mark.usefixtures("mock_bluetooth_adapters")
@pytest.mark.parametrize(
    (
        "entry_domain",
        "entry_discovery_keys",
    ),
    [

        (
            "switchbot",
            {
                "bluetooth": (
                    DiscoveryKey(
                        domain="bluetooth", key="44:44:33:11:23:45", version=1
                    ),
                )
            },
        ),

        (
            "switchbot",
            {
                "bluetooth": (
                    DiscoveryKey(
                        domain="bluetooth", key="44:44:33:11:23:45", version=1
                    ),
                ),
                "other": (DiscoveryKey(domain="other", key="blah", version=1),),
            },
        ),



        (
            "comp",
            {
                "bluetooth": (
                    DiscoveryKey(
                        domain="bluetooth", key="44:44:33:11:23:45", version=1
                    ),
                )
            },
        ),
    ],
)
@pytest.mark.parametrize(
    "entry_source",
    [
        config_entries.SOURCE_BLUETOOTH,
        config_entries.SOURCE_IGNORE,
        config_entries.SOURCE_USER,
    ],
)
async def test_bluetooth_rediscover(
    hass: HomeAssistant,
    entry_domain: str,
    entry_discovery_keys: dict[str, tuple[DiscoveryKey, ...]],
    entry_source: str,
) -> None:

    mock_bt = [
        {
            "domain": "switchbot",
            "service_data_uuid": "050a021a-0000-1000-8000-00805f9b34fb",
            "connectable": False,
        },
    ]
    with patch(
        "homeassistant.components.bluetooth.async_get_bluetooth", return_value=mock_bt
    ):
        assert await async_setup_component(hass, bluetooth.DOMAIN, {})
        await hass.async_block_till_done()

    assert async_scanner_count(hass, connectable=False) == 0
    switchbot_device_non_connectable = generate_ble_device(
        "44:44:33:11:23:45",
        "wohand",
        {},
    )
    switchbot_device_adv = generate_advertisement_data(
        local_name="wohand",
        service_uuids=["050a021a-0000-1000-8000-00805f9b34fb"],
        service_data={"050a021a-0000-1000-8000-00805f9b34fb": b"\n\xff"},
        manufacturer_data={1: b"\x01"},
        rssi=-100,
    )
    callbacks = []

    def _fake_subscriber(
        service_info: BluetoothServiceInfo,
        change: BluetoothChange,
    ) -> None:

        callbacks.append((service_info, change))

    cancel = bluetooth.async_register_callback(
        hass,
        _fake_subscriber,
        {"address": "44:44:33:11:23:45", "connectable": False},
        BluetoothScanningMode.ACTIVE,
    )

    class FakeScanner(BaseHaRemoteScanner):
        def inject_advertisement(
            self, device: BLEDevice, advertisement_data: AdvertisementData
        ) -> None:

            self._async_on_advertisement(
                device.address,
                advertisement_data.rssi,
                device.name,
                advertisement_data.service_uuids,
                advertisement_data.service_data,
                advertisement_data.manufacturer_data,
                advertisement_data.tx_power,
                {"scanner_specific_data": "test"},
                MONOTONIC_TIME(),
            )

        def clear_all_devices(self) -> None:

            self._previous_service_info.clear()

    connector = (
        HaBluetoothConnector(MockBleakClient, "mock_bleak_client", lambda: False),
    )
    non_connectable_scanner = FakeScanner(
        "connectable",
        "connectable",
        connector,
        False,
    )
    unsetup_connectable_scanner = non_connectable_scanner.async_setup()
    cancel_connectable_scanner = _get_manager().async_register_scanner(
        non_connectable_scanner
    )
    with patch.object(hass.config_entries.flow, "async_init") as mock_config_flow:
        non_connectable_scanner.inject_advertisement(
            switchbot_device_non_connectable, switchbot_device_adv
        )
        await hass.async_block_till_done()

        expected_context = {
            "discovery_key": DiscoveryKey(
                domain="bluetooth", key="44:44:33:11:23:45", version=1
            ),
            "source": "bluetooth",
        }
        assert len(mock_config_flow.mock_calls) == 1
        assert mock_config_flow.mock_calls[0][1][0] == "switchbot"
        assert mock_config_flow.mock_calls[0][2]["context"] == expected_context

        hass.config.components.add(entry_domain)
        mock_integration(hass, MockModule(entry_domain))

        entry = MockConfigEntry(
            domain=entry_domain,
            discovery_keys=entry_discovery_keys,
            unique_id="mock-unique-id",
            state=config_entries.ConfigEntryState.LOADED,
            source=entry_source,
        )
        entry.add_to_hass(hass)

        assert (
            async_ble_device_from_address(hass, "44:44:33:11:23:45", False) is not None
        )
        assert async_scanner_count(hass, connectable=False) == 1
        assert len(callbacks) == 1

        assert (
            "44:44:33:11:23:45"
            in non_connectable_scanner.discovered_devices_and_advertisement_data
        )

        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()

        assert (
            async_ble_device_from_address(hass, "44:44:33:11:23:45", False) is not None
        )
        assert async_scanner_count(hass, connectable=False) == 1
        assert len(callbacks) == 1

        assert len(mock_config_flow.mock_calls) == 2
        assert mock_config_flow.mock_calls[1][1][0] == "switchbot"
        assert mock_config_flow.mock_calls[1][2]["context"] == expected_context

    cancel()
    unsetup_connectable_scanner()
    cancel_connectable_scanner()


@pytest.mark.usefixtures("mock_bluetooth_adapters")
@pytest.mark.parametrize(
    (
        "entry_domain",
        "entry_discovery_keys",
        "entry_source",
        "entry_unique_id",
    ),
    [

        (
            "switchbot",
            {
                "zeroconf": (
                    DiscoveryKey(domain="zeroconf", key="44:44:33:11:23:45", version=1),
                )
            },
            config_entries.SOURCE_IGNORE,
            "mock-unique-id",
        ),

        (
            "switchbot",
            {
                "bluetooth": (
                    DiscoveryKey(
                        domain="bluetooth", key="44:44:33:11:23:45", version=2
                    ),
                )
            },
            config_entries.SOURCE_IGNORE,
            "mock-unique-id",
        ),
    ],
)
async def test_bluetooth_rediscover_no_match(
    hass: HomeAssistant,
    entry_domain: str,
    entry_discovery_keys: dict[str, tuple[DiscoveryKey, ...]],
    entry_source: str,
    entry_unique_id: str,
) -> None:

    mock_bt = [
        {
            "domain": "switchbot",
            "service_data_uuid": "050a021a-0000-1000-8000-00805f9b34fb",
            "connectable": False,
        },
    ]
    with patch(
        "homeassistant.components.bluetooth.async_get_bluetooth", return_value=mock_bt
    ):
        assert await async_setup_component(hass, bluetooth.DOMAIN, {})
        await hass.async_block_till_done()

    assert async_scanner_count(hass, connectable=False) == 0
    switchbot_device_non_connectable = generate_ble_device(
        "44:44:33:11:23:45",
        "wohand",
        {},
    )
    switchbot_device_adv = generate_advertisement_data(
        local_name="wohand",
        service_uuids=["050a021a-0000-1000-8000-00805f9b34fb"],
        service_data={"050a021a-0000-1000-8000-00805f9b34fb": b"\n\xff"},
        manufacturer_data={1: b"\x01"},
        rssi=-100,
    )
    callbacks = []

    def _fake_subscriber(
        service_info: BluetoothServiceInfo,
        change: BluetoothChange,
    ) -> None:

        callbacks.append((service_info, change))

    cancel = bluetooth.async_register_callback(
        hass,
        _fake_subscriber,
        {"address": "44:44:33:11:23:45", "connectable": False},
        BluetoothScanningMode.ACTIVE,
    )

    class FakeScanner(BaseHaRemoteScanner):
        def inject_advertisement(
            self, device: BLEDevice, advertisement_data: AdvertisementData
        ) -> None:

            self._async_on_advertisement(
                device.address,
                advertisement_data.rssi,
                device.name,
                advertisement_data.service_uuids,
                advertisement_data.service_data,
                advertisement_data.manufacturer_data,
                advertisement_data.tx_power,
                {"scanner_specific_data": "test"},
                MONOTONIC_TIME(),
            )

        def clear_all_devices(self) -> None:

            self._previous_service_info.clear()

    connector = (
        HaBluetoothConnector(MockBleakClient, "mock_bleak_client", lambda: False),
    )
    non_connectable_scanner = FakeScanner(
        "connectable",
        "connectable",
        connector,
        False,
    )
    unsetup_connectable_scanner = non_connectable_scanner.async_setup()
    cancel_connectable_scanner = _get_manager().async_register_scanner(
        non_connectable_scanner
    )
    with patch.object(hass.config_entries.flow, "async_init") as mock_config_flow:
        non_connectable_scanner.inject_advertisement(
            switchbot_device_non_connectable, switchbot_device_adv
        )
        await hass.async_block_till_done()

        expected_context = {
            "discovery_key": DiscoveryKey(
                domain="bluetooth", key="44:44:33:11:23:45", version=1
            ),
            "source": "bluetooth",
        }
        assert len(mock_config_flow.mock_calls) == 1
        assert mock_config_flow.mock_calls[0][1][0] == "switchbot"
        assert mock_config_flow.mock_calls[0][2]["context"] == expected_context

        hass.config.components.add(entry_domain)
        mock_integration(hass, MockModule(entry_domain))

        entry = MockConfigEntry(
            domain=entry_domain,
            discovery_keys=entry_discovery_keys,
            unique_id=entry_unique_id,
            state=config_entries.ConfigEntryState.LOADED,
            source=entry_source,
        )
        entry.add_to_hass(hass)

        assert (
            async_ble_device_from_address(hass, "44:44:33:11:23:45", False) is not None
        )
        assert async_scanner_count(hass, connectable=False) == 1
        assert len(callbacks) == 1

        assert (
            "44:44:33:11:23:45"
            in non_connectable_scanner.discovered_devices_and_advertisement_data
        )

        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()

        assert (
            async_ble_device_from_address(hass, "44:44:33:11:23:45", False) is not None
        )
        assert async_scanner_count(hass, connectable=False) == 1
        assert len(callbacks) == 1
        assert len(mock_config_flow.mock_calls) == 1

    cancel()
    unsetup_connectable_scanner()
    cancel_connectable_scanner()


@pytest.mark.usefixtures("enable_bluetooth")
async def test_async_register_disappeared_callback(
    hass: HomeAssistant,
    register_hci0_scanner: None,
    register_hci1_scanner: None,
) -> None:

    address = "44:44:33:11:23:12"

    switchbot_device_signal_100 = generate_ble_device(address, "wohand_signal_100")
    switchbot_adv_signal_100 = generate_advertisement_data(
        local_name="wohand_signal_100", service_uuids=[], rssi=-100
    )
    inject_advertisement_with_source(
        hass, switchbot_device_signal_100, switchbot_adv_signal_100, "hci0"
    )

    failed_disappeared: list[str] = []

    def _failing_callback(_address: str) -> None:

        failed_disappeared.append(_address)
        raise ValueError("This is a test")

    ok_disappeared: list[str] = []

    def _ok_callback(_address: str) -> None:

        ok_disappeared.append(_address)

    manager: HomeAssistantBluetoothManager = _get_manager()
    cancel1 = manager.async_register_disappeared_callback(_failing_callback)


    cancel2 = manager.async_register_disappeared_callback(_ok_callback)

    switchbot_adv_signal_100 = generate_advertisement_data(
        local_name="wohand_signal_100",
        manufacturer_data={123: b"abc"},
        service_uuids=[],
        rssi=-80,
    )
    inject_advertisement_with_source(
        hass, switchbot_device_signal_100, switchbot_adv_signal_100, "hci1"
    )

    future_time = utcnow() + timedelta(seconds=3600)
    future_monotonic_time = time.monotonic() + 3600
    with (
        freeze_time(future_time),
        patch(
            "habluetooth.manager.monotonic_time_coarse",
            return_value=future_monotonic_time,
        ),
    ):
        async_fire_time_changed(hass, future_time)

    assert len(ok_disappeared) == 1
    assert ok_disappeared[0] == address
    assert len(failed_disappeared) == 1
    assert failed_disappeared[0] == address

    cancel1()
    cancel2()


@pytest.mark.usefixtures("one_adapter")
async def test_repair_issue_created_for_degraded_scanner_in_docker(
    hass: HomeAssistant,
) -> None:

    await async_setup_component(hass, bluetooth.DOMAIN, {})
    await hass.async_block_till_done()

    manager = _get_manager()

    scanner = HaScanner(
        mode=BluetoothScanningMode.ACTIVE,
        adapter="hci0",
        address="00:11:22:33:44:55",
    )
    scanner.async_setup()

    mock_adapters = {
        "hci0": {
            "address": "00:11:22:33:44:55",
            "sw_version": "homeassistant",
            "hw_version": "usb:v0A5Cp21E8",
            "passive_scan": False,
            "manufacturer": "Broadcom",
            "product": "BCM20702A0",
            "vendor_id": "0A5C",
            "product_id": "21E8",
        }
    }

    with (
        patch("habluetooth.manager.IS_LINUX", True),
        patch.object(type(manager), "is_operating_degraded", return_value=True),
        patch(
            "homeassistant.components.bluetooth.manager.is_docker_env",
            return_value=True,
        ),
        patch.object(manager._bluetooth_adapters, "adapters", mock_adapters),
    ):
        manager.on_scanner_start(scanner)

        issue_id = f"bluetooth_adapter_missing_permissions_{scanner.source}"
        registry = ir.async_get(hass)
        issue = registry.async_get_issue(bluetooth.DOMAIN, issue_id)
        assert issue is not None
        assert issue.severity == ir.IssueSeverity.WARNING
        assert not issue.is_fixable
        assert issue.translation_key == "bluetooth_adapter_missing_permissions"


@pytest.mark.usefixtures("one_adapter")
async def test_repair_issue_deleted_when_scanner_not_degraded(
    hass: HomeAssistant,
) -> None:

    await async_setup_component(hass, bluetooth.DOMAIN, {})
    await hass.async_block_till_done()

    manager = _get_manager()
    registry = ir.async_get(hass)

    scanner = HaScanner(
        mode=BluetoothScanningMode.ACTIVE,
        adapter="hci0",
        address="00:11:22:33:44:55",
    )
    scanner.async_setup()

    mock_adapters = {
        "hci0": {
            "address": "00:11:22:33:44:55",
            "sw_version": "homeassistant",
            "hw_version": "usb:v0A5Cp21E8",
            "passive_scan": False,
            "manufacturer": "Broadcom",
            "product": "BCM20702A0",
            "vendor_id": "0A5C",
            "product_id": "21E8",
        }
    }

    issue_id = f"bluetooth_adapter_missing_permissions_{scanner.source}"

    with (
        patch("habluetooth.manager.IS_LINUX", True),
        patch.object(type(manager), "is_operating_degraded", return_value=True),
        patch(
            "homeassistant.components.bluetooth.manager.is_docker_env",
            return_value=True,
        ),
        patch.object(manager._bluetooth_adapters, "adapters", mock_adapters),
    ):
        manager.on_scanner_start(scanner)

    assert registry.async_get_issue(bluetooth.DOMAIN, issue_id) is not None

    with (
        patch(
            "homeassistant.components.bluetooth.manager.is_docker_env",
            return_value=True,
        ),
        patch.object(type(manager), "is_operating_degraded", return_value=False),
    ):
        manager.on_scanner_start(scanner)

    assert registry.async_get_issue(bluetooth.DOMAIN, issue_id) is None


@pytest.mark.usefixtures("one_adapter")
async def test_no_repair_issue_when_not_docker(
    hass: HomeAssistant,
) -> None:

    assert await async_setup_component(hass, bluetooth.DOMAIN, {})
    await hass.async_block_till_done()

    manager = _get_manager()

    scanner = HaScanner(
        mode=BluetoothScanningMode.ACTIVE,
        adapter="hci0",
        address="00:11:22:33:44:55",
    )
    scanner.async_setup()

    with (
        patch(
            "homeassistant.components.bluetooth.manager.is_docker_env",
            return_value=False,
        ),
        patch.object(type(manager), "is_operating_degraded", return_value=True),
    ):
        manager.on_scanner_start(scanner)

        issue_id = f"bluetooth_adapter_missing_permissions_{scanner.source}"
        registry = ir.async_get(hass)
        assert registry.async_get_issue(bluetooth.DOMAIN, issue_id) is None


@pytest.mark.usefixtures("one_adapter")
async def test_no_repair_issue_for_remote_scanner(
    hass: HomeAssistant,
) -> None:

    assert await async_setup_component(hass, bluetooth.DOMAIN, {})
    await hass.async_block_till_done()

    manager = _get_manager()

    connector = HaBluetoothConnector(MockBleakClient, "mock_connector", lambda: False)
    scanner = FakeRemoteScanner("remote_scanner", "esp32", connector, True)

    with (
        patch(
            "homeassistant.components.bluetooth.manager.is_docker_env",
            return_value=True,
        ),
        patch.object(type(manager), "is_operating_degraded", return_value=True),
    ):
        manager.on_scanner_start(scanner)

        registry = ir.async_get(hass)
        issues = [
            issue
            for issue in registry.issues.values()
            if issue.domain == bluetooth.DOMAIN
            and "bluetooth_adapter_missing_permissions" in issue.issue_id
        ]
        assert len(issues) == 0


@pytest.mark.usefixtures("one_adapter")
async def test_repair_issue_created_for_passive_mode_fallback(
    hass: HomeAssistant,
) -> None:

    assert await async_setup_component(hass, bluetooth.DOMAIN, {})
    await hass.async_block_till_done()

    manager = _get_manager()

    scanner = HaScanner(
        mode=BluetoothScanningMode.ACTIVE,
        adapter="hci0",
        address="00:11:22:33:44:55",
    )
    scanner.async_setup()

    cancel = manager.async_register_scanner(scanner, connection_slots=1)


    scanner.set_requested_mode(BluetoothScanningMode.ACTIVE)
    scanner.set_current_mode(BluetoothScanningMode.PASSIVE)

    manager.on_scanner_start(scanner)


    issue_id = f"bluetooth_adapter_passive_mode_{scanner.source}"
    registry = ir.async_get(hass)
    issue = registry.async_get_issue(bluetooth.DOMAIN, issue_id)
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING

    assert issue.translation_key == "bluetooth_adapter_passive_mode_usb"
    assert not issue.is_fixable

    cancel()


async def test_repair_issue_created_for_passive_mode_fallback_uart(
    hass: HomeAssistant,
) -> None:

    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.adapters",
        {
            "hci0": {
                "address": "00:11:22:33:44:55",
                "sw_version": "homeassistant",
                "hw_version": "uart:bcm2711",
                "passive_scan": False,
                "manufacturer": "Raspberry Pi",
                "product": "BCM2711",
                "adapter_type": "uart",
            }
        },
    ):
        assert await async_setup_component(hass, bluetooth.DOMAIN, {})
        await hass.async_block_till_done()

        manager = _get_manager()

        scanner = HaScanner(
            mode=BluetoothScanningMode.ACTIVE,
            adapter="hci0",
            address="00:11:22:33:44:55",
        )
        scanner.async_setup()

        cancel = manager.async_register_scanner(scanner, connection_slots=1)


        scanner.set_requested_mode(BluetoothScanningMode.ACTIVE)
        scanner.set_current_mode(BluetoothScanningMode.PASSIVE)

        manager.on_scanner_start(scanner)


        issue_id = f"bluetooth_adapter_passive_mode_{scanner.source}"
        registry = ir.async_get(hass)
        issue = registry.async_get_issue(bluetooth.DOMAIN, issue_id)
        assert issue is not None
        assert issue.severity == ir.IssueSeverity.WARNING
        assert issue.translation_key == "bluetooth_adapter_passive_mode_uart"
        assert not issue.is_fixable

        cancel()


@pytest.mark.usefixtures("one_adapter")
async def test_repair_issue_deleted_when_passive_mode_resolved(
    hass: HomeAssistant,
) -> None:

    assert await async_setup_component(hass, bluetooth.DOMAIN, {})
    await hass.async_block_till_done()

    manager = _get_manager()

    scanner = HaScanner(
        mode=BluetoothScanningMode.ACTIVE,
        adapter="hci0",
        address="00:11:22:33:44:55",
    )
    scanner.async_setup()

    cancel = manager.async_register_scanner(scanner, connection_slots=1)


    scanner.set_requested_mode(BluetoothScanningMode.ACTIVE)
    scanner.set_current_mode(BluetoothScanningMode.PASSIVE)

    manager.on_scanner_start(scanner)


    issue_id = f"bluetooth_adapter_passive_mode_{scanner.source}"
    registry = ir.async_get(hass)
    issue = registry.async_get_issue(bluetooth.DOMAIN, issue_id)
    assert issue is not None


    scanner.set_current_mode(BluetoothScanningMode.ACTIVE)
    manager.on_scanner_start(scanner)


    issue = registry.async_get_issue(bluetooth.DOMAIN, issue_id)
    assert issue is None

    cancel()
