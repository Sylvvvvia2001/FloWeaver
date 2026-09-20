

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any

from homeassistant.core import HassJobType, HomeAssistant, callback

from . import debug_info
from .client import async_subscribe_internal
from .const import DEFAULT_QOS
from .models import MessageCallbackType


@dataclass(slots=True, kw_only=True)
class EntitySubscription:


    hass: HomeAssistant
    topic: str | None
    message_callback: MessageCallbackType
    should_subscribe: bool | None
    unsubscribe_callback: Callable[[], None] | None
    qos: int = 0
    encoding: str = "utf-8"
    entity_id: str | None
    job_type: HassJobType | None

    def resubscribe_if_necessary(
        self, hass: HomeAssistant, other: EntitySubscription | None
    ) -> None:

        if not self._should_resubscribe(other):
            if TYPE_CHECKING:
                assert other
            self.unsubscribe_callback = other.unsubscribe_callback
            return

        if other is not None and other.unsubscribe_callback is not None:
            other.unsubscribe_callback()

            debug_info.remove_subscription(self.hass, str(other.topic), other.entity_id)

        if self.topic is None:

            return


        debug_info.add_subscription(self.hass, self.topic, self.entity_id)

        self.should_subscribe = True

    @callback
    def subscribe(self) -> None:

        if not self.should_subscribe or not self.topic:
            return
        self.unsubscribe_callback = async_subscribe_internal(
            self.hass,
            self.topic,
            self.message_callback,
            self.qos,
            self.encoding,
            self.job_type,
        )

    def _should_resubscribe(self, other: EntitySubscription | None) -> bool:

        if other is None:
            return True

        return (
            self.topic,
            self.qos,
            self.encoding,
        ) != (
            other.topic,
            other.qos,
            other.encoding,
        )


@callback
def async_prepare_subscribe_topics(
    hass: HomeAssistant,
    sub_state: dict[str, EntitySubscription] | None,
    topics: dict[str, dict[str, Any]],
) -> dict[str, EntitySubscription]:












    current_subscriptions: dict[str, EntitySubscription]
    current_subscriptions = sub_state if sub_state is not None else {}
    sub_state = {}
    for key, value in topics.items():

        requested = EntitySubscription(
            topic=value.get("topic"),
            message_callback=value["msg_callback"],
            unsubscribe_callback=None,
            qos=value.get("qos", DEFAULT_QOS),
            encoding=value.get("encoding", "utf-8"),
            hass=hass,
            should_subscribe=None,
            entity_id=value.get("entity_id"),
            job_type=value.get("job_type"),
        )

        current = current_subscriptions.pop(key, None)
        requested.resubscribe_if_necessary(hass, current)
        sub_state[key] = requested


    for remaining in current_subscriptions.values():
        if remaining.unsubscribe_callback is not None:
            remaining.unsubscribe_callback()

            debug_info.remove_subscription(
                hass,
                str(remaining.topic),
                remaining.entity_id,
            )

    return sub_state


async def async_subscribe_topics(
    hass: HomeAssistant,
    sub_state: dict[str, EntitySubscription],
) -> None:

    async_subscribe_topics_internal(hass, sub_state)


@callback
def async_subscribe_topics_internal(
    hass: HomeAssistant,
    sub_state: dict[str, EntitySubscription],
) -> None:





    for sub in sub_state.values():
        sub.subscribe()


if TYPE_CHECKING:

    def async_unsubscribe_topics(
        hass: HomeAssistant, sub_state: dict[str, EntitySubscription] | None
    ) -> dict[str, EntitySubscription]:
        pass


async_unsubscribe_topics = partial(async_prepare_subscribe_topics, topics={})
