#!/usr/bin/env python3
"""Lab 05 — focus one sensor (fire-and-forget SENSOR_CFG, no RES wait).

Examples:
  python lab.py              # BMI270 for 12s
  python lab.py 15           # BMI270 for 15s
  python lab.py --focus 4    # pots (periodic smoke)
  python lab.py 15 --focus 5 # buttons for 15s
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.lab_helpers import connect_and_live, duration_arg
from shared.rates import TEACHING_HMI_PERIODIC_MS, TEACHING_PERIODIC_MS
from shared.sensor_cfg_defaults import teaching_sensor_cfg
from shared.sensor_ids import DEFAULT_MASKS, SENSOR_ADC_POT, SENSOR_NAMES, SENSOR_SW_BTN
from shared.session_lite import SessionLite


def _parse_focus() -> int:
    if "--focus" in sys.argv:
        i = sys.argv.index("--focus")
        if i + 1 < len(sys.argv):
            return int(sys.argv[i + 1])
    return 0


def _focus_cfg(sid: int) -> list[dict]:
    out: list[dict] = []
    for i in range(6):
        if i != sid:
            out.append(
                {
                    "sensor_id": i,
                    "enabled": False,
                    "publish_mode": 0,
                    "mask": 0,
                    "sampling_interval_ms": 1000,
                    "delta_x100": 0,
                    "min_publish_interval_ms": 0,
                    "publish_interval_ms": 0,
                }
            )
            continue
        cfg = teaching_sensor_cfg(i)
        if i in (SENSOR_ADC_POT, SENSOR_SW_BTN):
            cfg = {
                **cfg,
                "publish_mode": 0,
                "sampling_interval_ms": TEACHING_HMI_PERIODIC_MS,
                "publish_interval_ms": TEACHING_HMI_PERIODIC_MS,
                "delta_x100": 0,
                "min_publish_interval_ms": 0,
                "mask": DEFAULT_MASKS[i],
            }
        else:
            cfg = {
                **cfg,
                "sampling_interval_ms": TEACHING_PERIODIC_MS,
                "publish_interval_ms": TEACHING_PERIODIC_MS,
            }
        out.append(cfg)
    return out


async def main() -> None:
    duration = duration_arg(12.0)
    focus = _parse_focus()
    name = SENSOR_NAMES.get(focus, f"id={focus}")
    print(f"Lab 05 — Focus sensor {focus} ({name}) for {duration:.0f}s")
    print("SENSOR_CFG is fire-and-forget (no RES wait).\n")

    count = 0
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        nonlocal count
        if sample["sensor_id"] != focus:
            return
        count += 1
        brief = ", ".join(
            f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in list(sample["fields"].items())[:6]
        )
        print(f"  {sample['label']:<8}  #{sample['counter']}  {brief}")

    session.set_sample_handler(on_sample)

    try:
        await connect_and_live(session)
        await session.apply_cfgs_fire(_focus_cfg(focus))
        await asyncio.sleep(0.4)
        print(f"Listening for {name} only...\n")
        await asyncio.sleep(duration)

        print(f"\nSamples for {name}: {count}")
        if count == 0:
            print("FAIL: no EVT for focused sensor.")
            raise SystemExit(1)
        print("SUCCESS — focused stream OK.")
        print("Next: Lab 06 (IMU+env) / 07 (pots) / 08 (buttons)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
