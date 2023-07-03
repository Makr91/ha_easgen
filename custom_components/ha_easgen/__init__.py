"""The Emergency Alert System Generator"""
import logging
import re
import socket
import requests
import sys

from EASGen import EASGen
from requests.exceptions import ConnectionError as reConnectionError

from pydub.playback import play
from datetime import datetime, timedelta, timezone
from dateutil import parser

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Emergency Alert System component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the EAS from a config entry."""
    try:
        await hass.async_add_executor_job(
            _test_connection, entry.data[CONF_HOST], entry.data[CONF_PORT]
        )

    except reConnectionError as error:
        raise ConfigEntryNotReady from error

    hass.data.setdefault(DOMAIN, {})

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, MEDIA_PLAYER_DOMAIN)
    )

    return True