"""Minimal BS2-over-BLE session for teaching labs (no Flet)."""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

# Flet-less, but WinRT still needs STA when a GUI host exists; safe no-op elsewhere.
try:
    from bleak.backends.winrt.util import allow_sta

    allow_sta()
except ImportError:
    pass

from bleak import BleakClient
from bleak.exc import BleakDeviceNotFoundError, BleakError

from . import gatt_ops
from .decode import decode_sensor_cfg_body, encode_sensor_cfg_body, map_sensor_sample
from .framing import (
    BS_CMD_BLE_POLICY_SET,
    BS_CMD_PING,
    BS_CMD_SENSOR_CFG_GET,
    BS_CMD_SENSOR_CFG_SET,
    BS_PREFIX,
    BS2_BLE_CHUNK_VER,
    BLE_POLICY_BOOT_DEFAULT,
    BLE_POLICY_FACTORY_STREAMING,
    Bs2BleChunkReassembler,
    encode_bs_req,
    try_parse_bs2_res,
    try_parse_evt_sensor,
)
from .gatt_ids import (
    BS2_BLE_ADV_NAME_PREFIX,
    BS2_BLE_CHAR_BS_TX_UUID,
)
from .sensor_cfg_defaults import teaching_sensor_cfgs

ROOT = Path(__file__).resolve().parents[1]


def ensure_shared_on_path() -> None:
    """Allow `from shared…` when running labs/*/lab.py directly."""
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


@dataclass
class PendingReq:
    cmd_id: int
    future: asyncio.Future


@dataclass
class SessionLite:
    """Connect, ATT helpers, and BS2 REQ/RES + EVT delivery."""

    scan_timeout_s: float = 10.0
    post_notify_settle_s: float = 0.5
    _client: BleakClient | None = field(default=None, repr=False)
    _reassembler: Bs2BleChunkReassembler = field(default_factory=Bs2BleChunkReassembler, repr=False)
    _pending: dict[int, PendingReq] = field(default_factory=dict, repr=False)
    _next_req_id: int = 1
    _req_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _notify_loop: asyncio.AbstractEventLoop | None = field(default=None, repr=False)
    _on_sample: Callable[[dict], None] | None = field(default=None, repr=False)
    _on_raw_notify: Callable[[bytes], None] | None = field(default=None, repr=False)
    _samples_muted: bool = field(default=False, repr=False)
    _notify_enabled: bool = field(default=False, repr=False)
    _touched_sensor_cfg: bool = field(default=False, repr=False)
    _last_counter: dict[int, int] = field(default_factory=dict, repr=False)
    _seen_evt: dict[int, set[int]] = field(default_factory=dict, repr=False)
    device_name: str = ""
    device_address: str = ""

    @property
    def client(self) -> BleakClient:
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("not connected")
        return self._client

    def set_sample_handler(self, handler: Callable[[dict], None] | None) -> None:
        self._on_sample = handler

    def set_raw_notify_handler(self, handler: Callable[[bytes], None] | None) -> None:
        self._on_raw_notify = handler

    def mute_samples(self, muted: bool = True) -> None:
        """Drop EVT delivery to the sample handler (keeps RES matching)."""
        self._samples_muted = muted

    async def write_req_fire(self, cmd_id: int, body: bytes = b"") -> None:
        """Write Command a BS2 REQ — do not wait for RES (WinRT-safe)."""
        req_id = self._next_req_id
        self._next_req_id = (self._next_req_id + 1) & 0xFFFF or 1
        wire = encode_bs_req(req_id, cmd_id, body)
        await self.write_rx(wire, with_response=False)

    async def go_live(self, *, settle_s: float = 0.8) -> None:
        """EVT-first bring-up: enable BS_TX notify. No PING / no RES wait.

        Firmware arms TX_EVT on CCCD rising edge. Do not fire POLICY_SET here —
        that Write can stall the WinRT notify pipe; CCCD auto-arm is enough.
        """
        if not self._notify_enabled:
            await self.enable_notify()
        self._samples_muted = False
        await asyncio.sleep(settle_s)
        print("Live: BS_TX notify on (TX_EVT via CCCD)")

    async def apply_cfgs_fire(self, cfgs: list[dict], *, gap_s: float = 0.05) -> None:
        """Push SENSOR_CFG_SET without waiting for RES."""
        from .decode import encode_sensor_cfg_body

        for cfg in cfgs:
            await self.write_req_fire(BS_CMD_SENSOR_CFG_SET, encode_sensor_cfg_body(cfg))
            self._touched_sensor_cfg = True
            await asyncio.sleep(gap_s)

    async def quiet_for_config(self) -> None:
        """Turn off BLE TX_EVT (fire-and-forget). Optional — advanced labs only."""
        if not self._notify_enabled:
            await self.enable_notify()
        await self.write_req_fire(BS_CMD_BLE_POLICY_SET, bytes((BLE_POLICY_BOOT_DEFAULT,)))
        await asyncio.sleep(0.4)

    async def scan_first(self, timeout: float | None = None, *, attempts: int = 3) -> object:
        timeout = self.scan_timeout_s if timeout is None else timeout
        last_err: Exception | None = None
        for attempt in range(max(1, attempts)):
            print(f"Scanning for {BS2_BLE_ADV_NAME_PREFIX}* ({timeout:.0f}s)…")
            try:
                ranked = await gatt_ops.scan_tesaiot(timeout_s=timeout)
            except Exception as exc:
                last_err = exc
                ranked = []
            if ranked:
                device, rssi = ranked[0]
                print(
                    f"  pick {getattr(device, 'name', None)}  "
                    f"{getattr(device, 'address', '')}  rssi={rssi}"
                )
                return device
            if attempt + 1 < attempts:
                wait_s = 5.0 + 3.0 * attempt
                print(f"  no advert yet — waiting {wait_s:.0f}s for ADV resume…")
                await asyncio.sleep(wait_s)
        raise RuntimeError(
            f"No device advertising name {BS2_BLE_ADV_NAME_PREFIX}* — "
            "press the board RESET (TFT should return soft-blue), "
            "close other BLE apps, then retry."
            + (f" ({last_err!r})" if last_err else "")
        )

    async def connect(self, device: object | None = None) -> None:
        last_exc: Exception | None = None
        for attempt in range(5):
            try:
                if device is None or attempt > 0:
                    if attempt > 0:
                        # WinRT TimeoutError often kills peripheral ADV without
                        # CONNECTION_DOWN. CM33 idle force-refresh is ~20s;
                        # ghost links may need a manual RESET.
                        wait_s = 12.0 + 4.0 * (attempt - 1)
                        print(
                            f"  connect retry {attempt + 1}/5 — "
                            f"waiting {wait_s:.0f}s for ADV (or press RESET)…"
                        )
                        await asyncio.sleep(wait_s)
                    device = await self.scan_first(attempts=4 if attempt > 0 else 3)
                kwargs: dict = {
                    "disconnected_callback": self._on_ble_disconnected,
                    "timeout": 45.0,
                }
                # WinRT: avoid stale GATT cache after MCU reboot
                if sys.platform == "win32":
                    kwargs["winrt"] = {"use_cached_services": False}
                self._client = BleakClient(device, **kwargs)
                await self._client.connect()
                last_exc = None
                break
            except (
                OSError,
                asyncio.TimeoutError,
                TimeoutError,
                BleakDeviceNotFoundError,
                BleakError,
                asyncio.CancelledError,
                RuntimeError,
            ) as exc:
                last_exc = (
                    exc if not isinstance(exc, asyncio.CancelledError) else TimeoutError(str(exc))
                )
                print(f"  connect attempt {attempt + 1}/5 failed: {type(exc).__name__}: {exc}")
                if self._client is not None:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    self._client = None
                device = None  # force re-scan
        if last_exc is not None or self._client is None:
            hint = (
                "\nHint: after a WinRT connect timeout the board often stops advertising. "
                "Press RESET once (wait for soft-blue), then re-run the lab."
            )
            if isinstance(last_exc, RuntimeError):
                raise RuntimeError(str(last_exc) + hint) from last_exc
            raise RuntimeError(f"connect failed: {last_exc!r}{hint}") from last_exc

        self._notify_loop = asyncio.get_running_loop()
        self.device_name = getattr(device, "name", None) or "TESAIoT"
        self.device_address = getattr(device, "address", "") or ""
        print(f"Connected: {self.device_name} ({self.device_address})")
        await self._wait_bs2_gatt_ready()

    async def _wait_bs2_gatt_ready(self, timeout_s: float = 12.0) -> None:
        """WinRT sometimes returns from connect before BS2 chars/CCCD are visible."""
        deadline = time.perf_counter() + timeout_s
        last_exc: Exception | None = None
        while time.perf_counter() < deadline:
            client = self._client
            if client is None or not client.is_connected:
                raise RuntimeError("disconnected while waiting for GATT")
            get_services = getattr(client, "get_services", None)
            if callable(get_services):
                try:
                    await get_services()
                except Exception as exc:
                    last_exc = exc
            char = client.services.get_characteristic(BS2_BLE_CHAR_BS_TX_UUID)
            if char is not None and any(
                str(desc.uuid).lower() == "00002902-0000-1000-8000-00805f9b34fb"
                or str(desc.uuid).lower().endswith("2902")
                for desc in char.descriptors
            ):
                await asyncio.sleep(0.15)
                return
            await asyncio.sleep(0.25)
        raise RuntimeError(
            "BS_TX / CCCD not ready after connect"
            + (f" ({last_exc!r})" if last_exc else "")
        )

    async def enable_notify(self) -> None:
        await gatt_ops.enable_tx_notify(self.client, self._on_notify)
        self._notify_enabled = True
        await asyncio.sleep(self.post_notify_settle_s)

    async def restore_teaching_sensors(self) -> None:
        """Re-enable all six sensors so TFT / UART keep updating after a focused lab."""
        if not self._notify_enabled:
            await self.enable_notify()
        self.mute_samples(True)
        await self.quiet_for_config()
        for cfg in teaching_sensor_cfgs():
            try:
                await self.sensor_cfg_set(cfg, timeout=4.0, attempts=1)
            except Exception:
                pass
        self.mute_samples(False)

    async def disconnect(self) -> None:
        client = self._client
        had_link = client is not None and bool(getattr(client, "is_connected", False))
        # Only restore CFG when a lab changed it (07/08). Needs CCCD for RES.
        if had_link and self._touched_sensor_cfg:
            try:
                await self.restore_teaching_sensors()
            except Exception as exc:
                print(f"warn: restore teaching sensors: {exc}")
            try:
                if self._notify_enabled:
                    await self.set_ble_policy(BLE_POLICY_BOOT_DEFAULT, timeout=3.0)
                    await asyncio.sleep(0.2)
            except Exception:
                pass
        self._client = None
        self._reject_pending("disconnected")
        self._reassembler.reset()
        self._seen_evt.clear()
        self._last_counter.clear()
        self._notify_enabled = False
        self._touched_sensor_cfg = False
        if client is not None:
            try:
                if client.is_connected:
                    await gatt_ops.disable_tx_notify(client)
            except Exception:
                pass
            try:
                await client.disconnect()
            except Exception:
                pass
        # WinRT / stack needs a beat before the peripheral re-advertises.
        await asyncio.sleep(2.0)
        if had_link:
            print("Disconnected")

    def _on_ble_disconnected(self, _client: BleakClient) -> None:
        self._reject_pending("link lost")
        self._reassembler.reset()

    async def write_rx(self, data: bytes, *, with_response: bool) -> None:
        await gatt_ops.write_rx(self.client, data, with_response=with_response)

    async def read_link(self) -> bytes:
        return await gatt_ops.read_link(self.client)

    async def read_tx_cccd(self) -> bytes | None:
        return await gatt_ops.read_cccd(self.client, BS2_BLE_CHAR_BS_TX_UUID)

    async def ping(self, timeout: float = 6.0, *, attempts: int = 3) -> tuple[int, int, int, bytes]:
        last_exc: Exception | None = None
        for attempt in range(max(1, attempts)):
            try:
                res = await self.send_req(BS_CMD_PING, b"", timeout=timeout)
                if res[2] != 0:
                    raise RuntimeError(f"PING failed status={res[2]}")
                return res
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(0.25 * (attempt + 1))
        assert last_exc is not None
        raise last_exc

    async def set_ble_policy(self, flags: int, timeout: float = 6.0) -> None:
        res = await self.send_req(BS_CMD_BLE_POLICY_SET, bytes((flags & 0xFF,)), timeout=timeout)
        if res[2] != 0:
            raise RuntimeError(f"BLE_POLICY_SET status={res[2]}")

    async def enable_streaming_policy(self) -> None:
        await self.set_ble_policy(BLE_POLICY_FACTORY_STREAMING)
        self._samples_muted = False

    async def sensor_cfg_get(self, sensor_id: int, timeout: float = 8.0, *, attempts: int = 3) -> dict:
        last_exc: Exception | None = None
        for attempt in range(max(1, attempts)):
            try:
                res = await self.send_req(
                    BS_CMD_SENSOR_CFG_GET, bytes((sensor_id & 0xFF,)), timeout=timeout
                )
                if res[2] != 0:
                    raise RuntimeError(f"SENSOR_CFG_GET id={sensor_id} status={res[2]}")
                cfg = decode_sensor_cfg_body(res[3])
                if cfg is None:
                    raise RuntimeError(f"SENSOR_CFG_GET id={sensor_id}: bad body")
                return cfg
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(0.2 * (attempt + 1))
        assert last_exc is not None
        raise last_exc

    async def sensor_cfg_set(self, cfg: dict, timeout: float = 8.0, *, attempts: int = 3) -> dict:
        body = encode_sensor_cfg_body(cfg)
        last_exc: Exception | None = None
        for attempt in range(max(1, attempts)):
            try:
                res = await self.send_req(BS_CMD_SENSOR_CFG_SET, body, timeout=timeout)
                if res[2] != 0:
                    raise RuntimeError(f"SENSOR_CFG_SET id={cfg.get('sensor_id')} status={res[2]}")
                echoed = decode_sensor_cfg_body(res[3]) if res[3] else cfg
                self._touched_sensor_cfg = True
                return echoed or cfg
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(0.2 * (attempt + 1))
        assert last_exc is not None
        raise last_exc

    async def send_req(
        self, cmd_id: int, body: bytes = b"", timeout: float = 8.0, *, with_response: bool = False
    ) -> tuple[int, int, int, bytes]:
        async with self._req_lock:
            req_id = self._next_req_id
            self._next_req_id = (self._next_req_id + 1) & 0xFFFF
            if self._next_req_id == 0:
                self._next_req_id = 1
            loop = asyncio.get_running_loop()
            fut: asyncio.Future = loop.create_future()
            self._pending[req_id] = PendingReq(cmd_id=cmd_id, future=fut)
            wire = encode_bs_req(req_id, cmd_id, body)
            try:
                await self.write_rx(wire, with_response=with_response)
                await asyncio.sleep(0)
                return await asyncio.wait_for(fut, timeout=timeout)
            finally:
                self._pending.pop(req_id, None)

    def _reject_pending(self, reason: str) -> None:
        for pending in list(self._pending.values()):
            if not pending.future.done():
                pending.future.set_exception(RuntimeError(reason))
        self._pending.clear()

    def _on_notify(self, *args) -> None:
        # Bleak 0.22: (handle, data). Bleak 3: (characteristic, data). Some backends: (data,).
        if not args:
            return
        data = args[-1]
        if not isinstance(data, (bytes, bytearray)):
            return
        if len(data) == 0:
            # WinRT occasionally delivers empty ValueChanged — ignore.
            return
        if self._notify_loop is None or self._notify_loop.is_closed():
            return
        chunk = bytes(data)
        if self._on_raw_notify is not None:
            try:
                self._on_raw_notify(chunk)
            except Exception:
                pass
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self._notify_loop:
            self._notify_loop.create_task(self._handle_notify_chunk(chunk))
            return
        try:
            asyncio.run_coroutine_threadsafe(self._handle_notify_chunk(chunk), self._notify_loop)
        except RuntimeError:
            pass

    async def _handle_notify_chunk(self, chunk: bytes) -> None:
        frame: bytes | None = None
        if len(chunk) > 0 and chunk[0] == BS2_BLE_CHUNK_VER:
            frame = self._reassembler.feed(chunk)
        elif len(chunk) >= 3 and chunk[0:3] == BS_PREFIX:
            self._reassembler.reset()
            frame = chunk
        else:
            frame = None
        if not frame:
            return
        self._handle_frame(frame)

    def _handle_frame(self, frame: bytes) -> None:
        res = try_parse_bs2_res(frame)
        if res is not None:
            req_id, cmd_id, status, body = res
            pending = self._pending.get(req_id)
            if pending is not None and pending.cmd_id == cmd_id and not pending.future.done():
                pending.future.set_result((req_id, cmd_id, status, body))
            return

        evt = try_parse_evt_sensor(frame)
        if evt is None:
            return
        if self._samples_muted or self._on_sample is None:
            return
        sid = int(evt["sensor_id"])
        counter = int(evt["counter"])
        seen = self._seen_evt.setdefault(sid, set())
        if counter in seen:
            return
        seen.add(counter)
        if len(seen) > 256:
            # Drop oldest-ish half by clearing when large (counters are monotonic-ish).
            self._seen_evt[sid] = {counter}
        self._last_counter[sid] = counter
        sample = map_sensor_sample(evt)
        if sample is None:
            return
        self._on_sample(sample)


async def with_session(
    run: Callable[[SessionLite], Awaitable[None]],
    *,
    notify: bool = True,
    quiet_ping: bool = False,
) -> None:
    """Connect helper used by most labs."""
    ensure_shared_on_path()
    session = SessionLite()
    try:
        await session.connect()
        if notify:
            await session.enable_notify()
        if quiet_ping:
            await session.ping(attempts=3)
        await run(session)
    finally:
        await session.disconnect()


def now_ms() -> float:
    return time.perf_counter() * 1000.0
