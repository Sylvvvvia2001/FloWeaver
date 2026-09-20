

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from tuya_device_handlers.device_wrapper.base import DeviceWrapper
from tuya_device_handlers.device_wrapper.climate import (
    DefaultHVACModeWrapper,
    DefaultPresetModeWrapper,
    SwingModeCompositeWrapper,
)
from tuya_device_handlers.device_wrapper.common import (
    DPCodeBooleanWrapper,
    DPCodeEnumWrapper,
    DPCodeIntegerWrapper,
)
from tuya_device_handlers.device_wrapper.extended import DPCodeRoundedIntegerWrapper
from tuya_device_handlers.helpers.homeassistant import (
    TuyaClimateHVACMode,
    TuyaClimateSwingMode,
)
from tuya_sharing import CustomerDevice, Manager

from homeassistant.components.climate import (
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_ON,
    SWING_VERTICAL,
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TuyaConfigEntry
from .const import (
    CELSIUS_ALIASES,
    FAHRENHEIT_ALIASES,
    TUYA_DISCOVERY_NEW,
    DeviceCategory,
    DPCode,
)
from .entity import TuyaEntity

_TUYA_TO_HA_HVACMODE_MAPPINGS = {
    TuyaClimateHVACMode.OFF: HVACMode.OFF,
    TuyaClimateHVACMode.HEAT: HVACMode.HEAT,
    TuyaClimateHVACMode.COOL: HVACMode.COOL,
    TuyaClimateHVACMode.FAN_ONLY: HVACMode.FAN_ONLY,
    TuyaClimateHVACMode.DRY: HVACMode.DRY,
    TuyaClimateHVACMode.HEAT_COOL: HVACMode.HEAT_COOL,
    TuyaClimateHVACMode.AUTO: HVACMode.AUTO,
}
_HA_TO_TUYA_HVACMODE_MAPPINGS = {v: k for k, v in _TUYA_TO_HA_HVACMODE_MAPPINGS.items()}

_TUYA_TO_HA_SWING_MAPPINGS = {
    TuyaClimateSwingMode.BOTH: SWING_BOTH,
    TuyaClimateSwingMode.HORIZONTAL: SWING_HORIZONTAL,
    TuyaClimateSwingMode.OFF: SWING_OFF,
    TuyaClimateSwingMode.ON: SWING_ON,
    TuyaClimateSwingMode.VERTICAL: SWING_VERTICAL,
}
_HA_TO_TUYA_SWING_MAPPINGS = {v: k for k, v in _TUYA_TO_HA_SWING_MAPPINGS.items()}


@dataclass(frozen=True, kw_only=True)
class TuyaClimateEntityDescription(ClimateEntityDescription):


    switch_only_hvac_mode: HVACMode


CLIMATE_DESCRIPTIONS: dict[DeviceCategory, TuyaClimateEntityDescription] = {
    DeviceCategory.DBL: TuyaClimateEntityDescription(
        key="dbl",
        switch_only_hvac_mode=HVACMode.HEAT,
    ),
    DeviceCategory.KT: TuyaClimateEntityDescription(
        key="kt",
        switch_only_hvac_mode=HVACMode.COOL,
    ),
    DeviceCategory.QN: TuyaClimateEntityDescription(
        key="qn",
        switch_only_hvac_mode=HVACMode.HEAT,
    ),
    DeviceCategory.RS: TuyaClimateEntityDescription(
        key="rs",
        switch_only_hvac_mode=HVACMode.HEAT,
    ),
    DeviceCategory.WK: TuyaClimateEntityDescription(
        key="wk",
        switch_only_hvac_mode=HVACMode.HEAT_COOL,
    ),
    DeviceCategory.WKF: TuyaClimateEntityDescription(
        key="wkf",
        switch_only_hvac_mode=HVACMode.HEAT,
    ),
}


def _get_temperature_wrapper(
    wrappers: list[DPCodeIntegerWrapper | None], aliases: set[str]
) -> DPCodeIntegerWrapper | None:

    return next(
        (
            wrapper
            for wrapper in wrappers
            if wrapper is not None
            and (unit := wrapper.type_information.unit)
            and unit.lower() in aliases
        ),
        None,
    )


def _get_temperature_wrappers(
    device: CustomerDevice, system_temperature_unit: UnitOfTemperature
) -> tuple[DPCodeIntegerWrapper | None, DPCodeIntegerWrapper | None, UnitOfTemperature]:


    temp_current = DPCodeIntegerWrapper.find_dpcode(
        device, (DPCode.TEMP_CURRENT, DPCode.UPPER_TEMP)
    )
    temp_current_f = DPCodeIntegerWrapper.find_dpcode(
        device, (DPCode.TEMP_CURRENT_F, DPCode.UPPER_TEMP_F)
    )
    temp_set = DPCodeIntegerWrapper.find_dpcode(
        device, DPCode.TEMP_SET, prefer_function=True
    )
    temp_set_f = DPCodeIntegerWrapper.find_dpcode(
        device, DPCode.TEMP_SET_F, prefer_function=True
    )


    if (
        temp_unit_convert := DPCodeEnumWrapper.find_dpcode(
            device, DPCode.TEMP_UNIT_CONVERT
        )
    ) is not None:
        for wrapper in (temp_current, temp_current_f, temp_set, temp_set_f):
            if wrapper is not None and not wrapper.type_information.unit:
                wrapper.type_information.unit = temp_unit_convert.read_device_status(
                    device
                )



    current_celsius = _get_temperature_wrapper(
        [temp_current, temp_current_f], CELSIUS_ALIASES
    )
    current_fahrenheit = _get_temperature_wrapper(
        [temp_current_f, temp_current], FAHRENHEIT_ALIASES
    )
    set_celsius = _get_temperature_wrapper([temp_set, temp_set_f], CELSIUS_ALIASES)
    set_fahrenheit = _get_temperature_wrapper(
        [temp_set_f, temp_set], FAHRENHEIT_ALIASES
    )


    if system_temperature_unit == UnitOfTemperature.FAHRENHEIT:
        if (
            (current_fahrenheit and set_fahrenheit)
            or (current_fahrenheit and not set_celsius)
            or (set_fahrenheit and not current_celsius)
        ):
            return current_fahrenheit, set_fahrenheit, UnitOfTemperature.FAHRENHEIT
    if (
        (current_celsius and set_celsius)
        or (current_celsius and not set_fahrenheit)
        or (set_celsius and not current_fahrenheit)
    ):
        return current_celsius, set_celsius, UnitOfTemperature.CELSIUS



    if system_temperature_unit == UnitOfTemperature.FAHRENHEIT:
        return (
            temp_current_f or temp_current,
            temp_set_f or temp_set,
            UnitOfTemperature.FAHRENHEIT,
        )

    return (
        temp_current or temp_current_f,
        temp_set or temp_set_f,
        UnitOfTemperature.CELSIUS,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:

    manager = entry.runtime_data.manager

    @callback
    def async_discover_device(device_ids: list[str]) -> None:

        entities: list[TuyaClimateEntity] = []
        for device_id in device_ids:
            device = manager.device_map[device_id]
            if device and device.category in CLIMATE_DESCRIPTIONS:
                temperature_wrappers = _get_temperature_wrappers(
                    device, hass.config.units.temperature_unit
                )
                entities.append(
                    TuyaClimateEntity(
                        device,
                        manager,
                        CLIMATE_DESCRIPTIONS[device.category],
                        current_humidity_wrapper=DPCodeRoundedIntegerWrapper.find_dpcode(
                            device, DPCode.HUMIDITY_CURRENT
                        ),
                        current_temperature_wrapper=temperature_wrappers[0],
                        fan_mode_wrapper=DPCodeEnumWrapper.find_dpcode(
                            device,
                            (DPCode.FAN_SPEED_ENUM, DPCode.LEVEL, DPCode.WINDSPEED),
                            prefer_function=True,
                        ),
                        hvac_mode_wrapper=DefaultHVACModeWrapper.find_dpcode(
                            device, DPCode.MODE, prefer_function=True
                        ),
                        preset_wrapper=DefaultPresetModeWrapper.find_dpcode(
                            device, DPCode.MODE, prefer_function=True
                        ),
                        set_temperature_wrapper=temperature_wrappers[1],
                        swing_wrapper=SwingModeCompositeWrapper.find_dpcode(device),
                        switch_wrapper=DPCodeBooleanWrapper.find_dpcode(
                            device, DPCode.SWITCH, prefer_function=True
                        ),
                        target_humidity_wrapper=DPCodeRoundedIntegerWrapper.find_dpcode(
                            device, DPCode.HUMIDITY_SET, prefer_function=True
                        ),
                        temperature_unit=temperature_wrappers[2],
                    )
                )
        async_add_entities(entities)

    async_discover_device([*manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, TUYA_DISCOVERY_NEW, async_discover_device)
    )


class TuyaClimateEntity(TuyaEntity, ClimateEntity):


    entity_description: TuyaClimateEntityDescription
    _attr_name = None

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: TuyaClimateEntityDescription,
        *,
        current_humidity_wrapper: DeviceWrapper[int] | None,
        current_temperature_wrapper: DeviceWrapper[float] | None,
        fan_mode_wrapper: DeviceWrapper[str] | None,
        hvac_mode_wrapper: DeviceWrapper[TuyaClimateHVACMode] | None,
        preset_wrapper: DeviceWrapper[str] | None,
        set_temperature_wrapper: DeviceWrapper[float] | None,
        swing_wrapper: DeviceWrapper[TuyaClimateSwingMode] | None,
        switch_wrapper: DeviceWrapper[bool] | None,
        target_humidity_wrapper: DeviceWrapper[int] | None,
        temperature_unit: UnitOfTemperature,
    ) -> None:

        self._attr_target_temperature_step = 1.0
        self.entity_description = description

        super().__init__(device, device_manager)
        self._current_humidity_wrapper = current_humidity_wrapper
        self._current_temperature = current_temperature_wrapper
        self._fan_mode_wrapper = fan_mode_wrapper
        self._hvac_mode_wrapper = hvac_mode_wrapper
        self._preset_wrapper = preset_wrapper
        self._set_temperature = set_temperature_wrapper
        self._swing_wrapper = swing_wrapper
        self._switch_wrapper = switch_wrapper
        self._target_humidity_wrapper = target_humidity_wrapper
        self._attr_temperature_unit = temperature_unit



        if set_temperature_wrapper:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            self._attr_max_temp = set_temperature_wrapper.max_value
            self._attr_min_temp = set_temperature_wrapper.min_value
            self._attr_target_temperature_step = set_temperature_wrapper.value_step


        self._attr_hvac_modes = []
        if hvac_mode_wrapper:
            self._attr_hvac_modes = [HVACMode.OFF]
            for tuya_mode in cast(list[TuyaClimateHVACMode], hvac_mode_wrapper.options):
                if (
                    ha_mode := _TUYA_TO_HA_HVACMODE_MAPPINGS.get(tuya_mode)
                ) and ha_mode != HVACMode.OFF:

                    self._attr_hvac_modes.append(ha_mode)

        elif switch_wrapper:
            self._attr_hvac_modes = [
                HVACMode.OFF,
                description.switch_only_hvac_mode,
            ]


        if preset_wrapper and preset_wrapper.options:
            self._attr_hvac_modes.append(description.switch_only_hvac_mode)
            self._attr_preset_modes = preset_wrapper.options
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE


        if target_humidity_wrapper:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_HUMIDITY
            self._attr_min_humidity = round(target_humidity_wrapper.min_value)
            self._attr_max_humidity = round(target_humidity_wrapper.max_value)


        if fan_mode_wrapper:
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
            self._attr_fan_modes = fan_mode_wrapper.options


        if swing_wrapper:
            self._attr_supported_features |= ClimateEntityFeature.SWING_MODE
            self._attr_swing_modes = [
                ha_swing_mode
                for tuya_swing_mode in cast(
                    list[TuyaClimateSwingMode], swing_wrapper.options
                )
                if (ha_swing_mode := _TUYA_TO_HA_SWING_MAPPINGS.get(tuya_swing_mode))
            ]

        if switch_wrapper:
            self._attr_supported_features |= (
                ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:

        commands = []
        if self._switch_wrapper:
            commands.extend(
                self._switch_wrapper.get_update_commands(
                    self.device, hvac_mode != HVACMode.OFF
                )
            )
        if (
            self._hvac_mode_wrapper
            and (tuya_mode := _HA_TO_TUYA_HVACMODE_MAPPINGS.get(hvac_mode))
            and tuya_mode in self._hvac_mode_wrapper.options
        ):
            commands.extend(
                self._hvac_mode_wrapper.get_update_commands(self.device, tuya_mode)
            )
        await self._async_send_commands(commands)

    async def async_set_preset_mode(self, preset_mode: str) -> None:

        await self._async_send_wrapper_updates(self._preset_wrapper, preset_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:

        await self._async_send_wrapper_updates(self._fan_mode_wrapper, fan_mode)

    async def async_set_humidity(self, humidity: int) -> None:

        await self._async_send_wrapper_updates(self._target_humidity_wrapper, humidity)

    async def async_set_swing_mode(self, swing_mode: str) -> None:

        if tuya_mode := _HA_TO_TUYA_SWING_MAPPINGS.get(swing_mode):
            await self._async_send_wrapper_updates(self._swing_wrapper, tuya_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:

        await self._async_send_wrapper_updates(
            self._set_temperature, kwargs[ATTR_TEMPERATURE]
        )

    @property
    def current_temperature(self) -> float | None:

        return self._read_wrapper(self._current_temperature)

    @property
    def current_humidity(self) -> int | None:

        return self._read_wrapper(self._current_humidity_wrapper)

    @property
    def target_temperature(self) -> float | None:

        return self._read_wrapper(self._set_temperature)

    @property
    def target_humidity(self) -> int | None:

        return self._read_wrapper(self._target_humidity_wrapper)

    @property
    def hvac_mode(self) -> HVACMode | None:


        switch_status: bool | None
        if (switch_status := self._read_wrapper(self._switch_wrapper)) is False:
            return HVACMode.OFF


        if self._hvac_mode_wrapper is None:
            if switch_status is True:
                return self.entity_description.switch_only_hvac_mode
            return None


        tuya_mode = self._read_wrapper(self._hvac_mode_wrapper)
        return _TUYA_TO_HA_HVACMODE_MAPPINGS.get(tuya_mode) if tuya_mode else None

    @property
    def preset_mode(self) -> str | None:

        return self._read_wrapper(self._preset_wrapper)

    @property
    def fan_mode(self) -> str | None:

        return self._read_wrapper(self._fan_mode_wrapper)

    @property
    def swing_mode(self) -> str | None:

        tuya_value = self._read_wrapper(self._swing_wrapper)
        return _TUYA_TO_HA_SWING_MAPPINGS.get(tuya_value) if tuya_value else None

    async def async_turn_on(self) -> None:

        await self._async_send_wrapper_updates(self._switch_wrapper, True)

    async def async_turn_off(self) -> None:

        await self._async_send_wrapper_updates(self._switch_wrapper, False)
