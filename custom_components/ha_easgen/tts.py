"""
Setting up TTS entity.
"""
import logging
import pydub
from homeassistant.components.tts import TextToSpeechEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import generate_entity_id
from .const import NAME, DOMAIN, CALL_SIGN, UNIQUE_ID, ORG, SENSOR, TTS_ENGINE, VOICE, LANGUAGE, MANUFACTURER
from .version import __version__ as VERSION
from .eas_gen_tts_engine import EASGenTTSEngine
from urllib.parse import quote

from homeassistant.exceptions import MaxLengthExceeded

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EAS Generator Text-to-speech platform via config entry."""

    engine = EASGenTTSEngine(
        hass,
        config_entry.data[SENSOR],
        config_entry.data[TTS_ENGINE],
        config_entry.data[ORG],
        config_entry.data[CALL_SIGN],
        config_entry.data[VOICE],
        config_entry.data[LANGUAGE]
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
            self._attr_unique_id = f"{config.data[ORG]}_{config.data[VOICE]}_{config.data[LANGUAGE]}_{config.data[CALL_SIGN]}"
        self.entity_id = generate_entity_id("tts.eas_gen_tts_{}", config.data[CALL_SIGN], hass=hass)

    @property
    def default_language(self):
        """Return the default language."""
        return "en-us"

    @property
    def supported_languages(self):
        """Return the list of supported languages."""
        return self._engine.get_supported_langs()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "model": "Emergency Alert System TTS Generator",
            "manufacturer": MANUFACTURER,
            "sw_version": [VERSION]
        }

    @property
    def name(self):
        """Return name of entity"""
        return NAME

    def get_tts_audio(self, message, language, options=None):
        """Return EAS Header Audio, TTS, and End of Message Audio."""
        try:
            notification_data = self._engine.get_notifications()
            
            # Initialize an empty AudioSegment to combine all the alerts
            combined_speech = pydub.AudioSegment.silent(duration=0)
            
            for MinHeader, title, FullHeader in notification_data:
                if len(title) > 4096:
                    raise MaxLengthExceeded
                
                _LOGGER.debug("Generating WAV Files")
                
                # Generate Header and Footer WAV files
                header_wav = self._engine.get_header_audio(MinHeader, FullHeader)
                header, header_path = header_wav
                footer_wav = self._engine.get_footer_audio(MinHeader)
                footer, footer_path = footer_wav
                
                # Generate TTS for the current alert
                generated_speech = self._engine.get_tts(title, header_path, footer_path)
                tts_message, tts_message_path = generated_speech

                # Combine the header, TTS message, and footer for the current alert
                speech = header + tts_message + footer
                
                # Append the current alert's speech to the combined speech
                combined_speech += speech
            
            # Return the combined speech as a single WAV file
            return b"wav", combined_speech.export(format="wav").read()
    
        except MaxLengthExceeded:
            _LOGGER.error("Maximum length of the message exceeded")
        except Exception as e:
            _LOGGER.error("Unknown Error: %s", e)
    
        return None, None
    