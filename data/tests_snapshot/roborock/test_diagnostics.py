

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    setup_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:

    result = await get_diagnostics_for_config_entry(hass, hass_client, setup_entry)

    assert isinstance(result, dict)
    assert result == snapshot(exclude=props("Nonce"))
