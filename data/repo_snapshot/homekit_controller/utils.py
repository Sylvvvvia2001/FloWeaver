

from functools import lru_cache
from typing import cast

from aiohomekit import Controller

from homeassistant.components import bluetooth, zeroconf
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from .const import CONTROLLER
from .storage import async_get_entity_storage

type IidTuple = tuple[int, int | None, int | None]


def unique_id_to_iids(unique_id: str) -> IidTuple | None:






    try:
        match unique_id.split("_"):
            case (unique_id, aid, sid, cid):
                return (int(aid), int(sid), int(cid))
            case (unique_id, aid, sid):
                return (int(aid), int(sid), None)
            case (unique_id, aid):
                return (int(aid), None, None)
    except ValueError:


        pass

    return None


@lru_cache
def folded_name(name: str) -> str:

    return name.casefold().replace(" ", "")


async def async_get_controller(hass: HomeAssistant) -> Controller:

    if existing := hass.data.get(CONTROLLER):
        return cast(Controller, existing)

    async_zeroconf_instance = await zeroconf.async_get_async_instance(hass)

    char_cache = await async_get_entity_storage(hass)




    if existing := hass.data.get(CONTROLLER):
        return cast(Controller, existing)

    bleak_scanner_instance = bluetooth.async_get_scanner(hass)

    controller = Controller(
        async_zeroconf_instance=async_zeroconf_instance,
        bleak_scanner_instance=bleak_scanner_instance,
        char_cache=char_cache,
    )

    hass.data[CONTROLLER] = controller

    async def _async_stop_homekit_controller(event: Event) -> None:


        hass.data.pop(CONTROLLER, None)
        await controller.async_stop()



    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop_homekit_controller)

    await controller.async_start()

    return controller
