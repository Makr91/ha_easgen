"""
Setting up TTS entity.
"""
import logging
import asyncio
import pydub
from homeassistant.components.tts import TextToSpeechEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import generate_entity_id
from .const import DOMAIN, CALL_SIGN, UNIQUE_ID, ORG, STATE, ZONE, COUNTY, TTS_ENGINE, VOICE, LANGUAGE, MANUFACTURER
from .version import __version__ as VERSION
from .eas_gen_tts_engine import EASGenTTSEngine
from .weather_alerts import EASGenWeatherAlertsSensor
from urllib.parse import quote

from homeassistant.exceptions import MaxLengthExceeded

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EAS Generator Text-to-speech platform via config entry."""

    # Wait for coordinator to be available (retry mechanism)
    coordinator = None
    max_retries = 20
    for attempt in range(max_retries):
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][config_entry.entry_id]
            _LOGGER.info("Found alert coordinator on attempt %d", attempt + 1)
            break
        _LOGGER.debug("Waiting for alert coordinator (attempt %d/%d)", attempt + 1, max_retries)
        await asyncio.sleep(0.2)  # Wait 200ms between attempts
    
    if coordinator is None:
        _LOGGER.error("Alert coordinator not found after %d attempts - sensor platform may have failed", max_retries)
        return

    _LOGGER.info("Creating EAS TTS engine with coordinator")
    engine = EASGenTTSEngine(
        hass,
        coordinator.weather_sensor,
        config_entry.data[TTS_ENGINE],
        config_entry.data[ORG],
        config_entry.data[CALL_SIGN],
        config_entry.data[VOICE],
        config_entry.data[LANGUAGE],
        config_entry
    )
    
    # Register the TTS entity with coordinator access
    tts_entity = EASGenTTSEntity(hass, config_entry, engine, coordinator)
    
    # Store engine reference in coordinator for easier access
    if coordinator:
        coordinator.tts_engine = engine
    
    async_add_entities([tts_entity])
    _LOGGER.info("EAS TTS entity created successfully: %s", tts_entity.entity_id)


class EASGenTTSEntity(TextToSpeechEntity):
    """The EAS Generator TTS entity."""
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass, config, engine, coordinator=None):
        """Initialize TTS entity."""
        self.hass = hass
        self._engine = engine
        self._config = config
        self._coordinator = coordinator
        self._name = f"EAS Generator {config.data[STATE]}Z{config.data[ZONE]}"
        if config.data.get(COUNTY):
            self._name += f" {config.data[STATE]}C{config.data[COUNTY]}"

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
        """Return device information."""
        # Create location-based device name
        location = f"{self._config.data[STATE]}Z{self._config.data[ZONE]}"
        if self._config.data.get(COUNTY):
            location += f" {self._config.data[STATE]}C{self._config.data[COUNTY]}"
        
        return {
            "identifiers": {(DOMAIN, self._config.entry_id)},
            "name": f"EAS Generator {location}",
            "manufacturer": MANUFACTURER,
            "model": "Emergency Alert System",
            "sw_version": VERSION
        }

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    async def async_get_tts_audio(self, message, language, options=None):
        """Return EAS Header Audio, TTS, and End of Message Audio."""
        try:
            # Parse the specific alert data from the message
            import json
            try:
                alert_data = json.loads(message)
                _LOGGER.debug("Processing specific alert: %s", alert_data.get("event", "Unknown"))
            except json.JSONDecodeError:
                _LOGGER.error("Invalid alert data received: %s", message)
                return None, None
            
            # Process the specific alert instead of all alerts
            notification_data = await self._engine.get_single_notification(alert_data)
            
            if not notification_data:
                _LOGGER.error("No notification data generated for alert")
                return None, None
            
            # Initialize an empty AudioSegment to combine all the alerts
            combined_speech = pydub.AudioSegment.silent(duration=0)
            
            for MinHeader, title, FullHeader in notification_data:
                if len(title) > 4096:
                    raise MaxLengthExceeded
                
                _LOGGER.debug("Generating WAV Files")
                
                # Generate Header and Footer WAV files (now async)
                header_wav = await self._engine.get_header_audio(MinHeader, FullHeader)
                header, header_path = header_wav
                footer_wav = await self._engine.get_footer_audio(MinHeader)
                footer, footer_path = footer_wav
                
                # Generate TTS for the current alert (now async)
                generated_speech = await self._engine.get_tts(title, header_path, footer_path)
                
                # Check if TTS generation was successful
                if generated_speech is None or generated_speech == (None, None):
                    _LOGGER.error("TTS generation failed for alert: %s", title)
                    continue
                
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
