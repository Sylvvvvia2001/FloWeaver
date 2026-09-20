

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fnmatch import translate
from functools import lru_cache
import re
from typing import TYPE_CHECKING, Final, TypedDict

from lru import LRU

from homeassistant.core import callback
from homeassistant.loader import BluetoothMatcher, BluetoothMatcherOptional

from .models import BluetoothCallback, BluetoothServiceInfoBleak

if TYPE_CHECKING:
    from bleak.backends.scanner import AdvertisementData


MAX_REMEMBER_ADDRESSES: Final = 2048

CALLBACK: Final = "callback"
DOMAIN: Final = "domain"
ADDRESS: Final = "address"
CONNECTABLE: Final = "connectable"
LOCAL_NAME: Final = "local_name"
SERVICE_UUID: Final = "service_uuid"
SERVICE_DATA_UUID: Final = "service_data_uuid"
MANUFACTURER_ID: Final = "manufacturer_id"
MANUFACTURER_DATA_START: Final = "manufacturer_data_start"

LOCAL_NAME_MIN_MATCH_LENGTH = 3


class BluetoothCallbackMatcherOptional(TypedDict, total=False):


    address: str


class BluetoothCallbackMatcher(
    BluetoothMatcherOptional,
    BluetoothCallbackMatcherOptional,
):
    pass


class _BluetoothCallbackMatcherWithCallback(TypedDict):


    callback: BluetoothCallback


class BluetoothCallbackMatcherWithCallback(
    _BluetoothCallbackMatcherWithCallback,
    BluetoothCallbackMatcher,
):
    pass


@dataclass(slots=True, frozen=False)
class IntegrationMatchHistory:


    manufacturer_data: bool
    service_data: set[str]
    service_uuids: set[str]
    name: str


def seen_all_fields(
    previous_match: IntegrationMatchHistory,
    advertisement_data: AdvertisementData,
    name: str,
) -> bool:

    if previous_match.name != name:
        return False
    if not previous_match.manufacturer_data and advertisement_data.manufacturer_data:
        return False
    if advertisement_data.service_data and (
        not previous_match.service_data
        or not previous_match.service_data.issuperset(advertisement_data.service_data)
    ):
        return False
    if advertisement_data.service_uuids and (
        not previous_match.service_uuids
        or not previous_match.service_uuids.issuperset(advertisement_data.service_uuids)
    ):
        return False
    return True


class IntegrationMatcher:


    __slots__ = ("_index", "_integration_matchers", "_matched", "_matched_connectable")

    def __init__(self, integration_matchers: list[BluetoothMatcher]) -> None:

        self._integration_matchers = integration_matchers


        self._matched: LRU[str, IntegrationMatchHistory] = LRU(MAX_REMEMBER_ADDRESSES)
        self._matched_connectable: LRU[str, IntegrationMatchHistory] = LRU(
            MAX_REMEMBER_ADDRESSES
        )
        self._index = BluetoothMatcherIndex()

    @callback
    def async_setup(self) -> None:

        for matcher in self._integration_matchers:
            self._index.add(matcher)
        self._index.build()

    def async_clear_address(self, address: str) -> None:

        self._matched.pop(address, None)
        self._matched_connectable.pop(address, None)

    def match_domains(self, service_info: BluetoothServiceInfoBleak) -> set[str]:

        device = service_info.device
        advertisement_data = service_info.advertisement
        connectable = service_info.connectable
        name = service_info.name
        matched = self._matched_connectable if connectable else self._matched
        matched_domains: set[str] = set()
        if (previous_match := matched.get(device.address)) and seen_all_fields(
            previous_match, advertisement_data, name
        ):

            return matched_domains
        matched_domains = {
            matcher[DOMAIN] for matcher in self._index.match(service_info)
        }
        if not matched_domains:
            return matched_domains
        if previous_match:
            previous_match.manufacturer_data |= bool(
                advertisement_data.manufacturer_data
            )
            previous_match.service_data |= set(advertisement_data.service_data)
            previous_match.service_uuids |= set(advertisement_data.service_uuids)
            previous_match.name = name
        else:
            matched[device.address] = IntegrationMatchHistory(
                manufacturer_data=bool(advertisement_data.manufacturer_data),
                service_data=set(advertisement_data.service_data),
                service_uuids=set(advertisement_data.service_uuids),
                name=name,
            )
        return matched_domains


class BluetoothMatcherIndexBase[
    _T: (BluetoothMatcher, BluetoothCallbackMatcherWithCallback)
]:










    __slots__ = (
        "local_name",
        "manufacturer_id",
        "manufacturer_id_set",
        "service_data_uuid",
        "service_data_uuid_set",
        "service_uuid",
        "service_uuid_set",
    )

    def __init__(self) -> None:

        self.local_name: defaultdict[str, list[_T]] = defaultdict(list)
        self.service_uuid: defaultdict[str, list[_T]] = defaultdict(list)
        self.service_data_uuid: defaultdict[str, list[_T]] = defaultdict(list)
        self.manufacturer_id: defaultdict[int, list[_T]] = defaultdict(list)
        self.service_uuid_set: set[str] = set()
        self.service_data_uuid_set: set[str] = set()
        self.manufacturer_id_set: set[int] = set()

    def add(self, matcher: _T) -> bool:







        if LOCAL_NAME in matcher:
            self.local_name[_local_name_to_index_key(matcher[LOCAL_NAME])].append(
                matcher
            )
            return True


        if MANUFACTURER_ID in matcher:
            self.manufacturer_id[matcher[MANUFACTURER_ID]].append(matcher)
            return True

        if SERVICE_UUID in matcher:
            self.service_uuid[matcher[SERVICE_UUID]].append(matcher)
            return True

        if SERVICE_DATA_UUID in matcher:
            self.service_data_uuid[matcher[SERVICE_DATA_UUID]].append(matcher)
            return True

        return False

    def remove(self, matcher: _T) -> bool:





        if LOCAL_NAME in matcher:
            self.local_name[_local_name_to_index_key(matcher[LOCAL_NAME])].remove(
                matcher
            )
            return True

        if MANUFACTURER_ID in matcher:
            self.manufacturer_id[matcher[MANUFACTURER_ID]].remove(matcher)
            return True

        if SERVICE_UUID in matcher:
            self.service_uuid[matcher[SERVICE_UUID]].remove(matcher)
            return True

        if SERVICE_DATA_UUID in matcher:
            self.service_data_uuid[matcher[SERVICE_DATA_UUID]].remove(matcher)
            return True

        return False

    def build(self) -> None:

        self.service_uuid_set = set(self.service_uuid)
        self.service_data_uuid_set = set(self.service_data_uuid)
        self.manufacturer_id_set = set(self.manufacturer_id)

    def match(self, service_info: BluetoothServiceInfoBleak) -> list[_T]:

        matches: list[_T] = []
        if (name := service_info.name) and (
            local_name_matchers := self.local_name.get(
                name[:LOCAL_NAME_MIN_MATCH_LENGTH]
            )
        ):
            matches.extend(
                matcher
                for matcher in local_name_matchers
                if ble_device_matches(matcher, service_info)
            )

        if (
            (service_data_uuid_set := self.service_data_uuid_set)
            and (service_data := service_info.service_data)
            and (matched_uuids := service_data_uuid_set.intersection(service_data))
        ):
            matches.extend(
                matcher
                for service_data_uuid in matched_uuids
                for matcher in self.service_data_uuid[service_data_uuid]
                if ble_device_matches(matcher, service_info)
            )

        if (
            (manufacturer_id_set := self.manufacturer_id_set)
            and (manufacturer_data := service_info.manufacturer_data)
            and (matched_ids := manufacturer_id_set.intersection(manufacturer_data))
        ):
            matches.extend(
                matcher
                for manufacturer_id in matched_ids
                for matcher in self.manufacturer_id[manufacturer_id]
                if ble_device_matches(matcher, service_info)
            )

        if (
            (service_uuid_set := self.service_uuid_set)
            and (service_uuids := service_info.service_uuids)
            and (matched_uuids := service_uuid_set.intersection(service_uuids))
        ):
            matches.extend(
                matcher
                for service_uuid in matched_uuids
                for matcher in self.service_uuid[service_uuid]
                if ble_device_matches(matcher, service_info)
            )

        return matches


class BluetoothMatcherIndex(BluetoothMatcherIndexBase[BluetoothMatcher]):
    pass


class BluetoothCallbackMatcherIndex(
    BluetoothMatcherIndexBase[BluetoothCallbackMatcherWithCallback]
):





    __slots__ = ("address", "connectable")

    def __init__(self) -> None:

        super().__init__()
        self.address: defaultdict[str, list[BluetoothCallbackMatcherWithCallback]] = (
            defaultdict(list)
        )
        self.connectable: list[BluetoothCallbackMatcherWithCallback] = []

    def add_callback_matcher(
        self, matcher: BluetoothCallbackMatcherWithCallback
    ) -> None:






        if ADDRESS in matcher:
            self.address[matcher[ADDRESS]].append(matcher)
            return

        if super().add(matcher):
            self.build()
            return

        if CONNECTABLE in matcher:
            self.connectable.append(matcher)
            return

    def remove_callback_matcher(
        self, matcher: BluetoothCallbackMatcherWithCallback
    ) -> None:





        if ADDRESS in matcher:
            self.address[matcher[ADDRESS]].remove(matcher)
            return

        if super().remove(matcher):
            self.build()
            return

        if CONNECTABLE in matcher:
            self.connectable.remove(matcher)
            return

    def match_callbacks(
        self, service_info: BluetoothServiceInfoBleak
    ) -> list[BluetoothCallbackMatcherWithCallback]:

        matches = self.match(service_info)
        for matcher in self.address.get(service_info.address, []):
            if ble_device_matches(matcher, service_info):
                matches.append(matcher)
        for matcher in self.connectable:
            if ble_device_matches(matcher, service_info):
                matches.append(matcher)
        return matches


def _local_name_to_index_key(local_name: str) -> str:






    match_part = local_name[:LOCAL_NAME_MIN_MATCH_LENGTH]
    if "*" in match_part or "[" in match_part:
        raise ValueError(
            "Local name matchers may not have patterns in the first "
            f"{LOCAL_NAME_MIN_MATCH_LENGTH} characters because they "
            f"would match too broadly ({local_name})"
        )
    return match_part


def ble_device_matches(
    matcher: BluetoothMatcherOptional,
    service_info: BluetoothServiceInfoBleak,
) -> bool:




    if matcher.get(CONNECTABLE, True) and not service_info.connectable:
        return False

    if (
        service_uuid := matcher.get(SERVICE_UUID)
    ) and service_uuid not in service_info.service_uuids:
        return False

    if (
        service_data_uuid := matcher.get(SERVICE_DATA_UUID)
    ) and service_data_uuid not in service_info.service_data:
        return False

    if (manufacturer_id := matcher.get(MANUFACTURER_ID)) is not None:
        if manufacturer_id not in service_info.manufacturer_data:
            return False

        if manufacturer_data_start := matcher.get(MANUFACTURER_DATA_START):
            if not service_info.manufacturer_data[manufacturer_id].startswith(
                bytes(manufacturer_data_start)
            ):
                return False

    if (local_name := matcher.get(LOCAL_NAME)) and not _memorized_fnmatch(
        service_info.name,
        local_name,
    ):
        return False

    return True


@lru_cache(maxsize=4096, typed=True)
def _compile_fnmatch(pattern: str) -> re.Pattern:

    return re.compile(translate(pattern))


@lru_cache(maxsize=1024, typed=True)
def _memorized_fnmatch(name: str, pattern: str) -> bool:










    return bool(_compile_fnmatch(pattern).match(name))
