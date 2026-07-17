#!/usr/bin/env python3
"""Lab 09 — multi-sensor CLI dashboard (all six BS2 sensors)."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.decode import format_sw_btn_state
from shared.lab_helpers import connect_and_live, duration_arg
from shared.rates import TEACHING_PERIODIC_MS
from shared.sensor_cfg_defaults import teaching_sensor_cfgs
from shared.sensor_ids import ALL_SENSOR_IDS, SENSOR_NAMES, SENSOR_ADC_POT, SENSOR_SW_BTN
from shared.session_lite import SessionLite


def _fmt_fields(sid: int, fields: dict) -> str:
    if sid == SENSOR_ADC_POT:
        return " ".join(f"{k}={v}" for k, v in fields.items())
    if sid == SENSOR_SW_BTN:
        state = int(fields.get("state", 0))
        counts = " ".join(f"{k}={v}" for k, v in fields.items() if k != "state")
        return f"pressed={format_sw_btn_state(state)} {counts}"
    return " ".join(
        f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k, v in fields.items()
    )


async def main() -> None:
    duration = duration_arg(30.0)
    print(f"Lab 09 — multi-sensor mini-app ({duration:.0f}s)")
    print(f"IMU/env ~{1000 // TEACHING_PERIODIC_MS} Hz; pots/buttons on_change.\n")

    latest: dict[int, dict] = {}
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        latest[sample["sensor_id"]] = sample

    session.set_sample_handler(on_sample)

    try:
        await connect_and_live(session)
        # Teaching defaults already on device; refresh fire-and-forget.
        await session.apply_cfgs_fire(teaching_sensor_cfgs())
        await asyncio.sleep(0.3)

        print("Live dashboard (move / turn pots / press buttons). Ctrl+C to stop early.\n")
        end = time.monotonic() + duration
        try:
            while time.monotonic() < end:
                print("\033[2J\033[H", end="")
                print(f"TESAIoT multi-sensor  remaining={end - time.monotonic():.0f}s")
                print("-" * 60)
                for sid in ALL_SENSOR_IDS:
                    name = SENSOR_NAMES[sid]
                    sample = latest.get(sid)
                    if sample is None:
                        print(f"  {name:<8}  (waiting...)")
                    else:
                        print(
                            f"  {name:<8}  #{sample['counter']}  "
                            f"{_fmt_fields(sid, sample['fields'])}"
                        )
                print("-" * 60)
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            print("\nInterrupted.")

        got = sum(1 for sid in ALL_SENSOR_IDS if sid in latest)
        print(f"\nSensors seen: {got}/6")
        if got == 0:
            print("FAIL: no samples.")
            raise SystemExit(1)
        print("SUCCESS — dashboard received live EVTs.")
        print("Next: Lab 10 (your app)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
