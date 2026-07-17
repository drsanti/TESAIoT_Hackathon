#!/usr/bin/env python3
"""Lab 06 — live EVT stream for sensors 0–3 (IMU + environment)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.lab_helpers import connect_and_live, duration_arg
from shared.rates import TEACHING_PERIODIC_MS
from shared.sensor_ids import SENSOR_BMI270, SENSOR_BMM350, SENSOR_DPS368, SENSOR_SHT40
from shared.session_lite import SessionLite

TARGETS = (SENSOR_BMI270, SENSOR_BMM350, SENSOR_SHT40, SENSOR_DPS368)


async def main() -> None:
    duration = duration_arg(12.0)
    print(f"Lab 06 — IMU + environment stream ({duration:.0f}s)")
    print("Path: connect -> notify (CCCD TX_EVT) -> EVT_SENSOR\n")

    counts = {sid: 0 for sid in TARGETS}
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        sid = sample["sensor_id"]
        if sid not in counts:
            return
        counts[sid] += 1
        fields = sample["fields"]
        brief = ", ".join(
            f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k, v in fields.items()
        )
        print(f"  {sample['label']:<8}  #{sample['counter']}  {brief}")

    session.set_sample_handler(on_sample)

    try:
        await connect_and_live(session)
        print(f"Streaming (~{1000 // TEACHING_PERIODIC_MS} Hz)... move the board.\n")
        await asyncio.sleep(duration)

        print("\nCounts:")
        for sid in TARGETS:
            print(f"  sensor {sid}: {counts[sid]} samples")
        if sum(counts.values()) == 0:
            print("FAIL: no EVT — check TFT soft-blue / one central only.")
            raise SystemExit(1)
        print("SUCCESS — IMU/env EVTs decoded.")
        print("Next: Lab 07 (ADC_POT) or 08 (SW_BTN)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
