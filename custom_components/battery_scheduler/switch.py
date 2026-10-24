"""Hauptschalter der Steuerung."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import BatterySchedulerConfigEntry
from .entity import BatterySchedulerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BatterySchedulerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([BatteryEnabledSwitch(entry)])


class BatteryEnabledSwitch(BatterySchedulerEntity, SwitchEntity, RestoreEntity):
    """Aktiviert/deaktiviert die automatische Steuerung."""

    def __init__(self, entry: BatterySchedulerConfigEntry) -> None:
        super().__init__(entry, "enabled")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            self.controller.restore_setting("enabled", last.state != STATE_OFF)

    @property
    def is_on(self) -> bool:
        return self.controller.settings.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.controller.set_setting("enabled", True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.controller.set_setting("enabled", False)
