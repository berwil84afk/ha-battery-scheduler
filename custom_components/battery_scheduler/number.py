"""Einstellbare Zahlenwerte: Min-/Max-Ladung, Lade-/Entladeleistung."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BatterySchedulerConfigEntry
from .const import MAX_POWER
from .entity import BatterySchedulerEntity

SOC_GAP = 5  # Mindestabstand zwischen Min- und Max-Ladung in %


@dataclass(frozen=True, kw_only=True)
class BatteryNumberDescription(NumberEntityDescription):
    """Beschreibung inkl. Name des Settings-Felds (= key)."""


NUMBERS = (
    BatteryNumberDescription(
        key="min_soc",
        native_min_value=0,
        native_max_value=100 - SOC_GAP,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    BatteryNumberDescription(
        key="max_soc",
        native_min_value=SOC_GAP,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    BatteryNumberDescription(
        key="max_charge_power",
        native_min_value=0,
        native_max_value=MAX_POWER,
        native_step=10,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    BatteryNumberDescription(
        key="max_discharge_power",
        native_min_value=0,
        native_max_value=MAX_POWER,
        native_step=10,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BatterySchedulerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(BatteryNumber(entry, desc) for desc in NUMBERS)


class BatteryNumber(BatterySchedulerEntity, RestoreNumber):
    """Zahl, deren Wert im Controller liegt und Neustarts überlebt."""

    entity_description: BatteryNumberDescription

    def __init__(
        self, entry: BatterySchedulerConfigEntry, description: BatteryNumberDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            value = min(
                max(last.native_value, self.entity_description.native_min_value),
                self.entity_description.native_max_value,
            )
            self.controller.restore_setting(self.entity_description.key, value)

    @property
    def native_value(self) -> float:
        return getattr(self.controller.settings, self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        s = self.controller.settings
        key = self.entity_description.key
        if key == "min_soc" and value > s.max_soc - SOC_GAP:
            raise ServiceValidationError(
                f"Mindestladung muss mindestens {SOC_GAP} % unter der "
                f"Maximalladung ({s.max_soc:.0f} %) liegen"
            )
        if key == "max_soc" and value < s.min_soc + SOC_GAP:
            raise ServiceValidationError(
                f"Maximalladung muss mindestens {SOC_GAP} % über der "
                f"Mindestladung ({s.min_soc:.0f} %) liegen"
            )
        self.controller.set_setting(key, value)
