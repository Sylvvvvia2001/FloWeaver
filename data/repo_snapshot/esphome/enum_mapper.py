

from typing import overload

from aioesphomeapi import APIIntEnum


class EsphomeEnumMapper[_EnumT: APIIntEnum, _ValT]:


    def __init__(self, mapping: dict[_EnumT, _ValT]) -> None:


        augmented_mapping: dict[_EnumT | None, _ValT | None] = mapping
        augmented_mapping[None] = None

        self._mapping = augmented_mapping
        self._inverse: dict[_ValT, _EnumT] = {v: k for k, v in mapping.items()}

    @overload
    def from_esphome(self, value: _EnumT) -> _ValT: ...

    @overload
    def from_esphome(self, value: _EnumT | None) -> _ValT | None: ...

    def from_esphome(self, value: _EnumT | None) -> _ValT | None:

        return self._mapping[value]

    def from_hass(self, value: _ValT) -> _EnumT:

        return self._inverse[value]
