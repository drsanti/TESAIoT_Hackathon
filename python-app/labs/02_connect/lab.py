#!/usr/bin/env python3
"""Lab 02 — connect, list GATT properties, read BS_LINK."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared import gatt_ops
from shared.session_lite import SessionLite


async def main() -> None:
    print("Lab 02 — Connect & discover (Read BS_LINK)\n")
    session = SessionLite()
    try:
        await session.connect()
        client = session.client

        print("BS2 characteristics:")
        for line in gatt_ops.describe_bs2_chars(client):
            print(line)
        print()

        raw = await session.read_link()
        print("BS_LINK Read:")
        print(f"  {gatt_ops.format_link_snapshot(raw)}")
        print()
        print("SUCCESS — connected and Read completed.")
        print("Next: Lab 03 (Write Request / Write Command / Notify)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
