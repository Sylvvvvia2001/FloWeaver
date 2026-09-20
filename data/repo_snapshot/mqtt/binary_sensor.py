

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import binary_sensor
from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_FORCE_UPDATE,
    CONF_NAME,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    CONF_VALUE_TEMPLATE,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, event as evt
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from . import subscription
from .config import MQTT_RO_SCHEMA
from .const import CONF_OFF_DELAY, CONF_STATE_TOPIC, PAYLOAD_NONE
from .entity import MqttAvailabilityMixin, MqttEntity, async_setup_entity_entry_helper
from .models import MqttValueTemplate, ReceiveMessage
from .schemas import MQTT_ENTITY_COMMON_SCHEMA

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

DEFAULT_NAME = "MQTT Binary sensor"
DEFAULT_PAYLOAD_OFF = "OFF"
DEFAULT_PAYLOAD_ON = "ON"
DEFAULT_FORCE_UPDATE = False
CONF_EXPIRE_AFTER = "expire_after"

PLATFORM_SCHEMA_MODERN = MQTT_RO_SCHEMA.extend(
    {
        vol.Optional(CONF_DEVICE_CLASS): vol.Any(DEVICE_CLASSES_SCHEMA, None),
        vol.Optional(CONF_EXPIRE_AFTER): cv.positive_int,
        vol.Optional(CONF_FORCE_UPDATE, default=DEFAULT_FORCE_UPDATE): cv.boolean,
        vol.Optional(CONF_NAME): vol.Any(cv.string, None),
        vol.Optional(CONF_OFF_DELAY): cv.positive_int,
        vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
        vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
    }
).extend(MQTT_ENTITY_COMMON_SCHEMA.schema)

DISCOVERY_SCHEMA = PLATFORM_SCHEMA_MODERN.extend({}, extra=vol.REMOVE_EXTRA)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    async_setup_entity_entry_helper(
        hass,
        config_entry,
        MqttBinarySensor,
        binary_sensor.DOMAIN,
        async_add_entities,
        DISCOVERY_SCHEMA,
        PLATFORM_SCHEMA_MODERN,
    )


class MqttBinarySensor(MqttEntity, BinarySensorEntity, RestoreEntity):


    _default_name = DEFAULT_NAME
    _delay_listener: CALLBACK_TYPE | None = None
    _entity_id_format = binary_sensor.ENTITY_ID_FORMAT
    _expired: bool | None
    _expire_after: int | None
    _expiration_trigger: CALLBACK_TYPE | None = None

    async def mqtt_async_added_to_hass(self) -> None:

        if (
            self._expire_after
            and (last_state := await self.async_get_last_state()) is not None
            and last_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE]


            and not self._expiration_trigger
        ):
            expiration_at: datetime = last_state.last_changed + timedelta(
                seconds=self._expire_after
            )
            remain_seconds = (expiration_at - dt_util.utcnow()).total_seconds()

            if remain_seconds <= 0:

                _LOGGER.debug("Skip state recovery after reload for %s", self.entity_id)
                return
            self._expired = False
            self._attr_is_on = last_state.state == STATE_ON

            self._expiration_trigger = async_call_later(
                self.hass, remain_seconds, self._value_is_expired
            )
            _LOGGER.debug(
                (
                    "State recovered after reload for %s, remaining time before"
                    " expiring %s"
                ),
                self.entity_id,
                remain_seconds,
            )

    async def async_will_remove_from_hass(self) -> None:


        if self._expiration_trigger:
            _LOGGER.debug("Clean up expire after trigger for %s", self.entity_id)
            self._expiration_trigger()
            self._expiration_trigger = None
            self._expired = False
        await MqttEntity.async_will_remove_from_hass(self)

    @staticmethod
    def config_schema() -> vol.Schema:

        return DISCOVERY_SCHEMA

    def _setup_from_config(self, config: ConfigType) -> None:

        self._expire_after = config.get(CONF_EXPIRE_AFTER)
        if self._expire_after:
            self._expired = True
        else:
            self._expired = None
        self._attr_force_update = config[CONF_FORCE_UPDATE]
        self._attr_device_class = config.get(CONF_DEVICE_CLASS)

        self._value_template = MqttValueTemplate(
            self._config.get(CONF_VALUE_TEMPLATE),
            entity=self,
        ).async_render_with_possible_json_value

    @callback
    def _off_delay_listener(self, now: datetime) -> None:

        self._delay_listener = None
        self._attr_is_on = False
        self.async_write_ha_state()

    def _state_message_received(self, msg: ReceiveMessage) -> None:



        if self._expire_after:


            self._expired = False


            if self._expiration_trigger:
                self._expiration_trigger()


            self._expiration_trigger = async_call_later(
                self.hass, self._expire_after, self._value_is_expired
            )

        payload = self._value_template(msg.payload)
        if not payload.strip():
            _LOGGER.debug(
                (
                    "Empty template output for entity: %s with state topic: %s."
                    " Payload: '%s', with value template '%s'"
                ),
                self.entity_id,
                self._config[CONF_STATE_TOPIC],
                msg.payload,
                self._config.get(CONF_VALUE_TEMPLATE),
            )
            return

        if payload == self._config[CONF_PAYLOAD_ON]:
            self._attr_is_on = True
        elif payload == self._config[CONF_PAYLOAD_OFF]:
            self._attr_is_on = False
        elif payload == PAYLOAD_NONE:
            self._attr_is_on = None
        else:
            template_info = ""
            if self._config.get(CONF_VALUE_TEMPLATE) is not None:
                template_info = (
                    f", template output: '{payload!s}', with value template"
                    f" '{self._config.get(CONF_VALUE_TEMPLATE)!s}'"
                )
            _LOGGER.info(
                (
                    "No matching payload found for entity: %s with state topic: %s."
                    " Payload: '%s'%s"
                ),
                self.entity_id,
                self._config[CONF_STATE_TOPIC],
                msg.payload,
                template_info,
            )
            return

        if self._delay_listener is not None:
            self._delay_listener()
            self._delay_listener = None

        off_delay: int | None = self._config.get(CONF_OFF_DELAY)
        if self._attr_is_on and off_delay is not None:
            self._delay_listener = evt.async_call_later(
                self.hass, off_delay, self._off_delay_listener
            )

    @callback
    def _prepare_subscribe_topics(self) -> None:

        self.add_subscription(
            CONF_STATE_TOPIC, self._state_message_received, {"_attr_is_on", "_expired"}
        )

    async def _subscribe_topics(self) -> None:

        subscription.async_subscribe_topics_internal(self.hass, self._sub_state)

    @callback
    def _value_is_expired(self, *_: Any) -> None:

        self._expiration_trigger = None
        self._expired = True

        self.async_write_ha_state()

    @property
    def available(self) -> bool:


        return MqttAvailabilityMixin.available.fget(self) and (
            self._expire_after is None or not self._expired
        )
