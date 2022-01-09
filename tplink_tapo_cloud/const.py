""" TP-Link Tapo Cloud integration constants."""

from __future__ import annotations
from typing import Final

DOMAIN: Final[str] = "tplink_tapo_cloud"

MANUFACTURER: Final[str] = "TP-Link"
TAPOCLOUD_URL = "http://tapo.tplinkcloud.com/tapo_web"

COORDINATOR_DATA_KEY_NAME: Final[str] = "device_nickname"
COORDINATOR_DATA_KEY_DEVICEINFO: Final[str] = "device_info_result"
COORDINATOR_DATA_KEY_ENERGY: Final[str] = "energy_usage_result"

# Strings shown to User
# {} is replaced with Friendly name
SENSOR_NAME_ENERGY_TODAY: Final[str] = "{}:Energy today"
# {} is replaced with Friendly name
SENSOR_NAME_POWER: Final[str] = "{}:Power consumption"
