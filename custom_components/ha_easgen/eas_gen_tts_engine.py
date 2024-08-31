"""EAS Header and Footer Module"""
import requests
import sys
import logging
from EASGen import EASGen
from pydub.playback import play
from datetime import datetime, timedelta, timezone
from dateutil import parser
from .eventcodes import SAME, FIPS

_LOGGER = logging.getLogger(__name__)

class EASGenTTSEngine:
    def __init__(self, sensor: str, tts_engine: str, org: str, call_sign: str, state: str, zone: int, county: str):
        self._sensor = sensor
        self._tts_engine = tts_engine
        self._org = org
        self._call_sign = call_sign
        self._state = state
        self._zone = zone
        self._county = county

    def get_tts(self, text: str):
        """ Makes request to Standard TTS engine to convert text into audio"""

        headers: dict = {"Authorization": f"Bearer {self._org}"} if self._org else {}
        data: dict = {
            "state": self._state,
            "input": text,
            "call_sign": self._call_sign,
            "response_format": "wav",
            "zone": self._zone
        }
        return requests.post(self._county, headers=headers, json=data)

    def get_notifications(self, sensor: str):
        alert_number = 0
        _LOGGER.warning("Entered get_notifications function")
        _LOGGER.warning(sensor)
        for alert in sensor:
                alert_number += 1
                #log.warning("Alert #" + str(alert_number))
                if alert == None:
                  continue
                elif alert.get('severity') == 'Unknown':
                  continue
                else:
                  log.warning(alert)
                  event = alert.get('event')
                  Oridnal='0'

                  for item in SAME:
                     if item["Event Description"] == event:
                        EventCode = item["Event Code"]
                        break

                  zoneids = alert.get('zoneid')

                  Zone = zoneids.split(",")[0]
                  ZoneState = Zone.split("Z")[0]
                  ZoneID = str(int(Zone.split("Z")[1]))

                  County = zoneids.split(",")[1]
                  CountyState = County.split("C")[0]
                  CountyCode = str(int(County.split("C")[1]))

                  for item in FIPS:
                     if item["State"] == ZoneState:
                        StateCode = item["State Code"]
                        break
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
                  MinHeader = "ZCZC-" + ORG + "-" + EventCode + "-" + Oridnal + StateCode.zfill(2) + CountyCode.zfill(3) + "+" + PurgeTime.zfill(4) + "-" + IssueTime 
                  FullHeader = MinHeader + "-" + CallSignID + "-"

                  ## Logging EAS Protocol Header
                  log.warning(f"EAS ALERT!!: " + FullHeader)

                  ## Use EASGen to Generate Alert Header
                  pyscript_path = "pyscript/EAS/Alerts/"

                  ## Header
                  AlertHeader = EASGen.genEAS(header=FullHeader, attentionTone=True, endOfMessage=False)

                  ##  Exporting Header to WAV file
                  EASGen.export_wav(pyscript_path + MinHeader + "-Header.wav", AlertHeader)
                    
                  ## Footer
                  AlertEndofMessage = EASGen.genEAS(header="", attentionTone=False, endOfMessage=True)

                  ##  Exporting Footer to WAV file
                  EASGen.export_wav(pyscript_path + MinHeader + "-EndofMessage.wav", AlertEndofMessage)

                  ## Setting Volume -- Future

                  ## Play Header -- Future

                  ## Play TTS -- Future

                  ## Play Footer -- Future
                  
        pass

    def generate_header(url, headers, MinHeader, path):
        # Protocol Header Reference:
        # https://www.govinfo.gov/content/pkg/CFR-2010-title47-vol1/xml/CFR-2010-title47-vol1-sec11-31.xml
        # <Preamble>ZCZC-ORG-EEE-PSSCCC+TTTT-JJJHHMM-LLLLLLLL-


        HeaderFile = str(path) + str(MinHeader) + "-Header.wav"
        file = open(HeaderFile, 'rb')
        HeaderParams = {"uploadType": "media", "name": "Header.wav"}
        Headerresponse = requests.post(url, params=HeaderParams, headers=headers, data=file)
        return Headerresponse


    def generate_footer(url, headers, MinHeader, path):
        EndofMessageFile = str(path) + str(MinHeader) + "-EndofMessage.wav"
        file = open(EndofMessageFile, 'rb')
        EndofMessageParams = {"uploadType": "media", "name": "EndofMessage.wav"}
        EndofMessageresponse = requests.post(url, params=EndofMessageParams, headers=headers, data=file)
        return EndofMessageresponse

    @staticmethod
    def get_supported_langs() -> list:
        """Returns list of supported languages. Note: the state determines the provides language automatically."""
        return ["af", "ar", "hy", "az", "be", "bs", "bg", "ca", "zh", "hr", "cs", "da", "nl", "en", "et", "fi", "fr", "gl", "de", "el", "he", "hi", "hu", "is", "id", "it", "ja", "kn", "kk", "ko", "lv", "lt", "mk", "ms", "mr", "mi", "ne", "no", "fa", "pl", "pt", "ro", "ru", "sr", "sk", "sl", "es", "sw", "sv", "tl", "ta", "th", "tr", "uk", "ur", "vi", "cy"]
