#!/usr/bin/env python3
"""Lab 08 — SW_BTN live state + press counts."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.decode import format_sw_btn_state
from shared.lab_helpers import connect_and_live, duration_arg, flag
from shared.rates import TEACHING_BTN_SAMPLE_MS, TEACHING_HMI_PERIODIC_MS
from shared.sensor_ids import DEFAULT_MASKS, SENSOR_SW_BTN
from shared.session_lite import SessionLite


async def main() -> None:
    duration = duration_arg(20.0)
    force_periodic = flag("--periodic")
    mode = 0 if force_periodic else 1
    print(
        f"Lab 08 — SW_BTN ({duration:.0f}s) — press BTN0-BTN2"
        + (" [periodic smoke]" if force_periodic else " [on_change]")
        + "\n"
    )

    count = 0
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        nonlocal count
        if sample["sensor_id"] != SENSOR_SW_BTN:
            return
        count += 1
        f = sample["fields"]
        state = int(f.get("state", 0))
        pressed = format_sw_btn_state(state)
        counts = []
        for key, label in (
            ("btn0_count", "BTN0"),
            ("btn1_count", "BTN1"),
            ("btn2_count", "BTN2"),
        ):
            if key in f:
                counts.append(f"{label}#{f[key]}")
        print(f"  #{sample['counter']}  pressed={pressed}  counts=[{', '.join(counts)}]")

    session.set_sample_handler(on_sample)

    try:
        await connect_and_live(session)

        cfgs = []
        for sid in range(6):
            enabled = sid == SENSOR_SW_BTN
            cfgs.append(
                {
                    "sensor_id": sid,
                    "enabled": enabled,
                    "publish_mode": mode if enabled else 0,
                    "mask": DEFAULT_MASKS[sid] if enabled else 0,
                    "sampling_interval_ms": (
                        (TEACHING_HMI_PERIODIC_MS if force_periodic else TEACHING_BTN_SAMPLE_MS)
                        if enabled
                        else 1000
                    ),
                    "delta_x100": 0,
                    "min_publish_interval_ms": 0,
                    "publish_interval_ms": (
                        TEACHING_HMI_PERIODIC_MS if (enabled and force_periodic) else 0
                    ),
                }
            )
        await session.apply_cfgs_fire(cfgs)
        await asyncio.sleep(0.3)

        print("Listening for button events...\n")
        await asyncio.sleep(duration)

        print(f"\nSamples received: {count}")
        if count == 0:
            print("FAIL: no SW_BTN EVT — press a button (or use --periodic).")
            raise SystemExit(1)
        print("SUCCESS — button EVTs decoded.")
        print("Next: Lab 09 (multi-sensor)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
