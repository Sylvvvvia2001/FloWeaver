

from collections.abc import Callable
import dataclasses
from typing import Any
from unittest import mock

from aiohomekit.controller import TransportType
from aiohomekit.model import Accessories, Accessory
from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.services import Service, ServicesTypes
from aiohomekit.testing import FakeController
import pytest

from homeassistant.components.climate import ATTR_CURRENT_TEMPERATURE
from homeassistant.components.homekit_controller.connection import (
    MAX_CHARACTERISTICS_PER_REQUEST,
)
from homeassistant.components.homekit_controller.const import (
    DEBOUNCE_COOLDOWN,
    DOMAIN,
    IDENTIFIER_ACCESSORY_ID,
    IDENTIFIER_LEGACY_ACCESSORY_ID,
    IDENTIFIER_LEGACY_SERIAL_NUMBER,
)
from homeassistant.components.thread import async_add_dataset, dataset_store
from homeassistant.const import STATE_OFF, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_component import async_update_entity

from .common import (
    setup_accessories_from_file,
    setup_platform,
    setup_test_accessories,
    setup_test_component,
    time_changed,
)

from tests.common import MockConfigEntry


@dataclasses.dataclass
class DeviceMigrationTest:


    fixture: str
    manufacturer: str
    before: set[tuple[str, str, str]]
    after: set[tuple[str, str]]


DEVICE_MIGRATION_TESTS = [

    DeviceMigrationTest(
        fixture="ryse_smart_bridge_four_shades.json",
        manufacturer="RYSE Inc.",
        before={
            (DOMAIN, IDENTIFIER_LEGACY_ACCESSORY_ID, "00:00:00:00:00:00"),
        },
        after={(IDENTIFIER_ACCESSORY_ID, "00:00:00:00:00:00:aid:1")},
    ),

    DeviceMigrationTest(
        fixture="ryse_smart_bridge_four_shades.json",
        manufacturer="RYSE Inc.",
        before={
            (DOMAIN, IDENTIFIER_LEGACY_ACCESSORY_ID, "00:00:00:00:00:00_3"),
        },
        after={(IDENTIFIER_ACCESSORY_ID, "00:00:00:00:00:00:aid:3")},
    ),

    DeviceMigrationTest(
        fixture="hue_bridge.json",
        manufacturer="Philips Lighting",
        before={
            (DOMAIN, IDENTIFIER_LEGACY_ACCESSORY_ID, "00:00:00:00:00:00"),
        },
        after={
            (IDENTIFIER_ACCESSORY_ID, "00:00:00:00:00:00:aid:1"),
        },
    ),


    DeviceMigrationTest(
        fixture="hue_bridge.json",
        manufacturer="Philips",
        before={
            (DOMAIN, IDENTIFIER_LEGACY_SERIAL_NUMBER, "6623462389072572"),
        },
        after={
            (IDENTIFIER_ACCESSORY_ID, "00:00:00:00:00:00:aid:6623462389072572"),
        },
    ),

    DeviceMigrationTest(
        fixture="koogeek_ls1.json",
        manufacturer="Koogeek",
        before={
            (DOMAIN, IDENTIFIER_LEGACY_ACCESSORY_ID, "00:00:00:00:00:00"),
            (DOMAIN, IDENTIFIER_LEGACY_SERIAL_NUMBER, "AAAA011111111111"),
        },
        after={
            (IDENTIFIER_ACCESSORY_ID, "00:00:00:00:00:00:aid:1"),
        },
    ),
]


@pytest.mark.parametrize("variant", DEVICE_MIGRATION_TESTS)
async def test_migrate_device_id_no_serial_skip_if_other_owner(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    variant: DeviceMigrationTest,
) -> None:





    entry = MockConfigEntry()
    entry.add_to_hass(hass)

    bridge = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=variant.before,
        manufacturer="RYSE Inc.",
        model="RYSE SmartBridge",
        name="Wiring Closet",
        sw_version="1.3.0",
        hw_version="0101.2136.0344",
    )

    accessories = await setup_accessories_from_file(hass, variant.fixture)
    await setup_test_accessories(hass, accessories)

    bridge = device_registry.async_get(bridge.id)

    assert bridge.identifiers == variant.before
    assert bridge.config_entries == {entry.entry_id}


@pytest.mark.parametrize("variant", DEVICE_MIGRATION_TESTS)
async def test_migrate_device_id_no_serial(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    variant: DeviceMigrationTest,
) -> None:

    accessories = await setup_accessories_from_file(hass, variant.fixture)

    fake_controller = await setup_platform(hass)
    await fake_controller.add_paired_device(accessories, "00:00:00:00:00:00")
    config_entry = MockConfigEntry(
        version=1,
        domain="homekit_controller",
        entry_id="TestData",
        data={"AccessoryPairingID": "00:00:00:00:00:00"},
        title="test",
    )
    config_entry.add_to_hass(hass)

    device = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers=variant.before,
        manufacturer="Dummy Manufacturer",
        model="Dummy Model",
        name="Dummy Name",
        sw_version="99999999991",
        hw_version="99999999999",
    )

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    device = device_registry.async_get(device.id)

    assert device.identifiers == variant.after
    assert device.manufacturer == variant.manufacturer


async def test_migrate_ble_unique_id(hass: HomeAssistant) -> None:

    accessories = await setup_accessories_from_file(hass, "anker_eufycam.json")

    fake_controller = await setup_platform(hass)
    await fake_controller.add_paired_device(accessories, "02:03:EF:02:03:EF")
    config_entry = MockConfigEntry(
        version=1,
        domain="homekit_controller",
        entry_id="TestData",
        data={"AccessoryPairingID": "02:03:EF:02:03:EF"},
        title="test",
        unique_id="01:02:AB:01:02:AB",
    )
    config_entry.add_to_hass(hass)

    assert config_entry.unique_id == "01:02:AB:01:02:AB"

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.unique_id == "02:03:ef:02:03:ef"


async def test_thread_provision_no_creds(hass: HomeAssistant) -> None:

    accessories = await setup_accessories_from_file(hass, "nanoleaf_strip_nl55.json")

    fake_controller = await setup_platform(hass)
    await fake_controller.add_paired_device(accessories, "02:03:EF:02:03:EF")
    config_entry = MockConfigEntry(
        version=1,
        domain="homekit_controller",
        entry_id="TestData",
        data={"AccessoryPairingID": "02:03:EF:02:03:EF"},
        title="test",
        unique_id="02:03:ef:02:03:ef",
    )
    config_entry.add_to_hass(hass)

    fake_controller.transport_type = TransportType.BLE

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "button",
            "press",
            {
                "entity_id": "button.nanoleaf_strip_3b32_provision_preferred_thread_credentials"
            },
            blocking=True,
        )


async def test_thread_provision(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:

    await async_add_dataset(
        hass,
        "Tests",
        "0E080000000000010000000300000F35060004001FFFE0020811111111222222220708FDAD70BF"
        "E5AA15DD051000112233445566778899AABBCCDDEEFF030E4F70656E54687265616444656D6F01"
        "0212340410445F2B5CA6F2A93A55CE570A70EFEECB0C0402A0F7F8",
    )
    store = await dataset_store.async_get_store(hass)
    dataset_id = list(store.datasets.values())[0].id
    store.preferred_dataset = dataset_id

    accessories = await setup_accessories_from_file(hass, "nanoleaf_strip_nl55.json")

    fake_controller = await setup_platform(hass)
    await fake_controller.add_paired_device(accessories, "00:00:00:00:00:00")
    config_entry = MockConfigEntry(
        version=1,
        domain="homekit_controller",
        entry_id="TestData",
        data={"AccessoryPairingID": "00:00:00:00:00:00"},
        title="test",
        unique_id="00:00:00:00:00:00",
    )
    config_entry.add_to_hass(hass)

    fake_controller.transport_type = TransportType.BLE


    fake_controller.transports = {TransportType.COAP: fake_controller}


    discovery = fake_controller.discoveries["00:00:00:00:00:00"]
    discovery.description.address = "127.0.0.1"
    discovery.description.port = 53

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(
        "button.nanoleaf_strip_3b32_provision_preferred_thread_credentials"
    )
    assert entity_registry.async_get(
        "button.nanoleaf_strip_3b32_provision_preferred_thread_credentials"
    )

    await hass.services.async_call(
        "button",
        "press",
        {
            "entity_id": "button.nanoleaf_strip_3b32_provision_preferred_thread_credentials"
        },
        blocking=True,
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    assert config_entry.data["Connection"] == "CoAP"

    assert not hass.states.get(
        "button.nanoleaf_strip_3b32_provision_preferred_thread_credentials"
    )
    assert not entity_registry.async_get(
        "button.nanoleaf_strip_3b32_provision_preferred_thread_credentials"
    )


async def test_thread_provision_migration_failed(hass: HomeAssistant) -> None:

    await async_add_dataset(
        hass,
        "Tests",
        "0E080000000000010000000300000F35060004001FFFE0020811111111222222220708FDAD70BF"
        "E5AA15DD051000112233445566778899AABBCCDDEEFF030E4F70656E54687265616444656D6F01"
        "0212340410445F2B5CA6F2A93A55CE570A70EFEECB0C0402A0F7F8",
    )

    accessories = await setup_accessories_from_file(hass, "nanoleaf_strip_nl55.json")

    fake_controller = await setup_platform(hass)
    await fake_controller.add_paired_device(accessories, "00:00:00:00:00:00")
    config_entry = MockConfigEntry(
        version=1,
        domain="homekit_controller",
        entry_id="TestData",
        data={"AccessoryPairingID": "00:00:00:00:00:00", "Connection": "BLE"},
        title="test",
        unique_id="00:00:00:00:00:00",
    )
    config_entry.add_to_hass(hass)

    fake_controller.transport_type = TransportType.BLE


    fake_controller.transports = {TransportType.COAP: fake_controller}

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


    del fake_controller.discoveries["00:00:00:00:00:00"]

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "button",
            "press",
            {
                "entity_id": "button.nanoleaf_strip_3b32_provision_preferred_thread_credentials"
            },
            blocking=True,
        )

    assert config_entry.data["Connection"] == "BLE"


async def test_poll_firmware_version_only_all_watchable_accessory_mode(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:


    def _create_accessory(accessory: Accessory) -> Service:
        service = accessory.add_service(ServicesTypes.LIGHTBULB, name="TestDevice")

        on_char = service.add_char(CharacteristicsTypes.ON)
        on_char.value = 0

        brightness = service.add_char(CharacteristicsTypes.BRIGHTNESS)
        brightness.value = 0

        return service

    helper = await setup_test_component(hass, get_next_aid(), _create_accessory)

    with mock.patch.object(
        helper.pairing,
        "get_characteristics",
        wraps=helper.pairing.get_characteristics,
    ) as mock_get_characteristics:

        state = await helper.poll_and_get_state()
        assert state.state == STATE_OFF
        assert mock_get_characteristics.call_count == 2

        assert set(mock_get_characteristics.call_args_list[0][0][0]) == {
            (1, 10),
            (1, 11),
        }
        assert set(mock_get_characteristics.call_args_list[1][0][0]) == {
            (1, 10),
            (1, 11),
        }


        helper.pairing.available = False
        with mock.patch.object(
            FakeController,
            "async_reachable",
            return_value=False,
        ):
            state = await helper.poll_and_get_state()
            assert state.state == STATE_UNAVAILABLE

            assert mock_get_characteristics.call_count == 4


        helper.pairing.available = True
        state = await helper.poll_and_get_state()
        assert state.state == STATE_OFF
        assert mock_get_characteristics.call_count == 6



        state = await helper.poll_and_get_state()
        assert state.state == STATE_OFF
        assert mock_get_characteristics.call_count == 8


async def test_manual_poll_all_chars(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:


    def _create_accessory(accessory: Accessory) -> Service:
        service = accessory.add_service(ServicesTypes.LIGHTBULB, name="TestDevice")

        on_char = service.add_char(CharacteristicsTypes.ON)
        on_char.value = 0

        brightness = service.add_char(CharacteristicsTypes.BRIGHTNESS)
        brightness.value = 0

        return service

    helper = await setup_test_component(hass, get_next_aid(), _create_accessory)

    with mock.patch.object(
        helper.pairing,
        "get_characteristics",
        wraps=helper.pairing.get_characteristics,
    ) as mock_get_characteristics:

        await helper.poll_and_get_state()

        assert len(mock_get_characteristics.call_args_list[0][0][0]) > 1


        mock_get_characteristics.reset_mock()
        await async_update_entity(hass, helper.entity_id)
        await time_changed(hass, 60)
        await time_changed(hass, DEBOUNCE_COOLDOWN)
        await hass.async_block_till_done()
        assert len(mock_get_characteristics.call_args_list[0][0][0]) > 1


async def test_poll_all_on_startup_refreshes_stale_values(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:


    accessories = await setup_accessories_from_file(hass, "ecobee3.json")


    hass_storage["homekit_controller-entity-map"] = {
        "version": 1,
        "minor_version": 1,
        "key": "homekit_controller-entity-map",
        "data": {
            "pairings": {
                "00:00:00:00:00:00": {
                    "config_num": 1,
                    "accessories": [
                        a.to_accessory_and_service_list() for a in accessories
                    ],
                }
            }
        },
    }


    polled_chars: list[tuple[int, int]] = []


    fake_controller = await setup_platform(hass)


    async def mock_get_characteristics(
        chars: set[tuple[int, int]], **kwargs: Any
    ) -> dict[tuple[int, int], dict[str, Any]]:

        polled_chars.extend(chars)

        result: dict[tuple[int, int], dict[str, Any]] = {}
        for aid, iid in chars:

            for accessory in accessories:
                if accessory.aid != aid:
                    continue
                for service in accessory.services:
                    for char in service.characteristics:
                        if char.iid != iid:
                            continue

                        if char.type == CharacteristicsTypes.TEMPERATURE_CURRENT:
                            result[(aid, iid)] = {"value": 22.5}
                        else:
                            result[(aid, iid)] = {"value": char.value}
                        break
        return result


    await fake_controller.add_paired_device(accessories, "00:00:00:00:00:00")
    config_entry = MockConfigEntry(
        version=1,
        domain="homekit_controller",
        entry_id="TestData",
        data={"AccessoryPairingID": "00:00:00:00:00:00"},
        title="test",
    )
    config_entry.add_to_hass(hass)


    pairing = fake_controller.pairings["00:00:00:00:00:00"]

    with mock.patch.object(pairing, "get_characteristics", mock_get_characteristics):

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()


    assert (
        len(polled_chars) == 79
    )


    state = hass.states.get("climate.homew")
    assert state is not None
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 22.5


async def test_characteristic_polling_batching(
    hass: HomeAssistant, get_next_aid: Callable[[], int]
) -> None:



    def create_large_accessory_with_many_chars(accessory: Accessory) -> None:


        for service_num in range(10):
            service = accessory.add_service(
                ServicesTypes.LIGHTBULB, name=f"Light {service_num}"
            )

            service.add_char(CharacteristicsTypes.ON)
            service.add_char(CharacteristicsTypes.BRIGHTNESS)
            service.add_char(CharacteristicsTypes.HUE)
            service.add_char(CharacteristicsTypes.SATURATION)
            service.add_char(CharacteristicsTypes.COLOR_TEMPERATURE)

            for char in service.characteristics:
                if char.type != CharacteristicsTypes.IDENTIFY:
                    char.value = 0

    helper = await setup_test_component(
        hass, get_next_aid(), create_large_accessory_with_many_chars
    )


    get_chars_calls = []
    original_get_chars = helper.pairing.get_characteristics

    async def mock_get_characteristics(chars):

        get_chars_calls.append(list(chars))
        return await original_get_chars(chars)


    get_chars_calls.clear()


    with mock.patch.object(
        helper.pairing, "get_characteristics", side_effect=mock_get_characteristics
    ):


        await time_changed(hass, 300)
        await hass.async_block_till_done()




    assert len(get_chars_calls) == 2, (
        f"Should have made exactly 2 batched calls, got {len(get_chars_calls)}"
    )


    for i, batch in enumerate(get_chars_calls):
        assert len(batch) <= MAX_CHARACTERISTICS_PER_REQUEST, (
            f"Batch {i} size {len(batch)} exceeded maximum {MAX_CHARACTERISTICS_PER_REQUEST}"
        )


    total_chars = sum(len(batch) for batch in get_chars_calls)


    assert total_chars == 50, (
        f"Should have polled exactly 50 characteristics, got {total_chars}"
    )


    assert len(get_chars_calls[0]) == 49, (
        f"First batch should have exactly 49 characteristics, got {len(get_chars_calls[0])}"
    )


    assert len(get_chars_calls[1]) == 1, (
        f"Second batch should have exactly 1 characteristic, got {len(get_chars_calls[1])}"
    )


async def test_async_setup_handles_unparsable_response(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:

    accessories = Accessories()
    accessory = Accessory.create_with_info(
        1, "TestDevice", "example.com", "Test", "0001", "0.1"
    )
    service = accessory.add_service(ServicesTypes.LIGHTBULB)
    on_char = service.add_char(CharacteristicsTypes.ON)
    on_char.value = False
    accessories.add_accessory(accessory)

    async def mock_get_characteristics(
        chars: set[tuple[int, int]], **kwargs: Any
    ) -> dict[tuple[int, int], dict[str, Any]]:

        raise ValueError(
            "Unable to parse text",
            ("Error processing token: filename. Filename missing or too long?"),
        )

    fake_controller = await setup_platform(hass)
    await fake_controller.add_paired_device(accessories, "00:00:00:00:00:00")

    config_entry = MockConfigEntry(
        version=1,
        domain="homekit_controller",
        entry_id="TestData",
        data={"AccessoryPairingID": "00:00:00:00:00:00"},
        title="test",
    )
    config_entry.add_to_hass(hass)

    pairing = fake_controller.pairings["00:00:00:00:00:00"]

    with (
        caplog.at_level("DEBUG", logger="homeassistant.components.homekit_controller"),
        mock.patch.object(pairing, "get_characteristics", mock_get_characteristics),
    ):


        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    assert "responded with unparsable response, first update was skipped" in caplog.text
    assert "Error processing token: filename" in caplog.text




    state = hass.states.get("light.testdevice")
    assert state is not None
