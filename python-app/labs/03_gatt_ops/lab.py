#!/usr/bin/env python3
"""Lab 03 — go live: enable BS_TX notify and receive first EVT_SENSOR frames.

Replaces the old Write Request / PING teaching path. Continuous sensor data
does not need a PONG — firmware opens TX_EVT when CCCD notify turns on.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared import gatt_ops
from shared.lab_helpers import connect_and_live, duration_arg
from shared.session_lite import SessionLite


async def main() -> None:
    duration = duration_arg(8.0)
    print(f"Lab 03 — Go live / first EVTs ({duration:.0f}s)\n")
    print("Steps: connect -> start_notify(BS_TX) -> print decoded samples\n")

    counts: dict[int, int] = {}
    session = SessionLite()

    def on_sample(sample: dict) -> None:
        sid = int(sample["sensor_id"])
        counts[sid] = counts.get(sid, 0) + 1
        brief = ", ".join(
            f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in list(sample["fields"].items())[:4]
        )
        print(f"  {sample['label']:<8}  #{sample['counter']}  {brief}")

    session.set_sample_handler(on_sample)

    try:
        await connect_and_live(session)
        cccd = await session.read_tx_cccd()
        print(f"BS_TX CCCD: {gatt_ops.format_cccd(cccd)}\n")
        print("Listening...\n")
        await asyncio.sleep(duration)

        total = sum(counts.values())
        print("\nPer-sensor counts:", dict(sorted(counts.items())))
        if total == 0:
            print("FAIL: no EVT — TFT soft-blue? Only one BLE central?")
            raise SystemExit(1)
        print(f"SUCCESS — {total} sample(s) via Notify.")
        print("Next: Lab 04 (continuous multi-sensor stream)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
