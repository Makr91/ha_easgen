"""EAS Header and Footer Module"""
import logging
from EASGen import EASGen
import pydub
from .const import AVAIL_LANGUAGES, MAX_PURGE_DIFFERENCE, HOUR_IN_MINUTES, MINUTE_IN_SECONDS
from datetime import timedelta
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from dateutil import parser

_LOGGER = logging.getLogger(__name__)

class EASGenTTSEngine:
    def __init__(self, hass, weather_sensor, tts_engine: str, org: str, call_sign: str, voice: str, language: str, config_entry=None):
        self.hass = hass
        self._weather_sensor = weather_sensor
        self._tts_engine = tts_engine
        self._org = org
        self._call_sign = call_sign
        self._voice = voice
        self._language = language
        self._languages = AVAIL_LANGUAGES
        self._config_entry = config_entry

    async def get_tts(self, text: str, header_path, footer_path):
        """Generate TTS audio directly using Home Assistant TTS functions (like chime_tts does internally)"""
        try:
            import asyncio
            import io
            from homeassistant.components import tts
            
            # Step 1: Generate media source ID (same as chime_tts)
            timeout = 30  # seconds
            media_source_id = await asyncio.wait_for(
                asyncio.to_thread(
                    tts.media_source.generate_media_source_id,
                    hass=self.hass,
                    message=text,
                    engine=self._tts_engine,
                    language=self._language,
                    cache=False,
                    options={}
                ),
                timeout=timeout,
            )
            
            if not media_source_id:
                _LOGGER.error("Error: Unable to generate media_source_id")
                return None, None
            
            # Step 2: Get the audio data (same as chime_tts)
            audio_data = await tts.async_get_media_source_audio(
                hass=self.hass, 
                media_source_id=media_source_id
            )
            
            if audio_data is None or len(audio_data) != 2:
                _LOGGER.error("Error: Unable to get audio data from media_source_id")
                return None, None
            
            # Step 3: Convert to pydub AudioSegment (same as chime_tts)
            audio_bytes = audio_data[1]
            file = io.BytesIO(audio_bytes)
            tts_audio = pydub.AudioSegment.from_file(file)
            
            if tts_audio and len(tts_audio) > 0:
                _LOGGER.debug("TTS audio generated successfully")
                return (tts_audio, None)
            else:
                _LOGGER.error("Could not extract TTS audio from file")
                return None, None
                
        except asyncio.TimeoutError:
            _LOGGER.error("TTS audio generation timed out after %ss", timeout)
            return None, None
        except Exception as e:
            _LOGGER.error(f"TTS generation failed: {e}")
            return None, None
        
    async def get_single_notification(self, alert):
        """Process a single specific alert instead of all alerts."""
        from .eventcodes import get_same_data, get_fips_data
        valid_severities = {'Unknown', 'Minor', 'Moderate', 'Severe', 'Extreme'}
        results = []

        # Load data asynchronously
        SAME = await get_same_data()
        FIPS = await get_fips_data()

        _LOGGER.info("Processing single alert: %s", alert.get('event', 'Unknown'))

        if alert.get('severity') not in valid_severities:
            _LOGGER.warning("Skipping alert with invalid severity: %s", alert.get('severity'))
            return results
        elif alert.get('severity') == 'Unknown':
            _LOGGER.warning("Skipping alert with unknown severity")
            return results

        CardinalLocation='0'
        
        _LOGGER.debug("Gathering the Event Code from SAME data")
        EventCode = ""
        event = alert.get('event')
        for item in SAME:
           if item["Event Description"] == event:
              EventCode = item["Event Code"]
              break

        if not EventCode:
            _LOGGER.error(f"Event code not found for event: {event}")
            return results

        _LOGGER.debug("Gathering the Zone Data")
        Zone = alert.get('zoneid').split(",")[0]
        if len(Zone) >= 3:
            ZoneState = Zone[:2]
            ZoneID = str(int(Zone[2:].split("Z")[1]))
        else:
            _LOGGER.warning(f"Skipping Zone with less than 3 characters: {Zone}")
            return results
       
        _LOGGER.debug("Gathering the County Data")
        county_parts = alert.get('zoneid').split(",")
        if len(county_parts) > 1:
            County = county_parts[1]
            if len(County) >= 3:
                CountyState = County[:2]
                CountyCode = str(int(County[2:].split("C")[1]))
            else:
                _LOGGER.warning(f"Skipping County with less than 3 characters: {County}")
                return results
        else:
            # No county in zone ID, use zone state and a default county code
            CountyState = ZoneState
            CountyCode = "000"

        _LOGGER.debug("Gathering the FIPs Data")
        StateCode = "00"  # Default
        for item in FIPS:
           if item["State"] == ZoneState:
              StateCode = item["State Code"]
              break
          
        _LOGGER.debug("Gathering the Alert Spoken Title")
        spoken_title = alert.get('spoken_title')
        if spoken_title is None:
            title = alert.get('title')
            if title is None:
                spoken_title = "No Title for this Alert!"
                _LOGGER.warning(f"EAS ALERT!!: No Title!")
            else:
                spoken_title = title
                _LOGGER.warning(f"EAS ALERT!!: " + spoken_title)
        else:
            spoken_title = alert.get('spoken_title')
            _LOGGER.warning(f"EAS ALERT!!: " + spoken_title)

        # Add description if enabled in configuration
        if self._config_entry and self._config_entry.data.get('include_description', False):
            description = alert.get('description', '')
            if description:
                what_section = self._extract_what_section(description)
                if what_section:
                    spoken_title += f". {what_section}"
                    _LOGGER.debug("Added WHAT section to spoken title")

        _LOGGER.debug("Parsing the Alert Dates")
        BeginTime = parser.parse(alert.get('onset'))
        EndTime = parser.parse(alert.get('endsExpires'))

        diff = EndTime - BeginTime
        PurgeTimeDifference = int(diff / timedelta(minutes=1))
        PurgeTime = self.calculate_purge_time(PurgeTimeDifference)

        _LOGGER.debug("Generating the EAS Protocol Header String")
        IssueTime = BeginTime.strftime('%j') + BeginTime.strftime('%H') + BeginTime.strftime('%M')
        MinHeader = "ZCZC-" + self._org + "-" + EventCode + "-" + CardinalLocation + StateCode.zfill(2) + CountyCode.zfill(3) + "+" + PurgeTime.zfill(4) + "-" + IssueTime 
        FullHeader = MinHeader + "-" + self._call_sign + "-"

        _LOGGER.warning(f"EAS ALERT!!: " + FullHeader)
        
        _LOGGER.debug("Appending Data to Alerts to be Spoken List")
        results.append((MinHeader, spoken_title, FullHeader))
        return results

    async def get_notifications(self):
        from .eventcodes import get_same_data, get_fips_data
        valid_severities = {'Unknown', 'Minor', 'Moderate', 'Severe', 'Extreme'}
        alert_number = 0
        results = []

        # Load data asynchronously
        SAME = await get_same_data()
        FIPS = await get_fips_data()

        # Update the weather sensor to get latest alerts
        await self._weather_sensor.async_update()
        
        # Get alerts from the internal weather sensor
        attributes = self._weather_sensor.extra_state_attributes
        if "alerts" in attributes:
            for alert in attributes['alerts']:
                alert_number += 1
                _LOGGER.info("Alert #" + str(alert_number))

                if alert.get('severity') not in valid_severities:
                    continue
                elif alert.get('severity') == 'Unknown':
                    continue
                else:
                    CardinalLocation='0'
                    
                    _LOGGER.debug("Gathering the Event Code from SAME data")
                    EventCode = ""
                    event = alert.get('event')
                    for item in SAME:
                       if item["Event Description"] == event:
                          EventCode = item["Event Code"]
                          break

                    if not EventCode:
                        _LOGGER.error(f"Event code not found for event: {event}")
                        continue

                    _LOGGER.debug("Gathering the Zone Data")
                    Zone = alert.get('zoneid').split(",")[0]
                    if len(Zone) >= 3:
                        ZoneState = Zone[:2]
                        ZoneID = str(int(Zone[2:].split("Z")[1]))
                    else:
                        _LOGGER.warning(f"Skipping Zone with less than 3 characters: {Zone}")
                        continue
                   
                    _LOGGER.debug("Gathering the County Data")
                    county_parts = alert.get('zoneid').split(",")
                    if len(county_parts) > 1:
                        County = county_parts[1]
                        if len(County) >= 3:
                            CountyState = County[:2]
                            CountyCode = str(int(County[2:].split("C")[1]))
                        else:
                            _LOGGER.warning(f"Skipping County with less than 3 characters: {County}")
                            continue
                    else:
                        # No county in zone ID, use zone state and a default county code
                        CountyState = ZoneState
                        CountyCode = "000"

                    _LOGGER.debug("Gathering the FIPs Data")
                    StateCode = "00"  # Default
                    for item in FIPS:
                       if item["State"] == ZoneState:
                          StateCode = item["State Code"]
                          break
                      
                    _LOGGER.debug("Gathering the Alert Spoken Title")
                    spoken_title = alert.get('spoken_title')
                    if spoken_title is None:
                        title = alert.get('title')
                        if title is None:
                            spoken_title = "No Title for this Alert!"
                            _LOGGER.warning(f"EAS ALERT!!: No Title!")
                        else:
                            spoken_title = title
                            _LOGGER.warning(f"EAS ALERT!!: " + spoken_title)
                    else:
                        spoken_title = alert.get('spoken_title')
                        _LOGGER.warning(f"EAS ALERT!!: " + spoken_title)

                    # Add description if enabled in configuration
                    if self._config_entry and self._config_entry.data.get('include_description', False):
                        description = alert.get('description', '')
                        if description:
                            what_section = self._extract_what_section(description)
                            if what_section:
                                spoken_title += f". {what_section}"
                                _LOGGER.debug("Added WHAT section to spoken title")

                    _LOGGER.debug("Parsing the Alert Dates")
                    BeginTime = parser.parse(alert.get('onset'))
                    EndTime = parser.parse(alert.get('endsExpires'))

                    diff = EndTime - BeginTime
                    PurgeTimeDifference = int(diff / timedelta(minutes=1))
                    PurgeTime = self.calculate_purge_time(PurgeTimeDifference)

                    _LOGGER.debug("Generating the EAS Protocol Header String")
                    IssueTime = BeginTime.strftime('%j') + BeginTime.strftime('%H') + BeginTime.strftime('%M')
                    MinHeader = "ZCZC-" + self._org + "-" + EventCode + "-" + CardinalLocation + StateCode.zfill(2) + CountyCode.zfill(3) + "+" + PurgeTime.zfill(4) + "-" + IssueTime 
                    FullHeader = MinHeader + "-" + self._call_sign + "-"

                    _LOGGER.warning(f"EAS ALERT!!: " + FullHeader)
                    
                    _LOGGER.debug("Appending Data to Alerts to be Spoken List")
                    results.append((MinHeader, spoken_title, FullHeader))
        else:
            _LOGGER.info("No weather alerts found")
        return results

    def calculate_purge_time(self, purge_diff):
        if purge_diff > MAX_PURGE_DIFFERENCE:
            return "9930"
        elif purge_diff >= HOUR_IN_MINUTES:
            hours, minutes = divmod(purge_diff, HOUR_IN_MINUTES)
            if purge_diff >= MAX_PURGE_DIFFERENCE:
                minutes = divmod(minutes, MINUTE_IN_SECONDS)[0] * MINUTE_IN_SECONDS
            else:
                minutes = divmod(minutes, MINUTE_IN_SECONDS / 2)[0] * (MINUTE_IN_SECONDS / 2)
            return f"{int(hours):02d}{int(minutes):02d}"
        else:
            quarters = divmod(purge_diff, MINUTE_IN_SECONDS / 15)[0] * (MINUTE_IN_SECONDS / 15)
            return f"00{int(quarters):02d}"

    async def get_header_audio(self, MinHeader, FullHeader):
        import asyncio
        AlertHeader = EASGen.genEAS(header=FullHeader, attentionTone=True, endOfMessage=False)
        header_path = "/config/www/" + MinHeader + "-Header.wav"
        _LOGGER.debug("Generating EAS Header Audio")
        
        # Run blocking operations in thread pool to avoid blocking the event loop
        await asyncio.to_thread(EASGen.export_wav, header_path, AlertHeader)
        header = await asyncio.to_thread(pydub.AudioSegment.from_wav, header_path)
        return (header, header_path)
        
    async def get_footer_audio(self, MinHeader):
        import asyncio
        AlertEndofMessage = EASGen.genEAS(header="", attentionTone=False, endOfMessage=True)
        footer_path = "/config/www/" + MinHeader + "-EndofMessage.wav"
        _LOGGER.debug("Generating EAS Footer Audio")
        
        # Run blocking operations in thread pool to avoid blocking the event loop
        await asyncio.to_thread(EASGen.export_wav, footer_path, AlertEndofMessage)
        footer = await asyncio.to_thread(pydub.AudioSegment.from_wav, footer_path)
        return (footer, footer_path)

    async def get_audio_url(self, alert):
        """Generate complete EAS audio and return accessible URL for media player."""
        try:
            # Generate notification data for this specific alert
            notification_data = await self.get_single_notification(alert)
            
            if not notification_data:
                _LOGGER.error("No notification data generated for alert")
                return None
            
            # Process the first (and should be only) notification
            MinHeader, title, FullHeader = notification_data[0]
            
            # Generate Header and Footer WAV files
            header_wav = await self.get_header_audio(MinHeader, FullHeader)
            header, header_path = header_wav
            footer_wav = await self.get_footer_audio(MinHeader)
            footer, footer_path = footer_wav
            
            # Generate TTS for the alert
            generated_speech = await self.get_tts(title, header_path, footer_path)
            
            if generated_speech is None or generated_speech == (None, None):
                _LOGGER.error("TTS generation failed for alert: %s", title)
                return None
            
            tts_message, tts_message_path = generated_speech
            
            # Combine the header, TTS message, and footer
            complete_audio = header + tts_message + footer
            
            # Cache the duration for the queue system
            self._last_audio_duration = len(complete_audio) / 1000.0  # Convert to seconds
            
            # Save combined audio to accessible location (www folder for unauthenticated access)
            import os
            import asyncio
            filename = f"{MinHeader}-Complete.wav"
            file_path = f"/config/www/{filename}"
            
            # Ensure directory exists
            await asyncio.to_thread(os.makedirs, os.path.dirname(file_path), exist_ok=True)
            
            # Export the complete audio (run in thread to avoid blocking)
            await asyncio.to_thread(complete_audio.export, file_path, format="wav")
            
            # Return the accessible URL for Home Assistant media player
            # Use /local/ endpoint which doesn't require authentication
            from homeassistant.helpers.network import get_url
            
            try:
                # Get the Home Assistant base URL
                base_url = get_url(self.hass)
                media_url = f"{base_url}/local/{filename}"
                _LOGGER.debug("Generated audio URL: %s", media_url)
                return media_url
            except Exception as e:
                _LOGGER.error("Failed to generate full URL: %s", e)
                # Fallback to relative path
                media_url = f"/local/{filename}"
                _LOGGER.debug("Using fallback URL: %s", media_url)
                return media_url
            
        except Exception as e:
            _LOGGER.error("Failed to generate audio URL for alert: %s", e)
            return None

    async def get_audio_duration(self, alert):
        """Get the duration of the complete EAS audio for the given alert."""
        try:
            # Check if we have cached duration from the last get_audio_url call
            if hasattr(self, '_last_audio_duration'):
                duration = self._last_audio_duration
                _LOGGER.debug("Using cached audio duration: %ss", duration)
                return duration
            
            # If not cached, generate the audio components to calculate duration
            notification_data = await self.get_single_notification(alert)
            
            if not notification_data:
                _LOGGER.error("No notification data generated for alert")
                return 30.0  # Default fallback duration
            
            # Process the first (and should be only) notification
            MinHeader, title, FullHeader = notification_data[0]
            
            # Generate Header and Footer WAV files
            header_wav = await self.get_header_audio(MinHeader, FullHeader)
            header, header_path = header_wav
            footer_wav = await self.get_footer_audio(MinHeader)
            footer, footer_path = footer_wav
            
            # Generate TTS for the alert
            generated_speech = await self.get_tts(title, header_path, footer_path)
            
            if generated_speech is None or generated_speech == (None, None):
                _LOGGER.error("TTS generation failed for alert: %s", title)
                return 30.0  # Default fallback duration
            
            tts_message, tts_message_path = generated_speech
            
            # Combine the header, TTS message, and footer
            complete_audio = header + tts_message + footer
            
            # Calculate duration in seconds
            duration = len(complete_audio) / 1000.0
            
            # Cache for future use
            self._last_audio_duration = duration
            
            _LOGGER.debug("Calculated audio duration: %ss", duration)
            return duration
            
        except Exception as e:
            _LOGGER.error("Failed to calculate audio duration for alert: %s", e)
            return 30.0  # Default fallback duration

    def _extract_what_section(self, description: str) -> str:
        """Extract the WHAT section from weather alert description."""
        import re
        
        # Look for the WHAT section
        what_match = re.search(r'\* WHAT\.\.\.(.+?)(?=\n\s*\* [A-Z]|\Z)', description, re.DOTALL | re.IGNORECASE)
        
        if what_match:
            what_text = what_match.group(1).strip()
            # Clean up the text - remove extra whitespace and line breaks
            what_text = re.sub(r'\s+', ' ', what_text)
            # Remove any remaining asterisks or bullets
            what_text = re.sub(r'^[\*\-\•]\s*', '', what_text)
            return what_text
        
        return ""

    @staticmethod
    def get_supported_langs() -> list:
        """Returns list of supported languages. Note: the state determines the provides language automatically."""
        return ["af", "ar", "hy", "az", "be", "bs", "bg", "ca", "zh", "hr", "cs", "da", "nl", "en-us", "en", "et", "fi", "fr", "gl", "de", "el", "he", "hi", "hu", "is", "id", "it", "ja", "kn", "kk", "ko", "lv", "lt", "mk", "ms", "mr", "mi", "ne", "no", "fa", "pl", "pt", "ro", "ru", "sr", "sk", "sl", "es", "sw", "sv", "tl", "ta", "th", "tr", "uk", "ur", "vi", "cy"]
