

from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock, call

from bleak import BleakError
import pytest

from homeassistant.components.bluetooth import (
    DOMAIN,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo
from homeassistant.setup import async_setup_component

from . import inject_bluetooth_service_info

_LOGGER = logging.getLogger(__name__)


GENERIC_BLUETOOTH_SERVICE_INFO = BluetoothServiceInfo(
    name="Generic",
    address="aa:bb:cc:dd:ee:ff",
    rssi=-95,
    manufacturer_data={
        1: b"\x01\x01\x01\x01\x01\x01\x01\x01",
    },
    service_data={},
    service_uuids=[],
    source="local",
)
GENERIC_BLUETOOTH_SERVICE_INFO_2 = BluetoothServiceInfo(
    name="Generic",
    address="aa:bb:cc:dd:ee:ff",
    rssi=-95,
    manufacturer_data={1: b"\x01\x01\x01\x01\x01\x01\x01\x01", 2: b"\x02"},
    service_data={},
    service_uuids=[],
    source="local",
)


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_basic_usage(hass: HomeAssistant) -> None:

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    def _update_method(service_info: BluetoothServiceInfoBleak):
        return {"testdata": 0}

    def _poll_needed(*args, **kwargs):
        return True

    async def _poll(*args, **kwargs):
        return {"testdata": 1}

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address="aa:bb:cc:dd:ee:ff",
        mode=BluetoothScanningMode.ACTIVE,
        update_method=_update_method,
        needs_poll_method=_poll_needed,
        poll_method=_poll,
    )
    assert coordinator.available is False

    processor = MagicMock()
    coordinator.async_register_processor(processor)
    async_handle_update = processor.async_handle_update

    cancel = coordinator.async_start()

    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert coordinator.available is True




    assert len(async_handle_update.mock_calls) == 2
    assert async_handle_update.mock_calls[0] == call({"testdata": 0}, False)
    assert async_handle_update.mock_calls[1] == call({"testdata": 1})

    cancel()


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_poll_can_be_skipped(hass: HomeAssistant) -> None:

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    flag = True

    def _update_method(service_info: BluetoothServiceInfoBleak):
        return {"testdata": None}

    def _poll_needed(*args, **kwargs):
        nonlocal flag
        return flag

    async def _poll(*args, **kwargs):
        return {"testdata": flag}

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address="aa:bb:cc:dd:ee:ff",
        mode=BluetoothScanningMode.ACTIVE,
        update_method=_update_method,
        needs_poll_method=_poll_needed,
        poll_method=_poll,
        poll_debouncer=Debouncer(
            hass, _LOGGER, cooldown=0, immediate=True, background=True
        ),
    )
    assert coordinator.available is False

    processor = MagicMock()
    coordinator.async_register_processor(processor)
    async_handle_update = processor.async_handle_update

    cancel = coordinator.async_start()

    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[-1] == call({"testdata": True})

    flag = False

    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO_2)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[-1] == call({"testdata": None}, True)

    flag = True

    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[-1] == call({"testdata": True})

    cancel()


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_bleak_error_and_recover(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    flag = True

    def _update_method(service_info: BluetoothServiceInfoBleak):
        return {"testdata": None}

    def _poll_needed(*args, **kwargs):
        return True

    async def _poll(*args, **kwargs):
        nonlocal flag
        if flag:
            raise BleakError("Connection was aborted")
        return {"testdata": flag}

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address="aa:bb:cc:dd:ee:ff",
        mode=BluetoothScanningMode.ACTIVE,
        update_method=_update_method,
        needs_poll_method=_poll_needed,
        poll_method=_poll,
        poll_debouncer=Debouncer(
            hass,
            _LOGGER,
            cooldown=0,
            immediate=True,
        ),
    )
    assert coordinator.available is False

    processor = MagicMock()
    coordinator.async_register_processor(processor)
    async_handle_update = processor.async_handle_update

    cancel = coordinator.async_start()


    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[-1] == call({"testdata": None}, False)

    assert (
        "aa:bb:cc:dd:ee:ff: Bluetooth error whilst polling: Connection was aborted"
        in caplog.text
    )


    flag = False
    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO_2)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[-1] == call({"testdata": False})

    cancel()


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_poll_failure_and_recover(hass: HomeAssistant) -> None:

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    flag = True

    def _update_method(service_info: BluetoothServiceInfoBleak):
        return {"testdata": None}

    def _poll_needed(*args, **kwargs):
        return True

    async def _poll(*args, **kwargs):
        nonlocal flag
        if flag:
            raise RuntimeError("Poll failure")
        return {"testdata": flag}

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address="aa:bb:cc:dd:ee:ff",
        mode=BluetoothScanningMode.ACTIVE,
        update_method=_update_method,
        needs_poll_method=_poll_needed,
        poll_method=_poll,
        poll_debouncer=Debouncer(
            hass,
            _LOGGER,
            cooldown=0,
            immediate=True,
        ),
    )
    assert coordinator.available is False

    processor = MagicMock()
    coordinator.async_register_processor(processor)
    async_handle_update = processor.async_handle_update

    cancel = coordinator.async_start()


    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[-1] == call({"testdata": None}, False)


    flag = False
    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO_2)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[-1] == call({"testdata": False})

    cancel()


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_second_poll_needed(hass: HomeAssistant) -> None:

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    count = 0

    def _update_method(service_info: BluetoothServiceInfoBleak):
        return {"testdata": None}


    def _poll_needed(*args, **kwargs):
        nonlocal count
        return count == 0

    async def _poll(*args, **kwargs):
        nonlocal count
        count += 1
        return {"testdata": count}

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address="aa:bb:cc:dd:ee:ff",
        mode=BluetoothScanningMode.ACTIVE,
        update_method=_update_method,
        needs_poll_method=_poll_needed,
        poll_method=_poll,
    )
    assert coordinator.available is False

    processor = MagicMock()
    coordinator.async_register_processor(processor)
    async_handle_update = processor.async_handle_update

    cancel = coordinator.async_start()


    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)

    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO_2)

    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[1] == call({"testdata": 1})

    cancel()


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_rate_limit(hass: HomeAssistant) -> None:

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    count = 0

    def _update_method(service_info: BluetoothServiceInfoBleak):
        return {"testdata": None}

    def _poll_needed(*args, **kwargs):
        return True

    async def _poll(*args, **kwargs):
        nonlocal count
        count += 1
        await asyncio.sleep(0)
        return {"testdata": count}

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address="aa:bb:cc:dd:ee:ff",
        mode=BluetoothScanningMode.ACTIVE,
        update_method=_update_method,
        needs_poll_method=_poll_needed,
        poll_method=_poll,
    )
    assert coordinator.available is False

    processor = MagicMock()
    coordinator.async_register_processor(processor)
    async_handle_update = processor.async_handle_update

    cancel = coordinator.async_start()


    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)

    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO_2)

    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)

    await hass.async_block_till_done(wait_background_tasks=True)
    assert async_handle_update.mock_calls[-1] == call({"testdata": 1})

    cancel()


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_no_polling_after_stop_event(hass: HomeAssistant) -> None:

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
    needs_poll_calls = 0

    def _update_method(service_info: BluetoothServiceInfoBleak):
        return {"testdata": 0}

    def _poll_needed(*args, **kwargs):
        nonlocal needs_poll_calls
        needs_poll_calls += 1
        return True

    async def _poll(*args, **kwargs):
        return {"testdata": 1}

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address="aa:bb:cc:dd:ee:ff",
        mode=BluetoothScanningMode.ACTIVE,
        update_method=_update_method,
        needs_poll_method=_poll_needed,
        poll_method=_poll,
    )
    assert coordinator.available is False

    processor = MagicMock()
    coordinator.async_register_processor(processor)
    async_handle_update = processor.async_handle_update

    cancel = coordinator.async_start()

    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert needs_poll_calls == 1

    assert coordinator.available is True




    assert len(async_handle_update.mock_calls) == 2
    assert async_handle_update.mock_calls[0] == call({"testdata": 0}, False)
    assert async_handle_update.mock_calls[1] == call({"testdata": 1})

    hass.set_state(CoreState.stopping)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert needs_poll_calls == 1


    inject_bluetooth_service_info(hass, GENERIC_BLUETOOTH_SERVICE_INFO_2)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert needs_poll_calls == 1

    cancel()
