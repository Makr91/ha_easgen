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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get

from .const import ICON, NAME, DOMAIN, CALL_SIGN, UNIQUE_ID, ORG, ORGS, SENSOR, TTS_ENGINE, VOICE, LANGUAGE, AVAIL_LANGUAGES

_LOGGER = logging.getLogger(__name__)

def generate_unique_id(user_input: dict) -> str:
    """Generate a unique id from user input."""
    return f"emergency_alert_system_tts_{user_input[SENSOR]}_{user_input[TTS_ENGINE]}_{CALL_SIGN}_{ORG}"

async def validate_user_input(hass: HomeAssistant, user_input: dict):
    """Validate user input fields."""
    if user_input.get(SENSOR) is None:
        raise ValueError("Alert Sensor is required")
    if user_input.get(TTS_ENGINE) is None:
        raise ValueError("Default TTS Engine is required")

class EASGenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EAS TTS Generator."""
    VERSION = 1

    async def async_get_tts_entities(self, hass: HomeAssistant):
        """Get a list of available TTS entities."""
        entity_registry = async_get(hass)
        tts_entities = [
            entity.entity_id
            for entity in entity_registry.entities.values()
            if entity.domain == "tts"
        ]
        return tts_entities

    async def async_get_weatheralerts_sensors(self, hass: HomeAssistant):
        """Get a list of sensor entities with integration attribute set to 'weatheralerts'."""
        entity_registry = async_get(hass)
        weatheralerts_sensors = [
            entity.entity_id
            for entity in entity_registry.entities.values()
            if entity.domain == "sensor" and 
               entity.platform == "weatheralerts"
        ]
        return weatheralerts_sensors

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}
        if user_input is None:
            tts_entities = await self.async_get_tts_entities(self.hass)
            weatheralerts_sensors = await self.async_get_weatheralerts_sensors(self.hass)
            data_schema = vol.Schema({
                vol.Required(TTS_ENGINE, default=tts_entities[0] if tts_entities else ""): selector({
                    "select": {
                        "options": tts_entities,
                        "mode": "dropdown",
                        "sort": True,
                        "custom_value": True
                    }
                }),
                vol.Required(SENSOR, default=weatheralerts_sensors[0] if weatheralerts_sensors else ""): selector({
                    "select": {
                        "options": weatheralerts_sensors,
                        "mode": "dropdown",
                        "sort": True,
                        "custom_value": True
                    }
                }),
                vol.Optional(CALL_SIGN, default="KF5NTR"): str,
                vol.Required(ORG, default="EAS"): selector({
                    "select": {
                        "options": ORGS,
                        "mode": "dropdown",
                        "sort": True,
                        "custom_value": True
                    }
                }),
                vol.Required(VOICE, default="default"): str,
                vol.Required(LANGUAGE, default="en-us"): selector({
                    "select": {
                        "options": AVAIL_LANGUAGES,
                        "mode": "dropdown",
                        "sort": True,
                        "custom_value": True
                    }
                })
            })
            return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
        
        try:
            await validate_user_input(self.hass, user_input)
            unique_id = generate_unique_id(user_input)
            user_input[UNIQUE_ID] = unique_id
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=NAME, data=user_input)
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
