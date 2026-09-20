

from __future__ import annotations

import base64

from homeassistant.components.esphome.encryption_key_storage import (
    ESPHomeEncryptionKeyStorage,
    async_get_encryption_key_storage,
)
from homeassistant.core import HomeAssistant


async def test_dynamic_encryption_key_generation_mock(hass: HomeAssistant) -> None:

    storage = await async_get_encryption_key_storage(hass)


    mac_address = "11:22:33:44:55:aa"
    test_key = base64.b64encode(b"test_key_32_bytes_long_exactly!").decode()

    await storage.async_store_key(mac_address, test_key)


    retrieved_key = await storage.async_get_key(mac_address)
    assert retrieved_key == test_key


async def test_encryption_key_storage_remove_key(hass: HomeAssistant) -> None:


    storage = ESPHomeEncryptionKeyStorage(hass)


    mac_address = "11:22:33:44:55:aa"
    test_key = "test_encryption_key_32_bytes_long"


    await storage.async_store_key(mac_address, test_key)


    retrieved_key = await storage.async_get_key(mac_address)
    assert retrieved_key == test_key


    await storage.async_remove_key(mac_address)


    retrieved_key = await storage.async_get_key(mac_address)
    assert retrieved_key is None


    non_existent_mac = "aa:bb:cc:dd:ee:ff"
    await storage.async_remove_key(non_existent_mac)


    upper_mac = "22:33:44:55:66:77"
    await storage.async_store_key(upper_mac, test_key)


    await storage.async_remove_key(upper_mac.lower())


    retrieved_key = await storage.async_get_key(upper_mac)
    assert retrieved_key is None


async def test_encryption_key_basic_storage(
    hass: HomeAssistant,
) -> None:

    storage = await async_get_encryption_key_storage(hass)
    mac_address = "11:22:33:44:55:aa"
    key = "test_encryption_key_32_bytes_long"


    await storage.async_store_key(mac_address, key)


    retrieved_key = await storage.async_get_key(mac_address)
    assert retrieved_key == key


async def test_retrieve_key_from_storage(
    hass: HomeAssistant,
) -> None:


    storage = await async_get_encryption_key_storage(hass)
    mac_address = "11:22:33:44:55:aa"
    stored_key = "test_encryption_key_32_bytes_long"


    await storage.async_store_key(mac_address, stored_key)


    retrieved_key = await storage.async_get_key(mac_address)
    assert retrieved_key == stored_key


    retrieved_key_upper = await storage.async_get_key(mac_address.upper())
    assert retrieved_key_upper == stored_key
