"""EAS Header and Footer Module"""
import requests
import sys
import logging
from EASGen import EASGen
import pydub
from .const import AVAIL_LANGUAGES
from datetime import datetime, timedelta, timezone
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from dateutil import parser

_LOGGER = logging.getLogger(__name__)

class EASGenTTSEngine:
    def __init__(self, hass, sensor: str, tts_engine: str, org: str, call_sign: str, voice: str, language: str):
        self.hass = hass
        self._sensor = sensor
        self._tts_engine = tts_engine
        self._org = org
        self._call_sign = call_sign
        self._voice = voice
        self._language = language
        self._languages = AVAIL_LANGUAGES

    def get_tts(self, text: str, header_path, footer_path):
        """Generates TTS WAV data"""
        result = self.hass.services.call(
            "chime_tts",
            "say_url",
            {
                "tts_platform": self._tts_engine,
                "message": text
            },
            return_response=True,
            blocking=True
        )
        
        media_source = result['media_content_id'].split("://media_source")[1].split("local")[1]
        tts_message_path = "/media" + media_source
        tts_message = pydub.AudioSegment.from_mp3(tts_message_path)

        return (tts_message, tts_message_path)
        
    def get_notifications(self):
        from .eventcodes import SAME, FIPS
        # Protocol Header Reference:
        # https://www.govinfo.gov/content/pkg/CFR-2010-title47-vol1/xml/CFR-2010-title47-vol1-sec11-31.xml
        # <Preamble>ZCZC-ORG-EEE-PSSCCC+TTTT-JJJHHMM-LLLLLLLL-
        alert_number = 0
        attributes = self.hass.states.get(self._sensor).attributes
        
        # Check if the "integration" attribute contains "weatheralerts" for the user selected sensor
        if "integration" in attributes and "weatheralerts" in attributes["integration"].lower():
            # Process weather alerts
            for alert in attributes['alerts']:
                alert_number += 1
                _LOGGER.info("Alert #" + str(alert_number))
                if alert is None:
                    continue
                elif alert.get('severity') == 'Unknown':
                    continue
                else:
                    CardinalLocation='0'
                    # The use of county subdivisions will probably be rare and generally for oddly shaped or unusually large counties. Defaulting to All
                    # https://www.govinfo.gov/content/pkg/CFR-2010-title47-vol1/xml/CFR-2010-title47-vol1-sec11-31.xml

                    # Get the Event Code
                    EventCode = ""
                    event = alert.get('event')
                    for item in SAME:
                       if item["Event Description"] == event:
                          EventCode = item["Event Code"]
                          break

                    if not EventCode:
                        _LOGGER.error(f"Event code not found for event: {event}")
                        continue

                    # Get the Zone Data
                    Zone = alert.get('zoneid').split(",")[0]
                    if len(Zone) >= 3:
                        ZoneState = Zone[:2]
                        ZoneID = str(int(Zone[2:].split("Z")[1]))
                    else:
                        _LOGGER.warning(f"Skipping Zone with less than 3 characters: {Zone}")
                        continue
                   
                    # Get the County Data
                    County = alert.get('zoneid').split(",")[1]
                    if len(County) >= 3:
                        CountyState = County[:2]
                        CountyCode = str(int(County[2:].split("C")[1]))
                    else:
                        _LOGGER.warning(f"Skipping County with less than 3 characters: {County}")
                        continue

                    for item in FIPS:
                       if item["State"] == ZoneState:
                          StateCode = item["State Code"]
                          break
                      
                    # Get the Titlee  
                    title = alert.get('title')
                    _LOGGER.warning(f"EAS ALERT!!: " + title)

                    ## Generating Date String
                    BeginTime = parser.parse(alert.get('onset'))
                    EndTime = parser.parse(alert.get('endsExpires'))

                    diff = EndTime - BeginTime
                    PurgeTimeDifference = int(diff / timedelta(minutes=1))
                    if PurgeTimeDifference > 5940:
                      PurgeTime = "9930"
                    elif 360 < PurgeTimeDifference < 5940:
                      PurgeDifference = divmod(diff.total_seconds(), 3600)
                      PurgeTime = str(int(PurgeDifference[0])).zfill(2) + str(int(divmod(divmod(PurgeDifference[1], 60)[0], 60)[0]) * 60).zfill(2)
                    elif 60 < PurgeTimeDifference < 360:
                      PurgeDifference = divmod(diff.total_seconds(), 3600)
                      PurgeTime = str(int(PurgeDifference[0])).zfill(2) + str(int(divmod(divmod(PurgeDifference[1], 60)[0], 30)[0]) * 30).zfill(2)
                    elif PurgeTimeDifference < 60:
                      PurgeDifference = divmod(diff.total_seconds(), 60)
                      PurgeTime = "00" + str(int(divmod(PurgeDifference[0], 15)[0] * 15)).zfill(2) 

                    ## Creating EAS Protocol Header
                    IssueTime = BeginTime.strftime('%j') + BeginTime.strftime('%H') + BeginTime.strftime('%M')
                    MinHeader = "ZCZC-" + self._org + "-" + EventCode + "-" + CardinalLocation + StateCode.zfill(2) + CountyCode.zfill(3) + "+" + PurgeTime.zfill(4) + "-" + IssueTime 
                    FullHeader = MinHeader + "-" + self._call_sign + "-"

                    ## Logging EAS Protocol Header
                    _LOGGER.warning(f"EAS ALERT!!: " + FullHeader)
                    return (MinHeader, title, FullHeader)
        else:
            _LOGGER.info("Weather alerts integration not found")

    def get_header_audio(self, MinHeader, FullHeader):
        AlertHeader = EASGen.genEAS(header=FullHeader, attentionTone=True, endOfMessage=False)
        header_path = "/media/tts/" + MinHeader + "-Header.wav"
        EASGen.export_wav(header_path, AlertHeader)
        header = pydub.AudioSegment.from_wav(header_path)
        return (header, header_path)
        
    def get_footer_audio(self, MinHeader):
        AlertEndofMessage = EASGen.genEAS(header="", attentionTone=False, endOfMessage=True)
        footer_path = "/media/tts/" + MinHeader + "-EndofMessage.wav"
        EASGen.export_wav(footer_path, AlertEndofMessage)
        footer = pydub.AudioSegment.from_wav(footer_path)
        return (footer, footer_path)

    @staticmethod
    def get_supported_langs() -> list:
        """Returns list of supported languages. Note: the state determines the provides language automatically."""
        return ["af", "ar", "hy", "az", "be", "bs", "bg", "ca", "zh", "hr", "cs", "da", "nl", "en-us", "en", "et", "fi", "fr", "gl", "de", "el", "he", "hi", "hu", "is", "id", "it", "ja", "kn", "kk", "ko", "lv", "lt", "mk", "ms", "mr", "mi", "ne", "no", "fa", "pl", "pt", "ro", "ru", "sr", "sk", "sl", "es", "sw", "sv", "tl", "ta", "th", "tr", "uk", "ur", "vi", "cy"]

