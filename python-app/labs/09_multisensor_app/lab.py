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
from shared.rates import (
    TEACHING_ADC_DELTA_MV,
    TEACHING_ADC_MIN_PUB_MS,
    TEACHING_ADC_SAMPLE_MS,
    TEACHING_BTN_SAMPLE_MS,
    TEACHING_PERIODIC_MS,
)
from shared.sensor_ids import ALL_SENSOR_IDS, DEFAULT_MASKS, SENSOR_NAMES, SENSOR_ADC_POT, SENSOR_SW_BTN
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


def _cfg(sid: int) -> dict:
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
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    print(f"Lab 09 — multi-sensor mini-app ({duration:.0f}s)")
    print(f"IMU/env ~{1000 // TEACHING_PERIODIC_MS} Hz; pots/buttons on_change (BLE-safe).\n")

    latest: dict[int, dict] = {}
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        latest[sample["sensor_id"]] = sample

    session.set_sample_handler(on_sample)

    try:
        await session.connect()
        await session.enable_notify()
        await session.ping(attempts=3)

        session.mute_samples(True)
        await session.quiet_for_config()

        for sid in ALL_SENSOR_IDS:
            await session.sensor_cfg_set(_cfg(sid))

        try:
            await session.enable_streaming_policy()
        except Exception as exc:
            print(f"warn: BLE_POLICY_SET: {exc}")
            session.mute_samples(False)

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
                        print(f"  {name:<8}  (waiting…)")
                    else:
                        print(f"  {name:<8}  #{sample['counter']}  {_fmt_fields(sid, sample['fields'])}")
                print("-" * 60)
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            print("\nInterrupted.")

        missing = [SENSOR_NAMES[s] for s in ALL_SENSOR_IDS if s not in latest]
        if missing:
            print(f"Note: no samples yet for: {', '.join(missing)}")
        if len(latest) == 0:
            print("FAIL: no samples at all.")
            raise SystemExit(1)
        print(f"SUCCESS — received {len(latest)}/6 sensor families.")
        print("Next: Lab 10 (your app template)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
