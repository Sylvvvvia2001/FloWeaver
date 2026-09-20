

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class NetatmoArea:


    area_name: str
    lat_ne: float
    lon_ne: float
    lat_sw: float
    lon_sw: float
    mode: str
    show_on_map: bool
    uuid: UUID = uuid4()
