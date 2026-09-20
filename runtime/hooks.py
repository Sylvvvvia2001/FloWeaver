from __future__ import annotations

from typing import Any, Callable

from runtime.events import EventRecorder


class HAHooks:
    def __init__(self, recorder: EventRecorder):
        self.recorder = recorder

    def entry_setup(self, target: str, **params: Any) -> None:
        self.recorder.emit("HA", "ENTRY_SETUP", target, params_abst=params, phase="SETUP")

    def entry_unload(self, target: str, **params: Any) -> None:
        self.recorder.emit("HA", "ENTRY_UNLOAD", target, params_abst=params, phase="TEARDOWN")

    def state_write(self, entity_id: str, **params: Any) -> None:
        self.recorder.emit("HA", "STATE_WRITE", entity_id, params_abst=params, phase="RUNTIME")

    def coordinator_refresh(self, target: str, **params: Any) -> None:
        self.recorder.emit("HA", "COORD_REFRESH", target, params_abst=params, phase="RUNTIME")

    def subscribe(self, target: str, **params: Any) -> None:
        self.recorder.emit("HA", "SUBSCRIBE", target, params_abst=params, phase="RUNTIME")

    def unsubscribe(self, target: str, **params: Any) -> None:
        self.recorder.emit("HA", "UNSUBSCRIBE", target, params_abst=params, phase="TEARDOWN")


class BLEHooks:
    def __init__(self, recorder: EventRecorder):
        self.recorder = recorder

    def connect(self, device_id: str, **params: Any) -> None:
        self.recorder.emit("BLE", "BLE_CONNECT", device_id, params_abst=params)

    def disconnect(self, device_id: str, **params: Any) -> None:
        self.recorder.emit("BLE", "BLE_DISCONNECT", device_id, params_abst=params)

    def gatt_call(self, device_id: str, op: str, **params: Any) -> None:
        self.recorder.emit("BLE", op, device_id, params_abst=params)


class CloudHooks:
    def __init__(self, recorder: EventRecorder):
        self.recorder = recorder

    def call(self, endpoint: str, **params: Any) -> None:
        self.recorder.emit("CLOUD", "CLOUD_HTTP_CALL", endpoint, params_abst=params)

    def retry_backoff(self, endpoint: str, backoff_ms: int) -> None:
        self.recorder.emit("CLOUD", "CLOUD_BACKOFF_SLEEP", endpoint, params_abst={"backoff_ms": backoff_ms})

    def exception(self, endpoint: str, exc_type: str) -> None:
        self.recorder.emit("CLOUD", "EXCEPTION", endpoint, params_abst={"type": exc_type})


def wrap_callback(fn: Callable[..., Any], recorder: EventRecorder, op_name: str) -> Callable[..., Any]:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        recorder.emit("SYS", f"{op_name}_BEGIN", target=fn.__name__)
        try:
            return fn(*args, **kwargs)
        finally:
            recorder.emit("SYS", f"{op_name}_END", target=fn.__name__)

    return wrapped
