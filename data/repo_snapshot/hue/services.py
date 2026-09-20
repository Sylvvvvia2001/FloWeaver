

from __future__ import annotations

import asyncio
import logging

from aiohue import HueBridgeV1, HueBridgeV2
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import verify_domain_control

from .bridge import HueBridge, HueConfigEntry
from .const import (
    ATTR_DYNAMIC,
    ATTR_GROUP_NAME,
    ATTR_SCENE_NAME,
    ATTR_TRANSITION,
    DOMAIN,
    SERVICE_HUE_ACTIVATE_SCENE,
)

LOGGER = logging.getLogger(__name__)


@callback
def async_setup_services(hass: HomeAssistant) -> None:


    async def hue_activate_scene(call: ServiceCall, skip_reload=True) -> None:


        group_name = call.data[ATTR_GROUP_NAME]
        scene_name = call.data[ATTR_SCENE_NAME]
        transition = call.data.get(ATTR_TRANSITION)
        dynamic = call.data.get(ATTR_DYNAMIC, False)


        entries: list[HueConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
        tasks = [
            hue_activate_scene_v1(
                entry.runtime_data, group_name, scene_name, transition
            )
            if entry.runtime_data.api_version == 1
            else hue_activate_scene_v2(
                entry.runtime_data, group_name, scene_name, transition, dynamic
            )
            for entry in entries
        ]
        results = await asyncio.gather(*tasks)



        if True not in results:
            LOGGER.warning(
                "No bridge was able to activate scene %s in group %s",
                scene_name,
                group_name,
            )


    hass.services.async_register(
        DOMAIN,
        SERVICE_HUE_ACTIVATE_SCENE,
        verify_domain_control(DOMAIN)(hue_activate_scene),
        schema=vol.Schema(
            {
                vol.Required(ATTR_GROUP_NAME): cv.string,
                vol.Required(ATTR_SCENE_NAME): cv.string,
                vol.Optional(ATTR_TRANSITION): cv.positive_int,
                vol.Optional(ATTR_DYNAMIC): cv.boolean,
            }
        ),
    )


async def hue_activate_scene_v1(
    bridge: HueBridge,
    group_name: str,
    scene_name: str,
    transition: int | None = None,
    is_retry: bool = False,
) -> bool:

    api: HueBridgeV1 = bridge.api
    if api.scenes is None:
        LOGGER.warning("Hub %s does not support scenes", api.host)
        return False

    group = next(
        (group for group in api.groups.values() if group.name == group_name),
        None,
    )

    scene = next(
        (
            scene
            for scene in api.scenes.values()
            if scene.name == scene_name
            and group is not None
            and sorted(scene.lights) == sorted(group.lights)
        ),
        None,
    )

    if not is_retry and (group is None or scene is None):
        await bridge.async_request_call(api.groups.update)
        await bridge.async_request_call(api.scenes.update)
        return await hue_activate_scene_v1(
            bridge, group_name, scene_name, transition, is_retry=True
        )

    if group is None or scene is None:
        LOGGER.debug(
            "Unable to find scene %s for group %s on bridge %s",
            scene_name,
            group_name,
            bridge.host,
        )
        return False

    await bridge.async_request_call(
        group.set_action, scene=scene.id, transitiontime=transition
    )
    return True


async def hue_activate_scene_v2(
    bridge: HueBridge,
    group_name: str,
    scene_name: str,
    transition: int | None = None,
    dynamic: bool = True,
) -> bool:

    LOGGER.warning(
        (
            "Use of service_call '%s' is deprecated and will be removed "
            "in a future release. Please use scene entities instead"
        ),
        SERVICE_HUE_ACTIVATE_SCENE,
    )
    api: HueBridgeV2 = bridge.api
    for scene in api.scenes:
        if scene.metadata.name.lower() != scene_name.lower():
            continue
        group = api.scenes.get_group(scene.id)
        if group.metadata.name.lower() != group_name.lower():
            continue

        if transition:
            transition = transition * 1000
        await bridge.async_request_call(
            api.scenes.recall, scene.id, dynamic=dynamic, duration=transition
        )
        return True
    LOGGER.debug(
        "Unable to find scene %s for group %s on bridge %s",
        scene_name,
        group_name,
        bridge.host,
    )
    return False
