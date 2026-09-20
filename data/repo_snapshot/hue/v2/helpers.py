

from __future__ import annotations

from homeassistant.util import color as color_util


def normalize_hue_brightness(brightness: float | None) -> float | None:

    if brightness is not None:

        brightness = float((brightness / 255) * 100)

    return brightness


def normalize_hue_transition(transition: float | None) -> float | None:

    if transition is not None:

        transition = int(round(transition, 1) * 1000)

    return transition


def normalize_hue_colortemp(
    colortemp_k: int | None, min_mireds: int, max_mireds: int
) -> int | None:

    if colortemp_k is None:
        return None
    colortemp_mireds = color_util.color_temperature_kelvin_to_mired(colortemp_k)

    return min(max(colortemp_mireds, min_mireds), max_mireds)
