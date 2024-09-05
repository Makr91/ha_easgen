"""Constants for the Emergency Alert System Generator integration."""
NAME = "Emergency Alert System"
MANUFACTURER = "@Makr91"

DOMAIN = "ha_easgen"

SENSOR = "sensor"
CALL_SIGN = "call_sign"
ORG = "org"
ORGS = [
    "EAS", # EAS Participant 
    "WXR", # National Weather Service 
    "PEP", # Primary Entry Point System 
    "CIV"  # Civil authorities 
]
TTS_ENGINE = "tts_engine"
UNIQUE_ID = 'unique_id'
LANGUAGE = 'language'
VOICE = 'voice'
AVAIL_LANGUAGES = ["af", "ar", "hy", "az", "be", "bs", "bg", "ca", "zh", "hr", "cs", "da", "nl", "en", "en-us", "et", "fi", "fr", "gl", "de", "el", "he", "hi", "hu", "is", "id", "it", "ja", "kn", "kk", "ko", "lv", "lt", "mk", "ms", "mr", "mi", "ne", "no", "fa", "pl", "pt", "ro", "ru", "sr", "sk", "sl", "es", "sw", "sv", "tl", "ta", "th", "tr", "uk", "ur", "vi", "cy"]
