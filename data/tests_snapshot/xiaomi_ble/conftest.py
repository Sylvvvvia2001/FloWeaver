

from collections.abc import Generator
from unittest import mock

import pytest


class MockServices:


    def get_characteristic(self, key: str) -> str:

        return key


class MockBleakClient:


    services = MockServices()

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self, *args, **kwargs):

        return self

    async def __aexit__(self, *args, **kwargs):
        pass

    async def connect(self, *args, **kwargs):
        pass

    async def disconnect(self, *args, **kwargs):
        pass


class MockBleakClientBattery5(MockBleakClient):


    async def read_gatt_char(self, *args, **kwargs) -> bytes:

        return b"\x05\x001.2.3"


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth: None) -> Generator[None]:


    with mock.patch("xiaomi_ble.parser.BleakClient", MockBleakClientBattery5):
        yield
