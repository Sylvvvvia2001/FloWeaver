

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
import functools
import logging
import math
from typing import TYPE_CHECKING, Any, Concatenate, Generic, TypeVar, cast

from aioesphomeapi import (
    APIConnectionError,
    DeviceInfo as EsphomeDeviceInfo,
    EntityCategory as EsphomeEntityCategory,
    EntityInfo,
    EntityState,
)
import voluptuous as vol

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_platform,
    entity_registry as er,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


from .entry_data import (
    DeviceEntityKey,
    ESPHomeConfigEntry,
    RuntimeEntryData,
    build_device_unique_id,
)
from .enum_mapper import EsphomeEnumMapper

_LOGGER = logging.getLogger(__name__)

_InfoT = TypeVar("_InfoT", bound=EntityInfo)
_EntityT = TypeVar("_EntityT", bound="EsphomeEntity[Any,Any]")
_StateT = TypeVar("_StateT", bound=EntityState)


@callback
def async_static_info_updated(
    hass: HomeAssistant,
    entry_data: RuntimeEntryData,
    platform: entity_platform.EntityPlatform,
    async_add_entities: AddEntitiesCallback,
    info_type: type[_InfoT],
    entity_type: type[_EntityT],
    state_type: type[_StateT],
    infos: list[EntityInfo],
) -> None:

    current_infos = entry_data.info[info_type]
    device_info = entry_data.device_info
    if TYPE_CHECKING:
        assert device_info is not None
    new_infos: dict[DeviceEntityKey, EntityInfo] = {}
    add_entities: list[_EntityT] = []

    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)



    for info in infos:
        info_key = (info.device_id, info.key)
        new_infos[info_key] = info


        old_info = current_infos.pop(info_key, None)



        if not old_info:
            for existing_device_id, existing_key in list(current_infos):
                if existing_key == info.key:

                    old_info = current_infos.pop((existing_device_id, existing_key))
                    break


        if not old_info:
            entity = entity_type(entry_data, info, state_type)
            add_entities.append(entity)
            continue


        if old_info.device_id == info.device_id:
            continue


        old_unique_id = build_device_unique_id(device_info.mac_address, old_info)
        entity_id = ent_reg.async_get_entity_id(platform.domain, DOMAIN, old_unique_id)



        if entity_id is None:
            _LOGGER.info(
                "Entity with old unique_id %s not found in registry after device_id "
                "changed from %s to %s, re-adding entity",
                old_unique_id,
                old_info.device_id,
                info.device_id,
            )
            entity = entity_type(entry_data, info, state_type)
            add_entities.append(entity)
            continue

        updates: dict[str, Any] = {}
        new_unique_id = build_device_unique_id(device_info.mac_address, info)


        if old_unique_id != new_unique_id:
            updates["new_unique_id"] = new_unique_id


        if info.device_id:

            new_device = dev_reg.async_get_device(
                identifiers={(DOMAIN, f"{device_info.mac_address}_{info.device_id}")}
            )
        else:

            new_device = dev_reg.async_get_device(
                connections={(dr.CONNECTION_NETWORK_MAC, device_info.mac_address)}
            )

        if new_device:
            updates["device_id"] = new_device.id


        if updates:
            ent_reg.async_update_entity(entity_id, **updates)









        _LOGGER.debug(
            "Entity %s moving from device_id %s to %s",
            info.key,
            old_info.device_id,
            info.device_id,
        )



        entry_data.async_signal_entity_removal(info_type, old_info.device_id, info.key)


        add_entities.append(entity_type(entry_data, info, state_type))


    if current_infos:
        entry_data.async_remove_entities(
            hass, current_infos.values(), device_info.mac_address
        )


    entry_data.info[info_type] = new_infos

    if new_infos:
        entry_data.async_update_entity_infos(new_infos.values())

    if add_entities:

        async_add_entities(add_entities)


async def platform_async_setup_entry(
    hass: HomeAssistant,
    entry: ESPHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
    *,
    info_type: type[_InfoT],
    entity_type: type[_EntityT],
    state_type: type[_StateT],
    info_filter: Callable[[_InfoT], bool] | None = None,
) -> None:





    entry_data = entry.runtime_data
    entry_data.info[info_type] = {}
    platform = entity_platform.async_get_current_platform()
    on_static_info_update = functools.partial(
        async_static_info_updated,
        hass,
        entry_data,
        platform,
        async_add_entities,
        info_type,
        entity_type,
        state_type,
    )

    if info_filter is not None:

        def on_filtered_update(infos: list[EntityInfo]) -> None:
            on_static_info_update(
                [info for info in infos if info_filter(cast(_InfoT, info))]
            )

        info_callback = on_filtered_update
    else:
        info_callback = on_static_info_update

    entry_data.cleanup_callbacks.append(
        entry_data.async_register_static_info_callback(
            info_type,
            info_callback,
        )
    )


def esphome_state_property[_R, _EntityT: EsphomeEntity[Any, Any]](
    func: Callable[[_EntityT], _R],
) -> Callable[[_EntityT], _R | None]:






    @functools.wraps(func)
    def _wrapper(self: _EntityT) -> _R | None:
        return func(self) if self._has_state else None

    return _wrapper


def async_esphome_state_property[_R, _EntityT: EsphomeEntity[Any, Any]](
    func: Callable[[_EntityT], Awaitable[_R | None]],
) -> Callable[[_EntityT], Coroutine[Any, Any, _R | None]]:






    @functools.wraps(func)
    async def _wrapper(self: _EntityT) -> _R | None:
        return await func(self) if self._has_state else None

    return _wrapper


def esphome_float_state_property[_EntityT: EsphomeEntity[Any, Any]](
    func: Callable[[_EntityT], float | None],
) -> Callable[[_EntityT], float | None]:







    @functools.wraps(func)
    def _wrapper(self: _EntityT) -> float | None:
        if not self._has_state:
            return None
        val = func(self)


        return None if val is None or not math.isfinite(val) else val

    return _wrapper


def convert_api_error_ha_error[**_P, _R, _EntityT: EsphomeBaseEntity](
    func: Callable[Concatenate[_EntityT, _P], Awaitable[None]],
) -> Callable[Concatenate[_EntityT, _P], Coroutine[Any, Any, None]]:






    async def handler(self: _EntityT, *args: _P.args, **kwargs: _P.kwargs) -> None:
        try:
            return await func(self, *args, **kwargs)
        except APIConnectionError as error:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="error_communicating_with_device",
                translation_placeholders={
                    "device_name": self._device_info.name,
                    "error": str(error),
                },
            ) from error

    return handler


ICON_SCHEMA = vol.Schema(cv.icon)


ENTITY_CATEGORIES: EsphomeEnumMapper[EsphomeEntityCategory, EntityCategory | None] = (
    EsphomeEnumMapper(
        {
            EsphomeEntityCategory.NONE: None,
            EsphomeEntityCategory.CONFIG: EntityCategory.CONFIG,
            EsphomeEntityCategory.DIAGNOSTIC: EntityCategory.DIAGNOSTIC,
        }
    )
)


class EsphomeBaseEntity(Entity):


    _attr_has_entity_name = True
    _attr_should_poll = False
    _device_info: EsphomeDeviceInfo
    device_entry: dr.DeviceEntry


class EsphomeEntity(EsphomeBaseEntity, Generic[_InfoT, _StateT]):


    _static_info: _InfoT
    _state: _StateT
    _has_state: bool = False
    unique_id: str

    def __init__(
        self,
        entry_data: RuntimeEntryData,
        entity_info: EntityInfo,
        state_type: type[_StateT],
    ) -> None:

        self._entry_data = entry_data
        self._states = cast(dict[int, _StateT], entry_data.state[state_type])
        assert entry_data.device_info is not None
        device_info = entry_data.device_info
        self._on_entry_data_changed()
        self._key = entity_info.key
        self._state_type = state_type
        self._on_static_info_update(entity_info)


        if entity_info.device_id:

            self._attr_device_info = DeviceInfo(
                identifiers={
                    (DOMAIN, f"{device_info.mac_address}_{entity_info.device_id}")
                }
            )
        else:

            self._attr_device_info = DeviceInfo(
                connections={(dr.CONNECTION_NETWORK_MAC, device_info.mac_address)}
            )

    async def async_added_to_hass(self) -> None:

        entry_data = self._entry_data
        self.async_on_remove(
            entry_data.async_subscribe_device_updated(
                self._on_device_update,
            )
        )
        self.async_on_remove(
            entry_data.async_subscribe_state_update(
                self._static_info.device_id,
                self._state_type,
                self._key,
                self._on_state_update,
            )
        )
        self.async_on_remove(
            entry_data.async_register_key_static_info_updated_callback(
                self._static_info, self._on_static_info_update
            )
        )


        self.async_on_remove(
            entry_data.async_register_entity_removal_callback(
                type(self._static_info),
                self._static_info.device_id,
                self._key,
                self._on_removal_signal,
            )
        )
        self._update_state_from_entry_data()

    @callback
    def _on_removal_signal(self) -> None:

        _LOGGER.debug(
            "Entity %s received removal signal due to device_id change",
            self.entity_id,
        )


        self.hass.async_create_task(self.async_remove())

    @callback
    def _on_static_info_update(self, static_info: EntityInfo) -> None:





        device_info = self._entry_data.device_info
        if TYPE_CHECKING:
            static_info = cast(_InfoT, static_info)
            assert device_info
        self._static_info = static_info
        self._attr_unique_id = build_device_unique_id(
            device_info.mac_address, static_info
        )
        self._attr_entity_registry_enabled_default = not static_info.disabled_by_default





        self._attr_name = static_info.name or None
        if entity_category := static_info.entity_category:
            self._attr_entity_category = ENTITY_CATEGORIES.from_esphome(entity_category)
        else:
            self._attr_entity_category = None
        if icon := static_info.icon:
            self._attr_icon = cast(str, ICON_SCHEMA(icon))
        else:
            self._attr_icon = None

    @callback
    def _update_state_from_entry_data(self) -> None:

        key = self._key
        if has_state := key in self._states:
            self._state = self._states[key]
        self._has_state = has_state

    @callback
    def _on_state_update(self) -> None:




        self._update_state_from_entry_data()
        self.async_write_ha_state()

    @callback
    def _on_entry_data_changed(self) -> None:
        entry_data = self._entry_data


        if TYPE_CHECKING:
            assert entry_data.device_info is not None
        self._device_info = entry_data.device_info
        self._api_version = entry_data.api_version
        self._client = entry_data.client
        if self._device_info.has_deep_sleep:


            self._attr_available = entry_data.expected_disconnect
        else:
            self._attr_available = entry_data.available

    @callback
    def _on_device_update(self) -> None:

        self._on_entry_data_changed()
        if not self._entry_data.available:




            self.async_write_ha_state()


class EsphomeAssistEntity(EsphomeBaseEntity):


    def __init__(self, entry_data: RuntimeEntryData) -> None:

        self._entry_data = entry_data
        assert entry_data.device_info is not None
        device_info = entry_data.device_info
        self._device_info = device_info
        self._attr_unique_id = (
            f"{device_info.mac_address}-{self.entity_description.key}"
        )
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_NETWORK_MAC, device_info.mac_address)}
        )

    async def async_added_to_hass(self) -> None:

        await super().async_added_to_hass()
        self.async_on_remove(
            self._entry_data.async_subscribe_assist_pipeline_update(
                self.async_write_ha_state
            )
        )
