

from typing import TYPE_CHECKING

from pydeconz.utils import normalize_bridge_id
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.util.read_only_dict import ReadOnlyDict

from .const import CONF_BRIDGE_ID, DOMAIN, LOGGER
from .hub import DeconzHub
from .util import get_master_hub

if TYPE_CHECKING:
    from . import DeconzConfigEntry


DECONZ_SERVICES = "deconz_services"

SERVICE_FIELD = "field"
SERVICE_ENTITY = "entity"
SERVICE_DATA = "data"

SERVICE_CONFIGURE_DEVICE = "configure"
SERVICE_CONFIGURE_DEVICE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(SERVICE_ENTITY): cv.entity_id,
            vol.Optional(SERVICE_FIELD): cv.matches_regex("/.*"),
            vol.Required(SERVICE_DATA): dict,
            vol.Optional(CONF_BRIDGE_ID): str,
        }
    ),
    cv.has_at_least_one_key(SERVICE_ENTITY, SERVICE_FIELD),
)

SERVICE_DEVICE_REFRESH = "device_refresh"
SERVICE_REMOVE_ORPHANED_ENTRIES = "remove_orphaned_entries"
SELECT_GATEWAY_SCHEMA = vol.All(vol.Schema({vol.Optional(CONF_BRIDGE_ID): str}))

SUPPORTED_SERVICES = (
    SERVICE_CONFIGURE_DEVICE,
    SERVICE_DEVICE_REFRESH,
    SERVICE_REMOVE_ORPHANED_ENTRIES,
)

SERVICE_TO_SCHEMA = {
    SERVICE_CONFIGURE_DEVICE: SERVICE_CONFIGURE_DEVICE_SCHEMA,
    SERVICE_DEVICE_REFRESH: SELECT_GATEWAY_SCHEMA,
    SERVICE_REMOVE_ORPHANED_ENTRIES: SELECT_GATEWAY_SCHEMA,
}


@callback
def async_setup_services(hass: HomeAssistant) -> None:


    async def async_call_deconz_service(service_call: ServiceCall) -> None:

        service = service_call.service
        service_data = service_call.data

        if CONF_BRIDGE_ID in service_data:
            found_hub = False
            bridge_id = normalize_bridge_id(service_data[CONF_BRIDGE_ID])

            entry: DeconzConfigEntry
            for entry in hass.config_entries.async_loaded_entries(DOMAIN):
                possible_hub = entry.runtime_data
                if possible_hub.bridgeid == bridge_id:
                    hub = possible_hub
                    found_hub = True
                    break

            if not found_hub:
                LOGGER.error("Could not find the gateway %s", bridge_id)
                return
        else:
            try:
                hub = get_master_hub(hass)
            except ValueError:
                LOGGER.error("No master gateway available")
                return

        if service == SERVICE_CONFIGURE_DEVICE:
            await async_configure_service(hub, service_data)

        elif service == SERVICE_DEVICE_REFRESH:
            await async_refresh_devices_service(hub)

        elif service == SERVICE_REMOVE_ORPHANED_ENTRIES:
            await async_remove_orphaned_entries_service(hub)

    for service in SUPPORTED_SERVICES:
        hass.services.async_register(
            DOMAIN,
            service,
            async_call_deconz_service,
            schema=SERVICE_TO_SCHEMA[service],
        )


async def async_configure_service(hub: DeconzHub, data: ReadOnlyDict) -> None:















    field = data.get(SERVICE_FIELD, "")
    entity_id = data.get(SERVICE_ENTITY)
    data = data[SERVICE_DATA]

    if entity_id:
        try:
            field = hub.deconz_ids[entity_id] + field
        except KeyError:
            LOGGER.error("Could not find the entity %s", entity_id)
            return

    await hub.api.request("put", field, json=data)


async def async_refresh_devices_service(hub: DeconzHub) -> None:

    hub.ignore_state_updates = True
    await hub.api.refresh_state()
    hub.load_ignored_devices()
    hub.ignore_state_updates = False


async def async_remove_orphaned_entries_service(hub: DeconzHub) -> None:

    device_registry = dr.async_get(hub.hass)
    entity_registry = er.async_get(hub.hass)

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, hub.config_entry.entry_id
    )

    entities_to_be_removed = []
    devices_to_be_removed = [
        entry.id
        for entry in device_registry.devices.get_devices_for_config_entry_id(
            hub.config_entry.entry_id
        )
    ]


    hub_service = device_registry.async_get_device(
        identifiers={(DOMAIN, hub.api.config.bridge_id)}
    )
    if hub_service and hub_service.id in devices_to_be_removed:
        devices_to_be_removed.remove(hub_service.id)


    for event in hub.events:
        if event.device_id in devices_to_be_removed:
            devices_to_be_removed.remove(event.device_id)

    for entry in entity_entries:

        if entry.unique_id in hub.entities[entry.domain]:

            if entry.device_id in devices_to_be_removed:
                devices_to_be_removed.remove(entry.device_id)
            continue

        entities_to_be_removed.append(entry.entity_id)


    for entity_id in entities_to_be_removed:
        entity_registry.async_remove(entity_id)


    for device_id in devices_to_be_removed:
        if (
            len(
                er.async_entries_for_device(
                    entity_registry, device_id, include_disabled_entities=True
                )
            )
            == 0
        ):
            device_registry.async_remove_device(device_id)
