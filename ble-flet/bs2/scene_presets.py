"""Load sensor scene presets from checked-in JSON (host TypeScript is authoritative)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PRESETS_PATH = Path(__file__).with_name("sensor-scene-presets.v1.json")


@lru_cache(maxsize=1)
def _load_doc() -> dict:
    return json.loads(_PRESETS_PATH.read_text(encoding="utf-8"))


def flet_v1_preset_ids() -> list[str]:
    return list(_load_doc().get("fletV1Ids", ["motion", "realtime", "labQuiet"]))


def get_scene_preset(preset_id: str) -> dict:
    presets = _load_doc().get("presets", {})
    preset = presets.get(preset_id)
    if preset is None:
        raise KeyError(f"unknown sensor scene preset: {preset_id}")
    return preset


def scene_preset_sensor_cfgs(preset: dict) -> list[dict]:
    """Host camelCase → ble-flet snake_case SENSOR_CFG dicts."""

    def _map(cfg: dict) -> dict:
        return {
            "sensor_id": int(cfg["sensorId"]),
            "enabled": bool(cfg["enabled"]),
            "publish_mode": int(cfg["publishMode"]),
            "mask": int(cfg["mask"]),
            "sampling_interval_ms": int(cfg["samplingIntervalMs"]),
            "publish_interval_ms": int(cfg["publishIntervalMs"]),
            "delta_x100": int(cfg["deltaX100"]),
            "min_publish_interval_ms": int(cfg["minPublishIntervalMs"]),
        }

    return [
        _map(preset["bmi270"]["sensorCfg"]),
        _map(preset["bmm350"]),
        _map(preset["sht40"]),
        _map(preset["dps368"]),
    ]


def scene_preset_bmi270_mode(preset: dict) -> int:
    return int(preset["bmi270"]["streamMode"])


def scene_preset_fusion_feed_ms(preset: dict) -> int:
    return int(preset["bmi270"]["fusionFeedIntervalMs"])


def scene_preset_status_line(preset: dict) -> str:
    return str(preset.get("statusLine") or preset.get("label") or "")
