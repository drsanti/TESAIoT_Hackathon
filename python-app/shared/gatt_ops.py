"""Low-level GATT helpers — Write Request / Write Command / Notify / Read."""

from __future__ import annotations

import asyncio
from typing import Callable

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic

from .gatt_ids import (
    BS2_BLE_CHAR_BS_LINK_UUID,
    BS2_BLE_CHAR_BS_RX_UUID,
    BS2_BLE_CHAR_BS_TX_UUID,
    CCCD_UUID,
    matches_bs2_ble_name,
)

NotifyCallback = Callable[[int, bytearray], None]


async def scan_tesaiot(*, timeout_s: float = 8.0) -> list[tuple[object, int]]:
    """Return [(BLEDevice, rssi), ...] ranked by RSSI descending."""
    found: dict[str, tuple[object, int]] = {}

    def on_detect(device, adv) -> None:
        name = device.name or getattr(adv, "local_name", None)
        if not matches_bs2_ble_name(name):
            return
        rssi = int(getattr(adv, "rssi", None) or -999)
        prev = found.get(device.address)
        if prev is None or rssi > prev[1]:
            found[device.address] = (device, rssi)

    async with BleakScanner(detection_callback=on_detect):
        await asyncio.sleep(timeout_s)

    return sorted(found.values(), key=lambda item: item[1], reverse=True)


def _props(char: BleakGATTCharacteristic | None) -> str:
    if char is None:
        return "(missing)"
    return ",".join(sorted(char.properties)) if char.properties else "(none)"


def describe_bs2_chars(client: BleakClient) -> list[str]:
    lines: list[str] = []
    for label, uuid in (
        ("BS_RX", BS2_BLE_CHAR_BS_RX_UUID),
        ("BS_TX", BS2_BLE_CHAR_BS_TX_UUID),
        ("BS_LINK", BS2_BLE_CHAR_BS_LINK_UUID),
    ):
        char = client.services.get_characteristic(uuid)
        lines.append(f"  {label}  {uuid}")
        lines.append(f"         properties: {_props(char)}")
    return lines


async def read_cccd(client: BleakClient, char_uuid: str = BS2_BLE_CHAR_BS_TX_UUID) -> bytes | None:
    """Read Client Characteristic Configuration of a char (usually BS_TX)."""
    char = client.services.get_characteristic(char_uuid)
    if char is None:
        return None
    for desc in char.descriptors:
        if str(desc.uuid).lower() == CCCD_UUID.lower():
            return bytes(await client.read_gatt_descriptor(desc.handle))
    return None


def format_cccd(raw: bytes | None) -> str:
    if raw is None or len(raw) < 2:
        return "unavailable"
    val = raw[0] | (raw[1] << 8)
    bits = []
    if val & 0x0001:
        bits.append("notify")
    if val & 0x0002:
        bits.append("indicate")
    return f"0x{val:04X} ({'+'.join(bits) if bits else 'off'})"


async def write_rx(client: BleakClient, data: bytes, *, with_response: bool) -> None:
    """Write BS_RX — Write Request (ack) when with_response=True, else Write Command."""
    await client.write_gatt_char(BS2_BLE_CHAR_BS_RX_UUID, data, response=with_response)


async def enable_tx_notify(client: BleakClient, callback: NotifyCallback) -> None:
    """Enable BS_TX notify; retry if WinRT returns before services are ready."""
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            if attempt > 0:
                await asyncio.sleep(0.6 * attempt)
                # Force a fresh GATT table — WinRT often connects with an empty cache.
                get_services = getattr(client, "get_services", None)
                if callable(get_services):
                    await get_services()
            char = client.services.get_characteristic(BS2_BLE_CHAR_BS_TX_UUID)
            if char is None:
                get_services = getattr(client, "get_services", None)
                if callable(get_services):
                    await get_services()
                char = client.services.get_characteristic(BS2_BLE_CHAR_BS_TX_UUID)
            if char is None:
                raise LookupError(f"BS_TX {BS2_BLE_CHAR_BS_TX_UUID} missing after connect")
            await client.start_notify(BS2_BLE_CHAR_BS_TX_UUID, callback)
            return
        except Exception as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


async def disable_tx_notify(client: BleakClient) -> None:
    try:
        await client.stop_notify(BS2_BLE_CHAR_BS_TX_UUID)
    except Exception:
        pass


async def read_link(client: BleakClient) -> bytes:
    return bytes(await client.read_gatt_char(BS2_BLE_CHAR_BS_LINK_UUID))


def format_link_snapshot(raw: bytes) -> str:
    if not raw:
        return "(empty)"
    connected = raw[0] if len(raw) > 0 else 0
    mtu = (raw[1] | (raw[2] << 8)) if len(raw) >= 3 else 0
    drops = int.from_bytes(raw[3:7], "little") if len(raw) >= 7 else None
    parts = [f"state={connected}", f"mtu={mtu}"]
    if drops is not None:
        parts.append(f"tx_drops={drops}")
    parts.append(f"raw={raw.hex()}")
    return " ".join(parts)
