"""Module to pull and parse SAME and FIPS data"""
import requests
import os
import json
import aiofiles

import logging

_LOGGER = logging.getLogger(__name__)

# GitHub repository URLs for SAME and FIPS data
SAME_url = "https://raw.githubusercontent.com/Makr91/ha_easgen/refs/heads/main/custom_components/ha_easgen/cache/SAME_cache.json"
FIPS_url = "https://raw.githubusercontent.com/Makr91/ha_easgen/refs/heads/main/custom_components/ha_easgen/cache/FIPS_cache.json"

# Cache file paths
CACHE_DIR = "custom_components/ha_easgen/cache"
SAME_cache_file = os.path.join(CACHE_DIR, "SAME_cache.json")
FIPS_cache_file = os.path.join(CACHE_DIR, "FIPS_cache.json")

async def load_data_from_cache(cache_file):
    if os.path.exists(cache_file):
        async with aiofiles.open(cache_file, "r") as file:
            content = await file.read()
            return json.loads(content)
    return None

async def save_data_to_cache(data, cache_file):
    async with aiofiles.open(cache_file, "w") as file:
        await file.write(json.dumps(data))

# Initialize as None - will be loaded lazily when first accessed
SAME = None
FIPS = None

async def get_same_data():
    global SAME
    if SAME is None:
        SAME = await load_data_from_cache(SAME_cache_file)
        if SAME is None:
            _LOGGER.debug("Loading SAME data from GitHub repository")
            SAME_response = requests.get(SAME_url)
            SAME_response.raise_for_status()  # Raise an exception for bad status codes
            SAME = SAME_response.json()
            await save_data_to_cache(SAME, SAME_cache_file)
    return SAME

async def get_fips_data():
    global FIPS
    if FIPS is None:
        FIPS = await load_data_from_cache(FIPS_cache_file)
        if FIPS is None:
            _LOGGER.debug("Loading FIPS data from GitHub repository")
            FIPS_response = requests.get(FIPS_url)
            FIPS_response.raise_for_status()  # Raise an exception for bad status codes
            FIPS = FIPS_response.json()
            await save_data_to_cache(FIPS, FIPS_cache_file)
    return FIPS
