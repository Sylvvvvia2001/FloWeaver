

from datetime import timedelta
from unittest import mock

from aiohomekit.exceptions import AccessoryDisconnectedError, EncryptionError
from aiohomekit.model import CharacteristicsTypes, ServicesTypes
from aiohomekit.testing import FakeController, FakePairing
import pytest

from homeassistant.components.homekit_controller.connection import (
    MAX_POLL_FAILURES_TO_DECLARE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..common import Helper, setup_accessories_from_file, setup_test_accessories

from tests.common import async_fire_time_changed

LIGHT_ON = ("lightbulb", "on")


@pytest.mark.parametrize("failure_cls", [AccessoryDisconnectedError, EncryptionError])
async def test_recover_from_failure(hass: HomeAssistant, failure_cls) -> None:




    accessories = await setup_accessories_from_file(hass, "koogeek_ls1.json")
    config_entry, pairing = await setup_test_accessories(hass, accessories)

    helper = Helper(
        hass,
        "light.koogeek_ls1_20833f_light_strip",
        pairing,
        accessories[0],
        config_entry,
    )


    state = await helper.async_update(
        ServicesTypes.LIGHTBULB, {CharacteristicsTypes.ON: False}
    )


    assert state.state == "off"


    next_update = dt_util.utcnow() + timedelta(seconds=60)
    with (
        mock.patch.object(FakePairing, "get_characteristics") as get_char,
        mock.patch.object(
            FakeController,
            "async_reachable",
            return_value=False,
        ),
    ):
        get_char.side_effect = failure_cls("Disconnected")


        for _ in range(MAX_POLL_FAILURES_TO_DECLARE_UNAVAILABLE + 2):
            state = await helper.poll_and_get_state()
        assert state.state == "unavailable"

        chars = get_char.call_args[0][0]
        assert set(chars) == {(1, 8), (1, 9), (1, 10), (1, 11)}


    next_update += timedelta(seconds=60)
    async_fire_time_changed(hass, next_update)
    await hass.async_block_till_done()

    state = await helper.async_update(
        ServicesTypes.LIGHTBULB, {CharacteristicsTypes.ON: True}
    )
    assert state.state == "on"
