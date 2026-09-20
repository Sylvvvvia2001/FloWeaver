

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any

from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.characteristics.const import InputEventValues
from aiohomekit.model.services import Service, ServicesTypes
from aiohomekit.utils import clamp_enum_to_char
import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HassJob, HomeAssistant, callback
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, KNOWN_DEVICES, TRIGGERS

if TYPE_CHECKING:
    from .connection import HKDevice

TRIGGER_TYPES = {
    "doorbell",
    "button1",
    "button2",
    "button3",
    "button4",
    "button5",
    "button6",
    "button7",
    "button8",
    "button9",
    "button10",
}
TRIGGER_SUBTYPES = {"single_press", "double_press", "long_press"}

CONF_IID = "iid"
CONF_SUBTYPE = "subtype"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(CONF_SUBTYPE): vol.In(TRIGGER_SUBTYPES),
    }
)

HK_TO_HA_INPUT_EVENT_VALUES = {
    InputEventValues.SINGLE_PRESS: "single_press",
    InputEventValues.DOUBLE_PRESS: "double_press",
    InputEventValues.LONG_PRESS: "long_press",
}


class TriggerSource:


    def __init__(self, hass: HomeAssistant) -> None:

        self._hass = hass
        self._triggers: dict[tuple[str, str], dict[str, Any]] = {}
        self._callbacks: dict[tuple[str, str], list[Callable[[Any], None]]] = {}
        self._iid_trigger_keys: dict[int, set[tuple[str, str]]] = {}

    @callback
    def async_setup(
        self, connection: HKDevice, aid: int, triggers: list[dict[str, Any]]
    ) -> None:






        for trigger_data in triggers:
            trigger_key = (trigger_data[CONF_TYPE], trigger_data[CONF_SUBTYPE])
            self._triggers[trigger_key] = trigger_data
            iid = trigger_data["characteristic"]
            self._iid_trigger_keys.setdefault(iid, set()).add(trigger_key)
            connection.add_watchable_characteristics([(aid, iid)])

    def fire(self, iid: int, ev: dict[str, Any]) -> None:

        for trigger_key in self._iid_trigger_keys.get(iid, set()):
            for event_handler in self._callbacks.get(trigger_key, []):
                event_handler(ev)

    def async_get_triggers(self) -> Generator[tuple[str, str]]:

        yield from self._triggers

    @callback
    def async_attach_trigger(
        self,
        config: ConfigType,
        action: TriggerActionType,
        trigger_info: TriggerInfo,
    ) -> CALLBACK_TYPE:

        trigger_data = trigger_info["trigger_data"]
        type_: str = config[CONF_TYPE]
        sub_type: str = config[CONF_SUBTYPE]
        trigger_key = (type_, sub_type)
        job = HassJob(action)
        trigger_callbacks = self._callbacks.setdefault(trigger_key, [])
        hass = self._hass

        @callback
        def event_handler(ev: dict[str, Any]) -> None:
            if sub_type != HK_TO_HA_INPUT_EVENT_VALUES[ev["value"]]:
                return
            hass.async_run_hass_job(job, {"trigger": {**trigger_data, **config}})

        trigger_callbacks.append(event_handler)

        def async_remove_handler() -> None:
            trigger_callbacks.remove(event_handler)

        return async_remove_handler


def enumerate_stateless_switch(service: Service) -> list[dict[str, Any]]:




    if (
        service.has(CharacteristicsTypes.SERVICE_LABEL_INDEX)
        and len(service.linked) > 0
    ):
        return []

    char = service[CharacteristicsTypes.INPUT_EVENT]



    all_values = clamp_enum_to_char(InputEventValues, char)

    return [
        {
            "characteristic": char.iid,
            "value": event_type,
            "type": "button1",
            "subtype": HK_TO_HA_INPUT_EVENT_VALUES[event_type],
        }
        for event_type in all_values
    ]


def enumerate_stateless_switch_group(service: Service) -> list[dict[str, Any]]:

    switches = list(
        service.accessory.services.filter(
            service_type=ServicesTypes.STATELESS_PROGRAMMABLE_SWITCH,
            child_service=service,
            order_by=[CharacteristicsTypes.SERVICE_LABEL_INDEX],
        )
    )

    results: list[dict[str, Any]] = []
    for idx, switch in enumerate(switches):
        char = switch[CharacteristicsTypes.INPUT_EVENT]



        all_values = clamp_enum_to_char(InputEventValues, char)

        results.extend(
            {
                "characteristic": char.iid,
                "value": event_type,
                "type": f"button{idx + 1}",
                "subtype": HK_TO_HA_INPUT_EVENT_VALUES[event_type],
            }
            for event_type in all_values
        )
    return results


def enumerate_doorbell(service: Service) -> list[dict[str, Any]]:

    input_event = service[CharacteristicsTypes.INPUT_EVENT]



    all_values = clamp_enum_to_char(InputEventValues, input_event)

    return [
        {
            "characteristic": input_event.iid,
            "value": event_type,
            "type": "doorbell",
            "subtype": HK_TO_HA_INPUT_EVENT_VALUES[event_type],
        }
        for event_type in all_values
    ]


TRIGGER_FINDERS = {
    ServicesTypes.SERVICE_LABEL: enumerate_stateless_switch_group,
    ServicesTypes.STATELESS_PROGRAMMABLE_SWITCH: enumerate_stateless_switch,
    ServicesTypes.DOORBELL: enumerate_doorbell,
}


async def async_setup_triggers_for_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:

    hkid = config_entry.data["AccessoryPairingID"]
    conn: HKDevice = hass.data[KNOWN_DEVICES][hkid]

    @callback
    def async_add_characteristic(service: Service) -> bool:
        aid = service.accessory.aid
        service_type = service.type


        if service_type not in TRIGGER_FINDERS:
            return False





        device_id = conn.devices[aid]
        if TRIGGERS in hass.data and device_id in hass.data[TRIGGERS]:
            return False



        triggers = TRIGGER_FINDERS[service_type](service)
        if len(triggers) == 0:
            return False

        trigger = async_get_or_create_trigger_source(conn.hass, device_id)
        trigger.async_setup(conn, aid, triggers)

        return True

    conn.add_trigger_factory(async_add_characteristic)


@callback
def async_get_or_create_trigger_source(
    hass: HomeAssistant, device_id: str
) -> TriggerSource:

    trigger_sources: dict[str, TriggerSource] = hass.data.setdefault(TRIGGERS, {})
    if not (source := trigger_sources.get(device_id)):
        source = TriggerSource(hass)
        trigger_sources[device_id] = source
    return source


def async_fire_triggers(
    conn: HKDevice, events: dict[tuple[int, int], dict[str, Any]]
) -> None:

    trigger_sources: dict[str, TriggerSource] = conn.hass.data.get(TRIGGERS, {})
    if not trigger_sources:
        return
    for (aid, iid), ev in events.items():
        if aid in conn.devices:
            device_id = conn.devices[aid]
            if source := trigger_sources.get(device_id):


                if ev.get("value") is not None:
                    source.fire(iid, ev)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:


    if device_id not in hass.data.get(TRIGGERS, {}):
        return []

    device: TriggerSource = hass.data[TRIGGERS][device_id]

    return [
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: trigger,
            CONF_SUBTYPE: subtype,
        }
        for trigger, subtype in device.async_get_triggers()
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:

    device_id = config[CONF_DEVICE_ID]
    return async_get_or_create_trigger_source(hass, device_id).async_attach_trigger(
        config, action, trigger_info
    )
