




from __future__ import annotations

from collections.abc import Callable, Coroutine
import logging
from typing import Any

from bleak import BleakError
from bluetooth_data_tools import monotonic_time_coarse

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.debounce import Debouncer

from . import BluetoothChange, BluetoothScanningMode, BluetoothServiceInfoBleak
from .passive_update_processor import PassiveBluetoothProcessorCoordinator

POLL_DEFAULT_COOLDOWN = 10
POLL_DEFAULT_IMMEDIATE = True


class ActiveBluetoothProcessorCoordinator[_DataT](
    PassiveBluetoothProcessorCoordinator[_DataT]
):





























    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        address: str,
        mode: BluetoothScanningMode,
        update_method: Callable[[BluetoothServiceInfoBleak], _DataT],
        needs_poll_method: Callable[[BluetoothServiceInfoBleak, float | None], bool],
        poll_method: Callable[
            [BluetoothServiceInfoBleak],
            Coroutine[Any, Any, _DataT],
        ]
        | None = None,
        poll_debouncer: Debouncer[Coroutine[Any, Any, None]] | None = None,
        connectable: bool = True,
    ) -> None:

        super().__init__(hass, logger, address, mode, update_method, connectable)

        self._needs_poll_method = needs_poll_method
        self._poll_method = poll_method
        self._last_poll: float | None = None
        self.last_poll_successful = True



        self._last_service_info: BluetoothServiceInfoBleak | None = None

        if poll_debouncer is None:
            poll_debouncer = Debouncer(
                hass,
                logger,
                cooldown=POLL_DEFAULT_COOLDOWN,
                immediate=POLL_DEFAULT_IMMEDIATE,
                function=self._async_poll,
                background=True,
            )
        else:
            poll_debouncer.function = self._async_poll

        self._debounced_poll = poll_debouncer

    def needs_poll(self, service_info: BluetoothServiceInfoBleak) -> bool:

        if self.hass.is_stopping:
            return False
        poll_age: float | None = None
        if self._last_poll:
            poll_age = service_info.time - self._last_poll
        return self._needs_poll_method(service_info, poll_age)

    async def _async_poll_data(
        self, last_service_info: BluetoothServiceInfoBleak
    ) -> _DataT:

        if self._poll_method is None:
            raise NotImplementedError("Poll method not implemented")
        return await self._poll_method(last_service_info)

    async def _async_poll(self) -> None:

        assert self._last_service_info

        try:
            update = await self._async_poll_data(self._last_service_info)
        except BleakError as exc:
            if self.last_poll_successful:
                self.logger.error(
                    "%s: Bluetooth error whilst polling: %s", self.address, str(exc)
                )
                self.last_poll_successful = False
            return
        except Exception:
            if self.last_poll_successful:
                self.logger.exception("%s: Failure while polling", self.address)
                self.last_poll_successful = False
            return
        finally:
            self._last_poll = monotonic_time_coarse()

        if not self.last_poll_successful:
            self.logger.debug("%s: Polling recovered", self.address)
            self.last_poll_successful = True

        for processor in self._processors:
            processor.async_handle_update(update)

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:

        super()._async_handle_bluetooth_event(service_info, change)

        self._last_service_info = service_info




        if self.needs_poll(service_info):
            self._debounced_poll.async_schedule_call()

    @callback
    def _async_stop(self) -> None:

        self._debounced_poll.async_cancel()
        super()._async_stop()
