

from homeassistant.exceptions import HomeAssistantError


class DeconzException(HomeAssistantError):
    pass


class AlreadyConfigured(DeconzException):
    pass


class AuthenticationRequired(DeconzException):
    pass


class CannotConnect(DeconzException):
    pass
