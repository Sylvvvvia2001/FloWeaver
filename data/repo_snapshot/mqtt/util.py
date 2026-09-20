

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from functools import lru_cache
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import MAX_LENGTH_STATE_STATE, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, template
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.async_ import create_eager_task

from .const import (
    ATTR_PAYLOAD,
    ATTR_QOS,
    ATTR_RETAIN,
    ATTR_TOPIC,
    CONF_CERTIFICATE,
    CONF_CLIENT_CERT,
    CONF_CLIENT_KEY,
    DEFAULT_ENCODING,
    DEFAULT_QOS,
    DEFAULT_RETAIN,
    DOMAIN,
)
from .models import DATA_MQTT, DATA_MQTT_AVAILABLE, ReceiveMessage

AVAILABILITY_TIMEOUT = 50.0

TEMP_DIR_NAME = f"home-assistant-{DOMAIN}"

_VALID_QOS_SCHEMA = vol.All(vol.Coerce(int), vol.In([0, 1, 2]))

_LOGGER = logging.getLogger(__name__)


class EnsureJobAfterCooldown:









    def __init__(
        self, timeout: float, callback_job: Callable[[], Coroutine[Any, None, None]]
    ) -> None:

        self._loop = asyncio.get_running_loop()
        self._timeout = timeout
        self._callback = callback_job
        self._task: asyncio.Task | None = None
        self._timer: asyncio.TimerHandle | None = None
        self._next_execute_time = 0.0

    def set_timeout(self, timeout: float) -> None:

        self._timeout = timeout

    async def _async_job(self) -> None:

        try:
            await self._callback()
        except HomeAssistantError as ha_error:
            _LOGGER.error("%s", ha_error)

    @callback
    def _async_task_done(self, task: asyncio.Task) -> None:

        self._task = None

    @callback
    def async_execute(self) -> asyncio.Task:

        if self._task:


            self.async_schedule()
            return self._task

        self._async_cancel_timer()
        self._task = create_eager_task(self._async_job())
        self._task.add_done_callback(self._async_task_done)
        return self._task

    @callback
    def _async_cancel_timer(self) -> None:

        if self._timer:
            self._timer.cancel()
            self._timer = None

    @callback
    def async_schedule(self) -> None:



        next_when = self._loop.time() + self._timeout
        if not self._timer:
            self._timer = self._loop.call_at(next_when, self._async_timer_reached)
            return

        if self._timer.when() < next_when:


            self._next_execute_time = next_when

    @callback
    def _async_timer_reached(self) -> None:

        self._timer = None
        if self._loop.time() >= self._next_execute_time:
            self.async_execute()
            return


        self._timer = self._loop.call_at(
            self._next_execute_time, self._async_timer_reached
        )

    async def async_cleanup(self) -> None:

        self._async_cancel_timer()
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        except Exception:
            _LOGGER.exception("Error cleaning up task")


def platforms_from_config(config: list[ConfigType]) -> set[Platform | str]:

    return {key for platform in config for key in platform}


async def async_forward_entry_setup_and_setup_discovery(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    platforms: set[Platform | str],
    late: bool = False,
) -> None:

    mqtt_data = hass.data[DATA_MQTT]
    platforms_loaded = mqtt_data.platforms_loaded
    new_platforms: set[Platform | str] = platforms - platforms_loaded
    tasks: list[asyncio.Task] = []
    if "device_automation" in new_platforms:

        from . import device_automation

        tasks.append(
            create_eager_task(
                device_automation.async_setup_mqtt_device_automation_entry(
                    hass, config_entry
                )
            )
        )
    if "tag" in new_platforms:

        from . import tag

        tasks.append(
            create_eager_task(tag.async_setup_mqtt_tag_entry(hass, config_entry))
        )
    if new_entity_platforms := (new_platforms - {"tag", "device_automation"}):
        tasks.append(
            create_eager_task(
                hass.config_entries.async_forward_entry_setups(
                    config_entry, new_entity_platforms
                )
            )
        )
    if not tasks:
        return
    await asyncio.gather(*tasks)
    platforms_loaded.update(new_platforms)


def mqtt_config_entry_enabled(hass: HomeAssistant) -> bool | None:



    return (
        DATA_MQTT in hass.data and hass.data[DATA_MQTT].client.connected
    ) or hass.config_entries.async_has_entries(
        DOMAIN, include_disabled=False, include_ignore=False
    )


async def async_wait_for_mqtt_client(hass: HomeAssistant) -> bool:







    if not mqtt_config_entry_enabled(hass):
        return False

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    if entry.state == ConfigEntryState.LOADED:
        return True

    state_reached_future: asyncio.Future[bool]
    if DATA_MQTT_AVAILABLE not in hass.data:
        state_reached_future = hass.loop.create_future()
        hass.data[DATA_MQTT_AVAILABLE] = state_reached_future
    else:
        state_reached_future = hass.data[DATA_MQTT_AVAILABLE]

    try:
        async with asyncio.timeout(AVAILABILITY_TIMEOUT):

            return await state_reached_future
    except TimeoutError:
        return False


def valid_topic(topic: Any) -> str:










    validated_topic = cv.string(topic)
    try:
        raw_validated_topic = validated_topic.encode("utf-8")
    except UnicodeError as err:
        raise vol.Invalid("MQTT topic name/filter must be valid UTF-8 string.") from err
    if not raw_validated_topic:
        raise vol.Invalid("MQTT topic name/filter must not be empty.")
    if len(raw_validated_topic) > 65535:
        raise vol.Invalid(
            "MQTT topic name/filter must not be longer than 65535 encoded bytes."
        )

    for char in validated_topic:
        if char == "\0":
            raise vol.Invalid("MQTT topic name/filter must not contain null character.")
        if char <= "\u001f" or "\u007f" <= char <= "\u009f":
            raise vol.Invalid(
                "MQTT topic name/filter must not contain control characters."
            )
        if "\ufdd0" <= char <= "\ufdef" or (ord(char) & 0xFFFF) in (0xFFFE, 0xFFFF):
            raise vol.Invalid("MQTT topic name/filter must not contain non-characters.")

    return validated_topic


@lru_cache
def valid_subscribe_topic(topic: Any) -> str:

    validated_topic = valid_topic(topic)
    if "+" in validated_topic:
        for i in (i for i, c in enumerate(validated_topic) if c == "+"):
            if (i > 0 and validated_topic[i - 1] != "/") or (
                i < len(validated_topic) - 1 and validated_topic[i + 1] != "/"
            ):
                raise vol.Invalid(
                    "Single-level wildcard must occupy an entire level of the filter"
                )

    index = validated_topic.find("#")
    if index != -1:
        if index != len(validated_topic) - 1:

            raise vol.Invalid(
                "Multi-level wildcard must be the last character in the topic filter."
            )
        if len(validated_topic) > 1 and validated_topic[index - 1] != "/":
            raise vol.Invalid(
                "Multi-level wildcard must be after a topic level separator."
            )

    return validated_topic


def valid_subscribe_topic_template(value: Any) -> template.Template:

    tpl = cv.template(value)

    if tpl.is_static:
        valid_subscribe_topic(value)

    return tpl


@lru_cache
def valid_publish_topic(topic: Any) -> str:

    validated_topic = valid_topic(topic)
    if "+" in validated_topic or "#" in validated_topic:
        raise vol.Invalid("Wildcards cannot be used in topic names")
    return validated_topic


def valid_qos_schema(qos: Any) -> int:

    validated_qos: int = _VALID_QOS_SCHEMA(qos)
    return validated_qos


_MQTT_WILL_BIRTH_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TOPIC): valid_publish_topic,
        vol.Required(ATTR_PAYLOAD): cv.string,
        vol.Optional(ATTR_QOS, default=DEFAULT_QOS): valid_qos_schema,
        vol.Optional(ATTR_RETAIN, default=DEFAULT_RETAIN): cv.boolean,
    },
    required=True,
)


def valid_birth_will(config: ConfigType) -> ConfigType:

    if config:
        config = _MQTT_WILL_BIRTH_SCHEMA(config)
    return config


async def async_create_certificate_temp_files(
    hass: HomeAssistant, config: ConfigType
) -> None:


    def _create_temp_file(temp_file: Path, data: str | None) -> None:
        if data is None or data == "auto":
            if temp_file.exists():
                os.remove(Path(temp_file))
            return
        temp_file.write_text(data)

    def _create_temp_dir_and_files() -> None:

        temp_dir = Path(tempfile.gettempdir()) / TEMP_DIR_NAME

        if (
            config.get(CONF_CERTIFICATE)
            or config.get(CONF_CLIENT_CERT)
            or config.get(CONF_CLIENT_KEY)
        ) and not temp_dir.exists():
            temp_dir.mkdir(0o700)

        _create_temp_file(temp_dir / CONF_CERTIFICATE, config.get(CONF_CERTIFICATE))
        _create_temp_file(temp_dir / CONF_CLIENT_CERT, config.get(CONF_CLIENT_CERT))
        _create_temp_file(temp_dir / CONF_CLIENT_KEY, config.get(CONF_CLIENT_KEY))

    await hass.async_add_executor_job(_create_temp_dir_and_files)


def check_state_too_long(
    logger: logging.Logger, proposed_state: str, entity_id: str, msg: ReceiveMessage
) -> bool:

    if (state_length := len(proposed_state)) > MAX_LENGTH_STATE_STATE:
        logger.warning(
            "Cannot update state for entity %s after processing "
            "payload on topic %s. The requested state (%s) exceeds "
            "the maximum allowed length (%s). Fall back to "
            "%s, failed state: %s",
            entity_id,
            msg.topic,
            state_length,
            MAX_LENGTH_STATE_STATE,
            STATE_UNKNOWN,
            proposed_state[:8192],
        )
        return True

    return False


def get_file_path(option: str, default: str | None = None) -> str | None:

    temp_dir = Path(tempfile.gettempdir()) / TEMP_DIR_NAME
    if not temp_dir.exists():
        return default

    file_path: Path = temp_dir / option
    if not file_path.exists():
        return default

    return str(temp_dir / option)


def migrate_certificate_file_to_content(file_name_or_auto: str) -> str | None:

    if file_name_or_auto == "auto":
        return "auto"
    try:
        with open(file_name_or_auto, encoding=DEFAULT_ENCODING) as certificate_file:
            return certificate_file.read()
    except OSError:
        return None


@callback
def learn_more_url(platform: str) -> str:

    return f"https://www.home-assistant.io/integrations/{platform}.mqtt/"
