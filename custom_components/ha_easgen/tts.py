"""
Setting up TTS entity.
"""
import logging
import pydub
import io
from homeassistant.components.tts import TextToSpeechEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import generate_entity_id
from .const import ICON, NAME, DOMAIN, CALL_SIGN, UNIQUE_ID, ORG, SENSOR, TTS_ENGINE, VOICE, LANGUAGE
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
            "manufacturer": f"@Makr91 -- KF5NTR",
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
            MinHeader, title, FullHeader = notification_data

            _LOGGER.info("Hello")
            if len(title) > 4096:
                raise MaxLengthExceeded
            ## URL-encode the message
            #encoded_message = quote(title)
            ## Construct the tts_content with the encoded message
            #tts_content = f"media-source://tts/tts.piper?message={encoded_message}&language=en-us&voice=glados"
            #players = ['media_player.monitor_01', 'media_player.monitor_02', 'media_player.monitor_03']
            # wav_file_path = "https://home.m4kr.net/local/EAS/Alerts/" + MinHeader + "-Header.wav"
            ## Call the media_player.play_media service to play the .wav file
            #self.hass.services.call("media_player", "play_media", entity_id=players,blocking=True, media_content_id=wav_file_path, media_content_type="audio/wav")
            ## Call the media_player.play_media service to play the TTS message
            #self.hass.services.call("media_player", "play_media", entity_id=players,blocking=True, media_content_id=tts_content, media_content_type="provider")
            #
            #wav_file_path = "https://home.m4kr.net/local/EAS/Alerts/" + MinHeader + "-EndofMessage.wav"
            #self.hass.services.call("media_player", "play_media", entity_id=players,blocking=True, media_content_id=wav_file_path, media_content_type="audio/wav")
 
            _LOGGER.error("Generating WAV Files")
            # Generat Combined WAV File
            header_wav = self._engine.get_header_audio(MinHeader, FullHeader)
            header, header_path = header_wav
            footer_wav = self._engine.get_footer_audio(MinHeader)
            footer, footer_path = footer_wav

            generated_speech = self._engine.get_tts(title, header_path, footer_path)
            tts_message, tts_message_path = generated_speech

            _LOGGER.error(tts_message_path)

            # Combine the three wav files:
            speech = header
            speech += tts_message
            speech += footer
            return b"wav", speech.export(format="wav").read()

        except MaxLengthExceeded:
            _LOGGER.error("Maximum length of the message exceeded")
        except Exception as e:
            _LOGGER.error("Unknown Error: %s", e)

        return None, None
