"""Battery Scheduler: zeitgesteuertes Laden/Entladen eines Batteriespeichers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .controller import BatteryController

PLATFORMS = [Platform.NUMBER, Platform.SENSOR, Platform.SWITCH, Platform.TIME]

type BatterySchedulerConfigEntry = ConfigEntry[BatteryController]


async def async_setup_entry(
    hass: HomeAssistant, entry: BatterySchedulerConfigEntry
) -> bool:
    controller = BatteryController(hass, entry)
    entry.runtime_data = controller

    # Plattformen zuerst, damit gespeicherte Einstellungen wiederhergestellt sind
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await controller.async_start()

    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BatterySchedulerConfigEntry
) -> bool:
    await entry.runtime_data.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: BatterySchedulerConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
