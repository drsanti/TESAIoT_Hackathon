#!/usr/bin/env python3
"""Lab 01 — scan for TESAIoT BLE advertisements."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.gatt_ids import BS2_BLE_ADV_NAME_PREFIX
from shared.gatt_ops import scan_tesaiot


async def main() -> None:
    timeout = 8.0
    print(f"Lab 01 — Scan for {BS2_BLE_ADV_NAME_PREFIX}* ({timeout:.0f}s)")
    print("Hardware: TFT should be soft-blue (advertising).\n")

    matches = await scan_tesaiot(timeout_s=timeout)

    if not matches:
        print("FAIL: no TESAIoT-* advertisement found.")
        print("  - Check power / firmware / BLE module profile")
        print("  - Disconnect other centrals (nRF Connect, phones, other labs)")
        sys.exit(1)

    print(f"Found {len(matches)} device(s):\n")
    for i, (d, rssi) in enumerate(matches, 1):
        print(f"  {i}. {d.name}")
        print(f"     address: {d.address}")
        print(f"     RSSI:    {rssi} dBm")
        print()

    print("SUCCESS — advertising visible.")
    print("Next: Lab 02 (connect + read BS_LINK)")
    print("Tip: if a later connect times out and ADV vanishes, press board RESET.")


if __name__ == "__main__":
    asyncio.run(main())
