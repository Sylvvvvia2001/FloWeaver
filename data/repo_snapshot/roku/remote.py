

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import ATTR_NUM_REPEATS, RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RokuConfigEntry
from .entity import RokuEntity
from .helpers import roku_exception_handler

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RokuConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    async_add_entities(
        [
            RokuRemote(
                coordinator=entry.runtime_data,
            )
        ],
        True,
    )


class RokuRemote(RokuEntity, RemoteEntity):


    _attr_name = None

    @property
    def is_on(self) -> bool:

        return not self.coordinator.data.state.standby

    @roku_exception_handler()
    async def async_turn_on(self, **kwargs: Any) -> None:

        await self.coordinator.roku.remote("poweron")
        await self.coordinator.async_request_refresh()

    @roku_exception_handler(ignore_timeout=True)
    async def async_turn_off(self, **kwargs: Any) -> None:

        await self.coordinator.roku.remote("poweroff")
        await self.coordinator.async_request_refresh()

    @roku_exception_handler()
    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:

        num_repeats = kwargs[ATTR_NUM_REPEATS]

        for _ in range(num_repeats):
            for single_command in command:
                await self.coordinator.roku.remote(single_command)

        await self.coordinator.async_request_refresh()
