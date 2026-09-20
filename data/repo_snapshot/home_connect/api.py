

from typing import cast

from aiohomeconnect.client import AbstractAuth
from aiohomeconnect.const import API_ENDPOINT

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.httpx_client import get_async_client


class AsyncConfigEntryAuth(AbstractAuth):


    def __init__(
        self,
        hass: HomeAssistant,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:

        self.hass = hass
        super().__init__(get_async_client(hass), host=API_ENDPOINT)
        self.session = oauth_session

    async def async_get_access_token(self) -> str:

        await self.session.async_ensure_token_valid()

        return cast(str, self.session.token["access_token"])
