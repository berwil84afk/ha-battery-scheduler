"""Config-Flow für Battery Scheduler."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CHARGE_ENTITY,
    CONF_DISCHARGE_ENTITY,
    CONF_GRID_INVERT,
    CONF_GRID_SENSOR,
    CONF_SETPOINT_INVERT,
    CONF_SOC_SENSOR,
    CONF_TARGET_GRID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_TARGET_GRID,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_POWER_ENTITY = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["number", "input_number"])
)


def _entity_schema() -> dict:
    return {
        vol.Required(CONF_SOC_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_GRID_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_CHARGE_ENTITY): _POWER_ENTITY,
        vol.Required(CONF_DISCHARGE_ENTITY): _POWER_ENTITY,
        vol.Optional(CONF_GRID_INVERT, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_SETPOINT_INVERT, default=False): selector.BooleanSelector(),
        vol.Optional(
            CONF_TARGET_GRID, default=DEFAULT_TARGET_GRID
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-100, max=200, step=1, unit_of_measurement="W",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=2, max=120, step=1, unit_of_measurement="s",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }


class BatterySchedulerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ersteinrichtung."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            name = user_input.pop(CONF_NAME)
            return self.async_create_entry(title=name, data=user_input)

        schema = vol.Schema(
            {vol.Required(CONF_NAME, default=DEFAULT_NAME): str, **_entity_schema()}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BatterySchedulerOptionsFlow()


class BatterySchedulerOptionsFlow(OptionsFlow):
    """Nachträgliches Ändern der Entitäten und Regelparameter."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        schema = self.add_suggested_values_to_schema(
            vol.Schema(_entity_schema()), current
        )
        return self.async_show_form(step_id="init", data_schema=schema)
