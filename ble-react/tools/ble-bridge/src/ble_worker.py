#!/usr/bin/env python3
"""
JSON-lines BLE worker for the Node ble-bridge (stdin/stdout).
Uses bleak (proven on Windows WinRT). Node owns the WebSocket API.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time

try:
    from bleak.backends.winrt.util import allow_sta

    allow_sta()
except ImportError:
    pass

from bleak import BleakClient, BleakScanner

SERVICE = "6f6b7a80-0001-4000-8000-00805f9b34fb"
BS_RX = "6f6b7a80-0001-4001-8000-00805f9b34fb"
BS_TX = "6f6b7a80-0001-4002-8000-00805f9b34fb"
BS_LINK = "6f6b7a80-0001-4003-8000-00805f9b34fb"
NAME_PREFIX = "TESAIoT-"
SCAN_S = 10.0


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def b64(data: bytes | bytearray) -> str:
    import base64

    return base64.b64encode(bytes(data)).decode("ascii")


def from_b64(s: str) -> bytes:
    import base64

    return base64.b64decode(s.encode("ascii"))


def uuid_eq(a: str, b: str) -> bool:
    return a.replace("-", "").lower() == b.replace("-", "").lower()


class Worker:
    def __init__(self) -> None:
        self.client: BleakClient | None = None
        self.notify_on = False
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        await self.disconnect()
        emit({"event": "log", "level": "info", "message": "scanning for TESAIoT-* …"})
        hits: dict[str, object] = {}

        def on_detect(device, adv) -> None:
            name = device.name or getattr(adv, "local_name", None)
            uuids = [str(u).lower() for u in (getattr(adv, "service_uuids", None) or [])]
            name_ok = isinstance(name, str) and (
                name.startswith(NAME_PREFIX) or name == "TESAIoT-"
            )
            uuid_ok = any(uuid_eq(u, SERVICE) for u in uuids)
            if name_ok or uuid_ok:
                hits[device.address] = device

        async with BleakScanner(detection_callback=on_detect):
            await asyncio.sleep(SCAN_S)

        if not hits:
            raise RuntimeError("No TESAIoT-* in scan - RESET to soft-blue; close other centrals")

        device = next(iter(hits.values()))
        kwargs: dict = {"timeout": 30.0}
        if sys.platform == "win32":
            kwargs["winrt"] = {"use_cached_services": False}
        client = BleakClient(device, **kwargs)
        await client.connect()
        self.client = client
        name = getattr(device, "name", None) or "TESAIoT"
        address = getattr(device, "address", "") or ""
        chars = []
        for label, uuid in (("BS_RX", BS_RX), ("BS_TX", BS_TX), ("BS_LINK", BS_LINK)):
            ch = client.services.get_characteristic(uuid)
            if ch is None:
                raise RuntimeError(f"{label} missing after connect")
            props = sorted(list(ch.properties)) if ch.properties else []
            chars.append({"label": label, "uuid": uuid, "properties": props})
        emit(
            {
                "event": "connected",
                "name": name if isinstance(name, str) else "TESAIoT",
                "address": str(address),
                "chars": chars,
            }
        )

    async def disconnect(self) -> None:
        client = self.client
        self.client = None
        self.notify_on = False
        if client is None:
            return
        try:
            if client.is_connected:
                await client.disconnect()
        except Exception:
            pass

    def _on_notify(self, _handle: int, data: bytearray) -> None:
        emit({"event": "notify", "data": b64(data)})

    async def start_notify(self) -> None:
        if not self.client or not self.client.is_connected:
            raise RuntimeError("not connected")
        await self.client.start_notify(BS_TX, self._on_notify)
        self.notify_on = True
        emit({"event": "notify_started"})

    async def stop_notify(self) -> None:
        if not self.client:
            emit({"event": "notify_stopped"})
            return
        try:
            await self.client.stop_notify(BS_TX)
        except Exception:
            pass
        self.notify_on = False
        emit({"event": "notify_stopped"})

    async def write_rx(self, data_b64: str, with_response: bool = False) -> None:
        if not self.client or not self.client.is_connected:
            raise RuntimeError("not connected")
        data = from_b64(data_b64)
        await self.client.write_gatt_char(BS_RX, data, response=with_response)
        emit({"event": "write_ok"})

    async def read_link(self) -> None:
        if not self.client or not self.client.is_connected:
            raise RuntimeError("not connected")
        data = await self.client.read_gatt_char(BS_LINK)
        emit({"event": "link", "data": b64(data)})


async def main() -> None:
    worker = Worker()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    def reader() -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError as exc:
                emit({"event": "error", "message": f"bad JSON: {exc}"})
                continue
            asyncio.run_coroutine_threadsafe(queue.put(msg), loop)

    import threading

    threading.Thread(target=reader, daemon=True).start()
    emit({"event": "ready", "backend": "bleak", "t": time.time()})

    while True:
        msg = await queue.get()
        cmd = msg.get("cmd")
        try:
            async with worker._lock:
                if cmd == "ping":
                    emit({"event": "pong", "t": time.time()})
                elif cmd == "connect":
                    await worker.connect()
                elif cmd == "disconnect":
                    await worker.disconnect()
                    emit({"event": "disconnected", "reason": "client-disconnect"})
                elif cmd == "start_notify":
                    await worker.start_notify()
                elif cmd == "stop_notify":
                    await worker.stop_notify()
                elif cmd == "write_rx":
                    await worker.write_rx(str(msg.get("data") or ""), bool(msg.get("withResponse")))
                elif cmd == "read_link":
                    await worker.read_link()
                else:
                    emit({"event": "error", "message": f"unknown cmd: {cmd}"})
        except Exception as exc:
            emit({"event": "error", "message": str(exc), "op": cmd})


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
