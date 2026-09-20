

from collections.abc import Generator
from typing import Any
from unittest import mock

import pytest


class MockServices:


    def get_characteristic(self, key: str) -> str:

        return key


class MockBleakClient:


    services = MockServices()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self, *args, **kwargs):

        return self

    async def __aexit__(self, *args, **kwargs):
        pass

    async def connect(self, *args, **kwargs):
        pass

    async def disconnect(self, *args, **kwargs):
        pass


class MockBleakClientBattery49(MockBleakClient):


    async def read_gatt_char(self, *args, **kwargs) -> bytes:

        return b"\x31\x00"


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth: None) -> Generator[None]:


    with mock.patch(
        "oralb_ble.parser.BleakClientWithServiceCache", MockBleakClientBattery49
    ):
        yield
