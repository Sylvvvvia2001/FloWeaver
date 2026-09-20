

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from functools import partial
import logging
from operator import attrgetter
from types import MappingProxyType
from typing import Any, cast

from aiohomekit import Controller
from aiohomekit.controller import TransportType
from aiohomekit.controller.ble.discovery import BleDiscovery
from aiohomekit.exceptions import (
    AccessoryDisconnectedError,
    AccessoryNotFoundError,
    EncryptionError,
)
from aiohomekit.model import Accessories, Accessory, Transport
from aiohomekit.model.characteristics import (
    EVENT_CHARACTERISTICS,
    Characteristic,
    CharacteristicPermissions,
    CharacteristicsTypes,
)
from aiohomekit.model.services import Service, ServicesTypes

from homeassistant.components.thread import async_get_preferred_dataset
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_VIA_DEVICE, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CALLBACK_TYPE, CoreState, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .config_flow import normalize_hkid
from .const import (
    CHARACTERISTIC_PLATFORMS,
    CONTROLLER,
    DEBOUNCE_COOLDOWN,
    DOMAIN,
    HOMEKIT_ACCESSORY_DISPATCH,
    IDENTIFIER_ACCESSORY_ID,
    IDENTIFIER_LEGACY_ACCESSORY_ID,
    IDENTIFIER_LEGACY_SERIAL_NUMBER,
    IDENTIFIER_SERIAL_NUMBER,
    STARTUP_EXCEPTIONS,
    SUBSCRIBE_COOLDOWN,
)
from .device_trigger import async_fire_triggers, async_setup_triggers_for_entry
from .utils import IidTuple, unique_id_to_iids

RETRY_INTERVAL = 60
MAX_POLL_FAILURES_TO_DECLARE_UNAVAILABLE = 3



MAX_CHARACTERISTICS_PER_REQUEST = 49

BLE_AVAILABILITY_CHECK_INTERVAL = 1800

_LOGGER = logging.getLogger(__name__)

type AddAccessoryCb = Callable[[Accessory], bool]
type AddServiceCb = Callable[[Service], bool]
type AddCharacteristicCb = Callable[[Characteristic], bool]


def valid_serial_number(serial: str) -> bool:

    if not serial:
        return False
    try:
        return float("".join(serial.rsplit(".", 1))) > 1
    except ValueError:
        return True


class HKDevice:


    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        pairing_data: MappingProxyType[str, Any],
    ) -> None:


        self.hass = hass
        self.config_entry = config_entry



        self.pairing_data = pairing_data.copy()

        connection: Controller = hass.data[CONTROLLER]

        self.pairing = connection.load_pairing(self.unique_id, self.pairing_data)


        self.accessory_factories: list[AddAccessoryCb] = []


        self.listeners: list[AddServiceCb] = []


        self.trigger_factories: list[AddServiceCb] = []



        self._triggers: set[tuple[int, int]] = set()


        self.char_factories: list[AddCharacteristicCb] = []






        self.platforms: set[str] = set()



        self.entities: set[tuple[int, int | None, int | None]] = set()



        self.devices: dict[int, str] = {}

        self.available = False

        self.pollable_characteristics: set[tuple[int, int]] = set()


        self._polling_lock = asyncio.Lock()
        self._polling_lock_warned = False
        self._poll_failures = 0


        self.unreliable_serial_numbers = False

        self.watchable_characteristics: set[tuple[int, int]] = set()

        self._debounced_update = Debouncer(
            hass,
            _LOGGER,
            cooldown=DEBOUNCE_COOLDOWN,
            immediate=False,
            function=self.async_update,
            background=True,
        )

        self._availability_callbacks: set[CALLBACK_TYPE] = set()
        self._config_changed_callbacks: set[CALLBACK_TYPE] = set()
        self._subscriptions: dict[tuple[int, int], set[CALLBACK_TYPE]] = {}
        self._pending_subscribes: set[tuple[int, int]] = set()
        self._subscribe_timer: CALLBACK_TYPE | None = None
        self._load_platforms_lock = asyncio.Lock()

    @property
    def entity_map(self) -> Accessories:

        return self.pairing.accessories_state.accessories

    @property
    def config_num(self) -> int:

        return self.pairing.accessories_state.config_num

    def add_pollable_characteristics(
        self, characteristics: list[tuple[int, int]]
    ) -> None:

        self.pollable_characteristics.update(characteristics)

    def remove_pollable_characteristics(
        self, characteristics: list[tuple[int, int]]
    ) -> None:

        for aid_iid in characteristics:
            self.pollable_characteristics.discard(aid_iid)

    def get_all_pollable_characteristics(self) -> set[tuple[int, int]]:





        return {
            (accessory.aid, char.iid)
            for accessory in self.entity_map.accessories
            for service in accessory.services
            for char in service.characteristics
            if CharacteristicPermissions.paired_read in char.perms
            and char.type not in EVENT_CHARACTERISTICS
        }

    def add_watchable_characteristics(
        self, characteristics: list[tuple[int, int]]
    ) -> None:

        self.watchable_characteristics.update(characteristics)
        self._pending_subscribes.update(characteristics)

        if not self._subscribe_timer:
            self._subscribe_timer = async_call_later(
                self.hass,
                SUBSCRIBE_COOLDOWN,
                self._async_subscribe,
            )

    @callback
    def _async_cancel_subscription_timer(self) -> None:

        if self._subscribe_timer:
            self._subscribe_timer()
            self._subscribe_timer = None

    @callback
    def _async_subscribe(self, _now: datetime) -> None:

        self._subscribe_timer = None
        if self._pending_subscribes:
            subscribes = self._pending_subscribes.copy()
            self._pending_subscribes.clear()
            self.config_entry.async_create_task(
                self.hass,
                self.pairing.subscribe(subscribes),
                name=f"hkc subscriptions {self.unique_id}",
                eager_start=True,
            )

    def remove_watchable_characteristics(
        self, characteristics: list[tuple[int, int]]
    ) -> None:

        for aid_iid in characteristics:
            self.watchable_characteristics.discard(aid_iid)
            self._pending_subscribes.discard(aid_iid)

    @callback
    def async_set_available_state(self, available: bool) -> None:

        _LOGGER.debug(
            "Called async_set_available_state with %s for %s", available, self.unique_id
        )


        if (self.hass.is_stopping and not available) or self.available == available:
            return
        self.available = available
        for callback_ in self._availability_callbacks:
            callback_()

    async def _async_populate_ble_accessory_state(self, event: Event) -> None:








        self._async_start_polling()
        try:
            await self.pairing.async_populate_accessories_state(force_update=True)
        except STARTUP_EXCEPTIONS as ex:
            _LOGGER.debug(
                (
                    "Failed to populate BLE accessory state for %s, accessory may be"
                    " sleeping and will be retried the next time it advertises: %s"
                ),
                self.config_entry.title,
                ex,
            )

    async def async_setup(self) -> None:

        pairing = self.pairing
        transport = pairing.transport
        entry = self.config_entry











        attempts = None if self.hass.state is CoreState.running else 1
        if (
            transport == Transport.BLE
            and pairing.accessories
            and pairing.accessories.has_aid(1)
        ):






            entry.async_on_unload(
                self.hass.bus.async_listen(
                    EVENT_HOMEASSISTANT_STARTED,
                    self._async_populate_ble_accessory_state,
                )
            )
        else:
            await self.pairing.async_populate_accessories_state(
                force_update=True, attempts=attempts
            )

        entry.async_on_unload(pairing.dispatcher_connect(self.process_new_events))
        entry.async_on_unload(
            pairing.dispatcher_connect_config_changed(self.process_config_changed)
        )
        entry.async_on_unload(
            pairing.dispatcher_availability_changed(self.async_set_available_state)
        )
        entry.async_on_unload(self._async_cancel_subscription_timer)

        if transport != Transport.BLE:







            try:
                await self.async_update(poll_all=True)
            except ValueError as exc:
                _LOGGER.debug(
                    "Accessory %s responded with unparsable response, first update was skipped: %s",
                    self.unique_id,
                    exc,
                )

        await self.async_process_entity_map()

        if transport != Transport.BLE:

            self._async_start_polling()



        await self.async_add_new_entities()

        self.async_set_available_state(self.pairing.is_available)

        if transport == Transport.BLE:




            entry.async_on_unload(
                async_track_time_interval(
                    self.hass,
                    self.async_update_available_state,
                    timedelta(seconds=BLE_AVAILABILITY_CHECK_INTERVAL),
                    name=f"HomeKit Device {self.unique_id} BLE availability check poll",
                )
            )

            if "sensor" not in self.platforms:
                async with self._load_platforms_lock:
                    await self._async_load_platforms({"sensor"})

    @callback
    def _async_start_polling(self) -> None:




        self.config_entry.async_on_unload(
            async_track_time_interval(
                self.hass,
                self._async_schedule_update,
                self.pairing.poll_interval,
                name=f"HomeKit Device {self.unique_id} availability check poll",
            )
        )

    @callback
    def _async_schedule_update(self, now: datetime) -> None:

        self.config_entry.async_create_background_task(
            self.hass,
            self._debounced_update.async_call(),
            name=f"hkc {self.unique_id} alive poll",
            eager_start=True,
        )

    async def async_add_new_entities(self) -> None:

        await self.async_load_platforms()
        self.add_entities()

    def device_info_for_accessory(self, accessory: Accessory) -> DeviceInfo:

        identifiers = {
            (
                IDENTIFIER_ACCESSORY_ID,
                f"{self.unique_id}:aid:{accessory.aid}",
            )
        }

        if not self.unreliable_serial_numbers:
            identifiers.add((IDENTIFIER_SERIAL_NUMBER, accessory.serial_number))

        connections: set[tuple[str, str]] = set()
        if self.pairing.transport == Transport.BLE and (
            discovery := self.pairing.controller.discoveries.get(
                normalize_hkid(self.unique_id)
            )
        ):
            connections = {
                (dr.CONNECTION_BLUETOOTH, cast(BleDiscovery, discovery).device.address),
            }

        device_info = DeviceInfo(
            identifiers={
                (
                    IDENTIFIER_ACCESSORY_ID,
                    f"{self.unique_id}:aid:{accessory.aid}",
                )
            },
            connections=connections,
            name=accessory.name,
            manufacturer=accessory.manufacturer,
            model=accessory.model,
            sw_version=accessory.firmware_revision,
            hw_version=accessory.hardware_revision,
            serial_number=accessory.serial_number,
        )

        if accessory.aid != 1:



            device_info[ATTR_VIA_DEVICE] = (
                IDENTIFIER_ACCESSORY_ID,
                f"{self.unique_id}:aid:1",
            )

        return device_info

    @callback
    def async_migrate_devices(self) -> None:

        _LOGGER.debug(
            "Migrating device registry entries for pairing %s", self.unique_id
        )

        device_registry = dr.async_get(self.hass)

        for accessory in self.entity_map.accessories:
            identifiers = {
                (
                    DOMAIN,
                    IDENTIFIER_LEGACY_ACCESSORY_ID,
                    f"{self.unique_id}_{accessory.aid}",
                ),
            }

            if accessory.aid == 1:
                identifiers.add(
                    (DOMAIN, IDENTIFIER_LEGACY_ACCESSORY_ID, self.unique_id)
                )

            if valid_serial_number(accessory.serial_number):
                identifiers.add(
                    (DOMAIN, IDENTIFIER_LEGACY_SERIAL_NUMBER, accessory.serial_number)
                )

            device = device_registry.async_get_device(identifiers=identifiers)
            if not device:
                continue

            if self.config_entry.entry_id not in device.config_entries:
                _LOGGER.warning(
                    (
                        "Found candidate device for %s:aid:%s, but owned by a different"
                        " config entry, skipping"
                    ),
                    self.unique_id,
                    accessory.aid,
                )
                continue

            _LOGGER.debug(
                "Migrating device identifiers for %s:aid:%s",
                self.unique_id,
                accessory.aid,
            )
            device_registry.async_update_device(
                device.id,
                new_identifiers={
                    (
                        IDENTIFIER_ACCESSORY_ID,
                        f"{self.unique_id}:aid:{accessory.aid}",
                    )
                },
            )

    @callback
    def async_migrate_unique_id(
        self, old_unique_id: str, new_unique_id: str | None, platform: str
    ) -> None:

        assert new_unique_id is not None
        _LOGGER.debug(
            "Checking if unique ID %s on %s needs to be migrated",
            old_unique_id,
            platform,
        )
        entity_registry = er.async_get(self.hass)




        if (
            entity_id := entity_registry.async_get_entity_id(
                platform, DOMAIN, old_unique_id
            )
        ) is None:
            _LOGGER.debug("Unique ID %s does not need to be migrated", old_unique_id)
            return
        if new_entity_id := entity_registry.async_get_entity_id(
            platform, DOMAIN, new_unique_id
        ):
            _LOGGER.debug(
                (
                    "Unique ID %s is already in use by %s (system may have been"
                    " downgraded)"
                ),
                new_unique_id,
                new_entity_id,
            )
            return
        _LOGGER.debug(
            "Migrating unique ID for entity %s (%s -> %s)",
            entity_id,
            old_unique_id,
            new_unique_id,
        )
        entity_registry.async_update_entity(entity_id, new_unique_id=new_unique_id)

    @callback
    def async_remove_legacy_device_serial_numbers(self) -> None:






        _LOGGER.debug(
            (
                "Removing legacy serial numbers from device registry entries for"
                " pairing %s"
            ),
            self.unique_id,
        )

        device_registry = dr.async_get(self.hass)
        for accessory in self.entity_map.accessories:
            identifiers = {
                (
                    IDENTIFIER_ACCESSORY_ID,
                    f"{self.unique_id}:aid:{accessory.aid}",
                )
            }
            legacy_serial_identifier = (
                IDENTIFIER_SERIAL_NUMBER,
                accessory.serial_number,
            )

            device = device_registry.async_get_device(identifiers=identifiers)
            if not device or legacy_serial_identifier not in device.identifiers:
                continue

            device_registry.async_update_device(device.id, new_identifiers=identifiers)

    @callback
    def async_reap_stale_entity_registry_entries(self) -> None:

        _LOGGER.debug(
            "Removing stale entity registry entries for pairing %s",
            self.unique_id,
        )

        reg = er.async_get(self.hass)





        entries = er.async_entries_for_config_entry(reg, self.config_entry.entry_id)
        existing_entities = {
            iids: entry.entity_id
            for entry in entries
            if (iids := unique_id_to_iids(entry.unique_id))
        }


        current_unique_id: set[IidTuple] = set()
        for accessory in self.entity_map.accessories:
            current_unique_id.add((accessory.aid, None, None))

            for service in accessory.services:
                current_unique_id.add((accessory.aid, service.iid, None))

                for char in service.characteristics:
                    if self.pairing.transport != Transport.BLE:
                        if char.type == CharacteristicsTypes.THREAD_CONTROL_POINT:
                            continue

                    current_unique_id.add(
                        (
                            accessory.aid,
                            service.iid,
                            char.iid,
                        )
                    )


        if stale := existing_entities.keys() - current_unique_id:
            for parts in stale:
                _LOGGER.debug(
                    "Removing stale entity registry entry %s for pairing %s",
                    existing_entities[parts],
                    self.unique_id,
                )
                reg.async_remove(existing_entities[parts])

    @callback
    def async_migrate_ble_unique_id(self) -> None:

        unique_id = normalize_hkid(self.unique_id)
        if unique_id != self.config_entry.unique_id:
            _LOGGER.debug(
                "Fixing incorrect unique_id: %s -> %s",
                self.config_entry.unique_id,
                unique_id,
            )
            self.hass.config_entries.async_update_entry(
                self.config_entry, unique_id=unique_id
            )

    @callback
    def async_create_devices(self) -> None:






        device_registry = dr.async_get(self.hass)

        devices = {}



        for accessory in sorted(self.entity_map.accessories, key=attrgetter("aid")):
            device_info = self.device_info_for_accessory(accessory)

            device = device_registry.async_get_or_create(
                config_entry_id=self.config_entry.entry_id,
                **device_info,
            )

            devices[accessory.aid] = device.id

        self.devices = devices

    @callback
    def async_detect_workarounds(self) -> None:

        unreliable_serial_numbers = False

        devices = set()

        for accessory in self.entity_map.accessories:
            if not valid_serial_number(accessory.serial_number):
                _LOGGER.debug(
                    (
                        "Serial number %r is not valid, it cannot be used as a unique"
                        " identifier"
                    ),
                    accessory.serial_number,
                )
                unreliable_serial_numbers = True

            elif accessory.serial_number in devices:
                _LOGGER.debug(
                    (
                        "Serial number %r is duplicated within this pairing, it cannot"
                        " be used as a unique identifier"
                    ),
                    accessory.serial_number,
                )
                unreliable_serial_numbers = True

            elif accessory.serial_number == accessory.hardware_revision:

                _LOGGER.debug(
                    (
                        "Serial number %r is actually the hardware revision, it cannot"
                        " be used as a unique identifier"
                    ),
                    accessory.serial_number,
                )
                unreliable_serial_numbers = True

            devices.add(accessory.serial_number)

        self.unreliable_serial_numbers = unreliable_serial_numbers

    async def async_process_entity_map(self) -> None:








        self.async_detect_workarounds()


        self.async_migrate_devices()


        self.async_remove_legacy_device_serial_numbers()

        self.async_migrate_ble_unique_id()

        self.async_reap_stale_entity_registry_entries()

        self.async_create_devices()


        await async_setup_triggers_for_entry(self.hass, self.config_entry)

    async def async_unload(self) -> None:

        await self.pairing.shutdown()


        if not self.hass.is_stopping:
            await self.hass.config_entries.async_unload_platforms(
                self.config_entry, self.platforms
            )

    def process_config_changed(self, config_num: int) -> None:

        self.config_entry.async_create_task(
            self.hass, self.async_update_new_accessories_state(), eager_start=True
        )

    async def async_update_new_accessories_state(self) -> None:

        await self.async_process_entity_map()
        for callback_ in self._config_changed_callbacks:
            callback_()
        await self.async_update()
        await self.async_add_new_entities()

    @callback
    def async_entity_key_removed(
        self, entity_key: tuple[int, int | None, int | None]
    ) -> None:




        self.entities.discard(entity_key)

    def add_accessory_factory(self, add_entities_cb: AddAccessoryCb) -> None:

        self.accessory_factories.append(add_entities_cb)
        self._add_new_entities_for_accessory([add_entities_cb])

    def _add_new_entities_for_accessory(self, handlers: list[AddAccessoryCb]) -> None:
        for accessory in self.entity_map.accessories:
            entity_key = (accessory.aid, None, None)
            for handler in handlers:
                if entity_key not in self.entities and handler(accessory):
                    self.entities.add(entity_key)
                    break

    def add_char_factory(self, add_entities_cb: AddCharacteristicCb) -> None:

        self.char_factories.append(add_entities_cb)
        self._add_new_entities_for_char([add_entities_cb])

    def _add_new_entities_for_char(self, handlers: list[AddCharacteristicCb]) -> None:
        for accessory in self.entity_map.accessories:
            for service in accessory.services:
                for char in service.characteristics:
                    entity_key = (accessory.aid, service.iid, char.iid)
                    for handler in handlers:
                        if entity_key not in self.entities and handler(char):
                            self.entities.add(entity_key)
                            break

    def add_listener(self, add_entities_cb: AddServiceCb) -> None:

        self.listeners.append(add_entities_cb)
        self._add_new_entities([add_entities_cb])

    def add_trigger_factory(self, add_triggers_cb: AddServiceCb) -> None:

        self.trigger_factories.append(add_triggers_cb)
        self._add_new_triggers([add_triggers_cb])

    def _add_new_triggers(self, callbacks: list[AddServiceCb]) -> None:
        for accessory in self.entity_map.accessories:
            aid = accessory.aid
            for service in accessory.services:
                iid = service.iid
                entity_key = (aid, iid)

                if entity_key in self._triggers:

                    continue

                for add_trigger_cb in callbacks:
                    if add_trigger_cb(service):
                        self._triggers.add(entity_key)
                        break

    def add_entities(self) -> None:

        self._add_new_entities(self.listeners)
        self._add_new_entities_for_accessory(self.accessory_factories)
        self._add_new_entities_for_char(self.char_factories)
        self._add_new_triggers(self.trigger_factories)

    def _add_new_entities(self, callbacks: list[AddServiceCb]) -> None:
        for accessory in self.entity_map.accessories:
            aid = accessory.aid
            for service in accessory.services:
                entity_key = (aid, None, service.iid)

                if entity_key in self.entities:

                    continue

                for listener in callbacks:
                    if listener(service):
                        self.entities.add(entity_key)
                        break

    async def _async_load_platforms(self, platforms: set[str]) -> None:

        assert self._load_platforms_lock.locked(), "Must be called with lock held"
        if not (to_load := platforms - self.platforms):
            return
        self.platforms.update(to_load)
        await self.hass.config_entries.async_forward_entry_setups(
            self.config_entry, platforms
        )

    async def async_load_platforms(self) -> None:

        async with self._load_platforms_lock:
            to_load: set[str] = set()
            for accessory in self.entity_map.accessories:
                for service in accessory.services:
                    if service.type in HOMEKIT_ACCESSORY_DISPATCH:
                        platform = HOMEKIT_ACCESSORY_DISPATCH[service.type]
                        if platform not in self.platforms:
                            to_load.add(platform)

                    for char in service.characteristics:
                        if char.type in CHARACTERISTIC_PLATFORMS:
                            platform = CHARACTERISTIC_PLATFORMS[char.type]
                            if platform not in self.platforms:
                                to_load.add(platform)

            if to_load:
                await self._async_load_platforms(to_load)

    @callback
    def async_update_available_state(self, *_: Any) -> None:

        self.async_set_available_state(self.pairing.is_available)

    async def async_request_update(self, now: datetime | None = None) -> None:

        await self._debounced_update.async_call()

    async def async_update(
        self, now: datetime | None = None, *, poll_all: bool = False
    ) -> None:









        if poll_all:


            to_poll = self.get_all_pollable_characteristics()
        else:
            to_poll = self.pollable_characteristics

        if not to_poll:
            self.async_update_available_state()
            _LOGGER.debug(
                "HomeKit connection not polling any characteristics: %s", self.unique_id
            )
            return

        if self._polling_lock.locked():
            if not self._polling_lock_warned:
                _LOGGER.warning(
                    (
                        "HomeKit device update skipped as previous poll still in"
                        " flight: %s"
                    ),
                    self.unique_id,
                )
                self._polling_lock_warned = True
            return

        if self._polling_lock_warned:
            _LOGGER.warning(
                (
                    "HomeKit device no longer detecting back pressure - not"
                    " skipping poll: %s"
                ),
                self.unique_id,
            )
            self._polling_lock_warned = False

        async with self._polling_lock:
            _LOGGER.debug("Starting HomeKit device update: %s", self.unique_id)

            new_values_dict: dict[tuple[int, int], dict[str, Any]] = {}
            to_poll_list = list(to_poll)

            for i in range(0, len(to_poll_list), MAX_CHARACTERISTICS_PER_REQUEST):
                batch = to_poll_list[i : i + MAX_CHARACTERISTICS_PER_REQUEST]
                try:
                    batch_values = await self.get_characteristics(batch)
                    new_values_dict.update(batch_values)
                except AccessoryNotFoundError:


                    self.async_set_available_state(False)
                    return
                except AccessoryDisconnectedError, EncryptionError, TimeoutError:


                    self._poll_failures += 1
                    if self._poll_failures >= MAX_POLL_FAILURES_TO_DECLARE_UNAVAILABLE:
                        self.async_set_available_state(False)
                    return

            self._poll_failures = 0
            self.process_new_events(new_values_dict)

            _LOGGER.debug("Finished HomeKit device update: %s", self.unique_id)

    def process_new_events(
        self, new_values_dict: dict[tuple[int, int], dict[str, Any]]
    ) -> None:

        self.async_set_available_state(True)


        async_fire_triggers(self, new_values_dict)

        to_callback: set[CALLBACK_TYPE] = set()
        for aid_iid in self.entity_map.process_changes(new_values_dict):
            if callbacks := self._subscriptions.get(aid_iid):
                to_callback.update(callbacks)

        for callback_ in to_callback:
            callback_()

    @callback
    def _remove_characteristics_callback(
        self, characteristics: set[tuple[int, int]], callback_: CALLBACK_TYPE
    ) -> None:

        for aid_iid in characteristics:
            self._subscriptions[aid_iid].remove(callback_)
            if not self._subscriptions[aid_iid]:
                del self._subscriptions[aid_iid]

    @callback
    def async_subscribe(
        self, characteristics: set[tuple[int, int]], callback_: CALLBACK_TYPE
    ) -> CALLBACK_TYPE:

        for aid_iid in characteristics:
            self._subscriptions.setdefault(aid_iid, set()).add(callback_)
        return partial(
            self._remove_characteristics_callback, characteristics, callback_
        )

    @callback
    def _remove_availability_callback(self, callback_: CALLBACK_TYPE) -> None:

        self._availability_callbacks.remove(callback_)

    @callback
    def async_subscribe_availability(self, callback_: CALLBACK_TYPE) -> CALLBACK_TYPE:

        self._availability_callbacks.add(callback_)
        return partial(self._remove_availability_callback, callback_)

    @callback
    def _remove_config_changed_callback(self, callback_: CALLBACK_TYPE) -> None:

        self._config_changed_callbacks.remove(callback_)

    @callback
    def async_subscribe_config_changed(self, callback_: CALLBACK_TYPE) -> CALLBACK_TYPE:

        self._config_changed_callbacks.add(callback_)
        return partial(self._remove_config_changed_callback, callback_)

    async def get_characteristics(
        self, *args: Any, **kwargs: Any
    ) -> dict[tuple[int, int], dict[str, Any]]:

        return await self.pairing.get_characteristics(*args, **kwargs)

    async def put_characteristics(
        self, characteristics: Iterable[tuple[int, int, Any]]
    ) -> None:

        await self.pairing.put_characteristics(characteristics)

    @property
    def is_unprovisioned_thread_device(self) -> bool:

        if self.pairing.controller.transport_type != TransportType.BLE:
            return False

        if not self.entity_map.aid(1).services.first(
            service_type=ServicesTypes.THREAD_TRANSPORT
        ):
            return False

        return True

    async def async_thread_provision(self) -> None:

        if self.pairing.controller.transport_type == TransportType.COAP:
            raise HomeAssistantError("Already connected to a thread network")

        if not (dataset := await async_get_preferred_dataset(self.hass)):
            raise HomeAssistantError("No thread network credentials available")

        await self.pairing.thread_provision(dataset)

        try:
            discovery = (
                await self.hass.data[CONTROLLER]
                .transports[TransportType.COAP]
                .async_find(self.unique_id, timeout=30)
            )
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    "Connection": "CoAP",
                    "AccessoryIP": discovery.description.address,
                    "AccessoryPort": discovery.description.port,
                },
            )
            _LOGGER.debug(
                "%s: Found device on local network, migrating integration to Thread",
                self.unique_id,
            )

        except AccessoryNotFoundError as exc:
            _LOGGER.debug(
                "%s: Failed to appear on local network as a Thread device, reverting to BLE",
                self.unique_id,
            )
            raise HomeAssistantError("Could not migrate device to Thread") from exc

        finally:
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

    @property
    def unique_id(self) -> str:




        return self.pairing_data["AccessoryPairingID"]
