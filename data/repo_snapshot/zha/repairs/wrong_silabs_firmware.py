

from __future__ import annotations

import enum
import logging

from homeassistant.components.homeassistant_hardware.util import (
    ApplicationType,
    probe_silabs_firmware_type,
)
from homeassistant.components.homeassistant_sky_connect import (
    hardware as skyconnect_hardware,
)
from homeassistant.components.homeassistant_yellow import (
    RADIO_DEVICE as YELLOW_RADIO_DEVICE,
    hardware as yellow_hardware,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AlreadyRunningEZSP(Exception):
    pass


class HardwareType(enum.StrEnum):


    SKYCONNECT = "skyconnect"
    YELLOW = "yellow"
    OTHER = "other"


ISSUE_WRONG_SILABS_FIRMWARE_INSTALLED = "wrong_silabs_firmware_installed"


def _detect_radio_hardware(hass: HomeAssistant, device: str) -> HardwareType:

    try:
        yellow_hardware.async_info(hass)
    except HomeAssistantError:
        pass
    else:
        if device == YELLOW_RADIO_DEVICE:
            return HardwareType.YELLOW

    try:
        info = skyconnect_hardware.async_info(hass)
    except HomeAssistantError:
        pass
    else:
        for hardware_info in info:
            for entry_id in hardware_info.config_entries or []:
                entry = hass.config_entries.async_get_entry(entry_id)

                if entry is not None and entry.data["device"] == device:
                    return HardwareType.SKYCONNECT

    return HardwareType.OTHER


async def warn_on_wrong_silabs_firmware(hass: HomeAssistant, device: str) -> bool:


    if device.startswith("socket://"):
        return False

    app_type = await probe_silabs_firmware_type(
        device,
        application_probe_methods=[
            (ApplicationType.GECKO_BOOTLOADER, 115200),
            (ApplicationType.EZSP, 115200),
            (ApplicationType.EZSP, 460800),
            (ApplicationType.SPINEL, 460800),
            (ApplicationType.CPC, 460800),
            (ApplicationType.CPC, 230400),
            (ApplicationType.CPC, 115200),
            (ApplicationType.ROUTER, 115200),
        ],
    )

    if app_type is None:

        return False

    if app_type == ApplicationType.EZSP:


        raise AlreadyRunningEZSP

    hardware_type = _detect_radio_hardware(hass, device)
    ir.async_create_issue(
        hass,
        domain=DOMAIN,
        issue_id=ISSUE_WRONG_SILABS_FIRMWARE_INSTALLED,
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=(
            ISSUE_WRONG_SILABS_FIRMWARE_INSTALLED
            + ("_nabucasa" if hardware_type != HardwareType.OTHER else "_other")
        ),
        translation_placeholders={"firmware_type": app_type.name},
    )

    return True
