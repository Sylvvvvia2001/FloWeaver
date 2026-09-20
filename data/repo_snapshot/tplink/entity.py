

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Coroutine, Iterable, Mapping
from dataclasses import dataclass, replace
import logging
from typing import Any, Concatenate

from kasa import (
    AuthenticationError,
    Device,
    DeviceType,
    Feature,
    KasaException,
    TimeoutError,
)

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.typing import UNDEFINED, UndefinedType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_device_name, legacy_device_id
from .const import (
    ATTR_CURRENT_A,
    ATTR_CURRENT_POWER_W,
    ATTR_TODAY_ENERGY_KWH,
    ATTR_TOTAL_ENERGY_KWH,
    DOMAIN,
    PRIMARY_STATE_ID,
)
from .coordinator import TPLinkConfigEntry, TPLinkDataUpdateCoordinator
from .deprecate import (
    DeprecatedInfo,
    async_check_create_deprecated,
    async_process_deprecated,
)

_LOGGER = logging.getLogger(__name__)


FEATURE_CATEGORY_TO_ENTITY_CATEGORY = {
    Feature.Category.Config: EntityCategory.CONFIG,
    Feature.Category.Info: EntityCategory.DIAGNOSTIC,
    Feature.Category.Debug: EntityCategory.DIAGNOSTIC,
}



DEVICETYPES_WITH_SPECIALIZED_PLATFORMS = {
    DeviceType.Bulb,
    DeviceType.LightStrip,
    DeviceType.Dimmer,
    DeviceType.Fan,
    DeviceType.Thermostat,
    DeviceType.Vacuum,
}


FEATURES_ALLOW_LIST = {

    "current_consumption"
}



EXCLUDED_FEATURES = {

    "current_firmware_version",
    "available_firmware_version",
    "update_available",
    "check_latest_firmware",

    "alarm",
}


LEGACY_KEY_MAPPING = {
    "current": ATTR_CURRENT_A,
    "current_consumption": ATTR_CURRENT_POWER_W,
    "consumption_today": ATTR_TODAY_ENERGY_KWH,
    "consumption_total": ATTR_TOTAL_ENERGY_KWH,
}


@dataclass(frozen=True, kw_only=True)
class TPLinkEntityDescription(EntityDescription):


    deprecated_info: DeprecatedInfo | None = None
    available_fn: Callable[[Device], bool] = lambda _: True


@dataclass(frozen=True, kw_only=True)
class TPLinkFeatureEntityDescription(TPLinkEntityDescription):
    pass


@dataclass(frozen=True, kw_only=True)
class TPLinkModuleEntityDescription(TPLinkEntityDescription):


    exists_fn: Callable[[Device, TPLinkConfigEntry], bool]
    unique_id_fn: Callable[[Device, TPLinkModuleEntityDescription], str] = (
        lambda device, desc: f"{legacy_device_id(device)}-{desc.key}"
    )
    entity_name_fn: (
        Callable[[Device, TPLinkModuleEntityDescription], str | None] | None
    ) = None


def async_refresh_after[_T: CoordinatedTPLinkEntity, **_P](
    func: Callable[Concatenate[_T, _P], Awaitable[None]],
) -> Callable[Concatenate[_T, _P], Coroutine[Any, Any, None]]:


    async def _async_wrap(self: _T, *args: _P.args, **kwargs: _P.kwargs) -> None:
        try:
            await func(self, *args, **kwargs)
        except AuthenticationError as ex:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_authentication",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        except TimeoutError as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_timeout",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        except KasaException as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_error",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        await self.coordinator.async_request_refresh()

    return _async_wrap


class CoordinatedTPLinkEntity(CoordinatorEntity[TPLinkDataUpdateCoordinator], ABC):


    _attr_has_entity_name = True
    _device: Device

    entity_description: TPLinkEntityDescription

    def __init__(
        self,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        description: TPLinkEntityDescription,
        *,
        feature: Feature | None = None,
        parent: Device | None = None,
    ) -> None:

        super().__init__(coordinator)
        self.entity_description = description
        self._device: Device = device
        self._parent = parent
        self._feature = feature

        registry_device = device
        device_name = get_device_name(device, parent=parent)
        translation_key: str | None = None
        translation_placeholders: Mapping[str, str] | None = None

        if parent and parent.device_type is not Device.Type.Hub:
            if not feature or feature.id == PRIMARY_STATE_ID:



                registry_device = parent
                device_name = get_device_name(registry_device)
                if not device_name:
                    translation_key = "unnamed_device"
                    translation_placeholders = {"model": parent.model}
            else:







                parent_device_name = get_device_name(parent)
                child_device_name = get_device_name(device, parent=parent)
                if parent_device_name:
                    device_name = f"{parent_device_name} {child_device_name}"
                else:
                    device_name = None
                    translation_key = "unnamed_device"
                    translation_placeholders = {
                        "model": f"{parent.model} {child_device_name}"
                    }

        if device_name is None and not translation_key:
            translation_key = "unnamed_device"
            translation_placeholders = {"model": device.model}

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(registry_device.device_id))},
            manufacturer="TP-Link",
            model=registry_device.model,
            name=device_name,
            translation_key=translation_key,
            translation_placeholders=translation_placeholders,
            sw_version=registry_device.hw_info["sw_ver"],
            hw_version=registry_device.hw_info["hw_ver"],
        )





        if (
            parent is not None
            and parent != registry_device
            and parent.device_type is not Device.Type.WallSwitch
        ):
            self._attr_device_info["via_device"] = (DOMAIN, parent.device_id)
        else:
            self._attr_device_info["connections"] = {
                (dr.CONNECTION_NETWORK_MAC, device.mac)
            }

        self._attr_unique_id = self._get_unique_id()

    def _get_unique_id(self) -> str:

        raise NotImplementedError

    async def async_added_to_hass(self) -> None:

        await super().async_added_to_hass()

        self._async_call_update_attrs()

    @abstractmethod
    @callback
    def _async_update_attrs(self) -> bool:




        raise NotImplementedError

    @callback
    def _async_call_update_attrs(self) -> None:

        try:
            available = self._async_update_attrs()
        except Exception as ex:
            if self._attr_available:
                _LOGGER.warning(
                    "Unable to read data for %s %s: %s",
                    self._device,
                    self.entity_id,
                    ex,
                )
            self._attr_available = False
        else:
            self._attr_available = available

    @callback
    def _handle_coordinator_update(self) -> None:

        self._async_call_update_attrs()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:

        return self.coordinator.last_update_success and self._attr_available


class CoordinatedTPLinkFeatureEntity(CoordinatedTPLinkEntity, ABC):


    entity_description: TPLinkFeatureEntityDescription
    _feature: Feature

    def __init__(
        self,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        description: TPLinkFeatureEntityDescription,
        *,
        feature: Feature,
        parent: Device | None = None,
    ) -> None:

        super().__init__(
            device, coordinator, description, parent=parent, feature=feature
        )



        self._async_call_update_attrs()

    def _get_unique_id(self) -> str:

        return self._get_feature_unique_id(self._device, self.entity_description)

    @staticmethod
    def _get_feature_unique_id(
        device: Device, entity_description: TPLinkFeatureEntityDescription
    ) -> str:

        key = entity_description.key


        if key == PRIMARY_STATE_ID:
            return legacy_device_id(device)





        key = LEGACY_KEY_MAPPING.get(key, key)
        return f"{legacy_device_id(device)}_{key}"

    @classmethod
    def _category_for_feature(cls, feature: Feature | None) -> EntityCategory | None:


        if feature is None or feature.category is Feature.Category.Primary:
            return None

        if (
            entity_category := FEATURE_CATEGORY_TO_ENTITY_CATEGORY.get(feature.category)
        ) is None:
            _LOGGER.error(
                "Unhandled category %s, fallback to DIAGNOSTIC", feature.category
            )
            entity_category = EntityCategory.DIAGNOSTIC

        return entity_category

    @classmethod
    def _description_for_feature[_D: EntityDescription](
        cls,
        feature: Feature,
        descriptions: Mapping[str, _D],
        *,
        device: Device,
        parent: Device | None = None,
    ) -> _D | None:






        if descriptions and (desc := descriptions.get(feature.id)):
            translation_key: str | None = feature.id




            name: str | None | UndefinedType = UNDEFINED



            if feature.id == PRIMARY_STATE_ID:
                translation_key = None

                name = get_device_name(device, parent=parent) if parent else None

            return replace(
                desc,
                translation_key=translation_key,
                name=name,
                entity_category=cls._category_for_feature(feature),

                entity_registry_enabled_default=feature.category
                is not Feature.Category.Debug
                and desc.entity_registry_enabled_default,
            )

        _LOGGER.debug(
            "Device feature: %s (%s) needs an entity description defined in HA",
            feature.name,
            feature.id,
        )
        return None

    @classmethod
    def _entities_for_device[
        _E: CoordinatedTPLinkFeatureEntity,
        _D: TPLinkFeatureEntityDescription,
    ](
        cls,
        hass: HomeAssistant,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        *,
        feature_type: Feature.Type,
        entity_class: type[_E],
        descriptions: Mapping[str, _D],
        platform_domain: str,
        parent: Device | None = None,
    ) -> list[_E]:





        entities: list[_E] = [
            entity_class(
                device,
                coordinator,
                feature=feat,
                description=desc,
                parent=parent,
            )
            for feat in device.features.values()
            if feat.type == feature_type
            and feat.id not in EXCLUDED_FEATURES
            and (
                feat.category is not Feature.Category.Primary
                or device.device_type not in DEVICETYPES_WITH_SPECIALIZED_PLATFORMS
                or feat.id in FEATURES_ALLOW_LIST
            )
            and (
                desc := cls._description_for_feature(
                    feat, descriptions, device=device, parent=parent
                )
            )
            and async_check_create_deprecated(
                hass,
                cls._get_feature_unique_id(device, desc),
                desc,
            )
        ]
        async_process_deprecated(
            hass, platform_domain, coordinator.config_entry.entry_id, entities, device
        )
        return entities

    @classmethod
    def entities_for_device_and_its_children[
        _E: CoordinatedTPLinkFeatureEntity,
        _D: TPLinkFeatureEntityDescription,
    ](
        cls,
        hass: HomeAssistant,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        *,
        feature_type: Feature.Type,
        entity_class: type[_E],
        descriptions: Mapping[str, _D],
        platform_domain: str,
        known_child_device_ids: set[str],
        first_check: bool,
    ) -> list[_E]:




        entities: list[_E] = []


        if first_check:
            entities.extend(
                cls._entities_for_device(
                    hass,
                    device,
                    coordinator=coordinator,
                    feature_type=feature_type,
                    entity_class=entity_class,
                    descriptions=descriptions,
                    platform_domain=platform_domain,
                )
            )

        children = _get_new_children(
            device, coordinator, known_child_device_ids, entity_class.__name__
        )

        if children:
            _LOGGER.debug(
                "Getting %s entities for %s child devices on device %s",
                entity_class.__name__,
                len(children),
                device.host,
            )

        for child in children:
            child_coordinator = coordinator.get_child_coordinator(
                child, platform_domain
            )

            child_entities = cls._entities_for_device(
                hass,
                child,
                coordinator=child_coordinator,
                feature_type=feature_type,
                entity_class=entity_class,
                descriptions=descriptions,
                platform_domain=platform_domain,
                parent=device,
            )
            _LOGGER.debug(
                "Device %s, found %s child %s entities for child id %s",
                device.host,
                len(entities),
                entity_class.__name__,
                child.device_id,
            )
            entities.extend(child_entities)

        return entities


class CoordinatedTPLinkModuleEntity(CoordinatedTPLinkEntity, ABC):


    entity_description: TPLinkModuleEntityDescription

    def __init__(
        self,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        description: TPLinkModuleEntityDescription,
        *,
        parent: Device | None = None,
    ) -> None:

        super().__init__(device, coordinator, description, parent=parent)






        if entity_name_fn := description.entity_name_fn:
            self._attr_name = entity_name_fn(device, description)
        elif not description.translation_key:
            if parent is None or parent.device_type is Device.Type.Hub:
                self._attr_name = None
            else:
                self._attr_name = get_device_name(device)

    def _get_unique_id(self) -> str:

        desc = self.entity_description
        return desc.unique_id_fn(self._device, desc)

    @classmethod
    def _entities_for_device[
        _E: CoordinatedTPLinkModuleEntity,
        _D: TPLinkModuleEntityDescription,
    ](
        cls,
        hass: HomeAssistant,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        *,
        entity_class: type[_E],
        descriptions: Iterable[_D],
        platform_domain: str,
        parent: Device | None = None,
    ) -> list[_E]:

        entities: list[_E] = [
            entity_class(
                device,
                coordinator,
                description=description,
                parent=parent,
            )
            for description in descriptions
            if description.exists_fn(device, coordinator.config_entry)
            and async_check_create_deprecated(
                hass,
                description.unique_id_fn(device, description),
                description,
            )
        ]
        async_process_deprecated(
            hass, platform_domain, coordinator.config_entry.entry_id, entities, device
        )
        return entities

    @classmethod
    def entities_for_device_and_its_children[
        _E: CoordinatedTPLinkModuleEntity,
        _D: TPLinkModuleEntityDescription,
    ](
        cls,
        hass: HomeAssistant,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        *,
        entity_class: type[_E],
        descriptions: Iterable[_D],
        platform_domain: str,
        known_child_device_ids: set[str],
        first_check: bool,
    ) -> list[_E]:




        entities: list[_E] = []



        if first_check:
            entities.extend(
                cls._entities_for_device(
                    hass,
                    device,
                    coordinator=coordinator,
                    entity_class=entity_class,
                    descriptions=descriptions,
                    platform_domain=platform_domain,
                )
            )
            has_parent_entities = bool(entities)

        children = _get_new_children(
            device, coordinator, known_child_device_ids, entity_class.__name__
        )

        if children:
            _LOGGER.debug(
                "Getting %s entities for %s child devices on device %s",
                entity_class.__name__,
                len(children),
                device.host,
            )
        for child in children:
            child_coordinator = coordinator.get_child_coordinator(
                child, platform_domain
            )

            child_entities: list[_E] = cls._entities_for_device(
                hass,
                child,
                coordinator=child_coordinator,
                entity_class=entity_class,
                descriptions=descriptions,
                platform_domain=platform_domain,
                parent=device,
            )
            _LOGGER.debug(
                "Device %s, found %s child %s entities for child id %s",
                device.host,
                len(entities),
                entity_class.__name__,
                child.device_id,
            )
            entities.extend(child_entities)

        if first_check and entities and not has_parent_entities:




            device_registry = dr.async_get(hass)
            device_registry.async_get_or_create(
                config_entry_id=coordinator.config_entry.entry_id,
                identifiers={(DOMAIN, device.device_id)},
            )
        return entities


def _get_new_children(
    device: Device,
    coordinator: TPLinkDataUpdateCoordinator,
    known_child_device_ids: set[str],
    entity_class_name: str,
) -> list[Device]:


    for removed_child_id in coordinator.removed_child_device_ids:
        _LOGGER.debug(
            "Removing %s from known %s child ids for device %s"
            "as it has been removed by the coordinator",
            removed_child_id,
            entity_class_name,
            device.host,
        )
        known_child_device_ids.discard(removed_child_id)

    current_child_devices = {child.device_id: child for child in device.children}
    current_child_device_ids = set(current_child_devices.keys())
    new_child_device_ids = current_child_device_ids - known_child_device_ids
    children = []

    if new_child_device_ids:
        children = [
            child
            for child_id, child in current_child_devices.items()
            if child_id in new_child_device_ids
        ]
        known_child_device_ids.update(new_child_device_ids)
        return children
    return []
