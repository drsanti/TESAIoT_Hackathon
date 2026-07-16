"""Default SENSOR_CFG used by teaching labs (BLE-safe + TFT-friendly)."""

from __future__ import annotations

from .rates import (
    TEACHING_ADC_DELTA_MV,
    TEACHING_ADC_MIN_PUB_MS,
    TEACHING_ADC_SAMPLE_MS,
    TEACHING_BTN_SAMPLE_MS,
    TEACHING_PERIODIC_MS,
)
from .sensor_ids import ALL_SENSOR_IDS, DEFAULT_MASKS


def teaching_sensor_cfg(sensor_id: int) -> dict:
    """Periodic IMU/env ~1 Hz; ADC/SW_BTN on_change — keeps TFT updating after labs."""
    sid = int(sensor_id)
    if sid == 4:
        return {
            "sensor_id": sid,
            "enabled": True,
            "publish_mode": 1,
            "mask": DEFAULT_MASKS[sid],
            "sampling_interval_ms": TEACHING_ADC_SAMPLE_MS,
            "delta_x100": TEACHING_ADC_DELTA_MV,
            "min_publish_interval_ms": TEACHING_ADC_MIN_PUB_MS,
            "publish_interval_ms": 0,
        }
    if sid == 5:
        return {
            "sensor_id": sid,
            "enabled": True,
            "publish_mode": 1,
            "mask": DEFAULT_MASKS[sid],
            "sampling_interval_ms": TEACHING_BTN_SAMPLE_MS,
            "delta_x100": 0,
            "min_publish_interval_ms": 0,
            "publish_interval_ms": 0,
        }
    return {
        "sensor_id": sid,
        "enabled": True,
        "publish_mode": 0,
        "mask": DEFAULT_MASKS[sid],
        "sampling_interval_ms": TEACHING_PERIODIC_MS,
        "delta_x100": 0,
        "min_publish_interval_ms": 0,
        "publish_interval_ms": TEACHING_PERIODIC_MS,
    }


def teaching_sensor_cfgs() -> list[dict]:
    return [teaching_sensor_cfg(sid) for sid in ALL_SENSOR_IDS]
