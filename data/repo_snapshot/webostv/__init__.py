

from __future__ import annotations

from contextlib import suppress

from aiowebostv import WebOsClient, WebOsTvPairError

from homeassistant.components import notify as hass_notify
from homeassistant.const import (
    ATTR_CONFIG_ENTRY_ID,
    CONF_CLIENT_SECRET,
    CONF_HOST,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import DATA_HASS_CONFIG, DOMAIN, PLATFORMS, WEBOSTV_EXCEPTIONS
from .helpers import WebOsTvConfigEntry, update_client_key
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:

    hass.data.setdefault(DOMAIN, {DATA_HASS_CONFIG: config})

    async_setup_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: WebOsTvConfigEntry) -> bool:

    host = entry.data[CONF_HOST]
    key = entry.data[CONF_CLIENT_SECRET]


    entry.runtime_data = client = WebOsClient(
        host, key, client_session=async_get_clientsession(hass)
    )
    with suppress(*WEBOSTV_EXCEPTIONS):
        try:
            await client.connect()
        except WebOsTvPairError as err:
            raise ConfigEntryAuthFailed(err) from err



    update_client_key(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)



    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {
                CONF_NAME: entry.title,
                ATTR_CONFIG_ENTRY_ID: entry.entry_id,
            },
            hass.data[DOMAIN][DATA_HASS_CONFIG],
        )
    )

    async def async_on_stop(_event: Event) -> None:

        client.clear_state_update_callbacks()
        await client.disconnect()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_on_stop)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WebOsTvConfigEntry) -> bool:

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        client = entry.runtime_data
        await hass_notify.async_reload(hass, DOMAIN)
        client.clear_state_update_callbacks()
        await client.disconnect()

    return unload_ok
