

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import partial
import logging
from operator import delitem
from typing import TYPE_CHECKING, Any, Final, TypedDict, cast

from aioesphomeapi import (
    COMPONENT_TYPE_TO_INFO,
    AlarmControlPanelInfo,
    APIClient,
    APIVersion,
    BinarySensorInfo,
    CameraInfo,
    CameraState,
    ClimateInfo,
    CoverInfo,
    DateInfo,
    DateTimeInfo,
    DeviceInfo,
    EntityInfo,
    EntityState,
    Event,
    EventInfo,
    FanInfo,
    InfraredInfo,
    LightInfo,
    LockInfo,
    MediaPlayerInfo,
    MediaPlayerSupportedFormat,
    NumberInfo,
    SelectInfo,
    SensorInfo,
    SensorState,
    SwitchInfo,
    TextInfo,
    TextSensorInfo,
    TimeInfo,
    UpdateInfo,
    UserService,
    ValveInfo,
    WaterHeaterInfo,
    build_unique_id,
)
from aioesphomeapi.model import ButtonInfo
from bleak_esphome.backend.device import ESPHomeBluetoothDevice

from homeassistant import config_entries
from homeassistant.components.assist_satellite import AssistSatelliteConfiguration
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import discovery_flow, entity_registry as er
from homeassistant.helpers.service_info.esphome import ESPHomeServiceInfo
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .dashboard import async_get_dashboard

type ESPHomeConfigEntry = ConfigEntry[RuntimeEntryData]
type EntityStateKey = tuple[type[EntityState], int, int]
type EntityInfoKey = tuple[type[EntityInfo], int, int]
type DeviceEntityKey = tuple[int, int]

INFO_TO_COMPONENT_TYPE: Final = {v: k for k, v in COMPONENT_TYPE_TO_INFO.items()}

_SENTINEL = object()
SAVE_DELAY = 120
_LOGGER = logging.getLogger(__name__)


INFO_TYPE_TO_PLATFORM: dict[type[EntityInfo], Platform] = {
    AlarmControlPanelInfo: Platform.ALARM_CONTROL_PANEL,
    BinarySensorInfo: Platform.BINARY_SENSOR,
    ButtonInfo: Platform.BUTTON,
    CameraInfo: Platform.CAMERA,
    ClimateInfo: Platform.CLIMATE,
    CoverInfo: Platform.COVER,
    DateInfo: Platform.DATE,
    DateTimeInfo: Platform.DATETIME,
    EventInfo: Platform.EVENT,
    FanInfo: Platform.FAN,
    InfraredInfo: Platform.INFRARED,
    LightInfo: Platform.LIGHT,
    LockInfo: Platform.LOCK,
    MediaPlayerInfo: Platform.MEDIA_PLAYER,
    NumberInfo: Platform.NUMBER,
    SelectInfo: Platform.SELECT,
    SensorInfo: Platform.SENSOR,
    SwitchInfo: Platform.SWITCH,
    TextInfo: Platform.TEXT,
    TextSensorInfo: Platform.SENSOR,
    TimeInfo: Platform.TIME,
    UpdateInfo: Platform.UPDATE,
    ValveInfo: Platform.VALVE,
    WaterHeaterInfo: Platform.WATER_HEATER,
}


def build_device_unique_id(mac: str, entity_info: EntityInfo) -> str:






    base_unique_id = build_unique_id(mac, entity_info)


    if entity_info.device_id:
        return f"{base_unique_id}@{entity_info.device_id}"

    return base_unique_id


class StoreData(TypedDict, total=False):


    device_info: dict[str, Any]
    services: list[dict[str, Any]]
    api_version: dict[str, Any]


class ESPHomeStorage(Store[StoreData]):
    pass


@dataclass(slots=True)
class RuntimeEntryData:


    entry_id: str
    title: str
    client: APIClient
    store: ESPHomeStorage
    state: defaultdict[type[EntityState], dict[int, EntityState]] = field(
        default_factory=lambda: defaultdict(dict)
    )



    stale_state: set[EntityStateKey] = field(default_factory=set)
    info: dict[type[EntityInfo], dict[DeviceEntityKey, EntityInfo]] = field(
        default_factory=dict
    )
    services: dict[int, UserService] = field(default_factory=dict)
    available: bool = False
    expected_disconnect: bool = False
    device_info: DeviceInfo | None = None
    bluetooth_device: ESPHomeBluetoothDevice | None = None
    api_version: APIVersion = field(default_factory=APIVersion)
    cleanup_callbacks: list[CALLBACK_TYPE] = field(default_factory=list)
    disconnect_callbacks: set[CALLBACK_TYPE] = field(default_factory=set)
    state_subscriptions: dict[EntityStateKey, CALLBACK_TYPE] = field(
        default_factory=dict
    )
    device_update_subscriptions: set[CALLBACK_TYPE] = field(default_factory=set)
    static_info_update_subscriptions: set[Callable[[list[EntityInfo]], None]] = field(
        default_factory=set
    )
    loaded_platforms: set[Platform] = field(default_factory=set)
    platform_load_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _storage_contents: StoreData | None = None
    _pending_storage: Callable[[], StoreData] | None = None
    assist_pipeline_update_callbacks: list[CALLBACK_TYPE] = field(default_factory=list)
    assist_pipeline_state: bool = False
    entity_info_callbacks: dict[
        type[EntityInfo], list[Callable[[list[EntityInfo]], None]]
    ] = field(default_factory=dict)
    entity_info_key_updated_callbacks: dict[
        EntityInfoKey, list[Callable[[EntityInfo], None]]
    ] = field(default_factory=dict)
    original_options: dict[str, Any] = field(default_factory=dict)
    media_player_formats: dict[str, list[MediaPlayerSupportedFormat]] = field(
        default_factory=lambda: defaultdict(list)
    )
    assist_satellite_config_update_callbacks: list[
        Callable[[AssistSatelliteConfiguration], None]
    ] = field(default_factory=list)
    assist_satellite_set_wake_words_callbacks: list[Callable[[list[str]], None]] = (
        field(default_factory=list)
    )
    assist_satellite_wake_words: dict[int, str] = field(default_factory=dict)
    device_id_to_name: dict[int, str] = field(default_factory=dict)
    entity_removal_callbacks: dict[EntityInfoKey, list[CALLBACK_TYPE]] = field(
        default_factory=dict
    )

    @property
    def name(self) -> str:

        device_info = self.device_info
        return (device_info and device_info.name) or self.title

    @property
    def friendly_name(self) -> str:

        device_info = self.device_info
        return (device_info and device_info.friendly_name) or self.name.title().replace(
            "_", " "
        )

    @callback
    def async_register_static_info_callback(
        self,
        entity_info_type: type[EntityInfo],
        callback_: Callable[[list[EntityInfo]], None],
    ) -> CALLBACK_TYPE:

        callbacks = self.entity_info_callbacks.setdefault(entity_info_type, [])
        callbacks.append(callback_)
        return partial(callbacks.remove, callback_)

    @callback
    def async_register_key_static_info_updated_callback(
        self,
        static_info: EntityInfo,
        callback_: Callable[[EntityInfo], None],
    ) -> CALLBACK_TYPE:

        callback_key = (type(static_info), static_info.device_id, static_info.key)
        callbacks = self.entity_info_key_updated_callbacks.setdefault(callback_key, [])
        callbacks.append(callback_)
        return partial(callbacks.remove, callback_)

    @callback
    def async_set_assist_pipeline_state(self, state: bool) -> None:

        self.assist_pipeline_state = state
        for update_callback in self.assist_pipeline_update_callbacks:
            update_callback()

    @callback
    def async_subscribe_assist_pipeline_update(
        self, update_callback: CALLBACK_TYPE
    ) -> CALLBACK_TYPE:

        self.assist_pipeline_update_callbacks.append(update_callback)
        return partial(self.assist_pipeline_update_callbacks.remove, update_callback)

    @callback
    def async_remove_entities(
        self, hass: HomeAssistant, static_infos: Iterable[EntityInfo], mac: str
    ) -> None:


        ent_reg = er.async_get(hass)
        for info in static_infos:
            if entry := ent_reg.async_get_entity_id(
                INFO_TYPE_TO_PLATFORM[type(info)],
                DOMAIN,
                build_device_unique_id(mac, info),
            ):
                ent_reg.async_remove(entry)

    @callback
    def async_update_entity_infos(self, static_infos: Iterable[EntityInfo]) -> None:

        callbacks = self.entity_info_key_updated_callbacks
        for static_info in static_infos:
            for callback_ in callbacks.get(
                (type(static_info), static_info.device_id, static_info.key), ()
            ):
                callback_(static_info)

    async def _ensure_platforms_loaded(
        self,
        hass: HomeAssistant,
        entry: ESPHomeConfigEntry,
        platforms: set[Platform],
    ) -> None:
        async with self.platform_load_lock:
            if needed := platforms - self.loaded_platforms:
                await hass.config_entries.async_forward_entry_setups(entry, needed)
            self.loaded_platforms |= needed

    async def async_update_static_infos(
        self,
        hass: HomeAssistant,
        entry: ESPHomeConfigEntry,
        infos: list[EntityInfo],
        mac: str,
    ) -> None:


        needed_platforms: set[Platform] = set()

        if self.device_info:
            if async_get_dashboard(hass):




                needed_platforms.add(Platform.UPDATE)
            if self.device_info.voice_assistant_feature_flags_compat(self.api_version):
                needed_platforms.add(Platform.BINARY_SENSOR)
                needed_platforms.add(Platform.SELECT)



        info_types_to_platform = INFO_TYPE_TO_PLATFORM
        infos_by_type: defaultdict[type[EntityInfo], list[EntityInfo]] = defaultdict(
            list
        )
        for info in infos:
            info_type = type(info)
            if platform := info_types_to_platform.get(info_type):
                needed_platforms.add(platform)
                infos_by_type[info_type].append(info)
            else:
                _LOGGER.warning(
                    "Entity type %s is not supported in this version of Home Assistant",
                    info_type,
                )
        await self._ensure_platforms_loaded(hass, entry, needed_platforms)

        for type_, callbacks in self.entity_info_callbacks.items():



            entity_infos = infos_by_type.get(type_, [])
            for callback_ in callbacks:
                callback_(entity_infos)


        for callback_ in self.static_info_update_subscriptions:
            callback_(infos)

    @callback
    def async_subscribe_device_updated(self, callback_: CALLBACK_TYPE) -> CALLBACK_TYPE:

        self.device_update_subscriptions.add(callback_)
        return partial(self.device_update_subscriptions.remove, callback_)

    @callback
    def async_subscribe_static_info_updated(
        self, callback_: Callable[[list[EntityInfo]], None]
    ) -> CALLBACK_TYPE:

        self.static_info_update_subscriptions.add(callback_)
        return partial(self.static_info_update_subscriptions.remove, callback_)

    @callback
    def async_subscribe_state_update(
        self,
        device_id: int,
        state_type: type[EntityState],
        state_key: int,
        entity_callback: CALLBACK_TYPE,
    ) -> CALLBACK_TYPE:

        subscription_key = (state_type, device_id, state_key)
        self.state_subscriptions[subscription_key] = entity_callback
        return partial(delitem, self.state_subscriptions, subscription_key)

    @callback
    def async_update_state(self, state: EntityState) -> None:

        key = state.key
        state_type = type(state)
        stale_state = self.stale_state
        current_state_by_type = self.state[state_type]
        current_state = current_state_by_type.get(key, _SENTINEL)
        subscription_key = (state_type, state.device_id, key)
        if (
            current_state == state
            and subscription_key not in stale_state
            and state_type not in (CameraState, Event)
            and not (
                state_type is SensorState
                and (platform_info := self.info.get(SensorInfo))
                and (entity_info := platform_info.get((state.device_id, state.key)))
                and (cast(SensorInfo, entity_info)).force_update
            )
        ):
            return
        stale_state.discard(subscription_key)
        current_state_by_type[key] = state
        if subscription := self.state_subscriptions.get(subscription_key):
            try:
                subscription()
            except Exception:



                _LOGGER.exception("Error while calling subscription")

    @callback
    def async_update_device_state(self) -> None:

        for callback_ in self.device_update_subscriptions.copy():
            callback_()

    async def async_load_from_store(self) -> tuple[list[EntityInfo], list[UserService]]:

        if (restored := await self.store.async_load()) is None:
            return [], []
        self._storage_contents = restored.copy()

        self.device_info = DeviceInfo.from_dict(restored.pop("device_info"))
        self.api_version = APIVersion.from_dict(restored.pop("api_version", {}))
        infos: list[EntityInfo] = []
        for comp_type, restored_infos in restored.items():
            if TYPE_CHECKING:
                restored_infos = cast(list[dict[str, Any]], restored_infos)
            if comp_type not in COMPONENT_TYPE_TO_INFO:
                continue
            for info in restored_infos:
                cls = COMPONENT_TYPE_TO_INFO[comp_type]
                infos.append(cls.from_dict(info))
        services = [
            UserService.from_dict(service) for service in restored.pop("services", [])
        ]
        return infos, services

    def async_save_to_store(self) -> None:

        if TYPE_CHECKING:
            assert self.device_info is not None
        store_data: StoreData = {
            "device_info": self.device_info.to_dict(),
            "services": [],
            "api_version": self.api_version.to_dict(),
        }
        for info_type, infos in self.info.items():
            comp_type = INFO_TO_COMPONENT_TYPE[info_type]
            store_data[comp_type] = [info.to_dict() for info in infos.values()]

        store_data["services"] = [
            service.to_dict() for service in self.services.values()
        ]
        if store_data == self._storage_contents:
            return

        def _memorized_storage() -> StoreData:
            self._pending_storage = None
            self._storage_contents = store_data
            return store_data

        self._pending_storage = _memorized_storage
        self.store.async_delay_save(_memorized_storage, SAVE_DELAY)

    async def async_cleanup(self) -> None:

        if self._pending_storage:


            await self.store.async_save(self._pending_storage())

    @callback
    def async_on_disconnect(self) -> None:




        self.available = False
        if self.bluetooth_device:
            self.bluetooth_device.available = False


        for disconnect_cb in self.disconnect_callbacks.copy():
            disconnect_cb()


        self.disconnect_callbacks.clear()
        self.disconnect_callbacks = set()

    @callback
    def async_on_connect(
        self, hass: HomeAssistant, device_info: DeviceInfo, api_version: APIVersion
    ) -> None:

        self.available = True
        if self.bluetooth_device:
            self.bluetooth_device.available = True

        self.device_info = device_info
        self.api_version = api_version





        self.expected_disconnect = True

        if not device_info.zwave_proxy_feature_flags:
            return

        assert self.client.connected_address








        if not device_info.zwave_home_id:
            return

        self.async_create_zwave_js_flow(hass, device_info, device_info.zwave_home_id)

    def async_create_zwave_js_flow(
        self, hass: HomeAssistant, device_info: DeviceInfo, zwave_home_id: int
    ) -> None:

        assert self.client.connected_address is not None
        discovery_flow.async_create_flow(
            hass,
            "zwave_js",
            {"source": config_entries.SOURCE_ESPHOME},
            ESPHomeServiceInfo(
                name=device_info.name,
                zwave_home_id=zwave_home_id,
                ip_address=self.client.connected_address,
                port=self.client.port,
                noise_psk=self.client.noise_psk,
            ),
            discovery_key=discovery_flow.DiscoveryKey(
                domain=DOMAIN,
                key=device_info.mac_address,
                version=1,
            ),
        )

    @callback
    def async_register_assist_satellite_config_updated_callback(
        self,
        callback_: Callable[[AssistSatelliteConfiguration], None],
    ) -> CALLBACK_TYPE:

        self.assist_satellite_config_update_callbacks.append(callback_)
        return partial(self.assist_satellite_config_update_callbacks.remove, callback_)

    @callback
    def async_assist_satellite_config_updated(
        self, config: AssistSatelliteConfiguration
    ) -> None:

        for callback_ in self.assist_satellite_config_update_callbacks.copy():
            callback_(config)

    @callback
    def async_register_assist_satellite_set_wake_words_callback(
        self,
        callback_: Callable[[list[str]], None],
    ) -> CALLBACK_TYPE:

        self.assist_satellite_set_wake_words_callbacks.append(callback_)
        return partial(self.assist_satellite_set_wake_words_callbacks.remove, callback_)

    @callback
    def async_assist_satellite_set_wake_word(
        self, wake_word_index: int, wake_word_id: str | None
    ) -> None:

        if wake_word_id:
            self.assist_satellite_wake_words[wake_word_index] = wake_word_id
        else:
            self.assist_satellite_wake_words.pop(wake_word_index, None)

        wake_word_ids = list(self.assist_satellite_wake_words.values())

        for callback_ in self.assist_satellite_set_wake_words_callbacks.copy():
            callback_(wake_word_ids)

    @callback
    def async_register_entity_removal_callback(
        self,
        info_type: type[EntityInfo],
        device_id: int,
        key: int,
        callback_: CALLBACK_TYPE,
    ) -> CALLBACK_TYPE:

        callback_key = (info_type, device_id, key)
        callbacks = self.entity_removal_callbacks.setdefault(callback_key, [])
        callbacks.append(callback_)
        return partial(callbacks.remove, callback_)

    @callback
    def async_signal_entity_removal(
        self, info_type: type[EntityInfo], device_id: int, key: int
    ) -> None:

        callback_key = (info_type, device_id, key)
        for callback_ in self.entity_removal_callbacks.get(callback_key, []).copy():
            callback_()
