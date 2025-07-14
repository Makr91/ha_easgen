"""Constants for the Emergency Alert System Generator integration."""
DEFAULT_NAME = "Emergency Alert System"
MANUFACTURER = "@Makr91"

DOMAIN = "ha_easgen"

STATE = "state"
ZONE = "zone"
COUNTY = "county"
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
MEDIA_PLAYERS = 'media_players'
DISABLE_TTS = 'disable_tts'
INCLUDE_DESCRIPTION = 'include_description'

WEATHER_API_URL = "https://api.weather.gov/alerts/active?zone={}"
WEATHER_ID_CHECK_URL = "https://alerts.weather.gov/cap/wwaatmget.php?x={}&y=0"
ID_CHECK_ERRORS = ["? invalid county", "? invalid zone"]
AVAIL_LANGUAGES = ["af", "ar", "hy", "az", "be", "bs", "bg", "ca", "zh", "hr", "cs", "da", "nl", "en", "en-us", "et", "fi", "fr", "gl", "de", "el", "he", "hi", "hu", "is", "id", "it", "ja", "kn", "kk", "ko", "lv", "lt", "mk", "ms", "mr", "mi", "ne", "no", "fa", "pl", "pt", "ro", "ru", "sr", "sk", "sl", "es", "sw", "sv", "tl", "ta", "th", "tr", "uk", "ur", "vi", "cy"]
MAX_PURGE_DIFFERENCE = 5940
HOUR_IN_MINUTES = 60
MINUTE_IN_SECONDS = 60

# Alert Management Constants
MAX_ALERTS = 5
SEVERITY_LEVELS = ["Minor", "Moderate", "Severe", "Extreme"]
ANNOUNCEMENT_DELAY = 5  # seconds between multiple alerts
ALERT_TRACK_FILE = "alert_tracking.json"

# Alert Entity Names
ALERT_SENSOR_PREFIX = "ha_easgen_alert"
ALERTS_SUMMARY_SENSOR = "ha_easgen_alerts"

# Alert Icons Mapping
ALERT_ICONS = {
    '911 Telephone Outage Emergency': 'mdi:phone-alert',
    'Administrative Message': 'mdi:message-text',
    'Air Quality Alert': 'mdi:blur',
    'Air Stagnation Advisory': 'mdi:blur',
    'Arroyo And Small Stream Flood Advisory': 'mdi:water-alert',
    'Ashfall Advisory': 'mdi:cloud-alert',
    'Ashfall Warning': 'mdi:cloud-alert',
    'Avalanche Advisory': 'mdi:alert',
    'Avalanche Warning': 'mdi:alert',
    'Avalanche Watch': 'mdi:alert',
    'Beach Hazards Statement': 'mdi:beach',
    'Blizzard Warning': 'mdi:snowflake-alert',
    'Blizzard Watch': 'mdi:snowflake-alert',
    'Blowing Dust Advisory': 'mdi:blur',
    'Blowing Dust Warning': 'mdi:blur',
    'Brisk Wind Advisory': 'mdi:weather-windy',
    'Child Abduction Emergency': 'mdi:human-male-child',
    'Civil Danger Warning': 'mdi:image-filter-hdr',
    'Civil Emergency Message': 'mdi:image-filter-hdr',
    'Coastal Flood Advisory': 'mdi:waves',
    'Coastal Flood Statement': 'mdi:waves',
    'Coastal Flood Warning': 'mdi:waves',
    'Coastal Flood Watch': 'mdi:waves',
    'Cold Weather Advisory': 'mdi:snowflake',
    'Dense Fog Advisory': 'mdi:weather-fog',
    'Dense Smoke Advisory': 'mdi:smoke',
    'Dust Advisory': 'mdi:blur',
    'Dust Storm Warning': 'mdi:blur',
    'Earthquake Warning': 'mdi:alert',
    'Evacuation - Immediate': 'mdi:exit-run',
    'Excessive Heat Warning': 'mdi:thermometer-plus',
    'Excessive Heat Watch': 'mdi:thermometer-plus',
    'Extreme Cold Warning': 'mdi:thermometer-minus',
    'Extreme Cold Watch': 'mdi:thermometer-minus',
    'Extreme Fire Danger': 'mdi:fire-alert',
    'Extreme Wind Warning': 'mdi:weather-windy',
    'Fire Warning': 'mdi:fire-alert',
    'Fire Weather Watch': 'mdi:fire-alert',
    'Flash Flood Statement': 'mdi:water-alert',
    'Flash Flood Warning': 'mdi:water-alert',
    'Flash Flood Watch': 'mdi:water-alert',
    'Flood Advisory': 'mdi:water-alert',
    'Flood Statement': 'mdi:water-alert',
    'Flood Warning': 'mdi:water-alert',
    'Flood Watch': 'mdi:water-alert',
    'Freeze Warning': 'mdi:thermometer-minus',
    'Freeze Watch': 'mdi:thermometer-minus',
    'Freezing Fog Advisory': 'mdi:snowflake-alert',
    'Freezing Rain Advisory': 'mdi:snowflake-alert',
    'Freezing Spray Advisory': 'mdi:snowflake-alert',
    'Frost Advisory': 'mdi:snowflake-alert',
    'Gale Warning': 'mdi:weather-windy',
    'Gale Watch': 'mdi:weather-windy',
    'Hard Freeze Warning': 'mdi:thermometer-minus',
    'Hard Freeze Watch': 'mdi:thermometer-minus',
    'Hazardous Materials Warning': 'mdi:radioactive',
    'Hazardous Seas Warning': 'mdi:sail-boat',
    'Hazardous Seas Watch': 'mdi:sail-boat',
    'Hazardous Weather Outlook': 'mdi:message-alert',
    'Heat Advisory': 'mdi:thermometer-plus',
    'Heavy Freezing Spray Warning': 'mdi:snowflake-alert',
    'Heavy Freezing Spray Watch': 'mdi:snowflake-alert',
    'High Surf Advisory': 'mdi:surfing',
    'High Surf Warning': 'mdi:surfing',
    'High Wind Warning': 'mdi:weather-windy',
    'High Wind Watch': 'mdi:weather-windy',
    'Hurricane Force Wind Warning': 'mdi:weather-hurricane',
    'Hurricane Force Wind Watch': 'mdi:weather-hurricane',
    'Hurricane Local Statement': 'mdi:weather-hurricane',
    'Hurricane Warning': 'mdi:weather-hurricane',
    'Hurricane Watch': 'mdi:weather-hurricane',
    'Hydrologic Advisory': 'mdi:message-text',
    'Hydrologic Outlook': 'mdi:message-text',
    'Ice Storm Warning': 'mdi:snowflake-alert',
    'Lake Effect Snow Advisory': 'mdi:snowflake-alert',
    'Lake Effect Snow Warning': 'mdi:snowflake-alert',
    'Lake Effect Snow Watch': 'mdi:snowflake-alert',
    'Lake Wind Advisory': 'mdi:weather-windy',
    'Lakeshore Flood Advisory': 'mdi:waves-arrow-up',
    'Lakeshore Flood Statement': 'mdi:waves-arrow-up',
    'Lakeshore Flood Warning': 'mdi:waves-arrow-up',
    'Lakeshore Flood Watch': 'mdi:waves-arrow-up',
    'Law Enforcement Warning': 'mdi:car-emergency',
    'Local Area Emergency': 'mdi:alert',
    'Low Water Advisory': 'mdi:wave',
    'Marine Weather Statement': 'mdi:sail-boat',
    'Nuclear Power Plant Warning': 'mdi:radioactive',
    'Radiological Hazard Warning': 'mdi:biohazard',
    'Red Flag Warning': 'mdi:fire-alert',
    'Rip Current Statement': 'mdi:surfing',
    'Severe Thunderstorm Warning': 'mdi:weather-lightning',
    'Severe Thunderstorm Watch': 'mdi:weather-lightning',
    'Severe Weather Statement': 'mdi:message-text',
    'Shelter In Place Warning': 'mdi:account-box',
    'Short Term Forecast': 'mdi:message-text',
    'Small Craft Advisory': 'mdi:sail-boat',
    'Small Craft Advisory For Hazardous Seas': 'mdi:sail-boat',
    'Small Craft Advisory For Rough Bar': 'mdi:sail-boat',
    'Small Craft Advisory For Winds': 'mdi:sail-boat',
    'Small Stream Flood Advisory': 'mdi:water-alert',
    'Snow Squall Warning': 'mdi:snowflake-alert',
    'Special Marine Warning': 'mdi:sail-boat',
    'Special Weather Statement': 'mdi:message-alert',
    'Storm Surge Warning': 'mdi:waves-arrow-up',
    'Storm Surge Watch': 'mdi:waves-arrow-up',
    'Storm Warning': 'mdi:weather-lightning',
    'Storm Watch': 'mdi:weather-lightning',
    'Test': 'mdi:message-text',
    'Tornado Warning': 'mdi:weather-tornado',
    'Tornado Watch': 'mdi:weather-tornado',
    'Tropical Depression Local Statement': 'mdi:weather-hurricane',
    'Tropical Storm Local Statement': 'mdi:weather-hurricane',
    'Tropical Storm Warning': 'mdi:weather-hurricane',
    'Tropical Storm Watch': 'mdi:weather-hurricane',
    'Tsunami Advisory': 'mdi:waves-arrow-up',
    'Tsunami Warning': 'mdi:waves-arrow-up',
    'Tsunami Watch': 'mdi:waves-arrow-up',
    'Typhoon Local Statement': 'mdi:weather-hurricane',
    'Typhoon Warning': 'mdi:weather-hurricane',
    'Typhoon Watch': 'mdi:weather-hurricane',
    'Urban And Small Stream Flood Advisory': 'mdi:home-flood',
    'Volcano Warning': 'mdi:image-filter-hdr',
    'Wind Advisory': 'mdi:weather-windy',
    'Wind Chill Advisory': 'mdi:thermometer-minus',
    'Wind Chill Warning': 'mdi:thermometer-minus',
    'Wind Chill Watch': 'mdi:thermometer-minus',
    'Winter Storm Warning': 'mdi:snowflake-alert',
    'Winter Storm Watch': 'mdi:snowflake-alert',
    'Winter Weather Advisory': 'mdi:snowflake-alert',
    'Extreme Heat Warning': 'mdi:thermometer-plus',
}
