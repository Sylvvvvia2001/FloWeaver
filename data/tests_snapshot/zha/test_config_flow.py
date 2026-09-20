

import asyncio
from collections.abc import Callable, Coroutine, Generator
from datetime import timedelta
from ipaddress import ip_address
import json
from typing import Any
from unittest.mock import (
    AsyncMock,
    MagicMock,
    PropertyMock,
    call,
    create_autospec,
    patch,
)
import uuid

import pytest
from serial.tools.list_ports_common import ListPortInfo
from zha.application.const import RadioType
from zigpy.application import ControllerApplication
from zigpy.backups import BackupManager
import zigpy.config
from zigpy.config import CONF_DEVICE, CONF_DEVICE_PATH, SCHEMA_DEVICE
import zigpy.device
from zigpy.exceptions import (
    CannotWriteNetworkSettings,
    DestructiveWriteNetworkSettings,
    NetworkNotFormed,
)
import zigpy.types

from homeassistant import config_entries
from homeassistant.components.hassio import AddonError, AddonState
from homeassistant.components.usb import USBDevice
from homeassistant.components.zha import config_flow, radio_manager
from homeassistant.components.zha.const import (
    CONF_BAUDRATE,
    CONF_FLOW_CONTROL,
    CONF_RADIO_TYPE,
    DOMAIN,
    EZSP_OVERWRITE_EUI64,
)
from homeassistant.components.zha.radio_manager import ProbeResult, ZhaRadioManager
from homeassistant.config_entries import (
    SOURCE_SSDP,
    SOURCE_USB,
    SOURCE_USER,
    SOURCE_ZEROCONF,
    ConfigEntriesFlowManager,
    ConfigEntryState,
    ConfigFlowResult,
)
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.service_info.ssdp import (
    ATTR_UPNP_MANUFACTURER_URL,
    ATTR_UPNP_SERIAL,
    SsdpServiceInfo,
)
from homeassistant.helpers.service_info.usb import UsbServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from tests.common import MockConfigEntry

type RadioPicker = Callable[
    [RadioType], Coroutine[Any, Any, tuple[ConfigFlowResult, ListPortInfo]]
]
PROBE_FUNCTION_PATH = "zigbee.application.ControllerApplication.probe"


@pytest.fixture(autouse=True)
def disable_platform_only():

    with patch("homeassistant.components.zha.PLATFORMS", []):
        yield


@pytest.fixture(autouse=True)
def mock_multipan_platform():

    with (
        patch(
            "homeassistant.components.zha.silabs_multiprotocol.async_get_channel",
            return_value=None,
        ),
        patch(
            "homeassistant.components.zha.silabs_multiprotocol.async_using_multipan",
            return_value=False,
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_app() -> Generator[AsyncMock]:

    mock_app = create_autospec(ControllerApplication, instance=True)
    mock_app.backups = create_autospec(BackupManager, instance=True)
    mock_app.backups.backups = []

    mock_app.state = MagicMock()
    mock_app.state.network_info.extended_pan_id = zigpy.types.EUI64.convert(
        "AABBCCDDEE000000"
    )
    mock_app.state.network_info.metadata = {
        "ezsp": {
            "can_burn_userdata_custom_eui64": True,
            "can_rewrite_custom_eui64": False,
        }
    }
    mock_app.add_listener = MagicMock()
    mock_app.groups = MagicMock()
    mock_app.devices = MagicMock()

    with patch(
        "zigpy.application.ControllerApplication.new", AsyncMock(return_value=mock_app)
    ):
        yield mock_app


@pytest.fixture
def make_backup():

    num_calls = 0

    def inner(*, backup_time_offset=0):
        nonlocal num_calls

        backup = zigpy.backups.NetworkBackup()
        backup.backup_time += timedelta(seconds=backup_time_offset)
        backup.node_info.ieee = zigpy.types.EUI64.convert(f"AABBCCDDEE{num_calls:06X}")
        num_calls += 1

        return backup

    return inner


@pytest.fixture
def backup(make_backup):

    return make_backup()


@pytest.fixture(autouse=True)
def mock_supervisor_client(
    supervisor_client: AsyncMock, addon_store_info: AsyncMock
) -> None:
    pass


def mock_detect_radio_type(
    radio_type: RadioType = RadioType.ezsp,
    ret: ProbeResult = ProbeResult.RADIO_TYPE_DETECTED,
):


    async def detect(self):
        self.radio_type = radio_type
        self.device_settings = SCHEMA_DEVICE({CONF_DEVICE_PATH: self.device_path})

        return ret

    return detect


def com_port(device="/dev/ttyUSB1234") -> ListPortInfo:

    port = ListPortInfo(device)
    port.serial_number = "1234"
    port.manufacturer = "Virtual serial port"
    port.device = device
    port.description = "Some serial port"

    return port


def usb_port(device="/dev/ttyUSB1234") -> USBDevice:

    return USBDevice(
        device=device,
        vid="10C4",
        pid="EA60",
        serial_number="1234",
        manufacturer="Virtual serial port",
        description="Some serial port",
    )


async def consume_progress_flow(
    hass: HomeAssistant,
    flow_id: str,
    valid_step_ids: tuple[str, ...],
    flow_manager: ConfigEntriesFlowManager | None = None,
) -> ConfigFlowResult:

    if flow_manager is None:
        flow_manager = hass.config_entries.flow

    while True:
        result = await flow_manager.async_configure(flow_id)
        flow_id = result["flow_id"]

        if result["type"] != FlowResultType.SHOW_PROGRESS:
            break

        assert result["type"] is FlowResultType.SHOW_PROGRESS
        assert result["step_id"] in valid_step_ids

        await asyncio.sleep(0.1)


    await hass.async_block_till_done()
    return result


class DelayedAsyncMock(AsyncMock):


    async def __call__(self, *args: Any, **kwargs: Any) -> Any:

        await asyncio.sleep(0)
        return await super().__call__(*args, **kwargs)


@pytest.mark.parametrize(
    ("entry_name", "unique_id", "radio_type", "service_info"),
    [
        (

            "tubeszb-cc2652-poe",
            "epid=aa:bb:cc:dd:ee:00:00:00",
            RadioType.znp,
            ZeroconfServiceInfo(
                ip_address=ip_address("192.168.1.200"),
                ip_addresses=[ip_address("192.168.1.200")],
                hostname="tubeszb-cc2652-poe.local.",
                name="tubeszb-cc2652-poe._esphomelib._tcp.local.",
                port=6053,
                type="_esphomelib._tcp.local.",
                properties={
                    "project_version": "3.0",
                    "project_name": "tubezb.cc2652-poe",
                    "network": "ethernet",
                    "board": "esp32-poe",
                    "platform": "ESP32",
                    "mac": "8c4b14c33c24",
                    "version": "2023.12.8",
                },
            ),
        ),
        (

            "tubeszb-efr32-poe",
            "epid=aa:bb:cc:dd:ee:00:00:00",
            RadioType.ezsp,
            ZeroconfServiceInfo(
                ip_address=ip_address("192.168.1.200"),
                ip_addresses=[ip_address("192.168.1.200")],
                hostname="tubeszb-efr32-poe.local.",
                name="tubeszb-efr32-poe._esphomelib._tcp.local.",
                port=6053,
                type="_esphomelib._tcp.local.",
                properties={
                    "project_version": "3.0",
                    "project_name": "tubezb.efr32-poe",
                    "network": "ethernet",
                    "board": "esp32-poe",
                    "platform": "ESP32",
                    "mac": "8c4b14c33c24",
                    "version": "2023.12.8",
                },
            ),
        ),
        (

            "TubeZB",
            "epid=aa:bb:cc:dd:ee:00:00:00",
            RadioType.znp,
            ZeroconfServiceInfo(
                ip_address=ip_address("192.168.1.200"),
                ip_addresses=[ip_address("192.168.1.200")],
                hostname="tubeszb-cc2652-poe.local.",
                name="tubeszb-cc2652-poe._tubeszb._tcp.local.",
                port=6638,
                properties={
                    "name": "TubeZB",
                    "radio_type": "znp",
                    "version": "1.0",
                    "baud_rate": "115200",
                    "data_flow_control": "software",
                },
                type="_tubeszb._tcp.local.",
            ),
        ),
        (

            "Some Zigbee Gateway (12345)",
            "epid=aa:bb:cc:dd:ee:00:00:00",
            RadioType.znp,
            ZeroconfServiceInfo(
                ip_address=ip_address("192.168.1.200"),
                ip_addresses=[ip_address("192.168.1.200")],
                hostname="some-zigbee-gateway-12345.local.",
                name="Some Zigbee Gateway (12345)._zigbee-coordinator._tcp.local.",
                port=6638,
                properties={"radio_type": "znp", "serial_number": "aabbccddeeff"},
                type="_zigbee-coordinator._tcp.local.",
            ),
        ),
    ],
)
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch(f"bellows.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_zeroconf_discovery(
    entry_name: str,
    unique_id: str,
    radio_type: RadioType,
    service_info: ZeroconfServiceInfo,
    hass: HomeAssistant,
) -> None:

    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=service_info
    )
    assert result_init["step_id"] == "confirm"


    result_confirm = await hass.config_entries.flow.async_configure(
        result_init["flow_id"], user_input={}
    )

    assert result_confirm["type"] is FlowResultType.MENU
    assert result_confirm["step_id"] == "choose_setup_strategy"

    result_setup = await hass.config_entries.flow.async_configure(
        result_confirm["flow_id"],
        user_input={"next_step_id": config_flow.SETUP_STRATEGY_RECOMMENDED},
    )

    result_form = await consume_progress_flow(
        hass,
        flow_id=result_setup["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()

    assert result_form["type"] is FlowResultType.CREATE_ENTRY
    assert result_form["title"] == entry_name
    assert result_form["context"]["unique_id"] == unique_id
    assert result_form["data"] == {
        CONF_DEVICE: {
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: None,
            CONF_DEVICE_PATH: "socket://192.168.1.200:6638",
        },
        CONF_RADIO_TYPE: radio_type.name,
    }


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
@patch(f"zigpy_zigate.{PROBE_FUNCTION_PATH}")
async def test_legacy_zeroconf_discovery_zigate(
    setup_entry_mock, hass: HomeAssistant
) -> None:

    service_info = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.200"),
        ip_addresses=[ip_address("192.168.1.200")],
        hostname="_zigate-zigbee-gateway.local.",
        name="some name._zigate-zigbee-gateway._tcp.local.",
        port=1234,
        properties={},
        type="mock_type",
    )
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=service_info
    )
    assert result_init["step_id"] == "confirm"


    result_confirm_deprecated = await hass.config_entries.flow.async_configure(
        result_init["flow_id"], user_input={}
    )
    assert result_confirm_deprecated["step_id"] == "verify_radio"
    assert "ZiGate" in result_confirm_deprecated["description_placeholders"]["name"]


    result_confirm = await hass.config_entries.flow.async_configure(
        result_confirm_deprecated["flow_id"], user_input={}
    )

    assert result_confirm["type"] is FlowResultType.MENU
    assert result_confirm["step_id"] == "choose_setup_strategy"

    result_setup = await hass.config_entries.flow.async_configure(
        result_confirm["flow_id"],
        user_input={"next_step_id": config_flow.SETUP_STRATEGY_RECOMMENDED},
    )

    result_form = await consume_progress_flow(
        hass,
        flow_id=result_setup["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()

    assert result_form["type"] is FlowResultType.CREATE_ENTRY
    assert result_form["title"] == "some name"
    assert result_form["data"] == {
        CONF_DEVICE: {
            CONF_DEVICE_PATH: "socket://192.168.1.200:1234",
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: None,
        },
        CONF_RADIO_TYPE: "zigate",
    }


async def test_zeroconf_discovery_bad_payload(hass: HomeAssistant) -> None:

    service_info = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.200"),
        ip_addresses=[ip_address("192.168.1.200")],
        hostname="some.hostname",
        name="any",
        port=1234,
        properties={"radio_type": "some bogus radio"},
        type="_zigbee-coordinator._tcp.local.",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=service_info
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_zeroconf_data"


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_legacy_zeroconf_discovery_ip_change_ignored(hass: HomeAssistant) -> None:


    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="tubeszb-cc2652-poe",
        source=config_entries.SOURCE_IGNORE,
    )
    entry.add_to_hass(hass)

    service_info = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.200"),
        ip_addresses=[ip_address("192.168.1.200")],
        hostname="tubeszb-cc2652-poe.local.",
        name="tubeszb-cc2652-poe._tubeszb._tcp.local.",
        port=6638,
        properties={
            "name": "TubeZB",
            "radio_type": "znp",
            "version": "1.0",
            "baud_rate": "115200",
            "data_flow_control": "software",
        },
        type="_tubeszb._tcp.local.",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=service_info
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_DEVICE] == {
        CONF_DEVICE_PATH: "socket://192.168.1.200:6638",
    }


async def test_legacy_zeroconf_discovery_confirm_final_abort_if_entries(
    hass: HomeAssistant,
) -> None:

    service_info = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.200"),
        ip_addresses=[ip_address("192.168.1.200")],
        hostname="tube._tube_zb_gw._tcp.local.",
        name="tube",
        port=6053,
        properties={"name": "tube_123456"},
        type="mock_type",
    )
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=service_info
    )
    assert flow["step_id"] == "confirm"


    with patch(
        "homeassistant.config_entries.ConfigFlow._async_current_entries",
        return_value=[MagicMock()],
    ):

        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input={}
        )


    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "choose_setup_strategy"


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_discovery_via_usb(hass: HomeAssistant) -> None:

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()

    assert result1["type"] is FlowResultType.FORM
    assert result1["step_id"] == "confirm"

    result2 = await hass.config_entries.flow.async_configure(
        result1["flow_id"], user_input={}
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.MENU
    assert result2["step_id"] == "choose_setup_strategy"

    with patch("homeassistant.components.zha.async_setup_entry", return_value=True):
        result_setup = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={"next_step_id": config_flow.SETUP_STRATEGY_RECOMMENDED},
        )

        result3 = await consume_progress_flow(
            hass,
            flow_id=result_setup["flow_id"],
            valid_step_ids=("form_new_network",),
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == "zigbee radio"
    assert result3["data"] == {
        "device": {
            "baudrate": 115200,
            "flow_control": None,
            "path": "/dev/ttyZIGBEE",
        },
        CONF_RADIO_TYPE: "znp",
    }


@patch(
    "homeassistant.components.zha.radio_manager.ZhaRadioManager.detect_radio_type",
    AsyncMock(return_value=ProbeResult.PROBING_FAILED),
)
async def test_discovery_via_usb_no_radio(hass: HomeAssistant) -> None:

    discovery_info = UsbServiceInfo(
        device="/dev/null",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    with patch("homeassistant.components.zha.async_setup_entry", return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "usb_probe_failed"


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_discovery_via_usb_already_setup(hass: HomeAssistant) -> None:


    MockConfigEntry(
        domain=DOMAIN, data={CONF_DEVICE: {CONF_DEVICE_PATH: "/dev/ttyUSB1"}}
    ).add_to_hass(hass)

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()

    confirm_result = await hass.config_entries.flow.async_configure(
        init_result["flow_id"],
        user_input={},
    )


    assert confirm_result["type"] is FlowResultType.MENU
    assert confirm_result["step_id"] == "choose_migration_strategy"


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_migration_strategy_recommended(
    hass: HomeAssistant, backup, mock_app
) -> None:

    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )

    with patch(
        "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
        return_value=[backup],
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
        )

        result_confirm = await hass.config_entries.flow.async_configure(
            result_init["flow_id"], user_input={}
        )

        assert result_confirm["step_id"] == "choose_migration_strategy"

    with (
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
        ) as mock_restore_backup,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_unload",
            return_value=True,
        ) as mock_async_unload,
    ):
        result_migrate = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"],
            user_input={"next_step_id": config_flow.MIGRATION_STRATEGY_RECOMMENDED},
        )

        result_recommended = await consume_progress_flow(
            hass,
            flow_id=result_migrate["flow_id"],
            valid_step_ids=("maybe_reset_old_radio", "restore_backup"),
        )

    assert mock_async_unload.mock_calls == [call(entry.entry_id)]
    assert result_recommended["type"] is FlowResultType.ABORT
    assert result_recommended["reason"] == "reconfigure_successful"
    mock_restore_backup.assert_called_once()


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_migration_strategy_recommended_cannot_write(
    hass: HomeAssistant, backup, mock_app
) -> None:

    MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DEVICE: {CONF_DEVICE_PATH: "/dev/ttyUSB1"},
            CONF_RADIO_TYPE: "ezsp",
        },
    ).add_to_hass(hass)

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )

    with patch(
        "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
        return_value=[backup],
    ):
        result_confirm = await hass.config_entries.flow.async_configure(
            result_init["flow_id"], user_input={}
        )

    assert result_confirm["step_id"] == "choose_migration_strategy"

    with patch(
        "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
        new_callable=DelayedAsyncMock,
        side_effect=CannotWriteNetworkSettings("test error"),
    ) as mock_restore_backup:
        result_migrate = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"],
            user_input={"next_step_id": config_flow.MIGRATION_STRATEGY_RECOMMENDED},
        )

        result_recommended = await consume_progress_flow(
            hass,
            flow_id=result_migrate["flow_id"],
            valid_step_ids=("maybe_reset_old_radio", "restore_backup"),
        )

    assert mock_restore_backup.call_count == 1
    assert result_recommended["type"] is FlowResultType.ABORT
    assert result_recommended["reason"] == "cannot_restore_backup"
    assert "test error" in result_recommended["description_placeholders"]["error"]


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_multiple_zha_entries_aborts(hass: HomeAssistant, mock_app) -> None:

    MockConfigEntry(
        domain=DOMAIN, data={CONF_DEVICE: {CONF_DEVICE_PATH: "/dev/ttyUSB1"}}
    ).add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, data={CONF_DEVICE: {CONF_DEVICE_PATH: "/dev/ttyUSB2"}}
    ).add_to_hass(hass)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )

    result_confirm = await hass.config_entries.flow.async_configure(
        result_init["flow_id"], user_input={}
    )

    assert result_confirm["step_id"] == "choose_migration_strategy"

    result_recommended = await hass.config_entries.flow.async_configure(
        result_confirm["flow_id"],
        user_input={"next_step_id": config_flow.MIGRATION_STRATEGY_ADVANCED},
    )

    result_reuse = await hass.config_entries.flow.async_configure(
        result_recommended["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_REUSE_SETTINGS},
    )

    assert result_reuse["type"] is FlowResultType.ABORT
    assert result_reuse["reason"] == "single_instance_allowed"


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_discovery_via_usb_duplicate_unique_id(hass: HomeAssistant) -> None:


    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AAAA:AAAA_1234_test_zigbee radio",
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB1",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            }
        },
    )
    entry.add_to_hass(hass)

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_discovery_via_usb_deconz_already_discovered(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        "deconz",
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location="http://1.2.3.4:80/",
            upnp={
                ATTR_UPNP_MANUFACTURER_URL: "http://www.dresden-elektronik.de",
                ATTR_UPNP_SERIAL: "0000000000000000",
            },
        ),
        context={"source": SOURCE_SSDP},
    )
    await hass.async_block_till_done()
    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_zha_device"


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_discovery_via_usb_deconz_already_setup(hass: HomeAssistant) -> None:

    MockConfigEntry(domain="deconz", data={}).add_to_hass(hass)
    await hass.async_block_till_done()
    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_zha_device"


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_discovery_via_usb_deconz_ignored(hass: HomeAssistant) -> None:

    MockConfigEntry(
        domain="deconz", source=config_entries.SOURCE_IGNORE, data={}
    ).add_to_hass(hass)
    await hass.async_block_till_done()
    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_discovery_via_usb_zha_ignored_updates(hass: HomeAssistant) -> None:

    entry = MockConfigEntry(
        domain=DOMAIN,
        source=config_entries.SOURCE_IGNORE,
        data={},
        unique_id="AAAA:AAAA_1234_test_zigbee radio",
    )
    entry.add_to_hass(hass)
    await hass.async_block_till_done()
    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_DEVICE] == {
        CONF_DEVICE_PATH: "/dev/ttyZIGBEE",
    }


async def test_discovery_via_usb_same_device_already_setup(hass: HomeAssistant) -> None:

    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE: {CONF_DEVICE_PATH: "/dev/serial/by-id/usb-device123"}},
    ).add_to_hass(hass)


    discovery_info = UsbServiceInfo(
        device="/dev/ttyUSB0",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )

    with patch(
        "homeassistant.components.zha.config_flow.usb.get_serial_by_id",
        return_value="/dev/serial/by-id/usb-device123",
    ) as mock_get_serial_by_id:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
        )
        await hass.async_block_till_done()


    assert mock_get_serial_by_id.mock_calls == [call("/dev/ttyUSB0")]


    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_legacy_zeroconf_discovery_already_setup(hass: HomeAssistant) -> None:

    service_info = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.200"),
        ip_addresses=[ip_address("192.168.1.200")],
        hostname="_tube_zb_gw._tcp.local.",
        name="mock_name",
        port=6053,
        properties={"name": "tube_123456"},
        type="mock_type",
    )

    MockConfigEntry(
        domain=DOMAIN, data={CONF_DEVICE: {CONF_DEVICE_PATH: "/dev/ttyUSB1"}}
    ).add_to_hass(hass)

    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=service_info
    )
    await hass.async_block_till_done()

    confirm_result = await hass.config_entries.flow.async_configure(
        init_result["flow_id"],
        user_input={},
    )


    assert confirm_result["type"] is FlowResultType.MENU
    assert confirm_result["step_id"] == "choose_migration_strategy"


async def test_zeroconf_discovery_via_socket_already_setup_with_ip_match(
    hass: HomeAssistant,
) -> None:

    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE: {CONF_DEVICE_PATH: "socket://192.168.1.101:6638"}},
    ).add_to_hass(hass)

    service_info = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.100"),
        ip_addresses=[
            ip_address("192.168.1.100"),
            ip_address("192.168.1.101"),
        ],
        hostname="tube-zigbee-gw.local.",
        name="mock_name",
        port=6638,
        properties={"name": "tube_123456"},
        type="mock_type",
    )


    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=service_info
    )
    await hass.async_block_till_done()


    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_zeroconf_not_onboarded(hass: HomeAssistant) -> None:

    service_info = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.100"),
        ip_addresses=[ip_address("192.168.1.100")],
        hostname="tube-zigbee-gw.local.",
        name="mock_name",
        port=6638,
        properties={"name": "tube_123456"},
        type="mock_type",
    )
    with patch(
        "homeassistant.components.onboarding.async_is_onboarded", return_value=False
    ):
        result_create = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=service_info,
        )
        await hass.async_block_till_done()


    assert result_create["type"] is FlowResultType.FORM
    assert result_create["step_id"] == "confirm"


@patch(
    "homeassistant.components.zha.radio_manager.ZhaRadioManager.detect_radio_type",
    mock_detect_radio_type(radio_type=RadioType.deconz),
)
@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(return_value=[usb_port()]),
)
async def test_user_flow(hass: HomeAssistant) -> None:


    port = usb_port()
    port_select = f"{port.device} - {port.description}, s/n: {port.serial_number} - {port.manufacturer}"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data={
            zigpy.config.CONF_DEVICE_PATH: port_select,
        },
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "choose_setup_strategy"

    with patch("homeassistant.components.zha.async_setup_entry", return_value=True):
        result_setup = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": config_flow.SETUP_STRATEGY_RECOMMENDED},
        )

        result2 = await consume_progress_flow(
            hass,
            flow_id=result_setup["flow_id"],
            valid_step_ids=("form_new_network",),
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"].startswith(port.description)
    assert result2["data"] == {
        "device": {
            "path": port.device,
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: None,
        },
        CONF_RADIO_TYPE: "deconz",
    }


@patch(
    "homeassistant.components.zha.radio_manager.ZhaRadioManager.detect_radio_type",
    AsyncMock(return_value=ProbeResult.PROBING_FAILED),
)
@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(return_value=[usb_port()]),
)
async def test_user_flow_not_detected(hass: HomeAssistant) -> None:


    port = com_port()
    port_select = f"{port}, s/n: {port.serial_number} - {port.manufacturer}"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data={
            zigpy.config.CONF_DEVICE_PATH: port_select,
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: None,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual_pick_radio_type"


@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(return_value=[usb_port()]),
)
async def test_user_flow_show_form(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "choose_serial_port"


@pytest.mark.usefixtures("addon_not_installed")
@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(return_value=[]),
)
async def test_user_flow_show_manual(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual_pick_radio_type"


async def test_user_flow_manual(hass: HomeAssistant) -> None:


    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data={zigpy.config.CONF_DEVICE_PATH: config_flow.CONF_MANUAL_PATH},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual_pick_radio_type"


@pytest.mark.parametrize("radio_type", RadioType.list())
async def test_pick_radio_flow(hass: HomeAssistant, radio_type) -> None:


    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: "manual_pick_radio_type"},
        data={CONF_RADIO_TYPE: radio_type},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual_port_config"


@patch(f"bellows.{PROBE_FUNCTION_PATH}", return_value=False)
@patch(f"zigpy_deconz.{PROBE_FUNCTION_PATH}", return_value=False)
@patch(f"zigpy_zigate.{PROBE_FUNCTION_PATH}", return_value=False)
@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", return_value=True)
async def test_detect_radio_type_success(
    znp_probe, zigate_probe, deconz_probe, bellows_probe, hass: HomeAssistant
) -> None:


    handler = config_flow.ZhaConfigFlowHandler()
    handler._radio_mgr.device_path = "/dev/null"
    handler.hass = hass

    await handler._radio_mgr.detect_radio_type()

    assert handler._radio_mgr.radio_type == RadioType.znp
    assert (
        handler._radio_mgr.device_settings[zigpy.config.CONF_DEVICE_PATH] == "/dev/null"
    )

    assert bellows_probe.await_count == 1
    assert znp_probe.await_count == 1
    assert deconz_probe.await_count == 0
    assert zigate_probe.await_count == 0


@patch(
    f"bellows.{PROBE_FUNCTION_PATH}",
    return_value={"new_setting": 123, zigpy.config.CONF_DEVICE_PATH: "/dev/null"},
)
@patch(f"zigpy_deconz.{PROBE_FUNCTION_PATH}", return_value=False)
@patch(f"zigpy_zigate.{PROBE_FUNCTION_PATH}", return_value=False)
@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", return_value=False)
async def test_detect_radio_type_success_with_settings(
    znp_probe, zigate_probe, deconz_probe, bellows_probe, hass: HomeAssistant
) -> None:


    handler = config_flow.ZhaConfigFlowHandler()
    handler._radio_mgr.device_path = "/dev/null"
    handler.hass = hass

    await handler._radio_mgr.detect_radio_type()

    assert handler._radio_mgr.radio_type == RadioType.ezsp
    assert handler._radio_mgr.device_settings["new_setting"] == 123
    assert (
        handler._radio_mgr.device_settings[zigpy.config.CONF_DEVICE_PATH] == "/dev/null"
    )

    assert bellows_probe.await_count == 1
    assert znp_probe.await_count == 0
    assert deconz_probe.await_count == 0
    assert zigate_probe.await_count == 0


@patch(f"bellows.{PROBE_FUNCTION_PATH}", return_value=False)
async def test_user_port_config_fail(probe_mock, hass: HomeAssistant) -> None:


    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: "manual_pick_radio_type"},
        data={CONF_RADIO_TYPE: RadioType.ezsp.description},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE_PATH: "/dev/ttyUSB33",
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: "none",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual_port_config"
    assert result["errors"]["base"] == "cannot_connect"
    assert probe_mock.await_count == 1


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
@patch(f"bellows.{PROBE_FUNCTION_PATH}", return_value=True)
async def test_user_port_config(probe_mock, hass: HomeAssistant) -> None:


    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: "manual_pick_radio_type"},
        data={CONF_RADIO_TYPE: RadioType.ezsp.description},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={zigpy.config.CONF_DEVICE_PATH: "/dev/ttyUSB33"},
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "choose_setup_strategy"

    result_setup = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.SETUP_STRATEGY_RECOMMENDED},
    )

    result2 = await consume_progress_flow(
        hass,
        flow_id=result_setup["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()

    assert (
        result2["data"][zigpy.config.CONF_DEVICE][zigpy.config.CONF_DEVICE_PATH]
        == "/dev/ttyUSB33"
    )
    assert result2["data"][CONF_RADIO_TYPE] == "ezsp"
    assert probe_mock.await_count == 1


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_hardware_not_onboarded(hass: HomeAssistant) -> None:

    data = {
        "name": "Yellow",
        "radio_type": "efr32",
        "port": {
            "path": "/dev/ttyAMA1",
            "baudrate": 115200,
            "flow_control": "hardware",
        },
    }
    with patch(
        "homeassistant.components.onboarding.async_is_onboarded", return_value=False
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HARDWARE}, data=data
        )

        result_create = await consume_progress_flow(
            hass,
            flow_id=result_init["flow_id"],
            valid_step_ids=("form_new_network",),
        )
        await hass.async_block_till_done()

    assert result_create["title"] == "Yellow"
    assert result_create["data"] == {
        CONF_DEVICE: {
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: "hardware",
            CONF_DEVICE_PATH: "/dev/ttyAMA1",
        },
        CONF_RADIO_TYPE: "ezsp",
    }


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_hardware_no_flow_strategy(hass: HomeAssistant) -> None:

    data = {
        "name": "Yellow",
        "radio_type": "efr32",
        "port": {
            "path": "/dev/ttyAMA1",
            "baudrate": 115200,
            "flow_control": "hardware",
        },
    }
    with patch(
        "homeassistant.components.onboarding.async_is_onboarded", return_value=True
    ):
        result1 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HARDWARE}, data=data
        )


    assert result1["type"] is FlowResultType.FORM
    assert result1["step_id"] == "confirm"

    result2 = await hass.config_entries.flow.async_configure(
        result1["flow_id"],
        user_input={},
    )

    assert result2["type"] is FlowResultType.MENU
    assert result2["step_id"] == "choose_setup_strategy"

    result_setup = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={"next_step_id": config_flow.SETUP_STRATEGY_RECOMMENDED},
    )

    result_create = await consume_progress_flow(
        hass,
        flow_id=result_setup["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()

    assert result_create["title"] == "Yellow"
    assert result_create["data"] == {
        CONF_DEVICE: {
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: "hardware",
            CONF_DEVICE_PATH: "/dev/ttyAMA1",
        },
        CONF_RADIO_TYPE: "ezsp",
    }


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_hardware_flow_strategy_advanced(hass: HomeAssistant) -> None:

    data = {
        "name": "Yellow",
        "radio_type": "efr32",
        "port": {
            "path": "/dev/ttyAMA1",
            "baudrate": 115200,
            "flow_control": "hardware",
        },
        "flow_strategy": "advanced",
    }
    with patch(
        "homeassistant.components.onboarding.async_is_onboarded", return_value=True
    ):
        result_hardware = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HARDWARE}, data=data
        )

    assert result_hardware["type"] is FlowResultType.FORM
    assert result_hardware["step_id"] == "confirm"

    confirm_result = await hass.config_entries.flow.async_configure(
        result_hardware["flow_id"],
        user_input={},
    )

    assert confirm_result["type"] is FlowResultType.MENU
    assert confirm_result["step_id"] == "choose_formation_strategy"

    result_form = await hass.config_entries.flow.async_configure(
        confirm_result["flow_id"],
        user_input={"next_step_id": "form_new_network"},
    )

    result_create = await consume_progress_flow(
        hass,
        flow_id=result_form["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()

    assert result_create["type"] is FlowResultType.CREATE_ENTRY
    assert result_create["title"] == "Yellow"
    assert result_create["data"] == {
        CONF_DEVICE: {
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: "hardware",
            CONF_DEVICE_PATH: "/dev/ttyAMA1",
        },
        CONF_RADIO_TYPE: "ezsp",
    }


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_hardware_flow_strategy_recommended(hass: HomeAssistant) -> None:

    data = {
        "name": "Yellow",
        "radio_type": "efr32",
        "port": {
            "path": "/dev/ttyAMA1",
            "baudrate": 115200,
            "flow_control": "hardware",
        },
        "flow_strategy": "recommended",
    }
    with patch(
        "homeassistant.components.onboarding.async_is_onboarded", return_value=True
    ):
        result_hardware = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HARDWARE}, data=data
        )

    assert result_hardware["type"] is FlowResultType.FORM
    assert result_hardware["step_id"] == "confirm"

    result_confirm = await hass.config_entries.flow.async_configure(
        result_hardware["flow_id"],
        user_input={},
    )

    result_create = await consume_progress_flow(
        hass,
        flow_id=result_confirm["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()

    assert result_create["type"] is FlowResultType.CREATE_ENTRY
    assert result_create["title"] == "Yellow"
    assert result_create["data"] == {
        CONF_DEVICE: {
            CONF_BAUDRATE: 115200,
            CONF_FLOW_CONTROL: "hardware",
            CONF_DEVICE_PATH: "/dev/ttyAMA1",
        },
        CONF_RADIO_TYPE: "ezsp",
    }


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_hardware_migration_flow_strategy_advanced(
    hass: HomeAssistant,
    backup: zigpy.backups.NetworkBackup,
    mock_app: AsyncMock,
) -> None:

    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    data = {
        "name": "Yellow",
        "radio_type": "efr32",
        "port": {
            "path": "/dev/ttyAMA1",
            "baudrate": 115200,
            "flow_control": "hardware",
        },
        "flow_strategy": "advanced",
    }
    with (
        patch(
            "homeassistant.components.onboarding.async_is_onboarded", return_value=True
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
            return_value=[backup],
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
        ) as mock_restore_backup,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_unload",
            return_value=True,
        ) as mock_async_unload,
    ):
        result_hardware = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HARDWARE}, data=data
        )

        assert result_hardware["type"] is FlowResultType.FORM
        assert result_hardware["step_id"] == "confirm"

        result_confirm = await hass.config_entries.flow.async_configure(
            result_hardware["flow_id"], user_input={}
        )

        assert result_confirm["type"] is FlowResultType.MENU
        assert result_confirm["step_id"] == "choose_formation_strategy"

        result_form = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"],
            user_input={"next_step_id": "form_new_network"},
        )

        result_formation_strategy = await consume_progress_flow(
            hass,
            flow_id=result_form["flow_id"],
            valid_step_ids=("form_new_network",),
        )
        await hass.async_block_till_done()

    assert result_formation_strategy["type"] is FlowResultType.ABORT
    assert result_formation_strategy["reason"] == "reconfigure_successful"
    assert mock_async_unload.call_count == 0
    assert mock_restore_backup.call_count == 0


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_hardware_migration_flow_strategy_recommended(
    hass: HomeAssistant,
    backup: zigpy.backups.NetworkBackup,
    mock_app: AsyncMock,
) -> None:

    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    data = {
        "name": "Yellow",
        "radio_type": "efr32",
        "port": {
            "path": "/dev/ttyAMA1",
            "baudrate": 115200,
            "flow_control": "hardware",
        },
        "flow_strategy": "recommended",
    }
    with (
        patch(
            "homeassistant.components.onboarding.async_is_onboarded", return_value=True
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
            return_value=[backup],
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
        ) as mock_restore_backup,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_unload",
            return_value=True,
        ) as mock_async_unload,
    ):
        result_hardware = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HARDWARE}, data=data
        )

        assert result_hardware["type"] is FlowResultType.FORM
        assert result_hardware["step_id"] == "confirm"

        result_migrate = await hass.config_entries.flow.async_configure(
            result_hardware["flow_id"], user_input={}
        )

        result_confirm = await consume_progress_flow(
            hass,
            flow_id=result_migrate["flow_id"],
            valid_step_ids=("maybe_reset_old_radio", "restore_backup"),
        )

    assert result_confirm["type"] is FlowResultType.ABORT
    assert result_confirm["reason"] == "reconfigure_successful"
    assert mock_async_unload.mock_calls == [call(entry.entry_id)]
    assert mock_restore_backup.call_count == 1


@pytest.mark.parametrize(
    "data", [None, {}, {"radio_type": "best_radio"}, {"radio_type": "efr32"}]
)
async def test_hardware_invalid_data(hass: HomeAssistant, data) -> None:


    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_HARDWARE}, data=data
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_hardware_data"


def test_allow_overwrite_ezsp_ieee() -> None:

    backup = zigpy.backups.NetworkBackup()
    new_backup = radio_manager._allow_overwrite_ezsp_ieee(backup)

    assert backup != new_backup
    assert new_backup.network_info.stack_specific["ezsp"][EZSP_OVERWRITE_EUI64] is True


def test_prevent_overwrite_ezsp_ieee() -> None:

    backup = zigpy.backups.NetworkBackup()
    backup.network_info.stack_specific["ezsp"] = {EZSP_OVERWRITE_EUI64: True}
    new_backup = radio_manager._prevent_overwrite_ezsp_ieee(backup)

    assert backup != new_backup
    assert not new_backup.network_info.stack_specific.get("ezsp", {}).get(
        EZSP_OVERWRITE_EUI64
    )


@pytest.fixture
def advanced_pick_radio(
    hass: HomeAssistant,
) -> Generator[RadioPicker]:


    async def wrapper(radio_type: RadioType) -> tuple[ConfigFlowResult, ListPortInfo]:
        port = com_port()
        port_select = f"{port}, s/n: {port.serial_number} - {port.manufacturer}"

        with patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.detect_radio_type",
            mock_detect_radio_type(radio_type=radio_type),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={CONF_SOURCE: SOURCE_USER},
                data={
                    zigpy.config.CONF_DEVICE_PATH: port_select,
                },
            )

        assert result["type"] is FlowResultType.MENU
        assert result["step_id"] == "choose_setup_strategy"

        advanced_strategy_result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": config_flow.SETUP_STRATEGY_ADVANCED},
        )

        assert advanced_strategy_result["type"] is FlowResultType.MENU
        assert advanced_strategy_result["step_id"] == "choose_formation_strategy"

        return advanced_strategy_result

    p1 = patch(
        "homeassistant.components.zha.config_flow.list_serial_ports",
        AsyncMock(return_value=[usb_port()]),
    )
    p2 = patch("homeassistant.components.zha.async_setup_entry")

    with p1, p2:
        yield wrapper


async def test_strategy_no_network_settings(
    advanced_pick_radio: RadioPicker, mock_app: AsyncMock, hass: HomeAssistant
) -> None:

    mock_app.load_network_info = DelayedAsyncMock(side_effect=NetworkNotFormed())

    result = await advanced_pick_radio(RadioType.ezsp)
    assert (
        config_flow.FORMATION_REUSE_SETTINGS
        not in result["data_schema"].schema["next_step_id"].container
    )


async def test_formation_strategy_form_new_network(
    advanced_pick_radio: RadioPicker, mock_app: AsyncMock, hass: HomeAssistant
) -> None:

    result = await advanced_pick_radio(RadioType.ezsp)

    result_form = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_FORM_NEW_NETWORK},
    )

    result2 = await consume_progress_flow(
        hass,
        flow_id=result_form["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()


    mock_app.form_network.assert_called_once()

    assert result2["type"] is FlowResultType.CREATE_ENTRY


async def test_formation_strategy_form_initial_network(
    advanced_pick_radio: RadioPicker, mock_app: AsyncMock, hass: HomeAssistant
) -> None:


    mock_app.load_network_info = DelayedAsyncMock(side_effect=NetworkNotFormed())


    async def form_network_side_effect(*args, **kwargs):
        mock_app.load_network_info = AsyncMock(return_value=mock_app.state.network_info)

    mock_app.form_network.side_effect = form_network_side_effect

    result = await advanced_pick_radio(RadioType.ezsp)
    result_form = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_FORM_INITIAL_NETWORK},
    )

    result2 = await consume_progress_flow(
        hass,
        flow_id=result_form["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()


    mock_app.form_network.assert_called_once()

    assert result2["type"] is FlowResultType.CREATE_ENTRY


async def test_formation_strategy_form_initial_network_failure(
    advanced_pick_radio: RadioPicker, mock_app: AsyncMock, hass: HomeAssistant
) -> None:


    mock_app.form_network.side_effect = DelayedAsyncMock(
        side_effect=Exception("Network formation failed")
    )

    result = await advanced_pick_radio(RadioType.ezsp)
    result_form = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_FORM_NEW_NETWORK},
    )

    result2 = await consume_progress_flow(
        hass,
        flow_id=result_form["flow_id"],
        valid_step_ids=("form_new_network",),
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "cannot_form_network"
    assert "Network formation failed" in result2["description_placeholders"]["error"]


    mock_app.form_network.assert_called_once()


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_onboarding_auto_formation_new_hardware(
    mock_app: AsyncMock, hass: HomeAssistant
) -> None:


    mock_app.load_network_info = DelayedAsyncMock(side_effect=NetworkNotFormed())
    mock_app.get_device = MagicMock(return_value=MagicMock(spec=zigpy.device.Device))


    async def form_network_side_effect(*args, **kwargs):
        mock_app.load_network_info = AsyncMock(return_value=mock_app.state.network_info)

    mock_app.form_network.side_effect = form_network_side_effect

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )

    with patch(
        "homeassistant.components.onboarding.async_is_onboarded", return_value=False
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
        )

        result = await consume_progress_flow(
            hass,
            flow_id=result_init["flow_id"],
            valid_step_ids=("form_new_network",),
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "zigbee radio"
    assert result["data"] == {
        "device": {
            "baudrate": 115200,
            "flow_control": None,
            "path": "/dev/ttyZIGBEE",
        },
        CONF_RADIO_TYPE: "znp",
    }


async def test_formation_strategy_reuse_settings(
    advanced_pick_radio: RadioPicker, mock_app: AsyncMock, hass: HomeAssistant
) -> None:

    result = await advanced_pick_radio(RadioType.ezsp)

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_REUSE_SETTINGS},
    )
    await hass.async_block_till_done()


    mock_app.write_network_info.assert_not_called()

    assert result2["type"] is FlowResultType.CREATE_ENTRY


@patch("homeassistant.components.zha.config_flow.process_uploaded_file")
def test_parse_uploaded_backup(process_mock) -> None:

    backup = zigpy.backups.NetworkBackup()

    text = json.dumps(backup.as_dict())
    process_mock.return_value.__enter__.return_value.read_text.return_value = text

    handler = config_flow.ZhaConfigFlowHandler()
    parsed_backup = handler._parse_uploaded_backup(str(uuid.uuid4()))

    assert backup == parsed_backup


@patch("homeassistant.components.zha.radio_manager._allow_overwrite_ezsp_ieee")
async def test_formation_strategy_restore_manual_backup_non_ezsp(
    allow_overwrite_ieee_mock,
    advanced_pick_radio: RadioPicker,
    mock_app: AsyncMock,
    hass: HomeAssistant,
) -> None:

    result = await advanced_pick_radio(RadioType.znp)

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_UPLOAD_MANUAL_BACKUP},
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "upload_manual_backup"

    with patch(
        "homeassistant.components.zha.config_flow.ZhaConfigFlowHandler._parse_uploaded_backup",
        return_value=zigpy.backups.NetworkBackup(),
    ):
        result_upload = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={config_flow.UPLOADED_BACKUP_FILE: str(uuid.uuid4())},
        )

        result3 = await consume_progress_flow(
            hass,
            flow_id=result_upload["flow_id"],
            valid_step_ids=("restore_backup",),
        )

    mock_app.backups.restore_backup.assert_called_once()
    allow_overwrite_ieee_mock.assert_not_called()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"][CONF_RADIO_TYPE] == "znp"


@patch("homeassistant.components.zha.radio_manager._allow_overwrite_ezsp_ieee")
async def test_formation_strategy_restore_manual_backup_overwrite_ieee_ezsp(
    allow_overwrite_ieee_mock,
    advanced_pick_radio: RadioPicker,
    mock_app: AsyncMock,
    backup,
    hass: HomeAssistant,
) -> None:

    result = await advanced_pick_radio(RadioType.ezsp)

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_UPLOAD_MANUAL_BACKUP},
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "upload_manual_backup"

    with (
        patch(
            "homeassistant.components.zha.config_flow.ZhaConfigFlowHandler._parse_uploaded_backup",
            return_value=backup,
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
            new_callable=DelayedAsyncMock,
            side_effect=[
                DestructiveWriteNetworkSettings("Radio IEEE change is permanent"),
                None,
            ],
        ) as mock_restore_backup,
    ):
        result_upload = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={config_flow.UPLOADED_BACKUP_FILE: str(uuid.uuid4())},
        )

        result3 = await consume_progress_flow(
            hass,
            flow_id=result_upload["flow_id"],
            valid_step_ids=("restore_backup",),
        )

        assert mock_restore_backup.call_count == 1
        assert not mock_restore_backup.mock_calls[0].kwargs.get("overwrite_ieee")
        mock_restore_backup.reset_mock()


        assert result3["type"] is FlowResultType.FORM
        assert result3["step_id"] == "confirm_ezsp_ieee_overwrite"

        result_confirm = await hass.config_entries.flow.async_configure(
            result3["flow_id"],
            user_input={config_flow.OVERWRITE_COORDINATOR_IEEE: True},
        )

        result_final = await consume_progress_flow(
            hass,
            flow_id=result_confirm["flow_id"],
            valid_step_ids=("restore_backup",),
        )

    assert result_final["type"] is FlowResultType.CREATE_ENTRY
    assert result_final["data"][CONF_RADIO_TYPE] == "ezsp"

    assert mock_restore_backup.call_count == 1
    assert mock_restore_backup.mock_calls[0].kwargs["overwrite_ieee"] is True


@patch("homeassistant.components.zha.radio_manager._allow_overwrite_ezsp_ieee")
async def test_formation_strategy_restore_manual_backup_ezsp(
    allow_overwrite_ieee_mock,
    advanced_pick_radio: RadioPicker,
    mock_app: AsyncMock,
    hass: HomeAssistant,
) -> None:

    result = await advanced_pick_radio(RadioType.ezsp)

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_UPLOAD_MANUAL_BACKUP},
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "upload_manual_backup"

    with (
        patch(
            "homeassistant.components.zha.config_flow.ZhaConfigFlowHandler._parse_uploaded_backup",
            return_value=backup,
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
            new_callable=DelayedAsyncMock,
            side_effect=[
                DestructiveWriteNetworkSettings("Radio IEEE change is permanent"),
                None,
            ],
        ) as mock_restore_backup,
    ):
        result_upload = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={config_flow.UPLOADED_BACKUP_FILE: str(uuid.uuid4())},
        )

        result3 = await consume_progress_flow(
            hass,
            flow_id=result_upload["flow_id"],
            valid_step_ids=("restore_backup",),
        )

        assert mock_restore_backup.call_count == 1
        assert not mock_restore_backup.mock_calls[0].kwargs.get("overwrite_ieee")
        mock_restore_backup.reset_mock()


        assert result3["type"] is FlowResultType.FORM
        assert result3["step_id"] == "confirm_ezsp_ieee_overwrite"

        result4 = await hass.config_entries.flow.async_configure(
            result3["flow_id"],

            user_input={config_flow.OVERWRITE_COORDINATOR_IEEE: False},
        )

    assert result4["type"] is FlowResultType.ABORT
    assert result4["reason"] == "cannot_restore_backup_no_ieee_confirm"
    assert mock_restore_backup.call_count == 0


async def test_formation_strategy_restore_manual_backup_invalid_upload(
    advanced_pick_radio: RadioPicker, mock_app: AsyncMock, hass: HomeAssistant
) -> None:

    result = await advanced_pick_radio(RadioType.ezsp)

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_UPLOAD_MANUAL_BACKUP},
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "upload_manual_backup"

    with patch(
        "homeassistant.components.zha.config_flow.ZhaConfigFlowHandler._parse_uploaded_backup",
        side_effect=ValueError("Invalid backup JSON"),
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={config_flow.UPLOADED_BACKUP_FILE: str(uuid.uuid4())},
        )

    mock_app.backups.restore_backup.assert_not_called()

    assert result3["type"] is FlowResultType.FORM
    assert result3["step_id"] == "upload_manual_backup"
    assert result3["errors"]["base"] == "invalid_backup_json"


def test_format_backup_choice() -> None:

    backup = zigpy.backups.NetworkBackup()
    backup.network_info.pan_id = zigpy.types.PanId(0x1234)
    backup.network_info.extended_pan_id = zigpy.types.EUI64.convert(
        "aa:bb:cc:dd:ee:ff:00:11"
    )

    with_ids = config_flow._format_backup_choice(backup, pan_ids=True)
    without_ids = config_flow._format_backup_choice(backup, pan_ids=False)

    assert with_ids.startswith(without_ids)
    assert "1234:aabbccddeeff0011" in with_ids
    assert "1234:aabbccddeeff0011" not in without_ids


@patch(
    "homeassistant.components.zha.config_flow._format_backup_choice",
    lambda s, **kwargs: "choice:" + repr(s),
)
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_formation_strategy_restore_automatic_backup_ezsp(
    advanced_pick_radio: RadioPicker,
    mock_app: AsyncMock,
    make_backup,
    hass: HomeAssistant,
) -> None:

    mock_app.backups.backups = [
        make_backup(),
        make_backup(),
        make_backup(),
    ]
    backup = mock_app.backups.backups[1]
    backup.is_compatible_with = MagicMock(return_value=False)

    result = await advanced_pick_radio(RadioType.ezsp)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": (config_flow.FORMATION_CHOOSE_AUTOMATIC_BACKUP)},
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "choose_automatic_backup"

    result_backup = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            config_flow.CHOOSE_AUTOMATIC_BACKUP: "choice:" + repr(backup),
        },
    )

    result3 = await consume_progress_flow(
        hass,
        flow_id=result_backup["flow_id"],
        valid_step_ids=("restore_backup",),
    )

    mock_app.backups.restore_backup.assert_called_once()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"][CONF_RADIO_TYPE] == "ezsp"


@patch(
    "homeassistant.components.zha.config_flow._format_backup_choice",
    lambda s, **kwargs: "choice:" + repr(s),
)
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
@pytest.mark.parametrize("is_advanced", [True, False])
async def test_formation_strategy_restore_automatic_backup_non_ezsp(
    is_advanced,
    advanced_pick_radio: RadioPicker,
    mock_app: AsyncMock,
    make_backup,
    hass: HomeAssistant,
) -> None:

    mock_app.backups.backups = [
        make_backup(backup_time_offset=5),
        make_backup(backup_time_offset=-3),
        make_backup(backup_time_offset=2),
    ]
    backup = mock_app.backups.backups[1]
    backup.is_compatible_with = MagicMock(return_value=False)

    result = await advanced_pick_radio(RadioType.znp)

    with patch(
        "homeassistant.config_entries.ConfigFlow.show_advanced_options",
        new_callable=PropertyMock(return_value=is_advanced),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "next_step_id": (config_flow.FORMATION_CHOOSE_AUTOMATIC_BACKUP)
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "choose_automatic_backup"


    assert config_flow.OVERWRITE_COORDINATOR_IEEE not in result2["data_schema"].schema


    assert result2["data_schema"].schema["choose_automatic_backup"].container == [
        f"choice:{mock_app.backups.backups[0]!r}",
        f"choice:{mock_app.backups.backups[2]!r}",
        f"choice:{mock_app.backups.backups[1]!r}",
    ]

    result_backup = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            config_flow.CHOOSE_AUTOMATIC_BACKUP: f"choice:{backup!r}",
        },
    )

    result3 = await consume_progress_flow(
        hass,
        flow_id=result_backup["flow_id"],
        valid_step_ids=("restore_backup",),
    )

    mock_app.backups.restore_backup.assert_called_once_with(backup)

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"][CONF_RADIO_TYPE] == "znp"


@patch("homeassistant.components.zha.async_setup_entry", return_value=True)
async def test_options_flow_creates_backup(
    async_setup_entry, hass: HomeAssistant, mock_app
) -> None:

    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    zha_gateway = MagicMock()
    zha_gateway.application_controller = mock_app

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    with patch(
        "homeassistant.components.zha.config_flow.get_zha_gateway",
        return_value=zha_gateway,
    ):
        flow = await hass.config_entries.options.async_init(entry.entry_id)

        assert flow["step_id"] == "init"

        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload", return_value=True
        ) as mock_async_unload:
            result = await hass.config_entries.options.async_configure(
                flow["flow_id"], user_input={}
            )

    mock_app.backups.create_backup.assert_called_once_with(load_devices=True)
    mock_async_unload.assert_called_once_with(entry.entry_id)

    assert result["step_id"] == "prompt_migrate_or_reconfigure"


@pytest.mark.parametrize(
    "async_unload_effect", [True, config_entries.OperationNotAllowed()]
)
@pytest.mark.parametrize(
    ("input_flow_control", "conf_flow_control"),
    [
        ("hardware", "hardware"),
        ("software", "software"),
        ("none", None),
    ],
)
@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(
        return_value=[
            usb_port("/dev/SomePort"),
            usb_port("/dev/ttyUSB0"),
            usb_port("/dev/SomeOtherPort"),
        ]
    ),
)
@patch("homeassistant.components.zha.async_setup_entry", return_value=True)
async def test_options_flow_defaults(
    async_setup_entry,
    async_unload_effect,
    input_flow_control,
    conf_flow_control,
    hass: HomeAssistant,
) -> None:


    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
                CONF_BAUDRATE: 12345,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flow = await hass.config_entries.options.async_init(entry.entry_id)

    async_setup_entry.reset_mock()


    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload",
        new_callable=DelayedAsyncMock,
        side_effect=[async_unload_effect],
    ) as mock_async_unload:
        result1 = await hass.config_entries.options.async_configure(
            flow["flow_id"], user_input={}
        )

    mock_async_unload.assert_called_once_with(entry.entry_id)


    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)


    assert result1["step_id"] == "prompt_migrate_or_reconfigure"
    result2 = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={"next_step_id": config_flow.OptionsMigrationIntent.RECONFIGURE},
    )


    assert result2["step_id"] == "choose_serial_port"
    assert "/dev/ttyUSB0" in result2["data_schema"]({})[CONF_DEVICE_PATH]


    result3 = await hass.config_entries.options.async_configure(
        flow["flow_id"], user_input={}
    )


    assert result3["step_id"] == "manual_pick_radio_type"
    assert result3["data_schema"]({})[CONF_RADIO_TYPE] == RadioType.znp.description


    result4 = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={
            CONF_RADIO_TYPE: RadioType.znp.description,
        },
    )


    assert result4["step_id"] == "manual_port_config"
    assert entry.data[CONF_DEVICE] == {
        "path": "/dev/ttyUSB0",
        "baudrate": 12345,
        "flow_control": None,
    }
    assert result4["data_schema"]({}) == {
        "path": "/dev/ttyUSB0",
        "baudrate": 12345,
        "flow_control": "none",
    }

    with patch(
        f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True)
    ) as mock_probe:

        result5 = await hass.config_entries.options.async_configure(
            flow["flow_id"],
            user_input={

                CONF_DEVICE_PATH: "/dev/new_serial_port",
                CONF_BAUDRATE: 54321,
                CONF_FLOW_CONTROL: input_flow_control,
            },
        )

        assert mock_probe.mock_calls == [
            call(
                {
                    "path": "/dev/new_serial_port",
                    "baudrate": 54321,
                    "flow_control": conf_flow_control,
                }
            )
        ]


    assert result5["step_id"] == "choose_migration_strategy"

    async_setup_entry.assert_not_called()

    result6 = await hass.config_entries.options.async_configure(
        result5["flow_id"],
        user_input={"next_step_id": config_flow.MIGRATION_STRATEGY_ADVANCED},
    )
    await hass.async_block_till_done()

    result7 = await hass.config_entries.options.async_configure(
        result6["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_REUSE_SETTINGS},
    )
    await hass.async_block_till_done()

    assert result7["type"] is FlowResultType.ABORT
    assert result7["reason"] == "reconfigure_successful"


    assert entry.data == {
        CONF_DEVICE: {
            CONF_DEVICE_PATH: "/dev/new_serial_port",
            CONF_BAUDRATE: 54321,
            CONF_FLOW_CONTROL: conf_flow_control,
        },
        CONF_RADIO_TYPE: "znp",
    }


    assert async_setup_entry.call_count == 1


@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(
        return_value=[
            usb_port("/dev/SomePort"),
            usb_port("/dev/SomeOtherPort"),
        ]
    ),
)
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_options_flow_defaults_socket(hass: HomeAssistant) -> None:


    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "socket://localhost:5678",
                CONF_BAUDRATE: 12345,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flow = await hass.config_entries.options.async_init(entry.entry_id)


    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload", return_value=True
    ):
        result1 = await hass.config_entries.options.async_configure(
            flow["flow_id"], user_input={}
        )

    assert result1["step_id"] == "prompt_migrate_or_reconfigure"
    result2 = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={"next_step_id": config_flow.OptionsMigrationIntent.RECONFIGURE},
    )


    assert result2["step_id"] == "choose_serial_port"
    assert result2["data_schema"]({})[CONF_DEVICE_PATH] == config_flow.CONF_MANUAL_PATH

    result3 = await hass.config_entries.options.async_configure(
        flow["flow_id"], user_input={}
    )


    assert result3["step_id"] == "manual_pick_radio_type"
    assert result3["data_schema"]({})[CONF_RADIO_TYPE] == RadioType.znp.description


    result4 = await hass.config_entries.options.async_configure(
        flow["flow_id"], user_input={}
    )


    assert result4["step_id"] == "manual_port_config"
    assert entry.data[CONF_DEVICE] == {
        "path": "socket://localhost:5678",
        "baudrate": 12345,
        "flow_control": None,
    }
    assert result4["data_schema"]({}) == {
        "path": "socket://localhost:5678",
        "baudrate": 12345,
        "flow_control": "none",
    }

    with patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True)):
        result5 = await hass.config_entries.options.async_configure(
            flow["flow_id"], user_input={}
        )

    assert result5["step_id"] == "choose_migration_strategy"


@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(return_value=[usb_port()]),
)
@patch("homeassistant.components.zha.async_setup_entry", return_value=True)
async def test_options_flow_restarts_running_zha_if_cancelled(
    async_setup_entry, hass: HomeAssistant
) -> None:


    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "socket://localhost:5678",
                CONF_BAUDRATE: 12345,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flow = await hass.config_entries.options.async_init(entry.entry_id)


    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload", return_value=True
    ):
        result1 = await hass.config_entries.options.async_configure(
            flow["flow_id"], user_input={}
        )

    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)

    assert result1["step_id"] == "prompt_migrate_or_reconfigure"
    result2 = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={"next_step_id": config_flow.OptionsMigrationIntent.RECONFIGURE},
    )


    assert result2["step_id"] == "choose_serial_port"

    async_setup_entry.reset_mock()


    hass.config_entries.options.async_abort(result2["flow_id"])
    await hass.async_block_till_done()


    async_setup_entry.assert_called_once_with(hass, entry)


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_options_flow_migration_reset_old_adapter(
    hass: HomeAssistant, backup, mock_app
) -> None:


    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB_old",
                CONF_BAUDRATE: 12345,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flow = await hass.config_entries.options.async_init(entry.entry_id)


    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload", return_value=True
    ):
        result_init = await hass.config_entries.options.async_configure(
            flow["flow_id"], user_input={}
        )

    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)

    assert result_init["step_id"] == "prompt_migrate_or_reconfigure"

    with (
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.detect_radio_type",
            return_value=ProbeResult.RADIO_TYPE_DETECTED,
        ),
        patch(
            "homeassistant.components.zha.config_flow.list_serial_ports",
            AsyncMock(return_value=[usb_port("/dev/ttyUSB_new")]),
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
            return_value=[backup],
        ),
    ):
        result_migrate = await hass.config_entries.options.async_configure(
            flow["flow_id"],
            user_input={"next_step_id": config_flow.OptionsMigrationIntent.MIGRATE},
        )


        assert result_migrate["step_id"] == "choose_serial_port"

        result_port = await hass.config_entries.options.async_configure(
            flow["flow_id"],
            user_input={
                CONF_DEVICE_PATH: "/dev/ttyUSB_new - Some serial port, s/n: 1234 - Virtual serial port"
            },
        )

    assert result_port["step_id"] == "choose_migration_strategy"


    mock_radio_manager = AsyncMock()

    with patch(
        "homeassistant.components.zha.config_flow.ZhaRadioManager",
        spec=ZhaRadioManager,
        side_effect=[mock_radio_manager],
    ):
        result_migrate_start = await hass.config_entries.options.async_configure(
            flow["flow_id"],
            user_input={
                "next_step_id": config_flow.MIGRATION_STRATEGY_RECOMMENDED,
            },
        )

        result_strategy = await consume_progress_flow(
            hass,
            flow_id=result_migrate_start["flow_id"],
            valid_step_ids=("maybe_reset_old_radio", "restore_backup"),
            flow_manager=hass.config_entries.options,
        )


    assert mock_radio_manager.device_path == "/dev/ttyUSB_old"
    assert mock_radio_manager.async_reset_adapter.call_count == 1

    assert result_strategy["type"] is FlowResultType.ABORT
    assert result_strategy["reason"] == "reconfigure_successful"


    assert entry.data["device"]["path"] == "/dev/ttyUSB_new"


@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(return_value=[usb_port()]),
)
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_options_flow_reconfigure_no_reset(
    hass: HomeAssistant, backup, mock_app
) -> None:


    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB_old",
                CONF_BAUDRATE: 12345,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "znp",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flow = await hass.config_entries.options.async_init(entry.entry_id)


    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload", return_value=True
    ):
        result_init = await hass.config_entries.options.async_configure(
            flow["flow_id"], user_input={}
        )

    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)

    assert result_init["step_id"] == "prompt_migrate_or_reconfigure"

    with (
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.detect_radio_type",
            return_value=ProbeResult.RADIO_TYPE_DETECTED,
        ),
        patch(
            "homeassistant.components.zha.config_flow.list_serial_ports",
            AsyncMock(return_value=[usb_port("/dev/ttyUSB_new")]),
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
            return_value=[backup],
        ),
    ):
        result_reconfigure = await hass.config_entries.options.async_configure(
            flow["flow_id"],
            user_input={"next_step_id": config_flow.OptionsMigrationIntent.RECONFIGURE},
        )


        assert result_reconfigure["step_id"] == "choose_serial_port"

        result_port = await hass.config_entries.options.async_configure(
            flow["flow_id"],
            user_input={
                CONF_DEVICE_PATH: "/dev/ttyUSB_new - Some serial port, s/n: 1234 - Virtual serial port"
            },
        )

    assert result_port["step_id"] == "choose_migration_strategy"

    with patch(
        "homeassistant.components.zha.config_flow.ZhaRadioManager"
    ) as mock_radio_manager:
        result_migrate_start = await hass.config_entries.options.async_configure(
            flow["flow_id"],
            user_input={
                "next_step_id": config_flow.MIGRATION_STRATEGY_RECOMMENDED,
            },
        )

        result_strategy = await consume_progress_flow(
            hass,
            flow_id=result_migrate_start["flow_id"],
            valid_step_ids=("maybe_reset_old_radio", "restore_backup"),
            flow_manager=hass.config_entries.options,
        )


    assert mock_radio_manager.call_count == 0

    assert result_strategy["type"] is FlowResultType.ABORT
    assert result_strategy["reason"] == "reconfigure_successful"


    assert entry.data["device"]["path"] == "/dev/ttyUSB_new"


@pytest.mark.parametrize(
    "device",
    [
        "/dev/ttyAMA1",
        "/dev/ttyAMA10",
    ],
)
async def test_config_flow_port_yellow_port_name(
    hass: HomeAssistant, device: str
) -> None:


    port = USBDevice(
        device=device,
        vid="10C4",
        pid="EA60",
        serial_number=None,
        manufacturer=None,
        description=None,
    )

    with (
        patch("homeassistant.components.zha.config_flow.yellow_hardware.async_info"),
        patch(
            "homeassistant.components.zha.config_flow.scan_serial_ports",
            return_value=[port],
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={CONF_SOURCE: SOURCE_USER},
        )


    assert (
        result["data_schema"].schema["path"].container[0]
        == "/dev/ttyAMA1 - Yellow Zigbee module - Nabu Casa"
    )


async def test_config_flow_ports_no_hassio(hass: HomeAssistant) -> None:


    with (
        patch("homeassistant.components.zha.config_flow.is_hassio", return_value=False),
        patch(
            "homeassistant.components.zha.config_flow.scan_serial_ports",
            return_value=[],
        ),
    ):
        ports = await config_flow.list_serial_ports(hass)

    assert ports == []


async def test_config_flow_port_multiprotocol_port_name(hass: HomeAssistant) -> None:


    with (
        patch("homeassistant.components.zha.config_flow.is_hassio", return_value=True),
        patch(
            "homeassistant.components.hassio.addon_manager.AddonManager.async_get_addon_info"
        ) as async_get_addon_info,
        patch(
            "homeassistant.components.zha.config_flow.scan_serial_ports",
            return_value=[],
        ),
    ):
        async_get_addon_info.return_value.state = AddonState.RUNNING
        async_get_addon_info.return_value.hostname = "core-silabs-multiprotocol"
        ports = await config_flow.list_serial_ports(hass)

    assert len(ports) == 1
    assert ports[0].description == "Silicon Labs Multiprotocol add-on"
    assert ports[0].manufacturer == "Nabu Casa"
    assert ports[0].device == "socket://core-silabs-multiprotocol:9999"


async def test_config_flow_port_no_multiprotocol(hass: HomeAssistant) -> None:


    with (
        patch("homeassistant.components.zha.config_flow.is_hassio", return_value=True),
        patch(
            "homeassistant.components.hassio.addon_manager.AddonManager.async_get_addon_info",
            new_callable=DelayedAsyncMock,
            side_effect=AddonError,
        ),
        patch(
            "homeassistant.components.zha.config_flow.scan_serial_ports",
            return_value=[],
        ),
    ):
        ports = await config_flow.list_serial_ports(hass)

    assert ports == []


async def test_list_serial_ports_ignored_devices(hass: HomeAssistant) -> None:

    mock_ports = [
        USBDevice(
            device="/dev/ttyUSB0",
            vid="303A",
            pid="4001",
            serial_number="1234",
            manufacturer="Nabu Casa",
            description="ZWA-2",
        ),
        USBDevice(
            device="/dev/ttyUSB1",
            vid="303A",
            pid="4001",
            serial_number="1235",
            manufacturer="Nabu Casa",
            description="ZBT-2",
        ),
        USBDevice(
            device="/dev/ttyUSB2",
            vid="10C4",
            pid="EA60",
            serial_number="1236",
            manufacturer="Nabu Casa",
            description="Home Assistant Connect ZBT-1",
        ),
        USBDevice(
            device="/dev/ttyUSB3",
            vid="10C4",
            pid="EA60",
            serial_number="1237",
            manufacturer="Nabu Casa",
            description="SkyConnect v1.0",
        ),
        USBDevice(
            device="/dev/ttyUSB4",
            vid="1234",
            pid="5678",
            serial_number="1238",
            manufacturer="Another Manufacturer",
            description="Zigbee USB Adapter",
        ),
        USBDevice(
            device="/dev/ttyUSB5",
            vid="1234",
            pid="5678",
            serial_number=None,
            manufacturer=None,
            description=None,
        ),
    ]

    with (
        patch("homeassistant.components.zha.config_flow.is_hassio", return_value=False),
        patch(
            "homeassistant.components.zha.config_flow.scan_serial_ports",
            return_value=mock_ports,
        ),
    ):
        ports = await config_flow.list_serial_ports(hass)


    assert len(ports) == 5

    assert ports[0].device == "/dev/ttyUSB1"
    assert ports[0].manufacturer == "Nabu Casa"
    assert ports[0].description == "ZBT-2"

    assert ports[1].device == "/dev/ttyUSB2"
    assert ports[1].manufacturer == "Nabu Casa"
    assert ports[1].description == "Home Assistant Connect ZBT-1"

    assert ports[2].device == "/dev/ttyUSB3"
    assert ports[2].manufacturer == "Nabu Casa"
    assert ports[2].description == "SkyConnect v1.0"

    assert ports[3].device == "/dev/ttyUSB4"
    assert ports[3].manufacturer == "Another Manufacturer"
    assert ports[3].description == "Zigbee USB Adapter"

    assert ports[4].device == "/dev/ttyUSB5"
    assert ports[4].manufacturer is None
    assert ports[4].description is None


@patch(
    "homeassistant.components.zha.config_flow.list_serial_ports",
    AsyncMock(return_value=[usb_port()]),
)
async def test_probe_wrong_firmware_installed(hass: HomeAssistant) -> None:


    with patch(
        "homeassistant.components.zha.radio_manager.ZhaRadioManager.detect_radio_type",
        return_value=ProbeResult.WRONG_FIRMWARE_INSTALLED,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={CONF_SOURCE: "choose_serial_port"},
            data={
                CONF_DEVICE_PATH: (
                    "/dev/ttyUSB1234 - Some serial port, s/n: 1234 - Virtual serial port"
                )
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_firmware_installed"


async def test_discovery_wrong_firmware_installed(hass: HomeAssistant) -> None:


    with (
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.detect_radio_type",
            return_value=ProbeResult.WRONG_FIRMWARE_INSTALLED,
        ),
        patch(
            "homeassistant.components.onboarding.async_is_onboarded", return_value=False
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={CONF_SOURCE: "confirm"},
            data={},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_firmware_installed"


@pytest.mark.parametrize(
    ("old_type", "new_type"),
    [
        ("ezsp", "ezsp"),
        ("ti_cc", "znp"),
        ("znp", "znp"),
        ("deconz", "deconz"),
    ],
)
async def test_migration_ti_cc_to_znp(
    old_type: str, new_type: str, hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:

    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, CONF_RADIO_TYPE: old_type}, version=2
    )

    with patch("homeassistant.components.zha.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.version > 2
    assert config_entry.data[CONF_RADIO_TYPE] == new_type


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_migration_resets_old_radio(
    hass: HomeAssistant, backup, mock_app
) -> None:

    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "ezsp",
        },
    )
    entry.add_to_hass(hass)

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )

    mock_temp_radio_mgr = AsyncMock()
    mock_temp_radio_mgr.async_reset_adapter = AsyncMock()

    with (
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
            return_value=[backup],
        ),
        patch(
            "homeassistant.components.zha.config_flow.ZhaRadioManager",
            side_effect=[ZhaRadioManager(), mock_temp_radio_mgr],
        ),
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
        )

        result_confirm = await hass.config_entries.flow.async_configure(
            result_init["flow_id"], user_input={}
        )

        assert result_confirm["step_id"] == "choose_migration_strategy"

        result_migrate = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"],
            user_input={"next_step_id": config_flow.MIGRATION_STRATEGY_RECOMMENDED},
        )

        result_recommended = await consume_progress_flow(
            hass,
            flow_id=result_migrate["flow_id"],
            valid_step_ids=("maybe_reset_old_radio", "restore_backup"),
        )

    assert result_recommended["type"] is FlowResultType.ABORT
    assert result_recommended["reason"] == "reconfigure_successful"


    assert mock_temp_radio_mgr.async_reset_adapter.call_count == 1


    assert mock_temp_radio_mgr.radio_type == RadioType.ezsp
    assert mock_temp_radio_mgr.device_path == "/dev/ttyUSB0"
    assert mock_temp_radio_mgr.device_settings == {
        CONF_DEVICE_PATH: "/dev/ttyUSB0",
        CONF_BAUDRATE: 115200,
        CONF_FLOW_CONTROL: None,
    }


@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
@patch(f"bellows.{PROBE_FUNCTION_PATH}", return_value=True)
async def test_config_flow_serial_resolution_oserror(
    probe_mock, hass: HomeAssistant
) -> None:


    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )

    with (
        patch(
            "homeassistant.components.zha.config_flow.usb.get_serial_by_id",
            side_effect=OSError("Test error"),
        ),
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
        )

    assert result_init["type"] is FlowResultType.ABORT
    assert result_init["reason"] == "cannot_resolve_path"
    assert result_init["description_placeholders"] == {"path": "/dev/ttyZIGBEE"}


@patch("homeassistant.components.zha.radio_manager._allow_overwrite_ezsp_ieee")
async def test_formation_strategy_restore_manual_backup_overwrite_ieee_ezsp_write_fail(
    allow_overwrite_ieee_mock,
    advanced_pick_radio: RadioPicker,
    mock_app: AsyncMock,
    backup,
    hass: HomeAssistant,
) -> None:

    advanced_strategy_result = await advanced_pick_radio(RadioType.ezsp)

    upload_backup_result = await hass.config_entries.flow.async_configure(
        advanced_strategy_result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_UPLOAD_MANUAL_BACKUP},
    )
    await hass.async_block_till_done()

    assert upload_backup_result["type"] is FlowResultType.FORM
    assert upload_backup_result["step_id"] == "upload_manual_backup"

    with (
        patch(
            "homeassistant.components.zha.config_flow.ZhaConfigFlowHandler._parse_uploaded_backup",
            return_value=backup,
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
            new_callable=DelayedAsyncMock,
            side_effect=[
                DestructiveWriteNetworkSettings("Radio IEEE change is permanent"),
                CannotWriteNetworkSettings("Failed to write settings"),
            ],
        ) as mock_restore_backup,
    ):
        result_upload = await hass.config_entries.flow.async_configure(
            upload_backup_result["flow_id"],
            user_input={config_flow.UPLOADED_BACKUP_FILE: str(uuid.uuid4())},
        )

        confirm_restore_result = await consume_progress_flow(
            hass,
            flow_id=result_upload["flow_id"],
            valid_step_ids=("restore_backup",),
        )

        assert mock_restore_backup.call_count == 1
        assert not mock_restore_backup.mock_calls[0].kwargs.get("overwrite_ieee")
        mock_restore_backup.reset_mock()


        assert confirm_restore_result["type"] is FlowResultType.FORM
        assert confirm_restore_result["step_id"] == "confirm_ezsp_ieee_overwrite"

        confirm_result = await hass.config_entries.flow.async_configure(
            confirm_restore_result["flow_id"],
            user_input={config_flow.OVERWRITE_COORDINATOR_IEEE: True},
        )

        final_result = await consume_progress_flow(
            hass,
            flow_id=confirm_result["flow_id"],
            valid_step_ids=("restore_backup",),
        )

    assert final_result["type"] is FlowResultType.ABORT
    assert final_result["reason"] == "cannot_restore_backup"
    assert (
        "Failed to write settings" in final_result["description_placeholders"]["error"]
    )

    assert mock_restore_backup.call_count == 1
    assert mock_restore_backup.mock_calls[0].kwargs["overwrite_ieee"] is True


@patch(f"bellows.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
async def test_migrate_setup_options_with_ignored_discovery(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:



    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AAAA:AAAA_1234_test_zigbee radio",
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB1",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            }
        },
        source=config_entries.SOURCE_IGNORE,
    )
    entry.add_to_hass(hass)


    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="BBBB",
        vid="BBBB",
        serial_number="5678",
        description="zigbee radio",
        manufacturer="test manufacturer",
    )
    discovery_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()


    confirm_result = await hass.config_entries.flow.async_configure(
        discovery_result["flow_id"], user_input={}
    )
    await hass.async_block_till_done()


    assert confirm_result["step_id"] == "choose_setup_strategy"
    assert confirm_result["menu_options"] == [
        "setup_strategy_recommended",
        "setup_strategy_advanced",
    ]


@patch("homeassistant.components.zha.radio_manager._allow_overwrite_ezsp_ieee")
async def test_plug_in_new_radio_retry(
    allow_overwrite_ieee_mock,
    advanced_pick_radio: RadioPicker,
    mock_app: AsyncMock,
    backup,
    hass: HomeAssistant,
) -> None:

    result = await advanced_pick_radio(RadioType.ezsp)

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": config_flow.FORMATION_UPLOAD_MANUAL_BACKUP},
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "upload_manual_backup"

    with (
        patch(
            "homeassistant.components.zha.config_flow.ZhaConfigFlowHandler._parse_uploaded_backup",
            return_value=backup,
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
            new_callable=DelayedAsyncMock,
            side_effect=[
                HomeAssistantError(
                    "Failed to connect to Zigbee adapter: [Errno 2] No such file or directory"
                ),
                DestructiveWriteNetworkSettings("Radio IEEE change is permanent"),
                HomeAssistantError(
                    "Failed to connect to Zigbee adapter: [Errno 2] No such file or directory"
                ),
                None,
            ],
        ) as mock_restore_backup,
    ):
        upload_result = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={config_flow.UPLOADED_BACKUP_FILE: str(uuid.uuid4())},
        )

        result3 = await consume_progress_flow(
            hass,
            flow_id=upload_result["flow_id"],
            valid_step_ids=("restore_backup",),
        )


        assert result3["type"] is FlowResultType.FORM
        assert result3["step_id"] == "plug_in_new_radio"
        assert result3["description_placeholders"] == {"device_path": "/dev/ttyUSB1234"}


        retry_result = await hass.config_entries.flow.async_configure(
            result3["flow_id"],
            user_input={},
        )

        result4 = await consume_progress_flow(
            hass,
            flow_id=retry_result["flow_id"],
            valid_step_ids=("restore_backup",),
        )


        assert result4["type"] is FlowResultType.FORM
        assert result4["step_id"] == "confirm_ezsp_ieee_overwrite"


        confirm_result = await hass.config_entries.flow.async_configure(
            result4["flow_id"],
            user_input={config_flow.OVERWRITE_COORDINATOR_IEEE: True},
        )

        result5 = await consume_progress_flow(
            hass,
            flow_id=confirm_result["flow_id"],
            valid_step_ids=("restore_backup",),
        )


        assert result5["type"] is FlowResultType.FORM
        assert result5["step_id"] == "plug_in_new_radio"
        assert result5["description_placeholders"] == {"device_path": "/dev/ttyUSB1234"}


        final_retry_result = await hass.config_entries.flow.async_configure(
            result5["flow_id"],
            user_input={},
        )

        result6 = await consume_progress_flow(
            hass,
            flow_id=final_retry_result["flow_id"],
            valid_step_ids=("restore_backup",),
        )


    assert result6["type"] is FlowResultType.CREATE_ENTRY
    assert result6["data"][CONF_RADIO_TYPE] == "ezsp"



    assert mock_restore_backup.call_count == 4


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_plug_in_old_radio_retry(hass: HomeAssistant, backup, mock_app) -> None:

    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "ezsp",
        },
    )
    entry.add_to_hass(hass)

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )

    mock_temp_radio_mgr = AsyncMock()
    mock_temp_radio_mgr.async_reset_adapter = DelayedAsyncMock(
        side_effect=HomeAssistantError(
            "Failed to connect to Zigbee adapter: [Errno 2] No such file or directory"
        )
    )

    with (
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
            return_value=[backup],
        ),
        patch(
            "homeassistant.components.zha.config_flow.ZhaRadioManager",
            side_effect=[ZhaRadioManager(), mock_temp_radio_mgr, mock_temp_radio_mgr],
        ),
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
        )

        result_confirm = await hass.config_entries.flow.async_configure(
            result_init["flow_id"], user_input={}
        )

        assert result_confirm["step_id"] == "choose_migration_strategy"

        recommended_result = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"],
            user_input={"next_step_id": config_flow.MIGRATION_STRATEGY_RECOMMENDED},
        )

        result_recommended = await consume_progress_flow(
            hass,
            flow_id=recommended_result["flow_id"],
            valid_step_ids=("maybe_reset_old_radio",),
        )


        assert result_recommended["type"] is FlowResultType.MENU
        assert result_recommended["step_id"] == "plug_in_old_radio"
        assert (
            result_recommended["description_placeholders"]["device_path"]
            == "/dev/ttyUSB0"
        )
        assert result_recommended["menu_options"] == [
            "retry_old_radio",
            "skip_reset_old_radio",
        ]


        retry_result = await hass.config_entries.flow.async_configure(
            result_recommended["flow_id"],
            user_input={"next_step_id": "retry_old_radio"},
        )

        result_retry = await consume_progress_flow(
            hass,
            flow_id=retry_result["flow_id"],
            valid_step_ids=("maybe_reset_old_radio",),
        )


    assert result_retry["type"] is FlowResultType.MENU
    assert result_retry["step_id"] == "plug_in_old_radio"


    result_skip_progress = await hass.config_entries.flow.async_configure(
        result_retry["flow_id"],
        user_input={"next_step_id": "skip_reset_old_radio"},
    )

    result_skip = await consume_progress_flow(
        hass,
        flow_id=result_skip_progress["flow_id"],
        valid_step_ids=("maybe_reset_old_radio", "restore_backup"),
    )


    assert result_skip["type"] is FlowResultType.ABORT
    assert result_skip["reason"] == "reconfigure_successful"


    assert mock_temp_radio_mgr.async_reset_adapter.call_count == 2


@patch(f"zigpy_znp.{PROBE_FUNCTION_PATH}", AsyncMock(return_value=True))
@patch("homeassistant.components.zha.async_setup_entry", AsyncMock(return_value=True))
async def test_plug_in_old_radio_config_entry_removed(
    hass: HomeAssistant, backup, mock_app
) -> None:

    entry = MockConfigEntry(
        version=config_flow.ZhaConfigFlowHandler.VERSION,
        domain=DOMAIN,
        data={
            CONF_DEVICE: {
                CONF_DEVICE_PATH: "/dev/ttyUSB0",
                CONF_BAUDRATE: 115200,
                CONF_FLOW_CONTROL: None,
            },
            CONF_RADIO_TYPE: "ezsp",
        },
    )
    entry.add_to_hass(hass)

    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )


    async def remove_entry_during_reset():

        await hass.config_entries.async_remove(entry.entry_id)

        raise HomeAssistantError(
            "Failed to connect to Zigbee adapter: [Errno 2] No such file or directory"
        )

    mock_temp_radio_mgr = AsyncMock()
    mock_temp_radio_mgr.async_reset_adapter = AsyncMock(
        side_effect=remove_entry_during_reset
    )

    with (
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager._async_read_backups_from_database",
            return_value=[backup],
        ),
        patch(
            "homeassistant.components.zha.config_flow.ZhaRadioManager",
            side_effect=[
                ZhaRadioManager(),
                mock_temp_radio_mgr,
            ],
        ),
        patch(
            "homeassistant.components.zha.radio_manager.ZhaRadioManager.restore_backup",
        ) as mock_restore_backup,
    ):
        result_init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
        )

        result_confirm = await hass.config_entries.flow.async_configure(
            result_init["flow_id"], user_input={}
        )

        assert result_confirm["step_id"] == "choose_migration_strategy"




        result_recommended = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"],
            user_input={"next_step_id": config_flow.MIGRATION_STRATEGY_RECOMMENDED},
        )



    assert result_recommended["type"] is FlowResultType.CREATE_ENTRY
    assert result_recommended["title"] == "zigbee radio"
    assert result_recommended["data"] == {
        "device": {
            "baudrate": 115200,
            "flow_control": None,
            "path": "/dev/ttyZIGBEE",
        },
        CONF_RADIO_TYPE: "znp",
    }


    assert mock_temp_radio_mgr.async_reset_adapter.call_count == 1

    assert mock_restore_backup.call_count == 1
