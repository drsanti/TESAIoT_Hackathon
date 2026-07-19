#!/usr/bin/env python3
"""Smoke: sensor-node viewer path — connect_as_viewer, no SENSOR_CFG_SET, EVTs flow.

Usage (from ble-flet/):
  python scripts/verify_viewer_go_live.py
  python scripts/verify_viewer_go_live.py --duration 12

Exit 0 = EVTs received without any SENSOR_CFG_SET in session logs.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bs2.session import Bs2BleSession


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--scan", type=float, default=10.0)
    args = parser.parse_args()

    logs: list[tuple[str, str]] = []
    counts: dict[str, int] = {}

    def on_log(level: str, text: str) -> None:
        logs.append((level, text))
        print(f"[{level}] {text}")

    def on_sample(sample: dict) -> None:
        key = sample["sensor"]
        counts[key] = counts.get(key, 0) + 1

    session = Bs2BleSession(on_log=on_log, on_sample=on_sample)

    ranked = await session.scan_ranked(timeout=args.scan)
    if not ranked:
        print("FAIL: no TESAIoT peripheral — press RESET and retry")
        return 2

    device = ranked[0][0]
    print(f"Pick {device.name} {device.address}\n")

    cfg_set_logged = False
    try:
        await session.connect_as_viewer(device)
        print(f"Soak {args.duration:.0f}s...\n")
        await asyncio.sleep(args.duration)
    finally:
        await session.disconnect()

    for _level, text in logs:
        if "SENSOR_CFG_SET" in text:
            cfg_set_logged = True

    total = sum(counts.values())
    print("\nPer-sensor EVT:", counts)
    print(f"Total EVT: {total}")
    if cfg_set_logged:
        print("FAIL: SENSOR_CFG_SET appeared in viewer session logs")
        return 3
    if total < 1:
        print("FAIL: no EVT_SENSOR samples")
        return 1
    print("PASS: viewer go-live without SENSOR_CFG_SET")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
