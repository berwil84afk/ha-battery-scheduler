"""Statussensoren: Betriebsmodus und aktuelle Sollwerte."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BatterySchedulerConfigEntry
from .const import MODES
from .controller import BatteryController
from .entity import BatterySchedulerEntity


@dataclass(frozen=True, kw_only=True)
class BatterySensorDescription(SensorEntityDescription):
    value_fn: Callable[[BatteryController], str | float | None]


SENSORS = (
    BatterySensorDescription(
        key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=MODES,
        value_fn=lambda c: c.mode,
    ),
    BatterySensorDescription(
        key="charge_setpoint",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda c: c.charge_setpoint,
    ),
    BatterySensorDescription(
        key="discharge_setpoint",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda c: c.discharge_setpoint,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BatterySchedulerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(BatterySensor(entry, desc) for desc in SENSORS)


class BatterySensor(BatterySchedulerEntity, SensorEntity):
    entity_description: BatterySensorDescription

    def __init__(
        self, entry: BatterySchedulerConfigEntry, description: BatterySensorDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | float | None:
        return self.entity_description.value_fn(self.controller)
