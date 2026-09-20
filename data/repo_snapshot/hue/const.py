

from aiohue.v2.models.button import ButtonEvent
from aiohue.v2.models.relative_rotary import (
    RelativeRotaryAction,
    RelativeRotaryDirection,
)

DOMAIN = "hue"

CONF_IGNORE_AVAILABILITY = "ignore_availability"

CONF_SUBTYPE = "subtype"

ATTR_HUE_EVENT = "hue_event"
SERVICE_HUE_ACTIVATE_SCENE = "hue_activate_scene"
ATTR_GROUP_NAME = "group_name"
ATTR_SCENE_NAME = "scene_name"
ATTR_TRANSITION = "transition"
ATTR_DYNAMIC = "dynamic"




GROUP_TYPE_LIGHT_GROUP = "LightGroup"
GROUP_TYPE_ROOM = "Room"
GROUP_TYPE_LUMINAIRE = "Luminaire"
GROUP_TYPE_LIGHT_SOURCE = "LightSource"
GROUP_TYPE_ZONE = "Zone"
GROUP_TYPE_ENTERTAINMENT = "Entertainment"

CONF_ALLOW_HUE_GROUPS = "allow_hue_groups"
DEFAULT_ALLOW_HUE_GROUPS = False

CONF_ALLOW_UNREACHABLE = "allow_unreachable"
DEFAULT_ALLOW_UNREACHABLE = False



REQUEST_REFRESH_DELAY = 0.3




DEFAULT_BUTTON_EVENT_TYPES = (

    ButtonEvent.INITIAL_PRESS,
    ButtonEvent.REPEAT,
    ButtonEvent.SHORT_RELEASE,
    ButtonEvent.LONG_PRESS,
    ButtonEvent.LONG_RELEASE,
)

DEFAULT_ROTARY_EVENT_TYPES = (RelativeRotaryAction.START, RelativeRotaryAction.REPEAT)
DEFAULT_ROTARY_EVENT_SUBTYPES = (
    RelativeRotaryDirection.CLOCK_WISE,
    RelativeRotaryDirection.COUNTER_CLOCK_WISE,
)

DEVICE_SPECIFIC_EVENT_TYPES = {

    "Hue tap switch": (ButtonEvent.INITIAL_PRESS,),
}
