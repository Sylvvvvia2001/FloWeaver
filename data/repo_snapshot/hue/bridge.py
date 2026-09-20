

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

import aiohttp
from aiohttp import client_exceptions
from aiohue import HueBridgeV1, HueBridgeV2, LinkButtonNotPressed, Unauthorized
from aiohue.errors import AiohueException, BridgeBusy

from homeassistant import core
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_API_VERSION, CONF_HOST, Platform
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN
from .v1.sensor_base import SensorManager
from .v2.device import async_setup_devices
from .v2.hue_event import async_setup_hue_events


HUB_BUSY_SLEEP = 0.5

PLATFORMS_v1 = [Platform.BINARY_SENSOR, Platform.LIGHT, Platform.SENSOR]
PLATFORMS_v2 = [
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.SCENE,
    Platform.SENSOR,
    Platform.SWITCH,
]

type HueConfigEntry = ConfigEntry[HueBridge]


class HueBridge:


    def __init__(self, hass: core.HomeAssistant, config_entry: HueConfigEntry) -> None:

        self.config_entry = config_entry
        self.hass = hass
        self.authorized = False

        self.reset_jobs: list[core.CALLBACK_TYPE] = []
        self.sensor_manager: SensorManager | None = None
        self.logger = logging.getLogger(__name__)

        app_key: str = self.config_entry.data[CONF_API_KEY]
        if self.api_version == 1:
            self.api = HueBridgeV1(
                self.host, app_key, aiohttp_client.async_get_clientsession(hass)
            )
        else:
            self.api = HueBridgeV2(self.host, app_key)

        self.config_entry.runtime_data = self

    @property
    def host(self) -> str:

        return self.config_entry.data[CONF_HOST]

    @property
    def api_version(self) -> int:

        return self.config_entry.data[CONF_API_VERSION]

    async def async_initialize_bridge(self) -> bool:

        setup_ok = False
        try:
            async with asyncio.timeout(10):
                await self.api.initialize()
            setup_ok = True
        except LinkButtonNotPressed, Unauthorized:




            create_config_flow(self.hass, self.host)
            return False
        except (
            TimeoutError,
            client_exceptions.ClientOSError,
            client_exceptions.ServerDisconnectedError,
            client_exceptions.ContentTypeError,
            BridgeBusy,
        ) as err:
            raise ConfigEntryNotReady(
                f"Error connecting to the Hue bridge at {self.host}"
            ) from err
        except Exception:
            self.logger.exception("Unknown error connecting to Hue bridge")
            return False
        finally:
            if not setup_ok:
                await self.api.close()


        if self.api_version == 1:
            if self.api.sensors is not None:
                self.sensor_manager = SensorManager(self)
            await self.hass.config_entries.async_forward_entry_setups(
                self.config_entry, PLATFORMS_v1
            )


        else:
            await async_setup_devices(self)
            await async_setup_hue_events(self)
            await self.hass.config_entries.async_forward_entry_setups(
                self.config_entry, PLATFORMS_v2
            )


        self.reset_jobs.append(self.config_entry.add_update_listener(_update_listener))
        self.authorized = True
        return True

    async def async_request_call(self, task: Callable, *args, **kwargs) -> Any:

        try:
            return await task(*args, **kwargs)
        except AiohueException as err:


            msg = f"Request failed: {err}"
            if "may not have effect" in str(err):

                self.logger.debug(msg)
                return None
            raise HomeAssistantError(msg) from err
        except aiohttp.ClientError as err:
            raise HomeAssistantError(
                f"Request failed due connection error: {err}"
            ) from err

    async def async_reset(self) -> bool:










        if self.api is None:
            return True

        while self.reset_jobs:
            self.reset_jobs.pop()()


        unload_success = await self.hass.config_entries.async_unload_platforms(
            self.config_entry, PLATFORMS_v1 if self.api_version == 1 else PLATFORMS_v2
        )

        if unload_success:
            delattr(self.config_entry, "runtime_data")

        return unload_success

    async def handle_unauthorized_error(self) -> None:

        if not self.authorized:

            return
        self.logger.error(
            "Unable to authorize to bridge %s, setup the linking again", self.host
        )
        self.authorized = False
        create_config_flow(self.hass, self.host)


async def _update_listener(hass: core.HomeAssistant, entry: HueConfigEntry) -> None:

    await hass.config_entries.async_reload(entry.entry_id)


def create_config_flow(hass: core.HomeAssistant, host: str) -> None:

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={"host": host},
        )
    )
