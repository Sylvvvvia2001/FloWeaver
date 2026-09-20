

from enum import StrEnum

from aioesphomeapi import APIIntEnum

from homeassistant.components.esphome.enum_mapper import EsphomeEnumMapper


class MockEnum(APIIntEnum):


    ESPHOME_FOO = 1
    ESPHOME_BAR = 2


class MockStrEnum(StrEnum):


    HA_FOO = "foo"
    HA_BAR = "bar"


MOCK_MAPPING: EsphomeEnumMapper[MockEnum, MockStrEnum] = EsphomeEnumMapper(
    {
        MockEnum.ESPHOME_FOO: MockStrEnum.HA_FOO,
        MockEnum.ESPHOME_BAR: MockStrEnum.HA_BAR,
    }
)


async def test_map_esphome_to_ha() -> None:


    assert MOCK_MAPPING.from_esphome(MockEnum.ESPHOME_FOO) == MockStrEnum.HA_FOO
    assert MOCK_MAPPING.from_esphome(MockEnum.ESPHOME_BAR) == MockStrEnum.HA_BAR


async def test_map_ha_to_esphome() -> None:


    assert MOCK_MAPPING.from_hass(MockStrEnum.HA_FOO) == MockEnum.ESPHOME_FOO
    assert MOCK_MAPPING.from_hass(MockStrEnum.HA_BAR) == MockEnum.ESPHOME_BAR
