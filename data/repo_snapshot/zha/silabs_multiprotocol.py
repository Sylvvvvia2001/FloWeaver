

from __future__ import annotations

import asyncio
import contextlib

from homeassistant.components.homeassistant_hardware.silabs_multiprotocol_addon import (
    is_multiprotocol_url,
)
from homeassistant.core import HomeAssistant

from . import api


ZHA_CHANNEL_CHANGE_TIME_S = 10.27


def _get_zha_url(hass: HomeAssistant) -> str | None:

    with contextlib.suppress(ValueError):
        return api.async_get_radio_path(hass)
    return None


async def _get_zha_channel(hass: HomeAssistant) -> int | None:

    zha_network_settings: api.NetworkBackup | None
    with contextlib.suppress(ValueError):
        zha_network_settings = await api.async_get_network_settings(hass)
    if not zha_network_settings:
        return None
    channel: int = zha_network_settings.network_info.channel

    return channel or None


async def async_change_channel(
    hass: HomeAssistant, channel: int, delay: float = 0
) -> asyncio.Task | None:




    zha_url = _get_zha_url(hass)
    if not zha_url:

        return None

    async def finish_migration() -> None:

        await asyncio.sleep(max(0, delay - ZHA_CHANNEL_CHANGE_TIME_S))
        return await api.async_change_channel(hass, channel)

    return hass.async_create_task(finish_migration())


async def async_get_channel(hass: HomeAssistant) -> int | None:




    zha_url = _get_zha_url(hass)
    if not zha_url:

        return None

    return await _get_zha_channel(hass)


async def async_using_multipan(hass: HomeAssistant) -> bool:




    zha_url = _get_zha_url(hass)
    if not zha_url:

        return False

    return is_multiprotocol_url(zha_url)
