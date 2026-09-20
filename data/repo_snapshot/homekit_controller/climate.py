

from __future__ import annotations

import logging
from typing import Any, Final

from aiohomekit.model.characteristics import (
    ActivationStateValues,
    CharacteristicsTypes,
    CurrentFanStateValues,
    CurrentHeaterCoolerStateValues,
    HeatingCoolingCurrentValues,
    HeatingCoolingTargetValues,
    SwingModeValues,
    TargetHeaterCoolerStateValues,
)
from aiohomekit.model.services import Service, ServicesTypes
from aiohomekit.utils import clamp_enum_to_char
from propcache.api import cached_property

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    FAN_ON,
    SWING_OFF,
    SWING_VERTICAL,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from . import KNOWN_DEVICES
from .connection import HKDevice
from .entity import HomeKitEntity

_LOGGER = logging.getLogger(__name__)


MODE_HOMEKIT_TO_HASS = {
    HeatingCoolingTargetValues.OFF: HVACMode.OFF,
    HeatingCoolingTargetValues.HEAT: HVACMode.HEAT,
    HeatingCoolingTargetValues.COOL: HVACMode.COOL,
    HeatingCoolingTargetValues.AUTO: HVACMode.HEAT_COOL,
}

CURRENT_MODE_HOMEKIT_TO_HASS = {
    HeatingCoolingCurrentValues.IDLE: HVACAction.IDLE,
    HeatingCoolingCurrentValues.HEATING: HVACAction.HEATING,
    HeatingCoolingCurrentValues.COOLING: HVACAction.COOLING,
}

SWING_MODE_HOMEKIT_TO_HASS = {
    SwingModeValues.DISABLED: SWING_OFF,
    SwingModeValues.ENABLED: SWING_VERTICAL,
}

CURRENT_HEATER_COOLER_STATE_HOMEKIT_TO_HASS = {
    CurrentHeaterCoolerStateValues.INACTIVE: HVACAction.OFF,
    CurrentHeaterCoolerStateValues.IDLE: HVACAction.IDLE,
    CurrentHeaterCoolerStateValues.HEATING: HVACAction.HEATING,
    CurrentHeaterCoolerStateValues.COOLING: HVACAction.COOLING,
}

TARGET_HEATER_COOLER_STATE_HOMEKIT_TO_HASS = {
    TargetHeaterCoolerStateValues.AUTOMATIC: HVACMode.HEAT_COOL,
    TargetHeaterCoolerStateValues.HEAT: HVACMode.HEAT,
    TargetHeaterCoolerStateValues.COOL: HVACMode.COOL,
}



MODE_HASS_TO_HOMEKIT = {v: k for k, v in MODE_HOMEKIT_TO_HASS.items()}

TARGET_HEATER_COOLER_STATE_HASS_TO_HOMEKIT = {
    v: k for k, v in TARGET_HEATER_COOLER_STATE_HOMEKIT_TO_HASS.items()
}

SWING_MODE_HASS_TO_HOMEKIT = {v: k for k, v in SWING_MODE_HOMEKIT_TO_HASS.items()}

DEFAULT_MIN_STEP: Final = 1.0

ROTATION_SPEED_LOW = 33
ROTATION_SPEED_MEDIUM = 66
ROTATION_SPEED_HIGH = 100

HASS_FAN_MODE_TO_HOMEKIT_ROTATION = {
    FAN_LOW: ROTATION_SPEED_LOW,
    FAN_MEDIUM: ROTATION_SPEED_MEDIUM,
    FAN_HIGH: ROTATION_SPEED_HIGH,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    hkid: str = config_entry.data["AccessoryPairingID"]
    conn: HKDevice = hass.data[KNOWN_DEVICES][hkid]

    @callback
    def async_add_service(service: Service) -> bool:
        if not (entity_class := ENTITY_TYPES.get(service.type)):
            return False
        info = {"aid": service.accessory.aid, "iid": service.iid}
        entity: HomeKitEntity = entity_class(conn, info)
        conn.async_migrate_unique_id(
            entity.old_unique_id, entity.unique_id, Platform.CLIMATE
        )
        async_add_entities([entity])
        return True

    conn.add_listener(async_add_service)


class HomeKitBaseClimateEntity(HomeKitEntity, ClimateEntity):


    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    @callback
    def _async_reconfigure(self) -> None:

        self._async_clear_property_cache(("supported_features", "fan_modes"))
        super()._async_reconfigure()

    def get_characteristic_types(self) -> list[str]:

        return [
            CharacteristicsTypes.TEMPERATURE_CURRENT,
            CharacteristicsTypes.FAN_STATE_TARGET,
        ]

    @property
    def current_temperature(self) -> float | None:

        return self.service.value(CharacteristicsTypes.TEMPERATURE_CURRENT)

    @cached_property
    def fan_modes(self) -> list[str] | None:

        if self.service.has(CharacteristicsTypes.FAN_STATE_TARGET):
            return [FAN_ON, FAN_AUTO]
        return None

    @property
    def fan_mode(self) -> str | None:

        fan_mode = self.service.value(CharacteristicsTypes.FAN_STATE_TARGET)
        return FAN_AUTO if fan_mode else FAN_ON

    async def async_set_fan_mode(self, fan_mode: str) -> None:

        await self.async_put_characteristics(
            {CharacteristicsTypes.FAN_STATE_TARGET: int(fan_mode == FAN_AUTO)}
        )

    @cached_property
    def supported_features(self) -> ClimateEntityFeature:

        features = ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON

        if self.service.has(CharacteristicsTypes.FAN_STATE_TARGET):
            features |= ClimateEntityFeature.FAN_MODE

        return features


class HomeKitHeaterCoolerEntity(HomeKitBaseClimateEntity):


    @callback
    def _async_reconfigure(self) -> None:

        self._async_clear_property_cache(("hvac_modes", "swing_modes"))
        super()._async_reconfigure()

    def get_characteristic_types(self) -> list[str]:

        return [
            *super().get_characteristic_types(),
            CharacteristicsTypes.ACTIVE,
            CharacteristicsTypes.CURRENT_HEATER_COOLER_STATE,
            CharacteristicsTypes.TARGET_HEATER_COOLER_STATE,
            CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD,
            CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD,
            CharacteristicsTypes.SWING_MODE,
            CharacteristicsTypes.ROTATION_SPEED,
        ]

    def _get_rotation_speed_range(self) -> tuple[float, float]:
        rotation_speed = self.service[CharacteristicsTypes.ROTATION_SPEED]
        return round(rotation_speed.minValue or 0) + 1, round(
            rotation_speed.maxValue or 100
        )

    @cached_property
    def fan_modes(self) -> list[str]:

        return [FAN_OFF, FAN_LOW, FAN_MEDIUM, FAN_HIGH]

    @property
    def fan_mode(self) -> str | None:

        speed_range = self._get_rotation_speed_range()
        speed_percentage = ranged_value_to_percentage(
            speed_range, self.service.value(CharacteristicsTypes.ROTATION_SPEED)
        )

        if speed_percentage > ROTATION_SPEED_MEDIUM:
            return FAN_HIGH
        if speed_percentage > ROTATION_SPEED_LOW:
            return FAN_MEDIUM
        if speed_percentage > 0:
            return FAN_LOW
        return FAN_OFF

    async def async_set_fan_mode(self, fan_mode: str) -> None:

        rotation = HASS_FAN_MODE_TO_HOMEKIT_ROTATION.get(fan_mode, 0)
        speed_range = self._get_rotation_speed_range()
        speed = round(percentage_to_ranged_value(speed_range, rotation))
        await self.async_put_characteristics(
            {CharacteristicsTypes.ROTATION_SPEED: speed}
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:

        temp = kwargs.get(ATTR_TEMPERATURE)
        state = self.service.value(CharacteristicsTypes.TARGET_HEATER_COOLER_STATE)
        if state == TargetHeaterCoolerStateValues.COOL:
            await self.async_put_characteristics(
                {CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD: temp}
            )
        elif state == TargetHeaterCoolerStateValues.HEAT:
            await self.async_put_characteristics(
                {CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD: temp}
            )
        else:
            hvac_mode = TARGET_HEATER_COOLER_STATE_HOMEKIT_TO_HASS.get(state)
            _LOGGER.warning(
                (
                    "HomeKit device %s: Setting temperature in %s mode is not supported"
                    " yet; Consider raising a ticket if you have this device and want"
                    " to help us implement this feature"
                ),
                self.entity_id,
                hvac_mode,
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:

        if hvac_mode == HVACMode.OFF:
            await self.async_put_characteristics(
                {CharacteristicsTypes.ACTIVE: ActivationStateValues.INACTIVE}
            )
            return
        if hvac_mode not in {HVACMode.HEAT, HVACMode.COOL}:
            _LOGGER.warning(
                (
                    "HomeKit device %s: Setting temperature in %s mode is not supported"
                    " yet; Consider raising a ticket if you have this device and want"
                    " to help us implement this feature"
                ),
                self.entity_id,
                hvac_mode,
            )
        await self.async_put_characteristics(
            {
                CharacteristicsTypes.ACTIVE: ActivationStateValues.ACTIVE,
                CharacteristicsTypes.TARGET_HEATER_COOLER_STATE: TARGET_HEATER_COOLER_STATE_HASS_TO_HOMEKIT[
                    hvac_mode
                ],
            }
        )

    @property
    def target_temperature(self) -> float | None:

        state = self.service.value(CharacteristicsTypes.TARGET_HEATER_COOLER_STATE)
        if state == TargetHeaterCoolerStateValues.COOL:
            return self.service.value(
                CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
            )
        if state == TargetHeaterCoolerStateValues.HEAT:
            return self.service.value(
                CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD
            )
        return None

    @property
    def target_temperature_step(self) -> float:

        state = self.service.value(CharacteristicsTypes.TARGET_HEATER_COOLER_STATE)
        if state == TargetHeaterCoolerStateValues.COOL and self.service.has(
            CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
        ):
            return (
                self.service[CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD].minStep
                or DEFAULT_MIN_STEP
            )
        if state == TargetHeaterCoolerStateValues.HEAT and self.service.has(
            CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD
        ):
            return (
                self.service[CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD].minStep
                or DEFAULT_MIN_STEP
            )
        return DEFAULT_MIN_STEP

    @property
    def min_temp(self) -> float:

        state = self.service.value(CharacteristicsTypes.TARGET_HEATER_COOLER_STATE)
        if state == TargetHeaterCoolerStateValues.COOL and self.service.has(
            CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
        ):
            return (
                self.service[
                    CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
                ].minValue
                or DEFAULT_MIN_TEMP
            )
        if state == TargetHeaterCoolerStateValues.HEAT and self.service.has(
            CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD
        ):
            return (
                self.service[
                    CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD
                ].minValue
                or DEFAULT_MIN_TEMP
            )
        return super().min_temp

    @property
    def max_temp(self) -> float:

        state = self.service.value(CharacteristicsTypes.TARGET_HEATER_COOLER_STATE)
        if state == TargetHeaterCoolerStateValues.COOL and self.service.has(
            CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
        ):
            return (
                self.service[
                    CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
                ].maxValue
                or DEFAULT_MAX_TEMP
            )
        if state == TargetHeaterCoolerStateValues.HEAT and self.service.has(
            CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD
        ):
            return (
                self.service[
                    CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD
                ].maxValue
                or DEFAULT_MAX_TEMP
            )
        return super().max_temp

    @property
    def hvac_action(self) -> HVACAction | None:




        if (
            self.service.value(CharacteristicsTypes.ACTIVE)
            == ActivationStateValues.INACTIVE
        ):
            return HVACAction.OFF
        value = self.service.value(CharacteristicsTypes.CURRENT_HEATER_COOLER_STATE)
        return CURRENT_HEATER_COOLER_STATE_HOMEKIT_TO_HASS.get(value)

    @property
    def hvac_mode(self) -> HVACMode:





        if (
            self.service.value(CharacteristicsTypes.ACTIVE)
            == ActivationStateValues.INACTIVE
        ):
            return HVACMode.OFF
        value = self.service.value(CharacteristicsTypes.TARGET_HEATER_COOLER_STATE)
        return TARGET_HEATER_COOLER_STATE_HOMEKIT_TO_HASS[value]

    @cached_property
    def hvac_modes(self) -> list[HVACMode]:

        valid_values = clamp_enum_to_char(
            TargetHeaterCoolerStateValues,
            self.service[CharacteristicsTypes.TARGET_HEATER_COOLER_STATE],
        )
        modes = [
            TARGET_HEATER_COOLER_STATE_HOMEKIT_TO_HASS[mode] for mode in valid_values
        ]
        modes.append(HVACMode.OFF)
        return modes

    @property
    def swing_mode(self) -> str:




        value = self.service.value(CharacteristicsTypes.SWING_MODE)
        return SWING_MODE_HOMEKIT_TO_HASS[value]

    @cached_property
    def swing_modes(self) -> list[str]:




        valid_values = clamp_enum_to_char(
            SwingModeValues,
            self.service[CharacteristicsTypes.SWING_MODE],
        )
        return [SWING_MODE_HOMEKIT_TO_HASS[mode] for mode in valid_values]

    async def async_set_swing_mode(self, swing_mode: str) -> None:

        await self.async_put_characteristics(
            {CharacteristicsTypes.SWING_MODE: SWING_MODE_HASS_TO_HOMEKIT[swing_mode]}
        )

    @cached_property
    def supported_features(self) -> ClimateEntityFeature:

        features = super().supported_features

        if self.service.has(CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        if self.service.has(CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        if self.service.has(CharacteristicsTypes.SWING_MODE):
            features |= ClimateEntityFeature.SWING_MODE

        if self.service.has(CharacteristicsTypes.ROTATION_SPEED):
            features |= ClimateEntityFeature.FAN_MODE

        return features


class HomeKitClimateEntity(HomeKitBaseClimateEntity):


    @callback
    def _async_reconfigure(self) -> None:

        self._async_clear_property_cache(("hvac_modes",))
        super()._async_reconfigure()

    def get_characteristic_types(self) -> list[str]:

        return [
            *super().get_characteristic_types(),
            CharacteristicsTypes.HEATING_COOLING_CURRENT,
            CharacteristicsTypes.HEATING_COOLING_TARGET,
            CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD,
            CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD,
            CharacteristicsTypes.TEMPERATURE_TARGET,
            CharacteristicsTypes.RELATIVE_HUMIDITY_CURRENT,
            CharacteristicsTypes.RELATIVE_HUMIDITY_TARGET,
            CharacteristicsTypes.FAN_STATE_CURRENT,
        ]

    async def async_set_temperature(self, **kwargs: Any) -> None:

        chars: dict[str, Any] = {}

        value = self.service.value(CharacteristicsTypes.HEATING_COOLING_TARGET)
        mode = MODE_HOMEKIT_TO_HASS[value]

        if kwargs.get(ATTR_HVAC_MODE, mode) != mode:
            mode = kwargs[ATTR_HVAC_MODE]
            chars[CharacteristicsTypes.HEATING_COOLING_TARGET] = MODE_HASS_TO_HOMEKIT[
                mode
            ]

        temp = kwargs.get(ATTR_TEMPERATURE)
        heat_temp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        cool_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        if (
            (mode == HVACMode.HEAT_COOL)
            and (
                ClimateEntityFeature.TARGET_TEMPERATURE_RANGE in self.supported_features
            )
            and heat_temp
            and cool_temp
        ):
            if temp is None:
                temp = (cool_temp + heat_temp) / 2
            chars.update(
                {
                    CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD: heat_temp,
                    CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD: cool_temp,
                    CharacteristicsTypes.TEMPERATURE_TARGET: temp,
                }
            )
        else:
            chars[CharacteristicsTypes.TEMPERATURE_TARGET] = temp

        await self.async_put_characteristics(chars)

    async def async_set_humidity(self, humidity: int) -> None:

        await self.async_put_characteristics(
            {CharacteristicsTypes.RELATIVE_HUMIDITY_TARGET: humidity}
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:

        await self.async_put_characteristics(
            {
                CharacteristicsTypes.HEATING_COOLING_TARGET: MODE_HASS_TO_HOMEKIT[
                    hvac_mode
                ],
            }
        )

    @property
    def target_temperature(self) -> float | None:

        value = self.service.value(CharacteristicsTypes.HEATING_COOLING_TARGET)
        if (MODE_HOMEKIT_TO_HASS.get(value) in {HVACMode.HEAT, HVACMode.COOL}) or (
            (MODE_HOMEKIT_TO_HASS.get(value) == HVACMode.HEAT_COOL)
            and ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            not in self.supported_features
        ):
            return self.service.value(CharacteristicsTypes.TEMPERATURE_TARGET)
        return None

    @property
    def target_temperature_high(self) -> float | None:

        value = self.service.value(CharacteristicsTypes.HEATING_COOLING_TARGET)
        if (MODE_HOMEKIT_TO_HASS.get(value) == HVACMode.HEAT_COOL) and (
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE in self.supported_features
        ):
            return self.service.value(
                CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
            )
        return None

    @property
    def target_temperature_low(self) -> float | None:

        value = self.service.value(CharacteristicsTypes.HEATING_COOLING_TARGET)
        if (MODE_HOMEKIT_TO_HASS.get(value) == HVACMode.HEAT_COOL) and (
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE in self.supported_features
        ):
            return self.service.value(
                CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD
            )
        return None

    @property
    def min_temp(self) -> float:

        value = self.service.value(CharacteristicsTypes.HEATING_COOLING_TARGET)
        if (MODE_HOMEKIT_TO_HASS.get(value) == HVACMode.HEAT_COOL) and (
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE in self.supported_features
        ):
            min_temp = self.service[
                CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD
            ].minValue
            if min_temp is not None:
                return min_temp
        elif MODE_HOMEKIT_TO_HASS.get(value) in {
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.HEAT_COOL,
        }:
            min_temp = self.service[CharacteristicsTypes.TEMPERATURE_TARGET].minValue
            if min_temp is not None:
                return min_temp
        return super().min_temp

    @property
    def max_temp(self) -> float:

        value = self.service.value(CharacteristicsTypes.HEATING_COOLING_TARGET)
        if (MODE_HOMEKIT_TO_HASS.get(value) == HVACMode.HEAT_COOL) and (
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE in self.supported_features
        ):
            max_temp = self.service[
                CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
            ].maxValue
            if max_temp is not None:
                return max_temp
        elif MODE_HOMEKIT_TO_HASS.get(value) in {
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.HEAT_COOL,
        }:
            max_temp = self.service[CharacteristicsTypes.TEMPERATURE_TARGET].maxValue
            if max_temp is not None:
                return max_temp
        return super().max_temp

    @property
    def current_humidity(self) -> int:

        return self.service.value(CharacteristicsTypes.RELATIVE_HUMIDITY_CURRENT)

    @property
    def target_humidity(self) -> int:

        return self.service.value(CharacteristicsTypes.RELATIVE_HUMIDITY_TARGET)

    @property
    def min_humidity(self) -> float:

        min_humidity = self.service[
            CharacteristicsTypes.RELATIVE_HUMIDITY_TARGET
        ].minValue
        if min_humidity is not None:
            return int(min_humidity)
        return super().min_humidity

    @property
    def max_humidity(self) -> float:

        max_humidity = self.service[
            CharacteristicsTypes.RELATIVE_HUMIDITY_TARGET
        ].maxValue
        if max_humidity is not None:
            return int(max_humidity)
        return super().max_humidity

    @property
    def hvac_action(self) -> HVACAction | None:





        target = self.service.value(CharacteristicsTypes.HEATING_COOLING_TARGET)
        value = self.service.value(CharacteristicsTypes.HEATING_COOLING_CURRENT)
        current_hass_value = CURRENT_MODE_HOMEKIT_TO_HASS.get(value)



        if (
            current_hass_value == HVACAction.IDLE
            and self.service.has(CharacteristicsTypes.FAN_STATE_CURRENT)
            and self.service.value(CharacteristicsTypes.FAN_STATE_CURRENT)
            == CurrentFanStateValues.ACTIVE
        ):
            return HVACAction.FAN




        if target == HeatingCoolingTargetValues.OFF:
            return HVACAction.IDLE

        return current_hass_value

    @property
    def hvac_mode(self) -> HVACMode:





        value = self.service.value(CharacteristicsTypes.HEATING_COOLING_TARGET)
        return MODE_HOMEKIT_TO_HASS[value]

    @cached_property
    def hvac_modes(self) -> list[HVACMode]:

        valid_values = clamp_enum_to_char(
            HeatingCoolingTargetValues,
            self.service[CharacteristicsTypes.HEATING_COOLING_TARGET],
        )
        return [MODE_HOMEKIT_TO_HASS[mode] for mode in valid_values]

    @cached_property
    def supported_features(self) -> ClimateEntityFeature:

        features = super().supported_features

        if self.service.has(CharacteristicsTypes.TEMPERATURE_TARGET):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        if self.service.has(
            CharacteristicsTypes.TEMPERATURE_COOLING_THRESHOLD
        ) and self.service.has(CharacteristicsTypes.TEMPERATURE_HEATING_THRESHOLD):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

        if self.service.has(CharacteristicsTypes.RELATIVE_HUMIDITY_TARGET):
            features |= ClimateEntityFeature.TARGET_HUMIDITY

        return features


ENTITY_TYPES = {
    ServicesTypes.HEATER_COOLER: HomeKitHeaterCoolerEntity,
    ServicesTypes.THERMOSTAT: HomeKitClimateEntity,
}
