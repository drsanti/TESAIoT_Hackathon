#!/usr/bin/env python3
"""
Fresh BLE step diagnostic — does NOT use SessionLite / lab wrappers.

Purpose: prove firmware + Windows bleak still work, independent of ble-react.

  cd TESAIoT_Hackathon/python-app
  ./.venv/Scripts/python.exe tools/ble_step_diag.py

Always disconnects in finally. Kill with Ctrl+C if stuck.
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field

try:
    from bleak.backends.winrt.util import allow_sta

    allow_sta()
except ImportError:
    pass

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

# Locked BS2 GATT IDs (inline — no shared session imports)
SERVICE = "6f6b7a80-0001-4000-8000-00805f9b34fb"
BS_RX = "6f6b7a80-0001-4001-8000-00805f9b34fb"
BS_TX = "6f6b7a80-0001-4002-8000-00805f9b34fb"
BS_LINK = "6f6b7a80-0001-4003-8000-00805f9b34fb"
NAME_PREFIX = "TESAIoT-"

SCAN_S = 8.0


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""
    ms: float = 0.0


@dataclass
class Report:
    steps: list[StepResult] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "", ms: float = 0.0) -> None:
        self.steps.append(StepResult(name, ok, detail, ms))
        mark = "PASS" if ok else "FAIL"
        timing = f" ({ms:.0f} ms)" if ms else ""
        print(f"[{mark}] {name}{timing}")
        if detail:
            for line in detail.strip().splitlines():
                print(f"       {line}")


def _uuid_eq(a: str, b: str) -> bool:
    return a.replace("-", "").lower() == b.replace("-", "").lower()


async def step_scan(report: Report) -> object | None:
    t0 = time.perf_counter()
    hits: dict[str, tuple[object, int | None, str | None]] = {}

    def on_detect(device, adv) -> None:
        name = device.name or getattr(adv, "local_name", None)
        uuids = [str(u).lower() for u in (getattr(adv, "service_uuids", None) or [])]
        name_ok = isinstance(name, str) and name.startswith(NAME_PREFIX)
        uuid_ok = any(_uuid_eq(u, SERVICE) for u in uuids)
        # Name often empty until active scan response; UUID in primary ADV is enough.
        if not (name_ok or uuid_ok):
            return
        label = name if isinstance(name, str) and name else f"(uuid){device.address}"
        rssi = getattr(adv, "rssi", None)
        hits[device.address] = (device, rssi, label)

    try:
        async with BleakScanner(detection_callback=on_detect):
            await asyncio.sleep(SCAN_S)
    except Exception as exc:
        report.add("1 scan ADV", False, f"{type(exc).__name__}: {exc}", (time.perf_counter() - t0) * 1000)
        return None

    ms = (time.perf_counter() - t0) * 1000
    if not hits:
        report.add(
            "1 scan ADV",
            False,
            f"No {NAME_PREFIX}* in {SCAN_S:.0f}s - RESET board until TFT soft-blue; close other centrals.",
            ms,
        )
        return None

    lines = [f"{name}  {addr}  rssi={rssi}" for addr, (_d, rssi, name) in hits.items()]
    # Prefer strongest RSSI when available
    ranked = sorted(hits.values(), key=lambda x: x[1] if x[1] is not None else -999, reverse=True)
    device = ranked[0][0]
    report.add("1 scan ADV", True, "\n".join(lines), ms)
    return device


async def step_connect(report: Report, device: object) -> BleakClient | None:
    t0 = time.perf_counter()
    kwargs: dict = {"timeout": 30.0}
    if sys.platform == "win32":
        kwargs["winrt"] = {"use_cached_services": False}
    client = BleakClient(device, **kwargs)
    try:
        await client.connect()
    except Exception as exc:
        report.add(
            "2 GATT connect",
            False,
            f"{type(exc).__name__}: {exc}",
            (time.perf_counter() - t0) * 1000,
        )
        try:
            await client.disconnect()
        except Exception:
            pass
        return None

    ms = (time.perf_counter() - t0) * 1000
    name = getattr(device, "name", None) or "?"
    addr = getattr(device, "address", "") or "?"
    report.add("2 GATT connect", True, f"{name} ({addr}) connected={client.is_connected}", ms)
    return client


async def step_discover_service(report: Report, client: BleakClient) -> bool:
    t0 = time.perf_counter()
    try:
        get_services = getattr(client, "get_services", None)
        if callable(get_services):
            await get_services()
        services = list(client.services)
        uuids = [str(s.uuid) for s in services]
        found = any(_uuid_eq(u, SERVICE) for u in uuids)
        ms = (time.perf_counter() - t0) * 1000
        detail = f"services={len(uuids)}\n" + "\n".join(f"  {u}" for u in uuids[:12])
        if len(uuids) > 12:
            detail += f"\n  ... +{len(uuids) - 12} more"
        report.add("3 discover BS2 service", found, detail if found else detail + f"\nmissing {SERVICE}", ms)
        return found
    except Exception as exc:
        report.add(
            "3 discover BS2 service",
            False,
            f"{type(exc).__name__}: {exc}",
            (time.perf_counter() - t0) * 1000,
        )
        return False


async def step_discover_chars(report: Report, client: BleakClient) -> bool:
    t0 = time.perf_counter()
    try:
        lines = []
        ok = True
        for label, uuid in (("BS_RX", BS_RX), ("BS_TX", BS_TX), ("BS_LINK", BS_LINK)):
            char = client.services.get_characteristic(uuid)
            if char is None:
                ok = False
                lines.append(f"{label}: MISSING")
            else:
                props = ",".join(sorted(char.properties)) if char.properties else "(none)"
                lines.append(f"{label}: ok  props={props}")
        report.add("4 discover chars", ok, "\n".join(lines), (time.perf_counter() - t0) * 1000)
        return ok
    except Exception as exc:
        report.add(
            "4 discover chars",
            False,
            f"{type(exc).__name__}: {exc}",
            (time.perf_counter() - t0) * 1000,
        )
        return False


async def step_read_link(report: Report, client: BleakClient) -> bool:
    t0 = time.perf_counter()
    try:
        raw = bytes(await client.read_gatt_char(BS_LINK))
        hex_s = raw.hex()
        state = raw[0] if raw else None
        report.add(
            "5 read BS_LINK",
            True,
            f"len={len(raw)} hex={hex_s} state={state}",
            (time.perf_counter() - t0) * 1000,
        )
        return True
    except Exception as exc:
        report.add(
            "5 read BS_LINK",
            False,
            f"{type(exc).__name__}: {exc}",
            (time.perf_counter() - t0) * 1000,
        )
        return False


async def step_notify_probe(report: Report, client: BleakClient, listen_s: float = 3.0) -> bool:
    t0 = time.perf_counter()
    chunks: list[int] = []

    def on_notify(_handle: int, data: bytearray) -> None:
        chunks.append(len(data))

    try:
        await client.start_notify(BS_TX, on_notify)
        await asyncio.sleep(listen_s)
        await client.stop_notify(BS_TX)
        ms = (time.perf_counter() - t0) * 1000
        # Notify enable can PASS even with 0 EVTs (no SENSOR_CFG yet).
        report.add(
            "6 BS_TX notify enable",
            True,
            f"CCCD on; received {len(chunks)} notify(s) in {listen_s:.0f}s "
            f"(0 is OK without streaming CFG)",
            ms,
        )
        return True
    except Exception as exc:
        report.add(
            "6 BS_TX notify enable",
            False,
            f"{type(exc).__name__}: {exc}",
            (time.perf_counter() - t0) * 1000,
        )
        try:
            await client.stop_notify(BS_TX)
        except Exception:
            pass
        return False


async def main() -> int:
    print("=" * 60)
    print("Fresh BLE step diagnostic (bleak / WinRT)")
    print("Independent of ble-react labs transport")
    print("=" * 60)
    print()

    report = Report()
    client: BleakClient | None = None

    try:
        device = await step_scan(report)
        if device is None:
            _print_summary(report)
            return 1

        client = await step_connect(report, device)
        if client is None:
            _print_summary(report)
            return 2

        if not await step_discover_service(report, client):
            _print_summary(report)
            return 3

        if not await step_discover_chars(report, client):
            _print_summary(report)
            return 4

        if not await step_read_link(report, client):
            _print_summary(report)
            return 5

        await step_notify_probe(report, client)
        _print_summary(report)
        failed = [s for s in report.steps if not s.ok]
        return 0 if not failed else 10
    finally:
        if client is not None:
            try:
                if client.is_connected:
                    await client.disconnect()
                    print("\nDisconnected (cleanup).")
            except Exception as exc:
                print(f"\nDisconnect warning: {exc}")


def _print_summary(report: Report) -> None:
    print()
    print("-" * 60)
    print("SUMMARY")
    for s in report.steps:
        print(f"  {'PASS' if s.ok else 'FAIL'}  {s.name}")
    failed = [s for s in report.steps if not s.ok]
    if not failed:
        print()
        print("Firmware + Windows bleak path OK.")
        print("If Chrome Lab 03 still fails, the bug is Web Bluetooth / WinRT browser path,")
        print("not the board firmware.")
    else:
        print()
        print(f"{len(failed)} step(s) failed - fix hardware/radio before debugging Chrome.")
        print("Typical: RESET -> soft-blue ADV, one central only, BT Off/On.")


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nAborted.")
        raise SystemExit(130)
