"""Config flow for EAS Generator text-to-speech custom component."""
from __future__ import annotations
from typing import Any
import voluptuous as vol
import logging
from urllib.parse import urlparse

from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.selector import selector
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get

from .const import DEFAULT_NAME, DOMAIN, CALL_SIGN, UNIQUE_ID, ORG, ORGS, STATE, ZONE, COUNTY, TTS_ENGINE, VOICE, LANGUAGE, AVAIL_LANGUAGES, MEDIA_PLAYERS, DISABLE_TTS, INCLUDE_DESCRIPTION, TTS_WARNINGS, TTS_WATCHES, TTS_STATEMENTS

_LOGGER = logging.getLogger(__name__)

def generate_unique_id(user_input: dict) -> str:
    """Generate a unique id from user input."""
    county_part = f"_{user_input[COUNTY]}" if user_input.get(COUNTY) else ""
    return f"emergency_alert_system_tts_{user_input[STATE]}_{user_input[ZONE]}{county_part}_{user_input[TTS_ENGINE]}_{user_input[CALL_SIGN]}"

async def validate_user_input(hass: HomeAssistant, user_input: dict):
    """Validate user input fields."""
    if user_input.get(STATE) is None:
        raise ValueError("State is required")
    if user_input.get(ZONE) is None:
        raise ValueError("Zone is required")
    if user_input.get(TTS_ENGINE) is None:
        raise ValueError("Default TTS Engine is required")
    
    # Validate state format
    state = user_input[STATE].upper()
    if len(state) != 2:
        raise ValueError("State must be a 2-letter code (e.g., TX, CA)")
    
    # Validate zone format
    zone = user_input[ZONE]
    if not zone.isdigit() or not (1 <= len(zone) <= 3):
        raise ValueError("Zone must be 1-3 digits")
    
    # Validate county format if provided
    county = user_input.get(COUNTY, "")
    if county and (not county.isdigit() or not (1 <= len(county) <= 3)):
        raise ValueError("County must be 1-3 digits if provided")

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

    async def async_get_media_player_entities(self, hass: HomeAssistant):
        """Get a list of available media player entities."""
        entity_registry = async_get(hass)
        media_player_entities = [
            entity.entity_id
            for entity in entity_registry.entities.values()
            if entity.domain == "media_player"
        ]
        return media_player_entities

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}
        if user_input is None:
            tts_entities = await self.async_get_tts_entities(self.hass)
            media_player_entities = await self.async_get_media_player_entities(self.hass)
            data_schema = vol.Schema({
                vol.Required(STATE, default="TX"): str,
                vol.Required(ZONE, default="19"): str,
                vol.Optional(COUNTY, default=""): str,
                vol.Required(TTS_ENGINE, default=tts_entities[0] if tts_entities else ""): selector({
                    "select": {
                        "options": tts_entities,
                        "mode": "dropdown",
                        "sort": True,
                        "custom_value": True
                    }
                }),
                vol.Required(MEDIA_PLAYERS, default=[]): selector({
                    "select": {
                        "options": media_player_entities,
                        "mode": "dropdown",
                        "multiple": True,
                        "sort": True,
                        "custom_value": False
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
                }),
                vol.Optional(DISABLE_TTS, default=False): bool,
                vol.Optional(INCLUDE_DESCRIPTION, default=False): bool,
                vol.Optional(TTS_WARNINGS, default=True): bool,
                vol.Optional(TTS_WATCHES, default=True): bool,
                vol.Optional(TTS_STATEMENTS, default=False): bool
            })
            return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
        
        try:
            await validate_user_input(self.hass, user_input)
            unique_id = generate_unique_id(user_input)
            user_input[UNIQUE_ID] = unique_id
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            
            # Create unique title based on location
            location = f"{user_input[STATE]}Z{user_input[ZONE]}"
            if user_input.get(COUNTY):
                location += f" {user_input[STATE]}C{user_input[COUNTY]}"
            title = f"{DEFAULT_NAME} ({location})"
            
            return self.async_create_entry(title=title, data=user_input)
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
        
        # If there are errors, show the form again with the same schema
        if errors:
            tts_entities = await self.async_get_tts_entities(self.hass)
            media_player_entities = await self.async_get_media_player_entities(self.hass)
            data_schema = vol.Schema({
                vol.Required(STATE, default=user_input.get(STATE, "TX")): str,
                vol.Required(ZONE, default=user_input.get(ZONE, "19")): str,
                vol.Optional(COUNTY, default=user_input.get(COUNTY, "")): str,
                vol.Required(TTS_ENGINE, default=user_input.get(TTS_ENGINE, tts_entities[0] if tts_entities else "")): selector({
                    "select": {
                        "options": tts_entities,
                        "mode": "dropdown",
                        "sort": True,
                        "custom_value": True
                    }
                }),
                vol.Required(MEDIA_PLAYERS, default=user_input.get(MEDIA_PLAYERS, [])): selector({
                    "select": {
                        "options": media_player_entities,
                        "mode": "dropdown",
                        "multiple": True,
                        "sort": True,
                        "custom_value": False
                    }
                }),
                vol.Optional(CALL_SIGN, default=user_input.get(CALL_SIGN, "KF5NTR")): str,
                vol.Required(ORG, default=user_input.get(ORG, "EAS")): selector({
                    "select": {
                        "options": ORGS,
                        "mode": "dropdown",
                        "sort": True,
                        "custom_value": True
                    }
                }),
                vol.Required(VOICE, default=user_input.get(VOICE, "default")): str,
                vol.Required(LANGUAGE, default=user_input.get(LANGUAGE, "en-us")): selector({
                    "select": {
                        "options": AVAIL_LANGUAGES,
                        "mode": "dropdown",
                        "sort": True,
                        "custom_value": True
                    }
                }),
                vol.Optional(DISABLE_TTS, default=user_input.get(DISABLE_TTS, False)): bool,
                vol.Optional(INCLUDE_DESCRIPTION, default=user_input.get(INCLUDE_DESCRIPTION, False)): bool,
                vol.Optional(TTS_WARNINGS, default=user_input.get(TTS_WARNINGS, True)): bool,
                vol.Optional(TTS_WATCHES, default=user_input.get(TTS_WATCHES, True)): bool,
                vol.Optional(TTS_STATEMENTS, default=user_input.get(TTS_STATEMENTS, False)): bool
            })
            return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
