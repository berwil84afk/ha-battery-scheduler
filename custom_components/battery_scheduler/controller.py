"""Steuerlogik: zeitgesteuertes Laden und netzgeführtes Entladen."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHARGE_ENTITY,
    CONF_DISCHARGE_ENTITY,
    CONF_GRID_INVERT,
    CONF_GRID_SENSOR,
    CONF_SETPOINT_INVERT,
    CONF_SOC_SENSOR,
    CONF_TARGET_GRID,
    CONF_UPDATE_INTERVAL,
    DEADBAND,
    DEFAULT_CHARGE_END,
    DEFAULT_CHARGE_START,
    DEFAULT_DISCHARGE_END,
    DEFAULT_DISCHARGE_START,
    DEFAULT_MAX_CHARGE,
    DEFAULT_MAX_DISCHARGE,
    DEFAULT_MAX_SOC,
    DEFAULT_MIN_SOC,
    DEFAULT_TARGET_GRID,
    DEFAULT_UPDATE_INTERVAL,
    MAX_POWER,
    MODE_CHARGING,
    MODE_DISABLED,
    MODE_DISCHARGING,
    MODE_EMPTY,
    MODE_ERROR,
    MODE_FULL,
    MODE_IDLE,
    SOC_HYSTERESIS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class Settings:
    """Vom Benutzer über Entitäten einstellbare Werte."""

    enabled: bool = True
    min_soc: float = DEFAULT_MIN_SOC
    max_soc: float = DEFAULT_MAX_SOC
    max_charge_power: float = DEFAULT_MAX_CHARGE
    max_discharge_power: float = DEFAULT_MAX_DISCHARGE
    charge_start: time = DEFAULT_CHARGE_START
    charge_end: time = DEFAULT_CHARGE_END
    discharge_start: time = DEFAULT_DISCHARGE_START
    discharge_end: time = DEFAULT_DISCHARGE_END


def in_window(now: time, start: time, end: time) -> bool:
    """Prüft, ob `now` im Zeitfenster liegt (auch über Mitternacht)."""
    if start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end


def clamp(value: float, low: float, high: float) -> float:
    """Begrenzt einen Wert auf [low, high]."""
    return max(low, min(high, value))


class BatteryController:
    """Regelt Lade- und Entladeleistung des Speichers."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        conf = {**entry.data, **entry.options}
        self._soc_entity: str = conf[CONF_SOC_SENSOR]
        self._grid_entity: str = conf[CONF_GRID_SENSOR]
        self._charge_entity: str = conf[CONF_CHARGE_ENTITY]
        self._discharge_entity: str = conf[CONF_DISCHARGE_ENTITY]
        self._grid_invert: bool = conf.get(CONF_GRID_INVERT, False)
        self._setpoint_invert: bool = conf.get(CONF_SETPOINT_INVERT, False)
        self._target_grid: float = conf.get(CONF_TARGET_GRID, DEFAULT_TARGET_GRID)
        self._interval = timedelta(
            seconds=conf.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        self.settings = Settings()
        self.mode: str = MODE_IDLE
        self.soc: float | None = None
        self.grid_power: float | None = None
        self.charge_setpoint: float = 0
        self.discharge_setpoint: float = 0

        self._full = False
        self._empty = False
        self._lock = asyncio.Lock()
        self._listeners: list[Callable[[], None]] = []
        self._unsub_interval: CALLBACK_TYPE | None = None

    @property
    def combined_setpoint(self) -> bool:
        """True, wenn Laden und Entladen über dieselbe Entität laufen."""
        return self._charge_entity == self._discharge_entity

    # --- Lebenszyklus -------------------------------------------------------

    async def async_start(self) -> None:
        """Startet die zyklische Regelung."""
        self._unsub_interval = async_track_time_interval(
            self.hass, self._async_tick, self._interval
        )
        await self.async_update()

    async def async_stop(self) -> None:
        """Stoppt die Regelung und setzt die Leistung auf 0."""
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None
        async with self._lock:
            await self._async_apply(0, 0)

    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> CALLBACK_TYPE:
        """Registriert eine Entität für Zustandsänderungen."""
        self._listeners.append(update_callback)

        @callback
        def remove() -> None:
            self._listeners.remove(update_callback)

        return remove

    @callback
    def set_setting(self, key: str, value: Any) -> None:
        """Ändert eine Einstellung und regelt sofort neu."""
        setattr(self.settings, key, value)
        self._notify()
        self.hass.async_create_task(self.async_update())

    @callback
    def restore_setting(self, key: str, value: Any) -> None:
        """Setzt einen wiederhergestellten Wert ohne Regelzyklus."""
        setattr(self.settings, key, value)

    # --- Regelung -----------------------------------------------------------

    async def _async_tick(self, _now: datetime) -> None:
        await self.async_update()

    async def async_update(self) -> None:
        """Ein Regelzyklus."""
        if self._lock.locked():
            return
        async with self._lock:
            try:
                await self._async_control()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Fehler im Regelzyklus")
                self.mode = MODE_ERROR
        self._notify()

    async def _async_control(self) -> None:
        s = self.settings

        if not s.enabled:
            # Beim Deaktivieren einmal auf 0 setzen, danach nicht mehr eingreifen
            if self.mode != MODE_DISABLED:
                await self._async_apply(0, 0)
            self.mode = MODE_DISABLED
            return

        self.soc = self._read_float(self._soc_entity)
        self.grid_power = self._read_grid_power()

        if self.soc is None:
            _LOGGER.warning("Ladezustand %s nicht verfügbar", self._soc_entity)
            self.mode = MODE_ERROR
            await self._async_apply(0, 0)
            return

        now = dt_util.now().time()

        # Laden hat Vorrang, falls sich die Fenster überschneiden
        if in_window(now, s.charge_start, s.charge_end):
            if self.soc >= s.max_soc:
                self._full = True
            elif self.soc <= s.max_soc - SOC_HYSTERESIS:
                self._full = False

            if self._full:
                self.mode = MODE_FULL
                await self._async_apply(0, 0)
            else:
                self.mode = MODE_CHARGING
                await self._async_apply(clamp(s.max_charge_power, 0, MAX_POWER), 0)
            return

        if in_window(now, s.discharge_start, s.discharge_end):
            if self.soc <= s.min_soc:
                self._empty = True
            elif self.soc >= s.min_soc + SOC_HYSTERESIS:
                self._empty = False

            if self._empty:
                self.mode = MODE_EMPTY
                await self._async_apply(0, 0)
                return

            if self.grid_power is None:
                _LOGGER.warning("Netzsensor %s nicht verfügbar", self._grid_entity)
                self.mode = MODE_ERROR
                await self._async_apply(0, 0)
                return

            await self._async_apply(0, self._next_discharge_power())
            self.mode = MODE_DISCHARGING
            return

        self.mode = MODE_IDLE
        await self._async_apply(0, 0)

    def _next_discharge_power(self) -> float:
        """Nulleinspeiseregelung: Netzbezug durch Entladung ausgleichen.

        Der Netzsensor misst Bezug positiv. Die aktuelle Entladung ist darin
        bereits enthalten, daher wird die Abweichung auf den bisherigen
        Sollwert addiert (I-Regler).
        """
        limit = clamp(self.settings.max_discharge_power, 0, MAX_POWER)
        current = self.discharge_setpoint
        target = clamp(round(current + self.grid_power - self._target_grid), 0, limit)
        if abs(target - current) < DEADBAND and target not in (0, limit):
            return current
        return target

    # --- Lesen ----------------------------------------------------------------

    def _read_float(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    def _read_grid_power(self) -> float | None:
        """Netzleistung in W, Bezug positiv, Einspeisung negativ."""
        value = self._read_float(self._grid_entity)
        if value is None:
            return None
        state = self.hass.states.get(self._grid_entity)
        unit = (state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) or "").lower()
        if unit == "kw":
            value *= 1000
        return -value if self._grid_invert else value

    # --- Schreiben ------------------------------------------------------------

    async def _async_apply(self, charge: float, discharge: float) -> None:
        """Schreibt Lade-/Entladesollwert an den Speicher."""
        if self.combined_setpoint:
            # Gemeinsame Entität: Entladen positiv, Laden negativ (ggf. invertiert)
            value = discharge - charge
            if self._setpoint_invert:
                value = -value
            await self._async_write(self._charge_entity, value)
            self.charge_setpoint = charge
            self.discharge_setpoint = discharge
            return

        charge = self._clamp_to_entity(self._charge_entity, charge)
        discharge = self._clamp_to_entity(self._discharge_entity, discharge)
        # Erst die Richtung abschalten, die nicht mehr gebraucht wird
        if charge > 0:
            await self._async_write(self._discharge_entity, discharge)
            await self._async_write(self._charge_entity, charge)
        else:
            await self._async_write(self._charge_entity, charge)
            await self._async_write(self._discharge_entity, discharge)
        self.charge_setpoint = charge
        self.discharge_setpoint = discharge

    def _clamp_to_entity(self, entity_id: str, value: float) -> float:
        """Begrenzt auf min/max der Ziel-Entität."""
        state = self.hass.states.get(entity_id)
        if state is None:
            return value
        try:
            low = float(state.attributes.get("min", value))
            high = float(state.attributes.get("max", value))
        except (TypeError, ValueError):
            return value
        return clamp(value, low, high)

    async def _async_write(self, entity_id: str, value: float) -> None:
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("Entität %s existiert nicht", entity_id)
            return
        value = self._clamp_to_entity(entity_id, value)
        try:
            if abs(float(state.state) - value) < 0.5:
                return
        except ValueError:
            pass
        domain = entity_id.split(".", 1)[0]
        _LOGGER.debug("Setze %s auf %s", entity_id, value)
        await self.hass.services.async_call(
            domain,
            "set_value",
            {"entity_id": entity_id, "value": value},
            blocking=True,
        )

    @callback
    def _notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()
