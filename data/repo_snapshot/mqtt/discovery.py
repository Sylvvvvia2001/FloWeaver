

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
import functools
from itertools import chain
import logging
import re
import time
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_MQTT,
    ConfigEntry,
    signal_discovered_config_entry_removed,
)
from homeassistant.const import CONF_DEVICE, CONF_PLATFORM
from homeassistant.core import HassJobType, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, discovery_flow
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo, ReceivePayloadType
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.loader import async_get_mqtt
from homeassistant.util.json import json_loads_object
from homeassistant.util.signal_type import SignalTypeFormat

from .abbreviations import ABBREVIATIONS, DEVICE_ABBREVIATIONS, ORIGIN_ABBREVIATIONS
from .client import async_subscribe_internal
from .const import (
    ATTR_DISCOVERY_HASH,
    ATTR_DISCOVERY_PAYLOAD,
    ATTR_DISCOVERY_TOPIC,
    CONF_AVAILABILITY,
    CONF_COMPONENTS,
    CONF_ORIGIN,
    CONF_TOPIC,
    DOMAIN,
    SUPPORTED_COMPONENTS,
)
from .models import DATA_MQTT, MqttComponentConfig, MqttOriginInfo, ReceiveMessage
from .schemas import DEVICE_DISCOVERY_SCHEMA, MQTT_ORIGIN_INFO_SCHEMA, SHARED_OPTIONS
from .util import async_forward_entry_setup_and_setup_discovery

ABBREVIATIONS_SET = set(ABBREVIATIONS)
DEVICE_ABBREVIATIONS_SET = set(DEVICE_ABBREVIATIONS)
ORIGIN_ABBREVIATIONS_SET = set(ORIGIN_ABBREVIATIONS)

_LOGGER = logging.getLogger(__name__)

TOPIC_MATCHER = re.compile(
    r"(?P<component>\w+)/(?:(?P<node_id>[a-zA-Z0-9_-]+)/)"
    r"?(?P<object_id>[a-zA-Z0-9_-]+)/config"
)

MQTT_DISCOVERY_UPDATED: SignalTypeFormat[MQTTDiscoveryPayload] = SignalTypeFormat(
    "mqtt_discovery_updated_{}_{}"
)
MQTT_DISCOVERY_NEW: SignalTypeFormat[MQTTDiscoveryPayload] = SignalTypeFormat(
    "mqtt_discovery_new_{}_{}"
)
MQTT_DISCOVERY_DONE: SignalTypeFormat[Any] = SignalTypeFormat(
    "mqtt_discovery_done_{}_{}"
)

TOPIC_BASE = "~"

CONF_MIGRATE_DISCOVERY = "migrate_discovery"

MIGRATE_DISCOVERY_SCHEMA = vol.Schema(
    {vol.Optional(CONF_MIGRATE_DISCOVERY): True},
)


class MQTTDiscoveryPayload(dict[str, Any]):


    device_discovery: bool = False
    migrate_discovery: bool = False
    discovery_data: DiscoveryInfoType


@dataclass(frozen=True)
class MQTTIntegrationDiscoveryConfig:


    integration: str
    msg: ReceiveMessage


@callback
def _async_process_discovery_migration(payload: MQTTDiscoveryPayload) -> bool:


    if migr_discvry := (payload.pop("migr_discvry", None)):
        payload[CONF_MIGRATE_DISCOVERY] = migr_discvry
    if CONF_MIGRATE_DISCOVERY in payload:
        try:
            MIGRATE_DISCOVERY_SCHEMA(payload)
        except vol.Invalid as exc:
            _LOGGER.warning(exc)
            return False
        payload.migrate_discovery = True
        payload.clear()
        return True
    return False


def clear_discovery_hash(hass: HomeAssistant, discovery_hash: tuple[str, str]) -> None:

    hass.data[DATA_MQTT].discovery_already_discovered.discard(discovery_hash)


def set_discovery_hash(hass: HomeAssistant, discovery_hash: tuple[str, str]) -> None:

    hass.data[DATA_MQTT].discovery_already_discovered.add(discovery_hash)


@callback
def get_origin_log_string(
    discovery_payload: MQTTDiscoveryPayload, *, include_url: bool
) -> str:

    if CONF_ORIGIN not in discovery_payload:
        return ""
    origin_info: MqttOriginInfo = discovery_payload[CONF_ORIGIN]
    sw_version_log = ""
    if sw_version := origin_info.get("sw_version"):
        sw_version_log = f", version: {sw_version}"
    support_url_log = ""
    if include_url and (support_url := get_origin_support_url(discovery_payload)):
        support_url_log = f", support URL: {support_url}"
    return (
        " from external application "
        f"{origin_info['name']}{sw_version_log}{support_url_log}"
    )


@callback
def get_origin_support_url(discovery_payload: MQTTDiscoveryPayload) -> str | None:

    if CONF_ORIGIN not in discovery_payload:
        return ""
    origin_info: MqttOriginInfo = discovery_payload[CONF_ORIGIN]
    return origin_info.get("support_url")


@callback
def async_log_discovery_origin_info(
    message: str, discovery_payload: MQTTDiscoveryPayload
) -> None:

    if not _LOGGER.isEnabledFor(logging.DEBUG):

        return
    _LOGGER.debug(
        "%s%s", message, get_origin_log_string(discovery_payload, include_url=True)
    )


@callback
def _replace_abbreviations(
    payload: dict[str, Any] | str,
    abbreviations: dict[str, str],
    abbreviations_set: set[str],
) -> None:

    if not isinstance(payload, dict):
        return
    for key in abbreviations_set.intersection(payload):
        payload[abbreviations[key]] = payload.pop(key)


@callback
def _replace_all_abbreviations(
    discovery_payload: dict[str, Any], component_only: bool = False
) -> None:


    _replace_abbreviations(discovery_payload, ABBREVIATIONS, ABBREVIATIONS_SET)

    if CONF_AVAILABILITY in discovery_payload:
        for availability_conf in cv.ensure_list(discovery_payload[CONF_AVAILABILITY]):
            _replace_abbreviations(availability_conf, ABBREVIATIONS, ABBREVIATIONS_SET)

    if component_only:
        return

    if CONF_ORIGIN in discovery_payload:
        _replace_abbreviations(
            discovery_payload[CONF_ORIGIN],
            ORIGIN_ABBREVIATIONS,
            ORIGIN_ABBREVIATIONS_SET,
        )

    if CONF_DEVICE in discovery_payload:
        _replace_abbreviations(
            discovery_payload[CONF_DEVICE],
            DEVICE_ABBREVIATIONS,
            DEVICE_ABBREVIATIONS_SET,
        )

    if CONF_COMPONENTS in discovery_payload:
        if not isinstance(discovery_payload[CONF_COMPONENTS], dict):
            return
        for comp_conf in discovery_payload[CONF_COMPONENTS].values():
            _replace_all_abbreviations(comp_conf, component_only=True)


@callback
def _replace_topic_base(discovery_payload: MQTTDiscoveryPayload) -> None:

    base = discovery_payload.pop(TOPIC_BASE)
    for key, value in discovery_payload.items():
        if isinstance(value, str) and value:
            if value[0] == TOPIC_BASE and key.endswith("topic"):
                discovery_payload[key] = f"{base}{value[1:]}"
            if value[-1] == TOPIC_BASE and key.endswith("topic"):
                discovery_payload[key] = f"{value[:-1]}{base}"
    if discovery_payload.get(CONF_AVAILABILITY):
        for availability_conf in cv.ensure_list(discovery_payload[CONF_AVAILABILITY]):
            if not isinstance(availability_conf, dict):
                continue
            if topic := str(availability_conf.get(CONF_TOPIC)):
                if topic[0] == TOPIC_BASE:
                    availability_conf[CONF_TOPIC] = f"{base}{topic[1:]}"
                if topic[-1] == TOPIC_BASE:
                    availability_conf[CONF_TOPIC] = f"{topic[:-1]}{base}"


@callback
def _generate_device_config(
    hass: HomeAssistant,
    object_id: str,
    node_id: str | None,
    migrate_discovery: bool = False,
) -> MQTTDiscoveryPayload:





    mqtt_data = hass.data[DATA_MQTT]
    device_node_id: str = f"{node_id} {object_id}" if node_id else object_id
    config = MQTTDiscoveryPayload({CONF_DEVICE: {}, CONF_COMPONENTS: {}})
    config.migrate_discovery = migrate_discovery
    comp_config = config[CONF_COMPONENTS]
    for platform, discover_id in mqtt_data.discovery_already_discovered:
        ids = discover_id.split(" ")
        component_node_id = f"{ids.pop(1)} {ids.pop(0)}" if len(ids) > 2 else ids.pop(0)
        component_object_id = " ".join(ids)
        if not ids:
            continue
        if device_node_id == component_node_id:
            comp_config[component_object_id] = {CONF_PLATFORM: platform}

    return config if comp_config else MQTTDiscoveryPayload({})


@callback
def _parse_device_payload(
    hass: HomeAssistant,
    payload: ReceivePayloadType,
    object_id: str,
    node_id: str | None,
) -> MQTTDiscoveryPayload:







    device_payload = MQTTDiscoveryPayload()
    if payload == "":
        if not (device_payload := _generate_device_config(hass, object_id, node_id)):
            _LOGGER.warning(
                "No device components to cleanup for %s, node_id '%s'",
                object_id,
                node_id,
            )
        return device_payload
    try:
        device_payload = MQTTDiscoveryPayload(json_loads_object(payload))
    except ValueError:
        _LOGGER.warning("Unable to parse JSON %s: '%s'", object_id, payload)
        return device_payload
    if _async_process_discovery_migration(device_payload):
        return _generate_device_config(hass, object_id, node_id, migrate_discovery=True)
    _replace_all_abbreviations(device_payload)
    try:
        DEVICE_DISCOVERY_SCHEMA(device_payload)
    except vol.Invalid as exc:
        _LOGGER.warning(
            "Invalid MQTT device discovery payload for %s, %s: '%s'",
            object_id,
            exc,
            payload,
        )
        return MQTTDiscoveryPayload({})
    return device_payload


@callback
def _valid_origin_info(discovery_payload: MQTTDiscoveryPayload) -> bool:

    if CONF_ORIGIN not in discovery_payload:
        return True
    try:
        MQTT_ORIGIN_INFO_SCHEMA(discovery_payload[CONF_ORIGIN])
    except Exception as exc:
        _LOGGER.warning(
            "Unable to parse origin information from discovery message: %s, got %s",
            exc,
            discovery_payload[CONF_ORIGIN],
        )
        return False
    return True


@callback
def _merge_common_device_options(
    component_config: MQTTDiscoveryPayload, device_config: dict[str, Any]
) -> None:















    for option in SHARED_OPTIONS:
        if option in device_config and option not in component_config:
            component_config[option] = device_config.get(option)


async def async_start(
    hass: HomeAssistant, discovery_topic: str, config_entry: ConfigEntry
) -> None:

    mqtt_data = hass.data[DATA_MQTT]
    platform_setup_lock: dict[str, asyncio.Lock] = {}
    integration_discovery_messages: dict[str, MQTTIntegrationDiscoveryConfig] = {}

    @callback
    def _async_add_component(discovery_payload: MQTTDiscoveryPayload) -> None:

        discovery_hash = discovery_payload.discovery_data[ATTR_DISCOVERY_HASH]
        component, discovery_id = discovery_hash
        message = f"Found new component: {component} {discovery_id}"
        async_log_discovery_origin_info(message, discovery_payload)
        mqtt_data.discovery_already_discovered.add(discovery_hash)
        async_dispatcher_send(
            hass, MQTT_DISCOVERY_NEW.format(component, "mqtt"), discovery_payload
        )

    async def _async_component_setup(
        component: str, discovery_payload: MQTTDiscoveryPayload
    ) -> None:

        async with platform_setup_lock.setdefault(component, asyncio.Lock()):
            if component not in mqtt_data.platforms_loaded:
                await async_forward_entry_setup_and_setup_discovery(
                    hass, config_entry, {component}
                )
        _async_add_component(discovery_payload)

    @callback
    def async_discovery_message_received(msg: ReceiveMessage) -> None:

        mqtt_data.last_discovery = msg.timestamp
        payload = msg.payload
        topic = msg.topic
        topic_trimmed = topic.replace(f"{discovery_topic}/", "", 1)

        if not (match := TOPIC_MATCHER.match(topic_trimmed)):
            if topic_trimmed.endswith("config"):
                _LOGGER.warning(
                    (
                        "Received message on illegal discovery topic '%s'. The topic"
                        " contains non allowed characters. For more information see "
                        "https://www.home-assistant.io/integrations/mqtt/#discovery-topic"
                    ),
                    topic,
                )
            return

        component, node_id, object_id = match.groups()

        discovered_components: list[MqttComponentConfig] = []
        if component == CONF_DEVICE:






            device_discovery_payload = _parse_device_payload(
                hass, payload, object_id, node_id
            )
            if not device_discovery_payload:
                return
            device_config: dict[str, Any]
            origin_config: dict[str, Any] | None
            component_configs: dict[str, dict[str, Any]]
            device_config = device_discovery_payload[CONF_DEVICE]
            origin_config = device_discovery_payload.get(CONF_ORIGIN)
            component_configs = device_discovery_payload[CONF_COMPONENTS]
            for component_id, config in component_configs.items():
                component = config.pop(CONF_PLATFORM)


                component_node_id = object_id



                component_object_id = (
                    f"{node_id} {component_id}" if node_id else component_id
                )




                if discovery_payload := MQTTDiscoveryPayload(config):
                    discovery_payload[CONF_DEVICE] = device_config
                    discovery_payload[CONF_ORIGIN] = origin_config


                    _merge_common_device_options(
                        discovery_payload, device_discovery_payload
                    )
                discovery_payload.device_discovery = True
                discovery_payload.migrate_discovery = (
                    device_discovery_payload.migrate_discovery
                )
                discovered_components.append(
                    MqttComponentConfig(
                        component,
                        component_object_id,
                        component_node_id,
                        discovery_payload,
                    )
                )
            _LOGGER.debug(
                "Process device discovery payload %s", device_discovery_payload
            )
            device_discovery_id = f"{node_id} {object_id}" if node_id else object_id
            message = f"Processing device discovery for '{device_discovery_id}'"
            async_log_discovery_origin_info(
                message, MQTTDiscoveryPayload(device_discovery_payload)
            )

        else:

            try:
                discovery_payload = MQTTDiscoveryPayload(
                    json_loads_object(payload) if payload else {}
                )
            except ValueError:
                _LOGGER.warning("Unable to parse JSON %s: '%s'", object_id, payload)
                return
            if not _async_process_discovery_migration(discovery_payload):
                _replace_all_abbreviations(discovery_payload)
                if not _valid_origin_info(discovery_payload):
                    return
            discovered_components.append(
                MqttComponentConfig(component, object_id, node_id, discovery_payload)
            )

        discovery_pending_discovered = mqtt_data.discovery_pending_discovered
        for component_config in discovered_components:
            component = component_config.component
            node_id = component_config.node_id
            object_id = component_config.object_id
            discovery_payload = component_config.discovery_payload

            if TOPIC_BASE in discovery_payload:
                _replace_topic_base(discovery_payload)


            discovery_id = f"{node_id} {object_id}" if node_id else object_id
            discovery_hash = (component, discovery_id)


            discovery_payload.discovery_data = {
                ATTR_DISCOVERY_HASH: discovery_hash,
                ATTR_DISCOVERY_PAYLOAD: discovery_payload,
                ATTR_DISCOVERY_TOPIC: topic,
            }

            if discovery_hash in discovery_pending_discovered:
                pending = discovery_pending_discovered[discovery_hash]["pending"]
                pending.appendleft(discovery_payload)
                _LOGGER.debug(
                    "Component has already been discovered: %s %s, queuing update",
                    component,
                    discovery_id,
                )
                return

            async_process_discovery_payload(component, discovery_id, discovery_payload)

    @callback
    def async_process_discovery_payload(
        component: str, discovery_id: str, payload: MQTTDiscoveryPayload
    ) -> None:


        _LOGGER.debug("Process component discovery payload %s", payload)
        discovery_hash = (component, discovery_id)

        already_discovered = discovery_hash in mqtt_data.discovery_already_discovered
        if (
            already_discovered or payload
        ) and discovery_hash not in mqtt_data.discovery_pending_discovered:
            discovery_pending_discovered = mqtt_data.discovery_pending_discovered

            @callback
            def discovery_done(_: Any) -> None:
                pending = discovery_pending_discovered[discovery_hash]["pending"]
                _LOGGER.debug("Pending discovery for %s: %s", discovery_hash, pending)
                if not pending:
                    discovery_pending_discovered[discovery_hash]["unsub"]()
                    discovery_pending_discovered.pop(discovery_hash)
                else:
                    payload = pending.pop()
                    async_process_discovery_payload(component, discovery_id, payload)

            discovery_pending_discovered[discovery_hash] = {
                "unsub": async_dispatcher_connect(
                    hass,
                    MQTT_DISCOVERY_DONE.format(*discovery_hash),
                    discovery_done,
                ),
                "pending": deque([]),
            }

        if component not in mqtt_data.platforms_loaded and payload:

            config_entry.async_create_task(
                hass, _async_component_setup(component, payload)
            )
        elif already_discovered:

            message = f"Component has already been discovered: {component} {discovery_id}, sending update"
            async_log_discovery_origin_info(message, payload)
            async_dispatcher_send(
                hass, MQTT_DISCOVERY_UPDATED.format(*discovery_hash), payload
            )
        elif payload:
            _async_add_component(payload)
        else:

            async_dispatcher_send(
                hass, MQTT_DISCOVERY_DONE.format(*discovery_hash), None
            )

    mqtt_data.discovery_unsubscribe = [
        async_subscribe_internal(
            hass,
            topic,
            async_discovery_message_received,
            0,
            job_type=HassJobType.Callback,
        )


        for topic in chain(
            (
                f"{discovery_topic}/{component}/+/config"
                for component in SUPPORTED_COMPONENTS
            ),
            (
                f"{discovery_topic}/{component}/+/+/config"
                for component in SUPPORTED_COMPONENTS
            ),
            (
                f"{discovery_topic}/device/+/config",
                f"{discovery_topic}/device/+/+/config",
            ),
        )
    ]

    mqtt_data.last_discovery = time.monotonic()
    mqtt_integrations = await async_get_mqtt(hass)
    integration_unsubscribe = mqtt_data.integration_unsubscribe

    async def _async_handle_config_entry_removed(entry: ConfigEntry) -> None:

        for discovery_key in entry.discovery_keys[DOMAIN]:
            if (
                discovery_key.version != 1
                or not isinstance(discovery_key.key, str)
                or discovery_key.key not in integration_discovery_messages
            ):
                continue
            topic = discovery_key.key
            discovery_message = integration_discovery_messages[topic]
            del integration_discovery_messages[topic]
            _LOGGER.debug("Rediscover service on topic %s", topic)

            await async_integration_message_received(
                discovery_message.integration, discovery_message.msg
            )

    mqtt_data.discovery_unsubscribe.append(
        async_dispatcher_connect(
            hass,
            signal_discovered_config_entry_removed(DOMAIN),
            _async_handle_config_entry_removed,
        )
    )

    async def async_integration_message_received(
        integration: str, msg: ReceiveMessage
    ) -> None:

        if (
            msg.topic in integration_discovery_messages
            and integration_discovery_messages[msg.topic].msg.payload == msg.payload
        ):
            _LOGGER.debug(
                "Ignoring already processed discovery message for '%s' on topic %s: %s",
                integration,
                msg.topic,
                msg.payload,
            )
            return
        if TYPE_CHECKING:
            assert mqtt_data.data_config_flow_lock



        async with mqtt_data.data_config_flow_lock:
            data = MqttServiceInfo(
                topic=msg.topic,
                payload=msg.payload,
                qos=msg.qos,
                retain=msg.retain,
                subscribed_topic=msg.subscribed_topic,
                timestamp=msg.timestamp,
            )
            discovery_key = discovery_flow.DiscoveryKey(
                domain=DOMAIN, key=msg.topic, version=1
            )
            discovery_flow.async_create_flow(
                hass,
                integration,
                {"source": SOURCE_MQTT},
                data,
                discovery_key=discovery_key,
            )
            if msg.payload:

                integration_discovery_messages[msg.topic] = (
                    MQTTIntegrationDiscoveryConfig(integration=integration, msg=msg)
                )
            elif msg.topic in integration_discovery_messages:

                del integration_discovery_messages[msg.topic]

    integration_unsubscribe.update(
        {
            f"{integration}_{topic}": async_subscribe_internal(
                hass,
                topic,
                functools.partial(async_integration_message_received, integration),
                0,
                job_type=HassJobType.Coroutinefunction,
            )
            for integration, topics in mqtt_integrations.items()
            for topic in topics
        }
    )


async def async_stop(hass: HomeAssistant) -> None:

    mqtt_data = hass.data[DATA_MQTT]
    for unsub in mqtt_data.discovery_unsubscribe:
        unsub()
    mqtt_data.discovery_unsubscribe = []
    for key, unsub in list(mqtt_data.integration_unsubscribe.items()):
        unsub()
        mqtt_data.integration_unsubscribe.pop(key)
