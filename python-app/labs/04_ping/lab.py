#!/usr/bin/env python3
"""Lab 04 — continuous stream of all teaching sensors (print every sample)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.lab_helpers import connect_and_live, duration_arg
from shared.sensor_ids import SENSOR_NAMES
from shared.session_lite import SessionLite


async def main() -> None:
    duration = duration_arg(15.0)
    print(f"Lab 04 — Continuous EVT stream ({duration:.0f}s)")
    print("All sensors the firmware already enables for TFT.\n")

    counts = {sid: 0 for sid in SENSOR_NAMES}
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        sid = int(sample["sensor_id"])
        if sid not in counts:
            counts[sid] = 0
        counts[sid] += 1
        fields = sample["fields"]
        brief = ", ".join(
            f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in list(fields.items())[:5]
        )
        print(f"  {sample['label']:<8}  #{sample['counter']}  {brief}")

    session.set_sample_handler(on_sample)

    try:
        await connect_and_live(session)
        print("Streaming... move the board / turn a pot / press a button.\n")
        await asyncio.sleep(duration)

        print("\nCounts:")
        for sid, name in SENSOR_NAMES.items():
            print(f"  {name:<8}  {counts.get(sid, 0)}")
        if sum(counts.values()) == 0:
            print("FAIL: no EVT received.")
            raise SystemExit(1)
        print("SUCCESS — continuous notifies working.")
        print("Next: Lab 05 (focus one sensor) or Lab 06 (IMU+env detail)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
