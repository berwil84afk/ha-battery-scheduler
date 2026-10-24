"""Einstellbare Zeiten für Lade- und Entladefenster."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import BatterySchedulerConfigEntry
from .entity import BatterySchedulerEntity

TIMES = ("charge_start", "charge_end", "discharge_start", "discharge_end")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BatterySchedulerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(BatteryTime(entry, key) for key in TIMES)


class BatteryTime(BatterySchedulerEntity, TimeEntity, RestoreEntity):
    """Uhrzeit, deren Wert im Controller liegt und Neustarts überlebt."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: BatterySchedulerConfigEntry, key: str) -> None:
        super().__init__(entry, key)
        self._key = key

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            self.controller.restore_setting(self._key, time.fromisoformat(last.state))
        except ValueError:
            pass

    @property
    def native_value(self) -> time:
        return getattr(self.controller.settings, self._key)

    async def async_set_value(self, value: time) -> None:
        self.controller.set_setting(self._key, value)
