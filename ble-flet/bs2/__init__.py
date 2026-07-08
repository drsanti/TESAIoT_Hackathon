"""BS2 BLE client for TESAIoT hackathon Flet app."""

from .connection_fsm import ConnPhase, DEFAULT_SCENE_PRESET, AUTO_STREAM_SCENE_PRESET
from .decode import (
    expected_cfg_hz,
    format_configured_rate,
    format_measured_rate,
    map_sensor_sample,
    rate_match_label,
)
from .gatt import BS2_BLE_ADV_NAME_PREFIX, matches_bs2_ble_name
from .session import Bs2BleSession, SessionState

__all__ = [
    "AUTO_STREAM_SCENE_PRESET",
    "BS2_BLE_ADV_NAME_PREFIX",
    "Bs2BleSession",
    "ConnPhase",
    "DEFAULT_SCENE_PRESET",
    "SessionState",
    "expected_cfg_hz",
    "format_configured_rate",
    "format_measured_rate",
    "map_sensor_sample",
    "matches_bs2_ble_name",
    "rate_match_label",
]
