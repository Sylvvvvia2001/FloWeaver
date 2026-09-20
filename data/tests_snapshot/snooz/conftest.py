

from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from . import SnoozFixture, create_mock_snooz, create_mock_snooz_config_entry


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth: None) -> None:
    pass


@pytest.fixture
async def mock_connected_snooz(hass: HomeAssistant):


    device = await create_mock_snooz()
    entry = await create_mock_snooz_config_entry(hass, device)

    return SnoozFixture(entry, device)
