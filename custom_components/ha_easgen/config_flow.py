"""Config flow for EAS Generator text-to-speech custom component."""
from __future__ import annotations
from typing import Any
import voluptuous as vol
import logging
import re
import socket
import requests
from urllib.parse import urlparse

from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.selector import selector
from homeassistant.exceptions import HomeAssistantError

from .const import ICON, NAME, DOMAIN, STATE, ZONE, COUNTY, CALL_SIGN, STATES, UNIQUE_ID, ORG, SENSOR, TTS_ENGINE

_LOGGER = logging.getLogger(__name__)

def generate_unique_id(user_input: dict) -> str:
    """Generate a unique id from user input."""
    return f"{user_input[STATE]}_{user_input[COUNTY]}_{user_input[ZONE]}_{user_input[CALL_SIGN]}"

async def validate_user_input(user_input: dict):
    """Validate user input fields."""
    if user_input.get(SENSOR) is None:
        raise ValueError("Alert Sensor is required")
    if user_input.get(TTS_ENGINE) is None:
        raise ValueError("Default TTS Engine is required")

class EASGenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EAS TTS Generator."""
    VERSION = 1
    data_schema = vol.Schema({
        vol.Optional(TTS_ENGINE, default="tts.piper"): str,
        vol.Optional(SENSOR, default="sensor.weather_alerts.alerts"): str,
        vol.Optional(CALL_SIGN, default="KF5NTR"): str,
        vol.Optional(ORG, default="EAS"): str,
        vol.Optional(ZONE, default=10): vol.Coerce(int),
        vol.Optional(COUNTY, default=10): vol.Coerce(int),
        vol.Required(STATE, default="IL"): selector({
            "select": {
                "options": STATES,
                "mode": "dropdown",
                "sort": True,
                "custom_value": True
            }
        })
    })

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                await validate_user_input(user_input)
                unique_id = generate_unique_id(user_input)
                user_input[UNIQUE_ID] = unique_id
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                #hostname = urlparse(user_input[CONF_URL]).hostname
                return self.async_create_entry(title=f"EAS Gen ({user_input[STATE]}, {user_input[ZONE]}, {user_input[COUNTY]}, {user_input[CALL_SIGN]}, {user_input[ORG]})", data=user_input)
            except data_entry_flow.AbortFlow:
                return self.async_abort(reason="already_configured")
            except HomeAssistantError as e:
                _LOGGER.exception(str(e))
                errors["base"] = str(e)
            except ValueError as e:
                _LOGGER.exception(str(e))
                errors["base"] = str(e)
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception(str(e))
                errors["base"] = "unknown_error"
        return self.async_show_form(step_id="user", data_schema=self.data_schema, errors=errors, description_placeholders=user_input)
