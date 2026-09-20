

from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.components.ruuvitag_ble.const import DOMAIN
from homeassistant.config_entries import SOURCE_IGNORE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .fixtures import CONFIGURED_NAME, NOT_RUUVITAG_SERVICE_INFO, RUUVI_V5_SERVICE_INFO

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth: None) -> None:
    pass


async def test_async_step_bluetooth_valid_device(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVI_V5_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    with patch(
        "homeassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == CONFIGURED_NAME
    assert result2["result"].unique_id == RUUVI_V5_SERVICE_INFO.address


async def test_async_step_bluetooth_not_ruuvitag(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=NOT_RUUVITAG_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_async_step_user_no_devices_found(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_user_with_found_devices(hass: HomeAssistant) -> None:

    with patch(
        "homeassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVI_V5_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch(
        "homeassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": RUUVI_V5_SERVICE_INFO.address},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == CONFIGURED_NAME
    assert result2["result"].unique_id == RUUVI_V5_SERVICE_INFO.address


async def test_async_step_user_device_added_between_steps(hass: HomeAssistant) -> None:

    with patch(
        "homeassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVI_V5_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=RUUVI_V5_SERVICE_INFO.address,
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": RUUVI_V5_SERVICE_INFO.address},
        )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_async_step_user_with_found_devices_already_setup(
    hass: HomeAssistant,
) -> None:

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=RUUVI_V5_SERVICE_INFO.address,
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVI_V5_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_bluetooth_devices_already_setup(hass: HomeAssistant) -> None:

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=RUUVI_V5_SERVICE_INFO.address,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVI_V5_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_async_step_bluetooth_already_in_progress(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVI_V5_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVI_V5_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_async_step_user_takes_precedence_over_discovery(
    hass: HomeAssistant,
) -> None:

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVI_V5_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch(
        "homeassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVI_V5_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        assert result["type"] is FlowResultType.FORM

    with patch(
        "homeassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": RUUVI_V5_SERVICE_INFO.address},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == CONFIGURED_NAME
    assert result2["data"] == {}
    assert result2["result"].unique_id == RUUVI_V5_SERVICE_INFO.address


async def test_user_setup_replaces_ignored_device(hass: HomeAssistant) -> None:

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=RUUVI_V5_SERVICE_INFO.address,
        source=SOURCE_IGNORE,
        data={},
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVI_V5_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


    assert (
        RUUVI_V5_SERVICE_INFO.address
        in result["data_schema"].schema["address"].container
    )

    with patch(
        "homeassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": RUUVI_V5_SERVICE_INFO.address},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == CONFIGURED_NAME
    assert result2["data"] == {}
    assert result2["result"].unique_id == RUUVI_V5_SERVICE_INFO.address
