

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any, TypeVar

from propcache.api import cached_property
from roborock import B01Props
from roborock.data import HomeDataScene
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.a01 import DyadApi, ZeoApi
from roborock.devices.traits.b01 import Q7PropertiesApi, Q10PropertiesApi
from roborock.devices.traits.v1 import PropertiesApi
from roborock.exceptions import RoborockDeviceBusy, RoborockException
from roborock.roborock_message import (
    RoborockB01Props,
    RoborockDyadDataProtocol,
    RoborockZeoProtocol,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_CONNECTIONS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util, slugify

from .const import (
    A01_UPDATE_INTERVAL,
    DOMAIN,
    IMAGE_CACHE_INTERVAL,
    Q10_UPDATE_INTERVAL,
    V1_CLOUD_IN_CLEANING_INTERVAL,
    V1_CLOUD_NOT_CLEANING_INTERVAL,
    V1_LOCAL_IN_CLEANING_INTERVAL,
    V1_LOCAL_NOT_CLEANING_INTERVAL,
)
from .models import DeviceState, get_device_info

SCAN_INTERVAL = timedelta(seconds=30)





MIN_UNAVAILABLE_DURATION = timedelta(minutes=2)

_LOGGER = logging.getLogger(__name__)


@dataclass
class RoborockCoordinators:


    v1: list[RoborockDataUpdateCoordinator]
    a01: list[RoborockDataUpdateCoordinatorA01]
    b01_q7: list[RoborockB01Q7UpdateCoordinator]
    b01_q10: list[RoborockB01Q10UpdateCoordinator]

    def values(
        self,
    ) -> list[
        RoborockDataUpdateCoordinator
        | RoborockDataUpdateCoordinatorA01
        | RoborockB01Q7UpdateCoordinator
        | RoborockB01Q10UpdateCoordinator
    ]:

        return self.v1 + self.a01 + self.b01_q7 + self.b01_q10


type RoborockConfigEntry = ConfigEntry[RoborockCoordinators]


class RoborockDataUpdateCoordinator(DataUpdateCoordinator[DeviceState | None]):


    config_entry: RoborockConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: RoborockConfigEntry,
        device: RoborockDevice,
        properties_api: PropertiesApi,
    ) -> None:

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,

            update_interval=V1_LOCAL_NOT_CLEANING_INTERVAL,
        )
        self._device = device
        self.properties_api = properties_api
        self.device_info = get_device_info(device)
        if mac := properties_api.network_info.mac:
            self.device_info[ATTR_CONNECTIONS] = {
                (dr.CONNECTION_NETWORK_MAC, dr.format_mac(mac))
            }
        self.last_update_state: str | None = None

        self._last_home_update_attempt: datetime
        self.last_home_update: datetime | None = None


        self._last_update_success_time: datetime | None = None
        self._has_connected_locally: bool = False

    @cached_property
    def dock_device_info(self) -> DeviceInfo:





        dock_type = self.properties_api.status.dock_type
        return DeviceInfo(
            name=f"{self._device.device_info.name} Dock",
            identifiers={(DOMAIN, f"{self.duid}_dock")},
            manufacturer="Roborock",
            model=f"{self._device.product.model} Dock",
            model_id=str(dock_type.value) if dock_type is not None else "Unknown",
            sw_version=self._device.device_info.fv,
        )

    async def _async_setup(self) -> None:

        await self._verify_api()
        try:
            await self.properties_api.status.refresh()
        except RoborockException as err:
            _LOGGER.debug("Failed to update data during setup: %s", err)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_data_fail",
            ) from err

        self._last_home_update_attempt = dt_util.utcnow()







        try:
            await self.properties_api.home.discover_home()
        except RoborockDeviceBusy:
            _LOGGER.info("Home discovery skipped while device is busy/cleaning")
        except RoborockException as err:
            _LOGGER.debug("Failed to get maps: %s", err)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="map_failure",
                translation_placeholders={"error": str(err)},
            ) from err
        else:

            self.last_home_update = dt_util.utcnow() - IMAGE_CACHE_INTERVAL

    async def update_map(self) -> None:

        try:
            await self.properties_api.home.discover_home()
            await self.properties_api.home.refresh()
        except RoborockException as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="map_failure",
            ) from ex
        else:
            self.last_home_update = dt_util.utcnow()

    async def _verify_api(self) -> None:

        if self._device.is_connected:
            self._has_connected_locally |= self._device.is_local_connected
            if self._has_connected_locally:
                async_delete_issue(
                    self.hass, DOMAIN, f"cloud_api_used_{self.duid_slug}"
                )
            else:
                self.update_interval = V1_CLOUD_NOT_CLEANING_INTERVAL
                async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"cloud_api_used_{self.duid_slug}",
                    is_fixable=False,
                    severity=IssueSeverity.WARNING,
                    translation_key="cloud_api_used",
                    translation_placeholders={"device_name": self._device.name},
                    learn_more_url="https://www.home-assistant.io/integrations/roborock/#the-integration-tells-me-it-cannot-reach-my-vacuum-and-is-using-the-cloud-api-and-that-this-is-not-supported-or-i-am-having-any-networking-issues",
                )

    async def _update_device_prop(self) -> None:

        await _refresh_traits(
            [
                trait
                for trait in (
                    self.properties_api.status,
                    self.properties_api.consumables,
                    self.properties_api.clean_summary,
                    self.properties_api.dnd,
                    self.properties_api.dust_collection_mode,
                    self.properties_api.wash_towel_mode,
                    self.properties_api.smart_wash_params,
                    self.properties_api.sound_volume,
                    self.properties_api.child_lock,
                    self.properties_api.flow_led_status,
                    self.properties_api.valley_electricity_timer,
                )
                if trait is not None
            ]
        )
        _LOGGER.debug("Updated device properties")

    async def _async_update_data(self) -> DeviceState | None:

        await self._verify_api()
        try:

            await self._update_device_prop()
        except UpdateFailed:
            if self._should_suppress_update_failure():
                _LOGGER.debug(
                    "Suppressing update failure until unavailable duration passed"
                )
                return self.data
            raise



        new_status = self.properties_api.status
        if (
            new_status.in_cleaning
            and (dt_util.utcnow() - self._last_home_update_attempt)
            > IMAGE_CACHE_INTERVAL
        ) or self.last_update_state != new_status.state_name:
            self._last_home_update_attempt = dt_util.utcnow()
            try:
                await self.update_map()
            except HomeAssistantError as err:
                _LOGGER.debug("Failed to update map: %s", err)

        if self.properties_api.status.in_cleaning:
            if self._device.is_local_connected:
                self.update_interval = V1_LOCAL_IN_CLEANING_INTERVAL
            else:
                self.update_interval = V1_CLOUD_IN_CLEANING_INTERVAL
        elif self._device.is_local_connected:
            self.update_interval = V1_LOCAL_NOT_CLEANING_INTERVAL
        else:
            self.update_interval = V1_CLOUD_NOT_CLEANING_INTERVAL
        self.last_update_state = self.properties_api.status.state_name
        self._last_update_success_time = dt_util.utcnow()
        _LOGGER.debug("Data update successful %s", self._last_update_success_time)
        return DeviceState(
            status=self.properties_api.status,
            dnd_timer=self.properties_api.dnd,
            consumable=self.properties_api.consumables,
            clean_summary=self.properties_api.clean_summary,
        )

    def _should_suppress_update_failure(self) -> bool:









        if self._last_update_success_time is None:

            return False
        failure_duration = dt_util.utcnow() - self._last_update_success_time
        _LOGGER.debug("Update failure duration: %s", failure_duration)
        return failure_duration < MIN_UNAVAILABLE_DURATION

    async def get_routines(self) -> list[HomeDataScene]:

        try:
            return await self.properties_api.routines.get_routines()
        except RoborockException as err:
            _LOGGER.error("Failed to get routines %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={
                    "command": "get_scenes",
                },
            ) from err

    async def execute_routines(self, routine_id: int) -> None:

        try:
            await self.properties_api.routines.execute_routine(routine_id)
        except RoborockException as err:
            _LOGGER.error("Failed to execute routines %s %s", routine_id, err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={
                    "command": "execute_scene",
                },
            ) from err

    @cached_property
    def duid(self) -> str:

        return self._device.duid

    @cached_property
    def duid_slug(self) -> str:

        return slugify(self.duid)

    @property
    def device(self) -> RoborockDevice:

        return self._device


async def _refresh_traits(traits: list[Any]) -> None:






    for trait in traits:
        try:
            await trait.refresh()
        except RoborockException as ex:
            _LOGGER.debug(
                "Failed to update data (%s): %s", trait.__class__.__name__, ex
            )
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_data_fail",
            ) from ex


_V = TypeVar("_V", bound=RoborockDyadDataProtocol | RoborockZeoProtocol)


class RoborockDataUpdateCoordinatorA01(DataUpdateCoordinator[dict[_V, StateType]]):


    config_entry: RoborockConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: RoborockConfigEntry,
        device: RoborockDevice,
    ) -> None:

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=A01_UPDATE_INTERVAL,
        )
        self._device = device
        self.device_info = get_device_info(device)
        self.request_protocols: list[_V] = []

    @cached_property
    def duid(self) -> str:

        return self._device.duid

    @cached_property
    def duid_slug(self) -> str:

        return slugify(self.duid)

    @property
    def device(self) -> RoborockDevice:

        return self._device


class RoborockWashingMachineUpdateCoordinator(
    RoborockDataUpdateCoordinatorA01[RoborockZeoProtocol]
):


    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: RoborockConfigEntry,
        device: RoborockDevice,
        api: ZeoApi,
    ) -> None:

        super().__init__(hass, config_entry, device)
        self.api = api
        self.request_protocols: list[RoborockZeoProtocol] = []

        self.request_protocols = [
            RoborockZeoProtocol.STATE,
            RoborockZeoProtocol.COUNTDOWN,
            RoborockZeoProtocol.WASHING_LEFT,
            RoborockZeoProtocol.ERROR,
            RoborockZeoProtocol.TIMES_AFTER_CLEAN,
            RoborockZeoProtocol.DETERGENT_EMPTY,
            RoborockZeoProtocol.SOFTENER_EMPTY,
            RoborockZeoProtocol.DETERGENT_TYPE,
            RoborockZeoProtocol.SOFTENER_TYPE,
            RoborockZeoProtocol.MODE,
            RoborockZeoProtocol.PROGRAM,
            RoborockZeoProtocol.TEMP,
            RoborockZeoProtocol.RINSE_TIMES,
            RoborockZeoProtocol.SPIN_LEVEL,
            RoborockZeoProtocol.DRYING_MODE,
            RoborockZeoProtocol.SOUND_SET,
        ]

    async def _async_update_data(
        self,
    ) -> dict[RoborockZeoProtocol, StateType]:
        try:
            return await self.api.query_values(self.request_protocols)
        except RoborockException as ex:
            _LOGGER.debug("Failed to update washing machine data: %s", ex)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_data_fail",
            ) from ex


class RoborockWetDryVacUpdateCoordinator(
    RoborockDataUpdateCoordinatorA01[RoborockDyadDataProtocol]
):


    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: RoborockConfigEntry,
        device: RoborockDevice,
        api: DyadApi,
    ) -> None:

        super().__init__(hass, config_entry, device)
        self.api = api

        self.request_protocols: list[RoborockDyadDataProtocol] = [
            RoborockDyadDataProtocol.STATUS,
            RoborockDyadDataProtocol.POWER,
            RoborockDyadDataProtocol.MESH_LEFT,
            RoborockDyadDataProtocol.BRUSH_LEFT,
            RoborockDyadDataProtocol.ERROR,
            RoborockDyadDataProtocol.TOTAL_RUN_TIME,
        ]

    async def _async_update_data(
        self,
    ) -> dict[RoborockDyadDataProtocol, StateType]:
        try:
            return await self.api.query_values(self.request_protocols)
        except RoborockException as ex:
            _LOGGER.debug("Failed to update wet dry vac data: %s", ex)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_data_fail",
            ) from ex


class RoborockDataUpdateCoordinatorB01(DataUpdateCoordinator[B01Props]):


    config_entry: RoborockConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: RoborockConfigEntry,
        device: RoborockDevice,
    ) -> None:

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=A01_UPDATE_INTERVAL,
        )
        self._device = device
        self.device_info = get_device_info(device)

    @cached_property
    def duid(self) -> str:

        return self._device.duid

    @cached_property
    def duid_slug(self) -> str:

        return slugify(self.duid)

    @property
    def device(self) -> RoborockDevice:

        return self._device


class RoborockB01Q7UpdateCoordinator(RoborockDataUpdateCoordinatorB01):


    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: RoborockConfigEntry,
        device: RoborockDevice,
        api: Q7PropertiesApi,
    ) -> None:

        super().__init__(hass, config_entry, device)
        self.api = api
        self.request_protocols: list[RoborockB01Props] = [
            RoborockB01Props.STATUS,
            RoborockB01Props.MAIN_BRUSH,
            RoborockB01Props.SIDE_BRUSH,
            RoborockB01Props.DUST_BAG_USED,
            RoborockB01Props.MOP_LIFE,
            RoborockB01Props.MAIN_SENSOR,
            RoborockB01Props.CLEANING_TIME,
            RoborockB01Props.REAL_CLEAN_TIME,
            RoborockB01Props.HYPA,
            RoborockB01Props.WIND,
            RoborockB01Props.WATER,
            RoborockB01Props.MODE,
            RoborockB01Props.QUANTITY,
        ]

    async def _async_update_data(
        self,
    ) -> B01Props:
        try:
            data = await self.api.query_values(self.request_protocols)
        except RoborockException as ex:
            _LOGGER.debug("Failed to update Q7 data: %s", ex)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_data_fail",
            ) from ex
        if data is None:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_data_fail",
            )
        return data


class RoborockB01Q10UpdateCoordinator(DataUpdateCoordinator[None]):











    config_entry: RoborockConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: RoborockConfigEntry,
        device: RoborockDevice,
        api: Q10PropertiesApi,
    ) -> None:

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=Q10_UPDATE_INTERVAL,
        )
        self._device = device
        self.api = api
        self.device_info = get_device_info(device)

    async def _async_update_data(self) -> None:






        try:
            await self.api.refresh()
        except RoborockException as ex:
            _LOGGER.debug("Failed to request Q10 data: %s", ex)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="request_fail",
            ) from ex

    @cached_property
    def duid(self) -> str:

        return self._device.duid

    @cached_property
    def duid_slug(self) -> str:

        return slugify(self.duid)

    @property
    def device(self) -> RoborockDevice:

        return self._device
