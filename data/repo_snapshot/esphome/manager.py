

from __future__ import annotations

import base64
from functools import partial
import logging
import secrets
import struct
from typing import TYPE_CHECKING, Any, NamedTuple

from aioesphomeapi import (
    APIClient,
    APIConnectionError,
    APIVersion,
    DeviceInfo as EsphomeDeviceInfo,
    EncryptionPlaintextAPIError,
    ExecuteServiceResponse,
    HomeassistantServiceCall,
    InvalidAuthAPIError,
    InvalidEncryptionKeyAPIError,
    LogLevel,
    ReconnectLogic,
    RequiresEncryptionAPIError,
    SupportsResponseType,
    UserService,
    UserServiceArgType,
    ZWaveProxyRequest,
    ZWaveProxyRequestType,
    parse_log_message,
)
from awesomeversion import AwesomeVersion
import voluptuous as vol

from homeassistant.components import bluetooth, tag, zeroconf
from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_MODE,
    EVENT_HOMEASSISTANT_CLOSE,
    EVENT_LOGGING_CHANGED,
    Platform,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    State,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceNotFound,
    ServiceValidationError,
    TemplateError,
)
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
    json as json_helper,
    template,
)
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.helpers.service import async_set_service_schema
from homeassistant.helpers.template import Template
from homeassistant.util.json import json_loads_object

from .bluetooth import async_connect_scanner
from .const import (
    CONF_ALLOW_SERVICE_CALLS,
    CONF_BLUETOOTH_MAC_ADDRESS,
    CONF_DEVICE_NAME,
    CONF_NOISE_PSK,
    CONF_SUBSCRIBE_LOGS,
    DEFAULT_ALLOW_SERVICE_CALLS,
    DEFAULT_URL,
    DOMAIN,
    PROJECT_URLS,
    STABLE_BLE_VERSION,
    STABLE_BLE_VERSION_STR,
)
from .dashboard import async_get_dashboard
from .domain_data import DomainData
from .encryption_key_storage import async_get_encryption_key_storage


from .entry_data import ESPHomeConfigEntry, RuntimeEntryData
from .enum_mapper import EsphomeEnumMapper

DEVICE_CONFLICT_ISSUE_FORMAT = "device_conflict-{}"
UNPACK_UINT32_BE = struct.Struct(">I").unpack_from


if TYPE_CHECKING:
    from aioesphomeapi.api_pb2 import SubscribeLogsResponse


_LOGGER = logging.getLogger(__name__)

LOG_LEVEL_TO_LOGGER = {
    LogLevel.LOG_LEVEL_NONE: logging.DEBUG,
    LogLevel.LOG_LEVEL_ERROR: logging.ERROR,
    LogLevel.LOG_LEVEL_WARN: logging.WARNING,
    LogLevel.LOG_LEVEL_INFO: logging.INFO,
    LogLevel.LOG_LEVEL_CONFIG: logging.INFO,
    LogLevel.LOG_LEVEL_DEBUG: logging.DEBUG,
    LogLevel.LOG_LEVEL_VERBOSE: logging.DEBUG,
    LogLevel.LOG_LEVEL_VERY_VERBOSE: logging.DEBUG,
}
LOGGER_TO_LOG_LEVEL = {
    logging.NOTSET: LogLevel.LOG_LEVEL_VERY_VERBOSE,
    logging.DEBUG: LogLevel.LOG_LEVEL_VERY_VERBOSE,
    logging.INFO: LogLevel.LOG_LEVEL_CONFIG,
    logging.WARNING: LogLevel.LOG_LEVEL_WARN,
    logging.ERROR: LogLevel.LOG_LEVEL_ERROR,
    logging.CRITICAL: LogLevel.LOG_LEVEL_ERROR,
}


@callback
def _async_check_firmware_version(
    hass: HomeAssistant, device_info: EsphomeDeviceInfo, api_version: APIVersion
) -> None:


    issue = f"ble_firmware_outdated-{device_info.mac_address}"
    if (
        not device_info.bluetooth_proxy_feature_flags_compat(api_version)


        or (device_info.project_name and device_info.project_name not in PROJECT_URLS)
        or AwesomeVersion(device_info.esphome_version) >= STABLE_BLE_VERSION
    ):
        async_delete_issue(hass, DOMAIN, issue)
        return
    async_create_issue(
        hass,
        DOMAIN,
        issue,
        is_fixable=False,
        severity=IssueSeverity.WARNING,
        learn_more_url=PROJECT_URLS.get(device_info.project_name, DEFAULT_URL),
        translation_key="ble_firmware_outdated",
        translation_placeholders={
            "name": device_info.name,
            "version": STABLE_BLE_VERSION_STR,
        },
    )


@callback
def _async_check_using_api_password(
    hass: HomeAssistant, device_info: EsphomeDeviceInfo, has_password: bool
) -> None:


    issue = f"api_password_deprecated-{device_info.mac_address}"
    if not has_password:
        async_delete_issue(hass, DOMAIN, issue)
        return
    async_create_issue(
        hass,
        DOMAIN,
        issue,
        is_fixable=False,
        severity=IssueSeverity.WARNING,
        learn_more_url="https://esphome.io/components/api.html",
        translation_key="api_password_deprecated",
        translation_placeholders={
            "name": device_info.name,
        },
    )


class ESPHomeManager:


    __slots__ = (
        "_cancel_subscribe_logs",
        "_log_level",
        "cli",
        "device_id",
        "domain_data",
        "entry",
        "entry_data",
        "hass",
        "host",
        "password",
        "reconnect_logic",
        "zeroconf_instance",
    )

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ESPHomeConfigEntry,
        host: str,
        password: str | None,
        cli: APIClient,
        zeroconf_instance: zeroconf.HaZeroconf,
        domain_data: DomainData,
    ) -> None:

        self.hass = hass
        self.host = host
        self.password = password
        self.entry = entry
        self.cli = cli
        self.device_id: str | None = None
        self.domain_data = domain_data
        self.reconnect_logic: ReconnectLogic | None = None
        self.zeroconf_instance = zeroconf_instance
        self.entry_data = entry.runtime_data
        self._cancel_subscribe_logs: CALLBACK_TYPE | None = None
        self._log_level = LogLevel.LOG_LEVEL_NONE

    async def on_stop(self, event: Event) -> None:

        await cleanup_instance(self.entry)

    @property
    def services_issue(self) -> str:

        return f"service_calls_not_enabled-{self.entry.unique_id}"

    @callback
    def async_on_service_call(self, service: HomeassistantServiceCall) -> None:

        hass = self.hass
        domain, service_name = service.service.split(".", 1)
        service_data = service.data

        if service.data_template:
            try:
                data_template = {
                    key: Template(value, hass)
                    for key, value in service.data_template.items()
                }
                service_data.update(
                    template.render_complex(data_template, service.variables)
                )
            except TemplateError as ex:
                _LOGGER.error(
                    "Error rendering data template %s for %s: %s",
                    service.data_template,
                    self.host,
                    ex,
                )
                return

        if service.is_event:
            device_id = self.device_id


            if domain != DOMAIN:
                _LOGGER.error(
                    "Can only generate events under esphome domain! (%s)", self.host
                )
                return


            if service_name == "tag_scanned" and device_id is not None:
                tag_id = service_data["tag_id"]
                hass.async_create_task(tag.async_scan_tag(hass, tag_id, device_id))
                return

            hass.bus.async_fire(
                service.service,
                {
                    ATTR_DEVICE_ID: device_id,
                    **service_data,
                },
            )
        elif self.entry.options.get(
            CONF_ALLOW_SERVICE_CALLS, DEFAULT_ALLOW_SERVICE_CALLS
        ):
            call_id = service.call_id
            if call_id and service.wants_response:

                self.entry.async_create_task(
                    hass,
                    self._handle_service_call_with_response(
                        domain,
                        service_name,
                        service_data,
                        call_id,
                        service.response_template,
                    ),
                )
            elif call_id:

                self.entry.async_create_task(
                    hass,
                    self._handle_service_call_with_notification(
                        domain, service_name, service_data, call_id
                    ),
                )
            else:

                self.entry.async_create_task(
                    hass, hass.services.async_call(domain, service_name, service_data)
                )
        else:
            device_info = self.entry_data.device_info
            assert device_info is not None
            async_create_issue(
                hass,
                DOMAIN,
                self.services_issue,
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="service_calls_not_allowed",
                translation_placeholders={
                    "name": device_info.friendly_name or device_info.name,
                },
            )
            _LOGGER.error(
                "%s: Service call %s.%s: with data %s rejected; "
                "If you trust this device and want to allow access for it to make "
                "Home Assistant service calls, you can enable this "
                "functionality in the options flow",
                device_info.friendly_name or device_info.name,
                domain,
                service_name,
                service_data,
            )

    async def _handle_service_call_with_response(
        self,
        domain: str,
        service_name: str,
        service_data: dict,
        call_id: int,
        response_template: str | None = None,
    ) -> None:

        try:

            action_response = await self.hass.services.async_call(
                domain=domain,
                service=service_name,
                service_data=service_data,
                blocking=True,
                return_response=True,
            )

            if response_template:
                try:

                    tmpl = Template(response_template, self.hass)
                    response = tmpl.async_render(
                        variables={"response": action_response},
                        strict=True,
                    )
                    response_dict = {"response": response}

                except TemplateError as ex:
                    raise HomeAssistantError(
                        f"Error rendering response template: {ex}"
                    ) from ex
            else:
                response_dict = {"response": action_response}


            response_data = json_helper.json_bytes(response_dict)

        except (
            ServiceNotFound,
            ServiceValidationError,
            vol.Invalid,
            HomeAssistantError,
        ) as ex:
            self._send_service_call_response(
                call_id, success=False, error_message=str(ex), response_data=b""
            )

        else:

            self._send_service_call_response(
                call_id=call_id,
                success=True,
                error_message="",
                response_data=response_data,
            )

    async def _handle_service_call_with_notification(
        self, domain: str, service_name: str, service_data: dict, call_id: int
    ) -> None:

        try:
            await self.hass.services.async_call(
                domain, service_name, service_data, blocking=True
            )
        except (ServiceNotFound, ServiceValidationError, vol.Invalid) as ex:
            self._send_service_call_response(call_id, False, str(ex), b"")
        else:
            self._send_service_call_response(call_id, True, "", b"")

    def _send_service_call_response(
        self,
        call_id: int,
        success: bool,
        error_message: str,
        response_data: bytes,
    ) -> None:

        _LOGGER.debug(
            "Service call response for call_id %s: success=%s, error=%s",
            call_id,
            success,
            error_message,
        )
        self.cli.send_homeassistant_action_response(
            call_id,
            success,
            error_message,
            response_data,
        )

    @callback
    def _send_home_assistant_state(
        self, entity_id: str, attribute: str | None, state: State | None
    ) -> None:

        if state is None or (attribute and attribute not in state.attributes):
            return

        send_state = state.state
        if attribute:
            attr_val = state.attributes[attribute]

            if isinstance(attr_val, bool):
                send_state = "on" if attr_val else "off"
            else:
                send_state = attr_val

        self.cli.send_home_assistant_state(entity_id, attribute, str(send_state))

    @callback
    def _send_home_assistant_state_event(
        self,
        attribute: str | None,
        event: Event[EventStateChangedData],
    ) -> None:

        event_data = event.data
        new_state = event_data["new_state"]
        old_state = event_data["old_state"]

        if new_state is None or old_state is None:
            return


        if (not attribute and old_state.state == new_state.state) or (
            attribute
            and old_state.attributes.get(attribute)
            == new_state.attributes.get(attribute)
        ):
            return

        self._send_home_assistant_state(event.data["entity_id"], attribute, new_state)

    @callback
    def async_on_state_subscription(
        self, entity_id: str, attribute: str | None = None
    ) -> None:

        hass = self.hass
        self.entry_data.disconnect_callbacks.add(
            async_track_state_change_event(
                hass,
                [entity_id],
                partial(self._send_home_assistant_state_event, attribute),
            )
        )

        self._send_home_assistant_state(
            entity_id, attribute, hass.states.get(entity_id)
        )

    @callback
    def async_on_state_request(
        self, entity_id: str, attribute: str | None = None
    ) -> None:

        self._send_home_assistant_state(
            entity_id, attribute, self.hass.states.get(entity_id)
        )

    async def on_connect(self) -> None:

        try:
            await self._on_connect()
        except InvalidAuthAPIError as err:
            _LOGGER.warning("Authentication failed for %s: %s", self.host, err)
            await self._start_reauth_and_disconnect()
        except APIConnectionError as err:
            _LOGGER.warning(
                "Error getting setting up connection for %s: %s", self.host, err
            )

            await self.cli.disconnect()

    def _async_on_log(self, msg: SubscribeLogsResponse) -> None:

        for line in parse_log_message(
            msg.message.decode("utf-8", "backslashreplace"), "", strip_ansi_escapes=True
        ):
            _LOGGER.log(
                LOG_LEVEL_TO_LOGGER.get(msg.level, logging.DEBUG),
                "%s: %s",
                self.entry.title,
                line,
            )

    @callback
    def _async_get_equivalent_log_level(self) -> LogLevel:

        return LOGGER_TO_LOG_LEVEL.get(
            _LOGGER.getEffectiveLevel(), LogLevel.LOG_LEVEL_VERY_VERBOSE
        )

    @callback
    def _async_subscribe_logs(self, log_level: LogLevel) -> None:

        if self._cancel_subscribe_logs is not None:
            self._cancel_subscribe_logs()
            self._cancel_subscribe_logs = None
        self._log_level = log_level
        self._cancel_subscribe_logs = self.cli.subscribe_logs(
            self._async_on_log, self._log_level
        )

    async def _on_connect(self) -> None:

        entry = self.entry
        unique_id = entry.unique_id
        entry_data = self.entry_data
        reconnect_logic = self.reconnect_logic
        assert reconnect_logic is not None, "Reconnect logic must be set"
        hass = self.hass
        cli = self.cli
        stored_device_name: str | None = entry.data.get(CONF_DEVICE_NAME)
        unique_id_is_mac_address = unique_id and ":" in unique_id
        if entry.options.get(CONF_SUBSCRIBE_LOGS):
            self._async_subscribe_logs(self._async_get_equivalent_log_level())
        device_info, entity_infos, services = await cli.device_info_and_list_entities()

        device_mac = format_mac(device_info.mac_address)
        mac_address_matches = unique_id == device_mac
        if (
            bluetooth_mac_address := device_info.bluetooth_mac_address
        ) and entry.data.get(CONF_BLUETOOTH_MAC_ADDRESS) != bluetooth_mac_address:
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_BLUETOOTH_MAC_ADDRESS: bluetooth_mac_address},
            )





        if not mac_address_matches and not unique_id_is_mac_address:
            hass.config_entries.async_update_entry(entry, unique_id=device_mac)

        issue = DEVICE_CONFLICT_ISSUE_FORMAT.format(entry.entry_id)
        if not mac_address_matches and unique_id_is_mac_address:





            if stored_device_name == device_info.name:





                shared_data = {
                    "name": device_info.name,
                    "mac": format_mac(device_mac),
                    "stored_mac": format_mac(unique_id),
                    "model": device_info.model,
                    "ip": self.host,
                }
                async_create_issue(
                    hass,
                    DOMAIN,
                    issue,
                    is_fixable=True,
                    severity=IssueSeverity.ERROR,
                    translation_key="device_conflict",
                    translation_placeholders=shared_data,
                    data={**shared_data, "entry_id": entry.entry_id},
                )
            _LOGGER.error(
                "Unexpected device found at %s; "
                "expected `%s` with mac address `%s`, "
                "found `%s` with mac address `%s`",
                self.host,
                stored_device_name,
                unique_id,
                device_info.name,
                device_mac,
            )
            await cli.disconnect()
            await reconnect_logic.stop()







            return

        async_delete_issue(hass, DOMAIN, issue)





        if stored_device_name != device_info.name:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_DEVICE_NAME: device_info.name}
            )

        api_version = cli.api_version
        assert api_version is not None, "API version must be set"
        entry_data.async_on_connect(hass, device_info, api_version)

        await self._handle_dynamic_encryption_key(device_info)

        if device_info.name:
            reconnect_logic.name = device_info.name

        if not device_info.friendly_name:
            _LOGGER.info(
                "No `friendly_name` set in the `esphome:` section of the "
                "YAML config for device '%s' (MAC: %s); It's recommended "
                "to add one for easier identification and better alignment "
                "with Home Assistant naming conventions",
                device_info.name,
                device_mac,
            )

        entry_data.device_id_to_name = {
            sub_device.device_id: sub_device.name or device_info.name
            for sub_device in device_info.devices
        }
        self.device_id = _async_setup_device_registry(hass, entry, entry_data)

        entry_data.async_update_device_state()
        await entry_data.async_update_static_infos(
            hass, entry, entity_infos, device_info.mac_address
        )
        _setup_services(hass, entry_data, services)

        if device_info.bluetooth_proxy_feature_flags_compat(api_version):
            entry_data.disconnect_callbacks.add(
                async_connect_scanner(
                    hass, entry_data, cli, device_info, self.device_id
                )
            )
        else:
            bluetooth.async_remove_scanner(
                hass, device_info.bluetooth_mac_address or device_info.mac_address
            )

        if device_info.voice_assistant_feature_flags_compat(api_version) and (
            Platform.ASSIST_SATELLITE not in entry_data.loaded_platforms
        ):

            await self.hass.config_entries.async_forward_entry_setups(
                self.entry, [Platform.ASSIST_SATELLITE]
            )
            entry_data.loaded_platforms.add(Platform.ASSIST_SATELLITE)

        if device_info.zwave_proxy_feature_flags:
            entry_data.disconnect_callbacks.add(
                cli.subscribe_zwave_proxy_request(self._async_zwave_proxy_request)
            )

        cli.subscribe_home_assistant_states_and_services(
            on_state=entry_data.async_update_state,
            on_service_call=self.async_on_service_call,
            on_state_sub=self.async_on_state_subscription,
            on_state_request=self.async_on_state_request,
        )

        entry_data.async_save_to_store()
        _async_check_firmware_version(hass, device_info, api_version)
        _async_check_using_api_password(hass, device_info, bool(self.password))

    def _async_zwave_proxy_request(self, request: ZWaveProxyRequest) -> None:

        if request.type != ZWaveProxyRequestType.HOME_ID_CHANGE:
            return









        zwave_home_id: int = UNPACK_UINT32_BE(request.data[0:4])[0]
        assert self.entry_data.device_info is not None
        self.entry_data.async_create_zwave_js_flow(
            self.hass, self.entry_data.device_info, zwave_home_id
        )

    async def on_disconnect(self, expected_disconnect: bool) -> None:

        entry_data = self.entry_data
        hass = self.hass
        host = self.host
        name = entry_data.device_info.name if entry_data.device_info else host
        _LOGGER.debug(
            "%s: %s disconnected (expected=%s), running disconnected callbacks",
            name,
            host,
            expected_disconnect,
        )
        entry_data.async_on_disconnect()
        entry_data.expected_disconnect = expected_disconnect


        entry_data.stale_state = {
            (type(entity_state), entity_state.device_id, key)
            for state_dict in entry_data.state.values()
            for key, entity_state in state_dict.items()
        }
        if not hass.is_stopping:




            entry_data.async_update_device_state()

        if Platform.ASSIST_SATELLITE in self.entry_data.loaded_platforms:
            await self.hass.config_entries.async_unload_platforms(
                self.entry, [Platform.ASSIST_SATELLITE]
            )

            self.entry_data.loaded_platforms.remove(Platform.ASSIST_SATELLITE)

    async def on_connect_error(self, err: Exception) -> None:

        if not isinstance(
            err,
            (
                EncryptionPlaintextAPIError,
                RequiresEncryptionAPIError,
                InvalidEncryptionKeyAPIError,
                InvalidAuthAPIError,
            ),
        ):
            return

        if isinstance(err, InvalidEncryptionKeyAPIError):
            if (
                (received_name := err.received_name)
                and (received_mac := err.received_mac)
                and (unique_id := self.entry.unique_id)
                and ":" in unique_id
            ):
                formatted_received_mac = format_mac(received_mac)
                formatted_expected_mac = format_mac(unique_id)
                if formatted_received_mac != formatted_expected_mac:
                    _LOGGER.error(
                        "Unexpected device found at %s; "
                        "expected `%s` with mac address `%s`, "
                        "found `%s` with mac address `%s`",
                        self.host,
                        self.entry.data.get(CONF_DEVICE_NAME),
                        formatted_expected_mac,
                        received_name,
                        formatted_received_mac,
                    )





                    if self.reconnect_logic:
                        await self.reconnect_logic.stop()
                    return
        await self._start_reauth_and_disconnect()

    async def _start_reauth_and_disconnect(self) -> None:

        self.entry.async_start_reauth(self.hass)
        await self.cli.disconnect()
        if self.reconnect_logic:
            await self.reconnect_logic.stop()

    async def _handle_dynamic_encryption_key(
        self, device_info: EsphomeDeviceInfo
    ) -> None:





        noise_psk: str | None = self.entry.data.get(CONF_NOISE_PSK)
        if noise_psk:

            return

        if not device_info.api_encryption_supported:

            return


        storage = await async_get_encryption_key_storage(self.hass)


        from_storage: bool = False
        if self.entry.unique_id and (
            stored_key := await storage.async_get_key(self.entry.unique_id)
        ):
            _LOGGER.debug(
                "Retrieved encryption key from storage for device %s",
                self.entry.unique_id,
            )

            new_key = stored_key.encode()
            new_key_str = stored_key
            from_storage = True
        else:

            _LOGGER.debug(
                "Generating new encryption key for device %s", self.entry.unique_id
            )
            new_key = base64.b64encode(secrets.token_bytes(32))
            new_key_str = new_key.decode()

        try:

            result = await self.cli.noise_encryption_set_key(new_key)
        except APIConnectionError as ex:
            _LOGGER.error(
                "Connection error while storing encryption key for device %s (%s): %s",
                self.entry.data.get(CONF_DEVICE_NAME, self.host),
                self.entry.unique_id,
                ex,
            )
            return
        else:
            if not result:
                _LOGGER.error(
                    "Failed to set dynamic encryption key on device %s (%s)",
                    self.entry.data.get(CONF_DEVICE_NAME, self.host),
                    self.entry.unique_id,
                )
                return


        assert self.entry.unique_id is not None


        if not from_storage:
            await storage.async_store_key(self.entry.unique_id, new_key_str)


        self.hass.config_entries.async_update_entry(
            self.entry,
            data={**self.entry.data, CONF_NOISE_PSK: new_key_str},
        )

        if from_storage:
            _LOGGER.info(
                "Set encryption key from storage on device %s (%s)",
                self.entry.data.get(CONF_DEVICE_NAME, self.host),
                self.entry.unique_id,
            )
        else:
            _LOGGER.info(
                "Generated and stored encryption key for device %s (%s)",
                self.entry.data.get(CONF_DEVICE_NAME, self.host),
                self.entry.unique_id,
            )

    @callback
    def _async_handle_logging_changed(self, _event: Event) -> None:

        self.cli.set_debug(_LOGGER.isEnabledFor(logging.DEBUG))
        if self.entry.options.get(CONF_SUBSCRIBE_LOGS) and self._log_level != (
            new_log_level := self._async_get_equivalent_log_level()
        ):
            self._async_subscribe_logs(new_log_level)

    @callback
    def _async_cleanup(self) -> None:

        assert self.entry_data.device_info is not None
        ent_reg = er.async_get(self.hass)


        if not (
            stale_entry_entity_id := ent_reg.async_get_entity_id(
                DOMAIN,
                Platform.BINARY_SENSOR,
                f"{self.entry_data.device_info.mac_address}-assist_in_progress",
            )
        ):
            return
        stale_entry = ent_reg.async_get(stale_entry_entity_id)
        assert stale_entry is not None
        ent_reg.async_remove(stale_entry_entity_id)
        issue_reg = ir.async_get(self.hass)
        if issue := issue_reg.async_get_issue(
            DOMAIN, f"assist_in_progress_deprecated_{stale_entry.id}"
        ):
            issue_reg.async_delete(DOMAIN, issue.issue_id)

    async def async_start(self) -> None:

        hass = self.hass
        entry = self.entry
        entry_data = self.entry_data

        if entry.options.get(CONF_ALLOW_SERVICE_CALLS, DEFAULT_ALLOW_SERVICE_CALLS):
            async_delete_issue(hass, DOMAIN, self.services_issue)

        reconnect_logic = ReconnectLogic(
            client=self.cli,
            on_connect=self.on_connect,
            on_disconnect=self.on_disconnect,
            zeroconf_instance=self.zeroconf_instance,
            name=entry.data.get(CONF_DEVICE_NAME, self.host),
            on_connect_error=self.on_connect_error,
        )
        self.reconnect_logic = reconnect_logic








        bus = hass.bus
        cleanups = (
            bus.async_listen(EVENT_HOMEASSISTANT_CLOSE, self.on_stop),
            bus.async_listen(EVENT_LOGGING_CHANGED, self._async_handle_logging_changed),
            reconnect_logic.stop_callback,
        )
        entry_data.cleanup_callbacks.extend(cleanups)

        infos, services = await entry_data.async_load_from_store()
        if entry.unique_id:
            await entry_data.async_update_static_infos(
                hass, entry, infos, entry.unique_id.upper()
            )
        _setup_services(hass, entry_data, services)

        if (device_info := entry_data.device_info) is not None:
            self._async_cleanup()
            if device_info.name:
                reconnect_logic.name = device_info.name
            if (
                bluetooth_mac_address := device_info.bluetooth_mac_address
            ) and entry.data.get(CONF_BLUETOOTH_MAC_ADDRESS) != bluetooth_mac_address:
                hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_BLUETOOTH_MAC_ADDRESS: bluetooth_mac_address,
                    },
                )
            if entry.unique_id is None:
                hass.config_entries.async_update_entry(
                    entry, unique_id=format_mac(device_info.mac_address)
                )

        await reconnect_logic.start()


@callback
def _async_setup_device_registry(
    hass: HomeAssistant, entry: ESPHomeConfigEntry, entry_data: RuntimeEntryData
) -> str:

    device_info = entry_data.device_info
    if TYPE_CHECKING:
        assert device_info is not None

    device_registry = dr.async_get(hass)

    valid_connections = {
        (dr.CONNECTION_NETWORK_MAC, format_mac(device_info.mac_address))
    }
    valid_identifiers = {
        (DOMAIN, f"{device_info.mac_address}_{sub_device.device_id}")
        for sub_device in device_info.devices
    }


    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):

        if (
            device.connections & valid_connections
            or device.identifiers & valid_identifiers
        ):
            continue

        device_registry.async_remove_device(device.id)

    sw_version = device_info.esphome_version
    if device_info.compilation_time:
        sw_version += f" ({device_info.compilation_time})"

    configuration_url = None
    if device_info.webserver_port > 0:
        entry_host = entry.data["host"]
        host = f"[{entry_host}]" if ":" in entry_host else entry_host
        configuration_url = f"http://{host}:{device_info.webserver_port}"
    elif (
        (dashboard := async_get_dashboard(hass))
        and dashboard.data
        and dashboard.data.get(device_info.name)
    ):
        configuration_url = f"homeassistant://app/{dashboard.addon_slug}"

    manufacturer = "espressif"
    if device_info.manufacturer:
        manufacturer = device_info.manufacturer
    model = device_info.model
    if device_info.project_name:
        project_name = device_info.project_name.split(".")
        manufacturer = project_name[0]
        model = project_name[1]
        sw_version = (
            f"{device_info.project_version} (ESPHome {device_info.esphome_version})"
        )

    suggested_area: str | None = None
    if device_info.area and device_info.area.name:

        suggested_area = device_info.area.name
    elif device_info.suggested_area:
        suggested_area = device_info.suggested_area


    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        configuration_url=configuration_url,
        connections={(dr.CONNECTION_NETWORK_MAC, device_info.mac_address)},
        name=entry_data.friendly_name or entry_data.name,
        manufacturer=manufacturer,
        model=model,
        sw_version=sw_version,
        suggested_area=suggested_area,
    )



    areas_by_id = {area.area_id: area for area in device_info.areas}

    if device_info.area:
        areas_by_id[device_info.area.area_id] = device_info.area

    for sub_device in device_info.devices:

        sub_device_suggested_area: str | None = None
        if sub_device.area_id is not None and sub_device.area_id in areas_by_id:
            sub_device_suggested_area = areas_by_id[sub_device.area_id].name

        sub_device_entry = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{device_info.mac_address}_{sub_device.device_id}")},
            name=sub_device.name or device_entry.name,
            manufacturer=manufacturer,
            model=model,
            sw_version=sw_version,
            suggested_area=sub_device_suggested_area,
        )


        device_registry.async_update_device(
            sub_device_entry.id,
            via_device_id=device_entry.id,
        )

    return device_entry.id


class ServiceMetadata(NamedTuple):


    validator: Any
    example: str
    selector: dict[str, Any]
    description: str | None = None


ARG_TYPE_METADATA = {
    UserServiceArgType.BOOL: ServiceMetadata(
        validator=cv.boolean,
        example="False",
        selector={"boolean": None},
    ),
    UserServiceArgType.INT: ServiceMetadata(
        validator=vol.Coerce(int),
        example="42",
        selector={"number": {CONF_MODE: "box"}},
    ),
    UserServiceArgType.FLOAT: ServiceMetadata(
        validator=vol.Coerce(float),
        example="12.3",
        selector={"number": {CONF_MODE: "box", "step": 1e-3}},
    ),
    UserServiceArgType.STRING: ServiceMetadata(
        validator=cv.string,
        example="Example text",
        selector={"text": None},
    ),
    UserServiceArgType.BOOL_ARRAY: ServiceMetadata(
        validator=[cv.boolean],
        description="A list of boolean values.",
        example="[True, False]",
        selector={"object": {}},
    ),
    UserServiceArgType.INT_ARRAY: ServiceMetadata(
        validator=[vol.Coerce(int)],
        description="A list of integer values.",
        example="[42, 34]",
        selector={"object": {}},
    ),
    UserServiceArgType.FLOAT_ARRAY: ServiceMetadata(
        validator=[vol.Coerce(float)],
        description="A list of floating point numbers.",
        example="[ 12.3, 34.5 ]",
        selector={"object": {}},
    ),
    UserServiceArgType.STRING_ARRAY: ServiceMetadata(
        validator=[cv.string],
        description="A list of strings.",
        example="['Example text', 'Another example']",
        selector={"object": {}},
    ),
}


async def execute_service(
    entry_data: RuntimeEntryData,
    service: UserService,
    call: ServiceCall,
    *,
    supports_response: SupportsResponseType,
) -> ServiceResponse:




    wait_for_response = supports_response != SupportsResponseType.NONE

    if not wait_for_response:

        try:
            await entry_data.client.execute_service(service, call.data)
        except APIConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_call_failed",
                translation_placeholders={
                    "call_name": service.name,
                    "device_name": entry_data.name,
                    "error": str(err),
                },
            ) from err
        else:
            return None





    need_response_data = supports_response == SupportsResponseType.ONLY or (
        supports_response == SupportsResponseType.OPTIONAL and call.return_response
    )

    try:
        response: (
            ExecuteServiceResponse | None
        ) = await entry_data.client.execute_service(
            service,
            call.data,
            return_response=need_response_data,
        )
    except APIConnectionError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="action_call_failed",
            translation_placeholders={
                "call_name": service.name,
                "device_name": entry_data.name,
                "error": str(err),
            },
        ) from err
    except TimeoutError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="action_call_timeout",
            translation_placeholders={
                "call_name": service.name,
                "device_name": entry_data.name,
            },
        ) from err

    assert response is not None

    if not response.success:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="action_call_failed",
            translation_placeholders={
                "call_name": service.name,
                "device_name": entry_data.name,
                "error": response.error_message,
            },
        )


    if need_response_data and response.response_data:
        try:
            return json_loads_object(response.response_data)
        except ValueError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_call_failed",
                translation_placeholders={
                    "call_name": service.name,
                    "device_name": entry_data.name,
                    "error": f"Invalid JSON response: {err}",
                },
            ) from err
    return None


def build_service_name(device_info: EsphomeDeviceInfo, service: UserService) -> str:

    return f"{device_info.name.replace('-', '_')}_{service.name}"





_RESPONSE_TYPE_MAPPER = EsphomeEnumMapper[SupportsResponseType, SupportsResponse](
    {
        SupportsResponseType.NONE: SupportsResponse.NONE,
        SupportsResponseType.OPTIONAL: SupportsResponse.OPTIONAL,
        SupportsResponseType.ONLY: SupportsResponse.ONLY,
        SupportsResponseType.STATUS: SupportsResponse.NONE,
    }
)


@callback
def _async_register_service(
    hass: HomeAssistant,
    entry_data: RuntimeEntryData,
    device_info: EsphomeDeviceInfo,
    service: UserService,
) -> None:

    service_name = build_service_name(device_info, service)
    schema = {}
    fields = {}

    for arg in service.args:
        if arg.type not in ARG_TYPE_METADATA:
            _LOGGER.error(
                "Can't register service %s because %s is of unknown type %s",
                service_name,
                arg.name,
                arg.type,
            )
            return
        metadata = ARG_TYPE_METADATA[arg.type]
        schema[vol.Required(arg.name)] = metadata.validator
        fields[arg.name] = {
            "name": arg.name,
            "required": True,
            "description": metadata.description,
            "example": metadata.example,
            "selector": metadata.selector,
        }


    esphome_supports_response = service.supports_response or SupportsResponseType.NONE
    ha_supports_response = _RESPONSE_TYPE_MAPPER.from_esphome(esphome_supports_response)

    hass.services.async_register(
        DOMAIN,
        service_name,
        partial(
            execute_service,
            entry_data,
            service,
            supports_response=esphome_supports_response,
        ),
        vol.Schema(schema),
        supports_response=ha_supports_response,
    )
    async_set_service_schema(
        hass,
        DOMAIN,
        service_name,
        {
            "description": (
                f"Performs the action {service.name} of the node {device_info.name}"
            ),
            "fields": fields,
        },
    )


@callback
def _setup_services(
    hass: HomeAssistant, entry_data: RuntimeEntryData, services: list[UserService]
) -> None:
    device_info = entry_data.device_info
    if device_info is None:

        return
    old_services = entry_data.services.copy()
    to_unregister: list[UserService] = []
    to_register: list[UserService] = []
    for service in services:
        if service.key in old_services:

            if (matching := old_services.pop(service.key)) != service:

                to_unregister.append(matching)
                to_register.append(service)
        else:

            to_register.append(service)

    to_unregister.extend(old_services.values())

    entry_data.services = {serv.key: serv for serv in services}

    for service in to_unregister:
        service_name = build_service_name(device_info, service)
        hass.services.async_remove(DOMAIN, service_name)

    for service in to_register:
        _async_register_service(hass, entry_data, device_info, service)


async def cleanup_instance(entry: ESPHomeConfigEntry) -> RuntimeEntryData:

    data = entry.runtime_data
    data.async_on_disconnect()
    for cleanup_callback in data.cleanup_callbacks:
        cleanup_callback()
    await data.async_cleanup()
    await data.client.disconnect()
    return data


async def async_replace_device(
    hass: HomeAssistant,
    entry_id: str,
    old_mac: str,
    new_mac: str,
) -> None:

    entry = hass.config_entries.async_get_entry(entry_id)
    assert entry is not None
    hass.config_entries.async_update_entry(entry, unique_id=new_mac)

    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        dev_reg.async_update_device(
            device.id,
            new_connections={(dr.CONNECTION_NETWORK_MAC, new_mac)},
        )

    ent_reg = er.async_get(hass)
    upper_mac = new_mac.upper()
    old_upper_mac = old_mac.upper()
    for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):

        old_unique_id = entity.unique_id.split("-")
        new_unique_id = "-".join([upper_mac, *old_unique_id[1:]])
        if entity.unique_id != new_unique_id and entity.unique_id.startswith(
            old_upper_mac
        ):
            ent_reg.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

    domain_data = DomainData.get(hass)
    store = domain_data.get_or_create_store(hass, entry)
    if data := await store.async_load():
        data["device_info"]["mac_address"] = upper_mac
        await store.async_save(data)
