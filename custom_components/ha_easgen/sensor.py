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
    SEVERITY_LEVELS, ANNOUNCEMENT_DELAY, TTS_ENGINE, CALL_SIGN, MEDIA_PLAYERS,
    DISABLE_TTS, INCLUDE_DESCRIPTION
)
from .weather_alerts import EASGenWeatherAlertsSensor

_LOGGER = logging.getLogger(__name__)

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
        config_entry.data.get(COUNTY, "")
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
        
        # Alert tracking storage
        self.store = Store(hass, 1, f"{DOMAIN}_{config_entry.entry_id}_alert_tracking")
        
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
        
        for i, alert_id in enumerate(alert_ids):
            alert = next((a for a in self.current_alerts if a.get("id") == alert_id), None)
            if not alert:
                continue
                
            # Create UI notification
            await self._create_ui_notification(alert)
            
            # Trigger EAS TTS (with delay between multiple alerts)
            if i > 0:
                await asyncio.sleep(ANNOUNCEMENT_DELAY)
            await self._trigger_eas_tts()
            
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
        
    async def _trigger_eas_tts(self):
        """Trigger EAS TTS announcement."""
        # Check if TTS is disabled
        if self.config_entry.data.get(DISABLE_TTS, False):
            _LOGGER.info("TTS is disabled, skipping EAS announcement")
            return
            
        tts_entity_id = f"tts.eas_gen_tts_{self.config_entry.data[CALL_SIGN].lower()}"
        media_players = self.config_entry.data.get(MEDIA_PLAYERS, [])
        
        if not media_players:
            _LOGGER.warning("No media players configured for EAS announcements")
            return
        
        try:
            # Call the TTS service to generate and play EAS announcement
            await self.hass.services.async_call(
                "tts",
                "speak",
                {
                    "entity_id": tts_entity_id,
                    "message": "Emergency Alert System Activation",
                    "media_player_entity_id": media_players,
                    "language": "en",
                    "cache": False,
                },
                blocking=False,  # Don't wait for completion
            )
            _LOGGER.info("EAS TTS triggered successfully on entity: %s with media players: %s", tts_entity_id, media_players)
            
        except Exception as e:
            _LOGGER.error("Failed to trigger EAS TTS on %s with media players %s: %s", tts_entity_id, media_players, e)
        
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
        self._attr_name = "EAS Alerts"
        self._attr_unique_id = f"{DOMAIN}_alerts_summary"
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
        return {
            "identifiers": {(DOMAIN, f"alerts_summary")},
            "name": "EAS Alerts Summary",
            "manufacturer": "EAS Generator",
            "model": "Alert Summary Sensor",
        }


class EASIndividualAlertSensor(SensorEntity):
    """Individual alert sensor for a specific alert slot."""
    
    def __init__(self, coordinator: EASAlertCoordinator, alert_number: int):
        self.coordinator = coordinator
        self.alert_number = alert_number
        self._attr_name = f"EAS Alert {alert_number}"
        self._attr_unique_id = f"{DOMAIN}_alert_{alert_number}"
        
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
        return {
            "identifiers": {(DOMAIN, f"alert_{self.alert_number}")},
            "name": f"EAS Alert {self.alert_number}",
            "manufacturer": "EAS Generator",
            "model": "Individual Alert Sensor",
        }
