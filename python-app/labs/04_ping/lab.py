#!/usr/bin/env python3
"""Lab 04 — BS2 PING / PONG via SessionLite."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.session_lite import SessionLite


async def main() -> None:
    print("Lab 04 — BS2 PING\n")
    session = SessionLite()
    try:
        await session.connect()
        await session.enable_notify()
        req_id, cmd_id, status, body = await session.ping(attempts=4)
        print(f"PONG  req_id={req_id} cmd=0x{cmd_id:02X} status={status} body_len={len(body)}")
        if status != 0:
            raise SystemExit(1)
        print("SUCCESS — link speaks BS2.")
        print("Next: Lab 05 (SENSOR_CFG for sensors 0–5)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
