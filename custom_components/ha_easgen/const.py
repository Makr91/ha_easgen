"""Constants for the Emergency Alert System Generator integration."""
DOMAIN = "ha_easgen"
ICON = "mdi:flash-alert"
NAME = "Emergency Alert System"
SENSOR = "sensor.weatheralerts"
CALL_SIGN = "KF5NTR"
ORG = "EAS"
ORGS = [
    "EAS", # EAS Participant 
    "WXR", # National Weather Service 
    "PEP", # Primary Entry Point System 
    "CIV"  # Civil authorities 
]
TTS_ENGINE = "tts_engine"
UNIQUE_ID = 'unique_id'
AVAIL_LANGUAGES = ''
LANGUAGE = 'en-us'
VOICE = 'voice'
AVAIL_LANGUAGES = ["af", "ar", "hy", "az", "be", "bs", "bg", "ca", "zh", "hr", "cs", "da", "nl", "en", "en-us", "et", "fi", "fr", "gl", "de", "el", "he", "hi", "hu", "is", "id", "it", "ja", "kn", "kk", "ko", "lv", "lt", "mk", "ms", "mr", "mi", "ne", "no", "fa", "pl", "pt", "ro", "ru", "sr", "sk", "sl", "es", "sw", "sv", "tl", "ta", "th", "tr", "uk", "ur", "vi", "cy"]
MEDIA_PLAYER = "media_player.emergency_alert_system"