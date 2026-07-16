"""Minimal BS2-over-BLE session for teaching labs (no Flet)."""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

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

    scan_timeout_s: float = 8.0
    post_notify_settle_s: float = 0.35
    _client: BleakClient | None = field(default=None, repr=False)
    _reassembler: Bs2BleChunkReassembler = field(default_factory=Bs2BleChunkReassembler, repr=False)
    _pending: dict[int, PendingReq] = field(default_factory=dict, repr=False)
    _next_req_id: int = 1
    _req_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _notify_loop: asyncio.AbstractEventLoop | None = field(default=None, repr=False)
    _on_sample: Callable[[dict], None] | None = field(default=None, repr=False)
    _on_raw_notify: Callable[[bytes], None] | None = field(default=None, repr=False)
    _samples_muted: bool = field(default=False, repr=False)
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

    async def quiet_for_config(self) -> None:
        """Turn off BLE TX_EVT so SENSOR_CFG REQ/RES is not starved."""
        try:
            await self.set_ble_policy(BLE_POLICY_BOOT_DEFAULT, timeout=8.0)
            await asyncio.sleep(0.35)
        except Exception as exc:
            print(f"warn: quiet policy: {exc}")

    async def scan_first(self, timeout: float | None = None) -> object:
        timeout = self.scan_timeout_s if timeout is None else timeout
        print(f"Scanning for {BS2_BLE_ADV_NAME_PREFIX}* ({timeout:.0f}s)…")
        ranked = await gatt_ops.scan_tesaiot(timeout_s=timeout)
        if not ranked:
            raise RuntimeError(
                f"No device advertising name {BS2_BLE_ADV_NAME_PREFIX}* — "
                "check TFT soft-blue and that no other central is connected."
            )
        device, rssi = ranked[0]
        print(f"  pick {getattr(device, 'name', None)}  {getattr(device, 'address', '')}  rssi={rssi}")
        return device

    async def connect(self, device: object | None = None) -> None:
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                if device is None or attempt > 0:
                    if attempt > 0:
                        print(f"  connect retry {attempt + 1}/4…")
                        # Failed connects often leave a ghost peripheral link;
                        # CM33 abandoned recovery is ~5s — wait it out.
                        await asyncio.sleep(8.0)
                    device = await self.scan_first()
                kwargs: dict = {
                    "disconnected_callback": self._on_ble_disconnected,
                    "timeout": 30.0,
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
                BleakDeviceNotFoundError,
                BleakError,
                asyncio.CancelledError,
            ) as exc:
                last_exc = exc if not isinstance(exc, asyncio.CancelledError) else TimeoutError(str(exc))
                print(f"  connect attempt {attempt + 1}/4 failed: {type(exc).__name__}: {exc}")
                if self._client is not None:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    self._client = None
                device = None  # force re-scan
        if last_exc is not None or self._client is None:
            raise last_exc or RuntimeError("connect failed")

        self._notify_loop = asyncio.get_running_loop()
        self.device_name = getattr(device, "name", None) or "TESAIoT"
        self.device_address = getattr(device, "address", "") or ""
        print(f"Connected: {self.device_name} ({self.device_address})")
        # WinRT: services can lag the connect ACK — settle before CCCD/notify.
        await asyncio.sleep(0.5)
        get_services = getattr(self._client, "get_services", None)
        if callable(get_services):
            try:
                await get_services()
            except Exception:
                pass

    async def enable_notify(self) -> None:
        await gatt_ops.enable_tx_notify(self.client, self._on_notify)
        await asyncio.sleep(self.post_notify_settle_s)

    async def restore_teaching_sensors(self) -> None:
        """Re-enable all six sensors so TFT / UART keep updating after a focused lab."""
        self.mute_samples(True)
        await self.quiet_for_config()
        for cfg in teaching_sensor_cfgs():
            try:
                await self.sensor_cfg_set(cfg, timeout=6.0, attempts=2)
            except Exception:
                pass
        self.mute_samples(False)

    async def disconnect(self) -> None:
        client = self._client
        # Restore multi-sensor CFG before tear-down (lab 07/08 disable siblings).
        if client is not None and client.is_connected:
            try:
                await self.restore_teaching_sensors()
            except Exception:
                pass
            try:
                await self.set_ble_policy(BLE_POLICY_BOOT_DEFAULT, timeout=4.0)
                await asyncio.sleep(0.3)
            except Exception:
                pass
        self._client = None
        self._reject_pending("disconnected")
        self._reassembler.reset()
        self._seen_evt.clear()
        self._last_counter.clear()
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
        await asyncio.sleep(3.0)
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

    def _on_notify(self, _handle: int, data: bytearray) -> None:
        if self._notify_loop is None or self._notify_loop.is_closed():
            return
        chunk = bytes(data)
        if self._on_raw_notify is not None:
            try:
                self._on_raw_notify(chunk)
            except Exception:
                pass
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
