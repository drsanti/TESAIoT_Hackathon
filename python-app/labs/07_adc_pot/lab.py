#!/usr/bin/env python3
"""Lab 07 — ADC_POT live millivolts (turn the pots)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.rates import (
    TEACHING_ADC_DELTA_MV,
    TEACHING_ADC_MIN_PUB_MS,
    TEACHING_ADC_SAMPLE_MS,
    TEACHING_HMI_PERIODIC_MS,
)
from shared.sensor_ids import DEFAULT_MASKS, SENSOR_ADC_POT
from shared.session_lite import SessionLite


async def main() -> None:
    duration = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else 20.0
    force_periodic = "--periodic" in sys.argv
    mode = 0 if force_periodic else 1
    print(
        f"Lab 07 — ADC_POT ({duration:.0f}s) — turn POT1–POT4"
        + (" [periodic smoke]" if force_periodic else " [on_change]")
        + "\n"
    )

    count = 0
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        nonlocal count
        if sample["sensor_id"] != SENSOR_ADC_POT:
            return
        count += 1
        f = sample["fields"]
        parts = []
        for key, label in (
            ("pot1_mv", "POT1"),
            ("pot2_mv", "POT2"),
            ("pot3_mv", "POT3"),
            ("pot4_mv", "POT4"),
        ):
            if key in f:
                parts.append(f"{label}={f[key]} mV")
        print(f"  #{sample['counter']}  " + "  ".join(parts))

    session.set_sample_handler(on_sample)

    try:
        await session.connect()
        await session.enable_notify()
        await session.ping(attempts=3)

        session.mute_samples(True)
        await session.quiet_for_config()

        for sid in range(6):
            enabled = sid == SENSOR_ADC_POT
            await session.sensor_cfg_set(
                {
                    "sensor_id": sid,
                    "enabled": enabled,
                    "publish_mode": mode if enabled else 0,
                    "mask": DEFAULT_MASKS[sid] if enabled else 0,
                    "sampling_interval_ms": (
                        (TEACHING_HMI_PERIODIC_MS if force_periodic else TEACHING_ADC_SAMPLE_MS)
                        if enabled
                        else 1000
                    ),
                    "delta_x100": TEACHING_ADC_DELTA_MV if enabled else 0,
                    "min_publish_interval_ms": TEACHING_ADC_MIN_PUB_MS if enabled else 0,
                    "publish_interval_ms": TEACHING_HMI_PERIODIC_MS if (enabled and force_periodic) else 0,
                }
            )

        try:
            await session.enable_streaming_policy()
        except Exception as exc:
            print(f"warn: BLE_POLICY_SET: {exc}")
            session.mute_samples(False)

        print("Listening for pot changes…\n")
        await asyncio.sleep(duration)

        print(f"\nSamples received: {count}")
        if count == 0:
            print("FAIL: no ADC_POT EVT — turn a pot, check mask/policy.")
            raise SystemExit(1)
        print("SUCCESS — potentiometer mV decoded.")
        print("Next: Lab 08 (SW_BTN) or 09 (multi-sensor)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
