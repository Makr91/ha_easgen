"""Platform for Emergency Alert System"""
import logging

from EASGen import EASGen
from pydub.playback import play
from datetime import datetime, timedelta, timezone
from dateutil import parser
import requests
import sys

# Reference:
# https://www.govinfo.gov/content/pkg/CFR-2010-title47-vol1/xml/CFR-2010-title47-vol1-sec11-31.xml
# <Preamble>ZCZC-ORG-EEE-PSSCCC+TTTT-JJJHHMM-LLLLLLLL-

@service
def EAS():
    from EventCodes import SAME, FIPS
    from PlayWav import playEndofMessage, playHeader
    if automation.spoken_weather_alerts == 'on':
          ORG="EAS"
          CallSignID = "KF5NTR//"
          alert_number = 0
          for alert in sensor.champaign.alerts:
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

                    IssueTime = BeginTime.strftime('%j') + BeginTime.strftime('%H') + BeginTime.strftime('%M')
                    MinHeader = "ZCZC-" + ORG + "-" + EventCode + "-" + Oridnal + StateCode.zfill(2) + CountyCode.zfill(3) + "+" + PurgeTime.zfill(4) + "-" + IssueTime 
                    FullHeader = MinHeader + "-" + CallSignID + "-"

                    log.warning(f"EAS ALERT!!: " + FullHeader)
                    AlertHeader = EASGen.genEAS(header=FullHeader, attentionTone=True, endOfMessage=False)
                    AlertEndofMessage = EASGen.genEAS(header="", attentionTone=False, endOfMessage=True)
                    pyscript_path = "pyscript/EAS/Alerts/"
                    EASGen.export_wav(pyscript_path + MinHeader + "-Header.wav", AlertHeader)
                    EASGen.export_wav(pyscript_path + MinHeader + "-EndofMessage.wav", AlertEndofMessage)
                    service.call("rest_command", "rhasspy_set_volume", payload="0.2", sites="rhasspy01")

                    wav_url = "http://rhasspy-01:12101/api/play-wav"
                    wav_headers = {"Content-Type": "audio/wav" }

                    task.executor(playHeader, wav_url, wav_headers, MinHeader, pyscript_path)
                    service.call("rest_command", "rhasspy_speak", payload=alert.get('title'), sites="rhasspy01")
                    task.executor(playEndofMessage, wav_url, wav_headers, MinHeader, pyscript_path)
          pass
    else:
        pass
