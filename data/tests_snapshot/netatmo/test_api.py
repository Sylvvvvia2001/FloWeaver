

from pyatmo.const import ALL_SCOPES

from homeassistant.components import cloud
from homeassistant.components.netatmo import api
from homeassistant.components.netatmo.const import API_SCOPES_EXCLUDED_FROM_CLOUD


async def test_get_api_scopes_cloud() -> None:

    result = api.get_api_scopes(cloud.DOMAIN)

    for scope in API_SCOPES_EXCLUDED_FROM_CLOUD:
        assert scope not in result


async def test_get_api_scopes_other() -> None:

    result = api.get_api_scopes("netatmo_239846i2f0j2")

    assert sorted(ALL_SCOPES) == result
