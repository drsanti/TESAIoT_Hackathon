#!/usr/bin/env python3
"""Lab 10 — build-your-own scaffold.

Edit MY_SENSORS: pick >=1 IMU, >=1 environment, >=1 HMI (pot or button).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.lab_helpers import connect_and_live, duration_arg
from shared.rates import (
    TEACHING_ADC_DELTA_MV,
    TEACHING_ADC_MIN_PUB_MS,
    TEACHING_ADC_SAMPLE_MS,
    TEACHING_BTN_SAMPLE_MS,
    TEACHING_PERIODIC_MS,
)
from shared.sensor_ids import (
    DEFAULT_MASKS,
    SENSOR_ADC_POT,
    SENSOR_BMI270,
    SENSOR_SHT40,
    SENSOR_SW_BTN,
)
from shared.session_lite import SessionLite

# --- Student picks (edit me) ---
MY_SENSORS = [
    SENSOR_BMI270,  # IMU
    SENSOR_SHT40,  # environment
    SENSOR_SW_BTN,  # HMI (or SENSOR_ADC_POT)
]


def _cfg(sid: int, *, enabled: bool) -> dict:
    if not enabled:
        return {
            "sensor_id": sid,
            "enabled": False,
            "publish_mode": 0,
            "mask": 0,
            "sampling_interval_ms": 1000,
            "delta_x100": 0,
            "min_publish_interval_ms": 0,
            "publish_interval_ms": 0,
        }
    if sid == SENSOR_ADC_POT:
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
    if sid == SENSOR_SW_BTN:
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


async def main() -> None:
    duration = duration_arg(15.0)
    print("Lab 10 — your app scaffold\n")
    print(f"Active sensor ids: {MY_SENSORS}")
    print(f"Teaching rate: ~{1000 // TEACHING_PERIODIC_MS} Hz periodic.\n")

    latest: dict[int, dict] = {}
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        latest[sample["sensor_id"]] = sample
        # TODO: replace with your application logic
        print(f"  {sample['label']}: {sample['fields']}")

    session.set_sample_handler(on_sample)

    try:
        await connect_and_live(session)
        await session.apply_cfgs_fire([_cfg(sid, enabled=sid in MY_SENSORS) for sid in range(6)])
        await asyncio.sleep(0.3)

        print("Running... edit on_sample / MY_SENSORS to customize.\n")
        await asyncio.sleep(duration)

        got = [s for s in MY_SENSORS if s in latest]
        print(f"\nReceived samples for {len(got)}/{len(MY_SENSORS)} chosen sensors.")
        if len(got) == 0:
            print("FAIL: no samples — check MY_SENSORS and hardware.")
            raise SystemExit(1)
        print("SUCCESS — scaffold runs. Now make it yours (see LAB.md).")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
