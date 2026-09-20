

from dataclasses import dataclass

from bleak.backends.device import BLEDevice
from pysnooz.device import SnoozDevice

from homeassistant.config_entries import ConfigEntry

type SnoozConfigEntry = ConfigEntry[SnoozConfigurationData]


@dataclass
class SnoozConfigurationData:


    ble_device: BLEDevice
    device: SnoozDevice
    title: str
