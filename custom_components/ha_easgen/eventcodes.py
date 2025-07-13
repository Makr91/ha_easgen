"""Module to pull and parse SAME and FIPS data"""
import requests
from io import StringIO
import csv
import os
import json
import aiofiles

import logging

_LOGGER = logging.getLogger(__name__)

document_id = "1msvlkDtCgO42IRoIxX9z5IIDQU0Ocq5eLvbW_E__awA"

SAME_sheet_id = "0"
FIPS_sheet_id = "532761371"

SAME_sheet = "https://docs.google.com/spreadsheets/d/" + document_id + "/export?format=csv&gid=" + SAME_sheet_id
FIPS_sheet = "https://docs.google.com/spreadsheets/d/" + document_id + "/export?format=csv&gid=" + FIPS_sheet_id

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
            SAME_response = requests.get(SAME_sheet)
            SAME = list(csv.DictReader(StringIO(SAME_response.text), delimiter=","))
            await save_data_to_cache(SAME, SAME_cache_file)
    return SAME

async def get_fips_data():
    global FIPS
    if FIPS is None:
        FIPS = await load_data_from_cache(FIPS_cache_file)
        if FIPS is None:
            FIPS_response = requests.get(FIPS_sheet)
            FIPS = list(csv.DictReader(StringIO(FIPS_response.text), delimiter=","))
            await save_data_to_cache(FIPS, FIPS_cache_file)
    return FIPS
