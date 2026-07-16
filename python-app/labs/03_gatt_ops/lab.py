#!/usr/bin/env python3
"""Lab 03 — Write Request vs Write Command vs Notify (+ CCCD)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared import gatt_ops
from shared.framing import BS_CMD_PING, encode_bs_req
from shared.session_lite import PendingReq, SessionLite, now_ms


async def _one_write(
    session: SessionLite,
    *,
    label: str,
    with_response: bool,
    req_id: int,
) -> None:
    wire = encode_bs_req(req_id, BS_CMD_PING, b"")
    print(f"--- {label} ---")
    print(f"  payload: {wire.hex()} ({len(wire)} bytes PING)")

    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()
    session._pending[req_id] = PendingReq(cmd_id=BS_CMD_PING, future=fut)

    try:
        t_att0 = now_ms()
        await session.write_rx(wire, with_response=with_response)
        att_ms = now_ms() - t_att0
        print(f"  ATT write returned in {att_ms:.1f} ms  (with_response={with_response})")

        t_n0 = now_ms()
        req_id_out, cmd_id, status, _body = await asyncio.wait_for(fut, timeout=6.0)
        notify_ms = now_ms() - t_n0
        assert cmd_id == BS_CMD_PING and req_id_out == req_id
        print(f"  Notify PONG in {notify_ms:.1f} ms  status={status}")
        if status != 0:
            raise RuntimeError(f"{label}: PONG status={status}")
        print()
    finally:
        session._pending.pop(req_id, None)


async def main() -> None:
    print("Lab 03 — GATT ATT ops\n")
    print("Write Request (ack) | Write Command (no ack) | Notify + CCCD\n")

    session = SessionLite()
    try:
        await session.connect()

        cccd_before = await session.read_tx_cccd()
        print(f"BS_TX CCCD before notify: {gatt_ops.format_cccd(cccd_before)}")

        await session.enable_notify()

        cccd_after = await session.read_tx_cccd()
        print(f"BS_TX CCCD after notify:  {gatt_ops.format_cccd(cccd_after)}")
        print()

        await asyncio.sleep(0.2)

        await _one_write(
            session,
            label="Write Request (GATT_REQ_WRITE / response=True)",
            with_response=True,
            req_id=1,
        )
        await _one_write(
            session,
            label="Write Command (GATT_CMD_WRITE / response=False)",
            with_response=False,
            req_id=2,
        )

        print("SUCCESS — both write modes delivered PING; Notify returned PONG.")
        print("Takeaway: Write Request waits for ATT ack; Write Command does not.")
        print("Streaming labs (04+) default to Write Command for BS_RX.")
        print("Next: Lab 04 (session.ping helper)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
