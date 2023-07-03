"""EAS Header and Footer Module"""
import requests

def playHeader(url, headers, MinHeader, path):
    HeaderFile = str(path) + str(MinHeader) + "-Header.wav"
    file = open(HeaderFile, 'rb')
    HeaderParams = {"uploadType": "media", "name": "Header.wav"}
    Headerresponse = requests.post(url, params=HeaderParams, headers=headers, data=file)
    return Headerresponse

def playEndofMessage(url, headers, MinHeader, path):
    EndofMessageFile = str(path) + str(MinHeader) + "-EndofMessage.wav"
    file = open(EndofMessageFile, 'rb')
    EndofMessageParams = {"uploadType": "media", "name": "EndofMessage.wav"}
    EndofMessageresponse = requests.post(url, params=EndofMessageParams, headers=headers, data=file)
    return EndofMessageresponse
