

from homeassistant.exceptions import HomeAssistantError


class HueException(HomeAssistantError):
    pass


class CannotConnect(HueException):
    pass


class AuthenticationRequired(HueException):
    pass
