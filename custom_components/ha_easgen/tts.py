"""
Setting up TTS entity.
"""
import logging
import requests
import sys
from datetime import datetime, timedelta, timezone
from dateutil import parser
from homeassistant.components.tts import TextToSpeechEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import generate_entity_id
from .const import ICON, DEFAULT_NAME, DEFAULT_PORT, DOMAIN, STATE, ZONE, COUNTY, CALL_SIGN

from .eventcodes import SAME, FIPS
from .eas_gen_tts_engine import playHeader, playEndofMessage
from pydub.playback import play

from homeassistant.exceptions import MaxLengthExceeded

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EAS Generator Text-to-speech platform via config entry."""

    engine = EASGenTTSEngine(
        config_entry.data[CALL_SIGN],
        config_entry.data[STATE],
        config_entry.data[ZONE],
        config_entry.data[COUNTY]
    )
    async_add_entities([EASGenTTSEntity(hass, config_entry, engine)])


class EASGenTTSEntity(TextToSpeechEntity):
    """The EAS Generator TTS entity."""
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass, config, engine):
        """Initialize TTS entity."""
        self.hass = hass
        self._engine = engine
        self._config = config

        self._attr_unique_id = config.data.get(UNIQUE_ID)
        if self._attr_unique_id is None:
            # generate a legacy unique_id
            self._attr_unique_id = f"{config.data[STATE]}_{config.data[ZONE]}"
        self.entity_id = generate_entity_id("tts.eas_gen_tts_{}", config.data[DOMAIN], hass=hass)

    @property
    def default_language(self):
        """Return the default language."""
        return "en"

    @property
    def supported_languages(self):
        """Return the list of supported languages."""
        return self._engine.get_supported_langs()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "model": f"{self._config.data[DOMAIN]}",
            "manufacturer": "EASGen"
        }

    @property
    def name(self):
        """Return name of entity"""
        return f"{self._config.data[DOMAIN]}"

    def get_tts_audio(self, message, language, options=None):
        """Convert a given text to speech and return it as bytes."""
        try:
            if len(message) > 4096:
                raise MaxLengthExceeded

            speech = self._engine.get_tts(message)

            # The response should contain the audio file content
            return "wav", speech.content
        except MaxLengthExceeded:
            _LOGGER.error("Maximum length of the message exceeded")
        except Exception as e:
            _LOGGER.error("Unknown Error: %s", e)

        return None, None
