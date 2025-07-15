"""Module to load SAME and FIPS data from local cache files"""
from __future__ import annotations

import os
import json
import logging
import aiofiles
from typing import Dict, List, Any, Optional

_LOGGER = logging.getLogger(__name__)

# Cache file paths
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
SAME_cache_file = os.path.join(CACHE_DIR, "SAME_cache.json")
FIPS_cache_file = os.path.join(CACHE_DIR, "FIPS_cache.json")

# Cache data in memory to avoid repeated file reads
_SAME_CACHE: Optional[List[Dict[str, Any]]] = None
_FIPS_CACHE: Optional[List[Dict[str, Any]]] = None


async def get_same_data() -> List[Dict[str, Any]]:
    """Load SAME data from local cache file."""
    global _SAME_CACHE
    
    if _SAME_CACHE is None:
        try:
            async with aiofiles.open(SAME_cache_file, 'r', encoding='utf-8') as file:
                content = await file.read()
                _SAME_CACHE = json.loads(content)
            _LOGGER.debug("Loaded SAME data from local cache: %d entries", len(_SAME_CACHE))
        except FileNotFoundError:
            _LOGGER.error("SAME cache file not found: %s", SAME_cache_file)
            _SAME_CACHE = []
        except json.JSONDecodeError as e:
            _LOGGER.error("Error parsing SAME cache file: %s", e)
            _SAME_CACHE = []
        except Exception as e:
            _LOGGER.error("Unexpected error loading SAME cache: %s", e)
            _SAME_CACHE = []
    
    return _SAME_CACHE


async def get_fips_data() -> List[Dict[str, Any]]:
    """Load FIPS data from local cache file."""
    global _FIPS_CACHE
    
    if _FIPS_CACHE is None:
        try:
            async with aiofiles.open(FIPS_cache_file, 'r', encoding='utf-8') as file:
                content = await file.read()
                _FIPS_CACHE = json.loads(content)
            _LOGGER.debug("Loaded FIPS data from local cache: %d entries", len(_FIPS_CACHE))
        except FileNotFoundError:
            _LOGGER.error("FIPS cache file not found: %s", FIPS_cache_file)
            _FIPS_CACHE = []
        except json.JSONDecodeError as e:
            _LOGGER.error("Error parsing FIPS cache file: %s", e)
            _FIPS_CACHE = []
        except Exception as e:
            _LOGGER.error("Unexpected error loading FIPS cache: %s", e)
            _FIPS_CACHE = []
    
    return _FIPS_CACHE
