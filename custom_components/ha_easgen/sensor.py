"""
Enhanced sensor platform for EAS Generator with individual alert sensors and automatic EAS.
"""
import logging
import json
import os
import asyncio
from datetime import datetime, timezone
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.storage import Store

from .const import (
    STATE, ZONE, COUNTY, DOMAIN, MAX_ALERTS, ALERT_TRACK_FILE, 
    ALERT_SENSOR_PREFIX, ALERTS_SUMMARY_SENSOR, ALERT_ICONS,
    SEVERITY_LEVELS, TTS_ENGINE, CALL_SIGN, MEDIA_PLAYERS,
    DISABLE_TTS, INCLUDE_DESCRIPTION, TTS_WARNINGS, TTS_WATCHES, TTS_STATEMENTS
)
from .weather_alerts import EASGenWeatherAlertsSensor

_LOGGER = logging.getLogger(__name__)


class EASAnnouncementQueue:
    """Queue manager for EAS announcements to prevent overlapping."""
    
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.queue = asyncio.Queue()
        self.processing = False
        
    async def add_announcement(self, alert, audio_url, media_players, audio_duration):
        """Add an announcement to the queue."""
        await self.queue.put({
            'alert': alert,
            'audio_url': audio_url,
            'media_players': media_players,
            'audio_duration': audio_duration
        })
        
        # Start processing if not already processing
        if not self.processing:
            self.hass.async_create_task(self._process_queue())
    
    async def _process_queue(self):
        """Process announcements sequentially."""
        self.processing = True
        
        try:
            while not self.queue.empty():
                announcement = await self.queue.get()
                await self._play_announcement(announcement)
                self.queue.task_done()
        finally:
            self.processing = False
    
    async def _play_announcement(self, announcement):
        """Play a single announcement and wait for completion."""
        alert = announcement['alert']
        audio_url = announcement['audio_url']
        media_players = announcement['media_players']
        audio_duration = announcement['audio_duration']
        
        event_name = alert.get("event", "Unknown")
        
        try:
            _LOGGER.debug("Playing announcement for %s on media players: %s", event_name, media_players)
            
            # Play the announcement
            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": media_players,
                    "media_content_type": "audio",
                    "media_content_id": audio_url,
                    "announce": True,  # This handles the interruption/resume automatically
                },
                blocking=False,  # Don't block the service call
            )
            
            # Wait for the audio duration (we know exactly how long it should take)
            await asyncio.sleep(audio_duration)
            
            # Wait for media players to finish playing
            await self._wait_for_players_idle(media_players)
            
            _LOGGER.info("EAS announcement completed for %s on media players: %s", event_name, media_players)
            
        except Exception as e:
            _LOGGER.error("Failed to play EAS announcement for %s: %s", event_name, e)
    
    async def _wait_for_players_idle(self, media_players):
        """Wait for media players to return to idle state."""
        max_wait = 30  # Maximum wait time in seconds
        check_interval = 0.5  # Check every 0.5 seconds
        
        for _ in range(int(max_wait / check_interval)):
            all_idle = True
            
            for player_id in media_players:
                try:
                    state = self.hass.states.get(player_id)
                    if state and state.state == "playing":
                        all_idle = False
                        break
                except Exception:
                    # If we can't get the state, assume it's idle
                    pass
            
            if all_idle:
                return
                
            await asyncio.sleep(check_interval)
        
        # Timeout reached
        _LOGGER.debug("Timeout waiting for media players to become idle")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EAS Generator sensor platform via config entry."""

    # Create internal weather alerts sensor
    weather_sensor = EASGenWeatherAlertsSensor(
        hass,
        config_entry.data[STATE],
        config_entry.data[ZONE],
        config_entry.data.get(COUNTY, ""),
        config_entry
    )
    
    # Validate the zone/county IDs with weather.gov API
    try:
        await weather_sensor.async_validate_ids()
    except ValueError as e:
        _LOGGER.error("Failed to validate weather zone/county configuration: %s", e)
        return

    # Create alert management coordinator
    alert_coordinator = EASAlertCoordinator(hass, config_entry, weather_sensor)
    
    # Store coordinator in hass data for TTS platform access
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][config_entry.entry_id] = alert_coordinator

    # Create summary sensor
    summary_sensor = EASAlertsSummarySensor(alert_coordinator)
    
    # Create individual alert sensors
    alert_sensors = []
    for i in range(1, MAX_ALERTS + 1):
        alert_sensors.append(EASIndividualAlertSensor(alert_coordinator, i))

    # Register all sensors
    all_sensors = [weather_sensor, summary_sensor] + alert_sensors
    async_add_entities(all_sensors)
    
    # Start the alert coordinator
    await alert_coordinator.async_start()


class EASAlertCoordinator:
    """Coordinates alert management, deduplication, and automatic EAS generation."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, weather_sensor: EASGenWeatherAlertsSensor):
        self.hass = hass
        self.config_entry = config_entry
        self.weather_sensor = weather_sensor
        self.current_alerts = []
        self.announced_alerts = set()
        self.alert_sensors = {}
        self.summary_sensor = None
        self.tts_engine = None  # Will be set by TTS entity when it's created
        
        # Alert tracking storage
        self.store = Store(hass, 1, f"{DOMAIN}_{config_entry.entry_id}_alert_tracking")
        
        # Initialize announcement queue
        self.announcement_queue = EASAnnouncementQueue(hass)
        
    async def async_start(self):
        """Start the alert coordinator."""
        # Load previously announced alerts
        data = await self.store.async_load()
        if data:
            self.announced_alerts = set(data.get("announced_alerts", []))
            
        # Set up weather sensor update listener
        await self.weather_sensor.async_added_to_hass()
        
        # Monitor weather sensor for changes by checking periodically
        self._setup_monitoring()
        
    def _setup_monitoring(self):
        """Set up monitoring of weather alerts."""
        # Create a method to check alerts that will be called by the weather sensor
        self.weather_sensor.set_alert_callback(self._process_alerts)
        
        # Initial check
        self.hass.async_create_task(self._initial_alert_check())
        
    async def _initial_alert_check(self):
        """Perform initial check of alerts."""
        await asyncio.sleep(5)  # Give weather sensor time to initialize
        try:
            # Only proceed if weather sensor is properly initialized
            if hasattr(self.weather_sensor, 'hass') and self.weather_sensor.hass:
                await self.weather_sensor.async_update()
                if hasattr(self.weather_sensor, '_attr_extra_state_attributes'):
                    alerts = self.weather_sensor._attr_extra_state_attributes.get("alerts", [])
                    await self._process_alerts(alerts)
        except Exception as e:
            _LOGGER.error("Error in initial alert check: %s", e)
        
    async def _handle_weather_alert_change(self, event):
        """Handle changes in weather alerts."""
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        
        if not new_state or not new_state.attributes:
            return
            
        new_alerts = new_state.attributes.get("alerts", [])
        
        # Process new alerts
        await self._process_alerts(new_alerts)
        
    async def _process_alerts(self, alerts):
        """Process new alerts and trigger EAS if needed."""
        new_alert_ids = []
        
        # Update current alerts
        self.current_alerts = alerts[:MAX_ALERTS]  # Limit to MAX_ALERTS
        
        # Check for new alerts that haven't been announced
        for alert in self.current_alerts:
            alert_id = alert.get("id", "")
            if alert_id and alert_id not in self.announced_alerts:
                new_alert_ids.append(alert_id)
                self.announced_alerts.add(alert_id)
                
        # Save announced alerts
        await self.store.async_save({"announced_alerts": list(self.announced_alerts)})
        
        # Update all sensor entities
        await self._update_sensors()
        
        # Trigger EAS for new alerts
        if new_alert_ids:
            await self._trigger_eas_for_new_alerts(new_alert_ids)
            
    async def _update_sensors(self):
        """Update all alert sensor entities."""
        # Update summary sensor
        if self.summary_sensor:
            self.summary_sensor.async_write_ha_state()
            
        # Update individual alert sensors
        for sensor in self.alert_sensors.values():
            sensor.async_write_ha_state()
            
    async def _trigger_eas_for_new_alerts(self, alert_ids):
        """Trigger EAS announcements and UI notifications for new alerts."""
        _LOGGER.info("Triggering EAS for new alerts: %s", alert_ids)
        
        for alert_id in alert_ids:
            alert = next((a for a in self.current_alerts if a.get("id") == alert_id), None)
            if not alert:
                continue
                
            # Create UI notification
            await self._create_ui_notification(alert)
            
            # Trigger EAS announcement
            await self._trigger_eas_announcement(alert)
            
    async def _create_ui_notification(self, alert):
        """Create a persistent notification for the alert."""
        alert_event = alert.get("event", "Weather Alert")
        alert_area = alert.get("area", "Your Area")
        alert_description = alert.get("description", "")
        alert_instruction = alert.get("instruction", "")
        alert_severity = alert.get("severity", "Unknown")
        
        # Create notification title
        title = f"🚨 {alert_event}"
        
        # Create notification message
        message = f"**{alert_event}** for {alert_area}\n\n"
        if alert_description:
            message += f"{alert_description[:200]}...\n\n" if len(alert_description) > 200 else f"{alert_description}\n\n"
        if alert_instruction:
            message += f"**Instructions:** {alert_instruction[:200]}..." if len(alert_instruction) > 200 else f"**Instructions:** {alert_instruction}"
            
        # Determine notification ID and styling based on severity
        notification_id = f"eas_alert_{alert.get('id', 'unknown')}"
        
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": notification_id,
            }
        )
        
    async def _get_event_type(self, alert):
        """Determine event type based on SAME cache lookup."""
        # First try to get the NWS event code from the alert data
        event_code = None
        if "eventCode" in alert and "NationalWeatherService" in alert["eventCode"]:
            event_codes = alert["eventCode"]["NationalWeatherService"]
            if isinstance(event_codes, list) and len(event_codes) > 0:
                event_code = event_codes[0]
        
        # If we have an event code, look it up in the SAME cache
        if event_code:
            try:
                # Load SAME cache
                same_cache_path = os.path.join(os.path.dirname(__file__), "cache", "SAME_cache.json")
                with open(same_cache_path, 'r') as f:
                    same_cache = json.load(f)
                
                # Find the event in the cache
                for item in same_cache:
                    if item.get("Event Code") == event_code:
                        event_level = item.get("Event Level", "")
                        # Map event level to our categories
                        if event_level == "WRN":
                            return "warning"
                        elif event_level == "WCH":
                            return "watch"
                        elif event_level == "ADV":
                            return "statement"
                        elif event_level == "TEST":
                            return "statement"  # Skip test messages by default
                        break
            except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                _LOGGER.warning("Error loading SAME cache: %s", e)
        
        # Fallback: try to determine by event name
        event = alert.get("event", "")
        event_lower = event.lower()
        if "warning" in event_lower:
            return "warning"
        elif "watch" in event_lower:
            return "watch"
        elif "statement" in event_lower or "advisory" in event_lower:
            return "statement"
        
        # Default to warning for unknown types
        return "warning"
        
    async def _trigger_eas_announcement(self, alert):
        """Trigger EAS announcement using queue system for proper sequencing."""
        # Check if TTS is disabled
        if self.config_entry.data.get(DISABLE_TTS, False):
            _LOGGER.info("TTS is disabled, skipping EAS announcement")
            return
            
        # Determine event type and check if TTS is enabled for this type
        event_type = await self._get_event_type(alert)
        event_name = alert.get("event", "Unknown")
        
        # Check if TTS is enabled for this event type
        tts_enabled = False
        if event_type == "warning" and self.config_entry.data.get(TTS_WARNINGS, True):
            tts_enabled = True
        elif event_type == "watch" and self.config_entry.data.get(TTS_WATCHES, True):
            tts_enabled = True
        elif event_type == "statement" and self.config_entry.data.get(TTS_STATEMENTS, False):
            tts_enabled = True
            
        if not tts_enabled:
            _LOGGER.info("TTS is disabled for event type '%s' (event: %s), skipping EAS announcement", event_type, event_name)
            return
            
        media_players = self.config_entry.data.get(MEDIA_PLAYERS, [])
        
        if not media_players:
            _LOGGER.warning("No media players configured for EAS announcements")
            return
        
        try:
            # Use the TTS engine directly from the coordinator
            if self.tts_engine:
                # Generate the audio URL and get duration using the TTS engine
                audio_url = await self.tts_engine.get_audio_url(alert)
                
                if audio_url:
                    # Get the audio duration from the TTS engine
                    audio_duration = await self.tts_engine.get_audio_duration(alert)
                    
                    _LOGGER.debug("Adding EAS announcement to queue for %s (duration: %ss)", event_name, audio_duration)
                    
                    # Add to queue for sequential processing
                    await self.announcement_queue.add_announcement(
                        alert=alert,
                        audio_url=audio_url,
                        media_players=media_players,
                        audio_duration=audio_duration
                    )
                    
                    _LOGGER.info("EAS announcement queued for %s (%s) on media players: %s", 
                                event_name, event_type, media_players)
                else:
                    _LOGGER.error("Failed to generate audio URL for alert: %s", event_name)
            else:
                _LOGGER.error("TTS engine not available for alert: %s", event_name)
                
        except Exception as e:
            _LOGGER.error("Failed to queue EAS announcement for %s: %s", event_name, e)
        
    def register_summary_sensor(self, sensor):
        """Register the summary sensor."""
        self.summary_sensor = sensor
        
    def register_alert_sensor(self, sensor, alert_number):
        """Register an individual alert sensor."""
        self.alert_sensors[alert_number] = sensor
        
    def get_alert(self, alert_number):
        """Get alert data for a specific alert number (1-based)."""
        if 1 <= alert_number <= len(self.current_alerts):
            return self.current_alerts[alert_number - 1]
        return None
        
    def get_alert_count(self):
        """Get total number of active alerts."""
        return len(self.current_alerts)
        
    def get_severity_counts(self):
        """Get counts of alerts by severity."""
        counts = {severity.lower(): 0 for severity in SEVERITY_LEVELS}
        
        for alert in self.current_alerts:
            severity = alert.get("severity", "Unknown").lower()
            if severity in counts:
                counts[severity] += 1
                
        return counts


class EASAlertsSummarySensor(SensorEntity):
    """Summary sensor for all EAS alerts."""
    
    def __init__(self, coordinator: EASAlertCoordinator):
        self.coordinator = coordinator
        config_entry = coordinator.config_entry
        
        # Create unique name and ID based on location
        location_name = f"{config_entry.data[STATE]}Z{config_entry.data[ZONE]}"
        if config_entry.data.get(COUNTY):
            location_name += f" {config_entry.data[STATE]}C{config_entry.data[COUNTY]}"
        
        self._attr_name = f"EAS Alerts {location_name}"
        self._attr_unique_id = f"{DOMAIN}_alerts_summary_{config_entry.entry_id}"
        self._attr_icon = "mdi:alert-rhombus"
        self._attr_unit_of_measurement = "Alerts"
        
        # Register with coordinator
        coordinator.register_summary_sensor(self)
        
    @property
    def native_value(self):
        """Return the number of active alerts."""
        return self.coordinator.get_alert_count()
        
    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        severity_counts = self.coordinator.get_severity_counts()
        
        return {
            "total_alerts": self.coordinator.get_alert_count(),
            "severe_count": severity_counts.get("severe", 0),
            "extreme_count": severity_counts.get("extreme", 0),
            "moderate_count": severity_counts.get("moderate", 0),
            "minor_count": severity_counts.get("minor", 0),
            "alerts_active": "Yes" if self.coordinator.get_alert_count() > 0 else "No",
            "integration": "ha_easgen_enhanced",
        }
        
    @property
    def device_info(self):
        """Return device information."""
        config_entry = self.coordinator.config_entry
        
        # Create location-based device name
        location = f"{config_entry.data[STATE]}Z{config_entry.data[ZONE]}"
        if config_entry.data.get(COUNTY):
            location += f" {config_entry.data[STATE]}C{config_entry.data[COUNTY]}"
        
        return {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"EAS Generator {location}",
            "manufacturer": "EAS Generator",
            "model": "Emergency Alert System",
        }


class EASIndividualAlertSensor(SensorEntity):
    """Individual alert sensor for a specific alert slot."""
    
    def __init__(self, coordinator: EASAlertCoordinator, alert_number: int):
        self.coordinator = coordinator
        self.alert_number = alert_number
        config_entry = coordinator.config_entry
        
        # Create unique name and ID based on location
        location_name = f"{config_entry.data[STATE]}Z{config_entry.data[ZONE]}"
        if config_entry.data.get(COUNTY):
            location_name += f" {config_entry.data[STATE]}C{config_entry.data[COUNTY]}"
        
        self._attr_name = f"EAS Alert {alert_number} {location_name}"
        self._attr_unique_id = f"{DOMAIN}_alert_{alert_number}_{config_entry.entry_id}"
        
        # Register with coordinator
        coordinator.register_alert_sensor(self, alert_number)
        
    @property
    def native_value(self):
        """Return on/off based on whether this alert slot has an active alert."""
        alert = self.coordinator.get_alert(self.alert_number)
        return "on" if alert else "off"
        
    @property
    def icon(self):
        """Return dynamic icon based on alert type."""
        alert = self.coordinator.get_alert(self.alert_number)
        if alert:
            event = alert.get("event", "")
            return ALERT_ICONS.get(event, "mdi:alert-rhombus")
        return "mdi:alert-rhombus"
        
    @property
    def extra_state_attributes(self):
        """Return alert details as attributes."""
        alert = self.coordinator.get_alert(self.alert_number)
        
        if not alert:
            return {
                "alert_id": None,
                "alert_event": None,
                "alert_area": None,
                "alert_severity": None,
                "alert_urgency": None,
                "alert_certainty": None,
                "alert_description": None,
                "alert_instruction": None,
                "alert_sent": None,
                "alert_effective": None,
                "alert_expires": None,
                "alert_title": None,
                "spoken_title": None,
                "display_title": None,
                "display_message": None,
            }
            
        # Generate spoken title
        spoken_title = f"Attention! Weather alert for {alert.get('area', 'your area')}. {alert.get('title', alert.get('event', 'Weather alert'))}."
        
        # Generate display message
        display_message = ""
        if alert.get("NWSheadline") and alert.get("NWSheadline") != "null":
            nws_headline = alert["NWSheadline"]
            if isinstance(nws_headline, list):
                nws_headline = nws_headline[0] if nws_headline else ""
            display_message += f"{nws_headline}<br><br>"
            
        if alert.get("description"):
            display_message += f"{alert['description']}<br><br>"
            
        if alert.get("instruction"):
            display_message += f"{alert['instruction']}<br><br>"
            
        display_message += f"Area: {alert.get('area', 'Unknown')}<br>"
        display_message += f"Effective: {alert.get('effective', 'Unknown')}<br>"
        if alert.get("expires"):
            display_message += f"Expires: {alert['expires']}<br>"
            
        return {
            "alert_id": alert.get("id"),
            "alert_event": alert.get("event"),
            "alert_area": alert.get("area"),
            "alert_severity": alert.get("severity"),
            "alert_urgency": alert.get("urgency"),
            "alert_certainty": alert.get("certainty"),
            "alert_description": alert.get("description"),
            "alert_instruction": alert.get("instruction"),
            "alert_sent": alert.get("sent"),
            "alert_effective": alert.get("effective"),
            "alert_expires": alert.get("expires"),
            "alert_title": alert.get("title"),
            "spoken_title": spoken_title,
            "display_title": alert.get("title", alert.get("event")),
            "display_message": display_message,
        }
        
    @property
    def device_info(self):
        """Return device information."""
        config_entry = self.coordinator.config_entry
        
        # Create location-based device name
        location = f"{config_entry.data[STATE]}Z{config_entry.data[ZONE]}"
        if config_entry.data.get(COUNTY):
            location += f" {config_entry.data[STATE]}C{config_entry.data[COUNTY]}"
        
        return {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"EAS Generator {location}",
            "manufacturer": "EAS Generator",
            "model": "Emergency Alert System",
        }
