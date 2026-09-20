

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.hassio import is_hassio
from homeassistant.helpers.singleton import singleton
from homeassistant.helpers.storage import Store
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN
from .coordinator import ESPHomeDashboardCoordinator

_LOGGER = logging.getLogger(__name__)


KEY_DASHBOARD_MANAGER: HassKey[ESPHomeDashboardManager] = HassKey(
    "esphome_dashboard_manager"
)

STORAGE_KEY = "esphome.dashboard"
STORAGE_VERSION = 1


async def async_setup(hass: HomeAssistant) -> None:




    await async_get_or_create_dashboard_manager(hass)


@singleton(KEY_DASHBOARD_MANAGER, async_=True)
async def async_get_or_create_dashboard_manager(
    hass: HomeAssistant,
) -> ESPHomeDashboardManager:

    manager = ESPHomeDashboardManager(hass)
    await manager.async_setup()
    return manager


class ESPHomeDashboardManager:


    def __init__(self, hass: HomeAssistant) -> None:

        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] | None = None
        self._current_dashboard: ESPHomeDashboardCoordinator | None = None
        self._cancel_shutdown: CALLBACK_TYPE | None = None

    async def async_setup(self) -> None:

        self._data = await self._store.async_load()
        if not (data := self._data) or not (info := data.get("info")):
            return
        if is_hassio(self._hass):
            from homeassistant.components.hassio import get_addons_info

            if (addons := get_addons_info(self._hass)) is not None and info[
                "addon_slug"
            ] not in addons:



                _LOGGER.debug("Addon %s is no longer installed", info["addon_slug"])
                return

        await self.async_set_dashboard_info(
            info["addon_slug"], info["host"], info["port"]
        )

    @callback
    def async_get(self) -> ESPHomeDashboardCoordinator | None:

        return self._current_dashboard

    async def async_set_dashboard_info(
        self, addon_slug: str, host: str, port: int
    ) -> None:

        url = f"http://{host}:{port}"
        hass = self._hass

        if cur_dashboard := self._current_dashboard:
            if cur_dashboard.addon_slug == addon_slug and cur_dashboard.url == url:

                return

            await cur_dashboard.async_shutdown()
            if self._cancel_shutdown is not None:
                self._cancel_shutdown()
                self._cancel_shutdown = None
            self._current_dashboard = None

        dashboard = ESPHomeDashboardCoordinator(hass, addon_slug, url)
        await dashboard.async_request_refresh()

        self._current_dashboard = dashboard

        async def on_hass_stop(_: Event) -> None:
            await dashboard.async_shutdown()

        self._cancel_shutdown = hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, on_hass_stop
        )

        new_data = {"info": {"addon_slug": addon_slug, "host": host, "port": port}}
        if self._data != new_data:
            await self._store.async_save(new_data)

        reloads = [
            hass.config_entries.async_reload(entry.entry_id)
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        ]


        if dashboard.last_update_success:
            reauths = [
                hass.config_entries.flow.async_configure(flow["flow_id"])
                for flow in hass.config_entries.flow.async_progress()
                if flow["handler"] == DOMAIN
                and flow["context"]["source"] == SOURCE_REAUTH
            ]
        else:
            reauths = []
            _LOGGER.error(
                "Dashboard unavailable; skipping reauth: %s", dashboard.last_exception
            )

        _LOGGER.debug(
            "Reloading %d and re-authenticating %d", len(reloads), len(reauths)
        )
        if reloads or reauths:
            await asyncio.gather(*reloads, *reauths)


@callback
def async_get_dashboard(hass: HomeAssistant) -> ESPHomeDashboardCoordinator | None:








    manager = hass.data.get(KEY_DASHBOARD_MANAGER)
    return manager.async_get() if manager else None


async def async_set_dashboard_info(
    hass: HomeAssistant, addon_slug: str, host: str, port: int
) -> None:

    manager = await async_get_or_create_dashboard_manager(hass)
    await manager.async_set_dashboard_info(addon_slug, host, port)
