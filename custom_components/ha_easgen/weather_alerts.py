"""
Internal weather alerts functionality for EAS Generator.
"""
import sys
import logging
import asyncio
import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.const import __version__

from .const import WEATHER_API_URL, ZONE_METADATA_URL, COUNTY_METADATA_URL

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "accept": "application/geo+json",
    "user-agent": f"HomeAssistant/{__version__}",
}


class EASGenWeatherAlertsSensor(SensorEntity):
    """Internal weather alerts sensor for EAS Generator."""

    def __init__(self, hass: HomeAssistant, state: str, zone: str, county: str = "", config_entry=None):
        """Initialize the weather alerts sensor."""
        self.hass = hass
        self.zone_state = state.upper()
        self.zone_config = zone
        self.county_config = county
        self.config_entry = config_entry
        self.session = async_create_clientsession(hass)
        self._attr_native_value = 0
        self.connected = True
        self.exception = None
        self._attr_extra_state_attributes = {}
        self._alert_callback = None
        
        # Process zone configuration
        zone_formatted = zone
        if len(zone_formatted) == 1:
            zone_formatted = f"00{zone_formatted}"
        elif len(zone_formatted) == 2:
            zone_formatted = f"0{zone_formatted}"
        
        if len(zone_formatted) == 3:
            self.zoneid = f"{self.zone_state}Z{zone_formatted}"
        else:
            raise ValueError(f"Invalid zone ID '{zone}' - must be 1-3 digits")
        
        # Process county configuration
        if county:
            county_formatted = county
            if len(county_formatted) == 1:
                county_formatted = f"00{county_formatted}"
            elif len(county_formatted) == 2:
                county_formatted = f"0{county_formatted}"
            
            if len(county_formatted) == 3:
                self.countyid = f"{self.zone_state}C{county_formatted}"
                self.feedid = f"{self.zoneid},{self.countyid}"
            else:
                raise ValueError(f"Invalid county ID '{county}' - must be 1-3 digits")
        else:
            self.countyid = None
            self.feedid = self.zoneid
        
        self._attr_name = f"Weather Alerts {self.zone_state}Z{zone_formatted}"
        if county:
            self._attr_name += f" {self.zone_state}C{county_formatted}"
        
        self._attr_unit_of_measurement = "Alerts"
        self._attr_icon = "mdi:alert-octagram"
        self._attr_unique_id = f"ha_easgen_weather_alerts_{self.feedid}".replace(",", "")

    async def async_validate_ids(self):
        """Validate zone and county IDs with weather.gov."""
        try:
            # Get the actual name from the Metadata API and validate Zone ID
            zone_url = ZONE_METADATA_URL.format(self.zoneid)
            _LOGGER.debug("Getting zone metadata from API with URL: %s", zone_url)
            async with async_timeout.timeout(20):
                response = await self.session.get(
                    zone_url,
                    headers=HEADERS
                )
                _LOGGER.debug("Zone name lookup response status: %s", response.status)
                
                if response.status == 404:
                    _LOGGER.error("Zone ID '%s' not found (404 status)", self.zoneid)
                    raise ValueError(f"Zone ID '{self.zoneid}' not found")

                data = await response.json()
                _LOGGER.debug("Zone name lookup response keys: %s", list(data.keys()) if isinstance(data, dict) else "Not a dict")
                
                if "status" in data and data["status"] == 404:
                    _LOGGER.error("Zone ID '%s' not found (404 status)", self.zoneid)
                    raise ValueError(f"Zone ID '{self.zoneid}' not found")
                
                # Update sensor name with the actual zone name
                if "properties" in data and "name" in data["properties"]:
                    zone_name = data["properties"]["name"]
                    self._attr_name = f"Weather Alerts {zone_name} ({self.zoneid})"
                else:
                    _LOGGER.warning("No 'name' property found in zone metadata")

            # Check county ID if provided
            if self.countyid:
                county_check_url = COUNTY_METADATA_URL.format(self.countyid)
                _LOGGER.debug("Validating county ID '%s' with URL: %s", self.countyid, county_check_url)
                async with async_timeout.timeout(20):
                    county_check_response = await self.session.get(
                        county_check_url,
                        headers=HEADERS
                    )
                    _LOGGER.debug("County validation response status: %s", county_check_response.status)
                    
                    if county_check_response.status == 404:
                        _LOGGER.error("County ID '%s' not found (404 status)", self.countyid)
                        raise ValueError(f"Invalid county ID '{self.countyid}'")

                    county_data = await county_check_response.json()
                    
                    if "status" in county_data and county_data["status"] == 404:
                        _LOGGER.error("County ID validation failed - found error in response for '%s'", self.countyid)
                        raise ValueError(f"Invalid county ID '{self.countyid}'")
                    _LOGGER.debug("County ID '%s' validation successful", self.countyid)

        except Exception as e:
            _LOGGER.error("Failed to validate zone/county IDs: %s", e)
            raise

    async def async_update(self):
        """Update weather alerts data."""
        alerts = []

        try:
            alerts_api_url = WEATHER_API_URL.format(self.feedid)
            _LOGGER.debug("[%s] Fetching weather alerts from URL: %s", self.feedid, alerts_api_url)
            async with async_timeout.timeout(10):
                response = await self.session.get(
                    alerts_api_url,
                    headers=HEADERS
                )
                _LOGGER.debug("[%s] Weather alerts API response status: %s", self.feedid, response.status)
                
                if response.status != 200:
                    self._attr_native_value = "unavailable"
                    _LOGGER.warning(
                        "[%s] API outage - unable to download from weather.gov - HTTP status %s",
                        self.feedid,
                        response.status
                    )
                    return

                data = await response.json()
                _LOGGER.debug("[%s] Weather alerts API response keys: %s", self.feedid, list(data.keys()) if isinstance(data, dict) else "Not a dict")

                if data.get("features") is not None:
                    features_count = len(data["features"])
                    _LOGGER.debug("[%s] Found %d alert features in response", self.feedid, features_count)
                    
                    for i, alert in enumerate(data["features"]):
                        if alert.get("properties") is not None:
                            properties = alert["properties"]
                            parameters = properties.get("parameters", {})
                            
                            # Log basic alert info
                            alert_event = properties.get("event", "Unknown")
                            alert_severity = properties.get("severity", "Unknown")
                            alert_id = properties.get("id", "Unknown")
                            _LOGGER.debug("[%s] Processing alert %d/%d: %s (Severity: %s, ID: %s)", 
                                        self.feedid, i+1, features_count, alert_event, alert_severity, alert_id)
                            
                            # Helper to safely extract single string from potential list parameters
                            def get_param(key):
                                val = parameters.get(key, "null")
                                if isinstance(val, list):
                                    return val[0] if val else "null"
                                return val

                            # Set endsExpires field
                            if properties.get("ends") is None:
                                properties["endsExpires"] = properties.get("expires", "null")
                            else:
                                properties["endsExpires"] = properties.get("ends")
                            
                            # Format alert data
                            alert_data = {
                                "area": properties.get("areaDesc", "null"),
                                "certainty": properties.get("certainty", "null"),
                                "description": properties.get("description", "null"),
                                "ends": properties.get("ends", "null"),
                                "event": properties.get("event", "null"),
                                "instruction": properties.get("instruction", "null"),
                                "response": properties.get("response", "null"),
                                "sent": properties.get("sent", "null"),
                                "severity": properties.get("severity", "null"),
                                "title": properties.get("headline", "null").split(" by ")[0],
                                "urgency": properties.get("urgency", "null"),
                                "NWSheadline": get_param("NWSheadline"),
                                "hailSize": get_param("hailSize"),
                                "windGust": get_param("windGust"),
                                "waterspoutDetection": get_param("waterspoutDetection"),
                                "effective": properties.get("effective", "null"),
                                "expires": properties.get("expires", "null"),
                                "endsExpires": properties.get("endsExpires", "null"),
                                "onset": properties.get("onset", "null"),
                                "status": properties.get("status", "null"),
                                "messageType": properties.get("messageType", "null"),
                                "category": properties.get("category", "null"),
                                "sender": properties.get("sender", "null"),
                                "senderName": properties.get("senderName", "null"),
                                "id": properties.get("id", "null"),
                                "zoneid": self.feedid,
                                "eventCode": properties.get("eventCode", {}), # Pass eventCode dict for SAME lookup
                            }
                            
                            # Add spoken_title for compatibility
                            if "headline" in properties:
                                alert_data["spoken_title"] = properties["headline"].split(" by ")[0]
                            
                            alerts.append(alert_data)
                        else:
                            _LOGGER.debug("[%s] Alert %d/%d has no properties, skipping", self.feedid, i+1, features_count)
                else:
                    _LOGGER.debug("[%s] No 'features' field found in API response", self.feedid)

                # Sort alerts by ID
                alerts.sort(key=lambda x: (x['id']), reverse=True)
                _LOGGER.debug("[%s] Processed and sorted %d alerts", self.feedid, len(alerts))

                for sorted_alert in alerts:
                    _LOGGER.debug(
                        "[%s] Alert ID: %s",
                        self.feedid,
                        sorted_alert.get("id", "null")
                    )

                self._attr_native_value = len(alerts)
                self._attr_extra_state_attributes = {
                    "alerts": alerts,
                    "integration": "ha_easgen_internal",  # Mark as internal
                    "state": self.zone_state,
                    "zone": self.feedid,
                }
                _LOGGER.debug("[%s] Weather alerts update completed - %d alerts found", self.feedid, len(alerts))
                
                # Notify callback if registered and entity is properly initialized
                if self._alert_callback and self.hass:
                    try:
                        await self._alert_callback(alerts)
                    except Exception as callback_error:
                        _LOGGER.error("Error in alert callback: %s", callback_error)
                
        except Exception as e:
            self.exception = sys.exc_info()[0].__name__
            self.connected = False
            _LOGGER.error("[%s] Could not update sensor: %s", self.feedid, e)
        else:
            self.connected = True

        if not self.connected:
            self._attr_native_value = "unavailable"
            
    def set_alert_callback(self, callback):
        """Set callback function to be called when alerts are updated."""
        self._alert_callback = callback

    @property
    def device_info(self):
        """Return device information."""
        from .const import DOMAIN, MANUFACTURER
        
        # Create location-based device name
        location = f"{self.zone_state}Z{self.zone_config}"
        if self.county_config:
            location += f" {self.zone_state}C{self.county_config}"
        
        # Use consistent device identifier with other sensors
        device_id = self.config_entry.entry_id if self.config_entry else f"weather_alerts_{self.feedid}"
        
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": f"EAS Generator {location}",
            "manufacturer": MANUFACTURER,
            "model": "Emergency Alert System",
        }
