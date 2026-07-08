"""Async BS2 BLE session (bleak) — desktop replacement for Web Bluetooth."""

from __future__ import annotations

import asyncio
import struct
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from .chunk import BS2_BLE_CHUNK_VER, Bs2BleChunkReassembler
from .decode import (
    LAB_1HZ_SENSOR_CFGS,
    decode_sensor_cfg_body,
    encode_sensor_cfg_body,
    format_configured_rate,
    format_measured_rate,
    map_sensor_sample,
)
from .gatt import (
    BS2_BLE_CHAR_BS_LINK_UUID,
    BS2_BLE_CHAR_BS_RX_UUID,
    BS2_BLE_CHAR_BS_TX_UUID,
    matches_bs2_ble_name,
)
from .wire import (
    BLE_POLICY_BOOT_DEFAULT,
    BLE_POLICY_FACTORY_STREAMING,
    BS_CMD_BLE_POLICY_GET,
    BS_CMD_BLE_POLICY_SET,
    BS_CMD_BMI270_MODE_SET,
    BS_CMD_PING,
    BS_CMD_SENSOR_CFG_GET,
    BS_CMD_SENSOR_CFG_SET,
    BS_PREFIX,
    encode_bs_req,
    try_parse_bs2_res,
    try_parse_evt_sensor,
)

LogFn = Callable[[str, str], None]
SampleFn = Callable[[dict], None]
RawEvtFn = Callable[[dict], None]

SENSOR_IDS = ("bmi270", "bmm350", "sht40", "dps368")
SENSOR_ID_TO_NUM = {"bmi270": 0, "bmm350": 1, "sht40": 2, "dps368": 3}
NUM_TO_SENSOR_ID = {v: k for k, v in SENSOR_ID_TO_NUM.items()}


@dataclass
class _PendingReq:
    cmd_id: int
    future: asyncio.Future


@dataclass
class _MeasPoint:
    device_ms: int
    counter: int


@dataclass
class SessionState:
    connected: bool = False
    device_name: str = ""
    device_address: str = ""
    policy_flags: int = 0
    link_state: int = 0
    link_mtu: int = 0
    link_tx_drops: int = 0
    streaming: bool = False
    sensor_cfg: dict[str, dict] = field(default_factory=dict)
    latest_sample: dict[str, dict] = field(default_factory=dict)
    measured_hz: dict[str, float] = field(default_factory=dict)


class Bs2BleSession:
    def __init__(
        self,
        *,
        on_log: LogFn | None = None,
        on_sample: SampleFn | None = None,
        on_raw_evt: RawEvtFn | None = None,
        on_state: Callable[[SessionState], None] | None = None,
    ) -> None:
        self._on_log = on_log or (lambda _level, _text: None)
        self._on_sample = on_sample
        self._on_raw_evt = on_raw_evt
        self._on_state = on_state
        self._client: BleakClient | None = None
        self._device: BLEDevice | None = None
        self._next_req_id = 1
        self._pending: dict[int, _PendingReq] = {}
        self._req_lock = asyncio.Lock()
        self._reassembler = Bs2BleChunkReassembler()
        self._last_counter: dict[int, int] = {}
        self._meas: dict[int, deque[_MeasPoint]] = {}
        self._samples_muted = True
        self._notify_loop: asyncio.AbstractEventLoop | None = None
        self.state = SessionState()

    def _emit_state(self) -> None:
        if self._on_state:
            self._on_state(self.state)

    def _log(self, level: str, text: str) -> None:
        self._on_log(level, text)

    async def scan(self, timeout: float = 8.0) -> list[BLEDevice]:
        found: list[BLEDevice] = []
        seen: set[str] = set()

        try:
            discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
        except TypeError:
            discovered = await BleakScanner.discover(timeout=timeout)

        if isinstance(discovered, dict):
            entries = discovered.values()
        else:
            entries = ((device, None) for device in discovered)

        for device, adv in entries:
            name = ""
            if adv is not None:
                name = adv.local_name or device.name or ""
            else:
                name = device.name or ""
            if not matches_bs2_ble_name(name):
                continue
            if device.address in seen:
                continue
            seen.add(device.address)
            found.append(device)

        found.sort(key=lambda d: (d.name or d.address))
        self._log("info", f"Scan: {len(found)} TESAIoT peripheral(s)")
        return found

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def connect(self, device: BLEDevice) -> None:
        await self.disconnect()
        self._device = device
        self._client = BleakClient(device)
        await self._client.connect()
        self._notify_loop = asyncio.get_running_loop()
        await self._client.start_notify(BS2_BLE_CHAR_BS_TX_UUID, self._on_notify)
        # WinRT notify path needs a short settle before first REQ/RES round-trip.
        await asyncio.sleep(0.35)
        self.state.connected = True
        self.state.device_name = device.name or "TESAIoT"
        self.state.device_address = device.address
        self._emit_state()
        self._log("info", f"Connected: {self.state.device_name} ({device.address})")
        await self._quiet_bootstrap()

    async def disconnect(self) -> None:
        client = self._client
        self._client = None
        self._reject_pending("disconnected")
        self._reassembler.reset()
        self._last_counter.clear()
        self._meas.clear()
        self._samples_muted = True
        if client is not None:
            try:
                if client.is_connected:
                    await client.stop_notify(BS2_BLE_CHAR_BS_TX_UUID)
            except Exception as exc:
                self._log("error", f"stop_notify: {exc}")
            try:
                await client.disconnect()
            except Exception as exc:
                self._log("error", f"disconnect: {exc}")
        self.state = SessionState()
        self._emit_state()
        self._log("info", "Disconnected")

    async def ping(self, timeout: float = 6.0, *, attempts: int = 3) -> None:
        last_exc: Exception | None = None
        for attempt in range(max(1, attempts)):
            try:
                res = await self._send_req(BS_CMD_PING, b"", timeout=timeout)
                if res[2] != 0:
                    raise RuntimeError(f"PING failed status={res[2]}")
                return
            except Exception as exc:
                last_exc = exc
                self._log("warn", f"PING attempt {attempt + 1}/{attempts}: {exc}")
                await asyncio.sleep(0.25 * (attempt + 1))
        assert last_exc is not None
        raise last_exc

    async def enable_streaming(self, *, refresh_cfg: bool = True) -> None:
        self._samples_muted = True
        if refresh_cfg or len(self.state.sensor_cfg) < 4:
            await self.refresh_sensor_configs()
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("connection dropped before BLE_POLICY_SET")
        flags = await self.set_ble_policy(BLE_POLICY_FACTORY_STREAMING)
        self._samples_muted = len(self.state.sensor_cfg) == 0
        self.state.streaming = not self._samples_muted
        self._emit_state()
        self._log(
            "info",
            f"Stream on — policy 0x{flags:02x}, SENSOR_CFG {len(self.state.sensor_cfg)}/4",
        )

    async def set_ble_policy(self, flags: int, timeout: float = 8.0, *, attempts: int = 3) -> int:
        want = flags & 0x3F
        if self.state.policy_flags == want and self.connected:
            return want
        last_exc: Exception | None = None
        for attempt in range(max(1, attempts)):
            try:
                res = await self._send_req(
                    BS_CMD_BLE_POLICY_SET,
                    bytes((want,)),
                    timeout=timeout,
                )
                if res[2] != 0:
                    raise RuntimeError(f"BLE_POLICY_SET status={res[2]}")
                echoed = res[3][0] if res[3] else want
                self.state.policy_flags = echoed & 0x3F
                self._emit_state()
                return self.state.policy_flags
            except Exception as exc:
                last_exc = exc
                self._log("warn", f"BLE_POLICY_SET attempt {attempt + 1}/{attempts}: {exc}")
                await asyncio.sleep(0.25 * (attempt + 1))
        assert last_exc is not None
        raise last_exc

    async def refresh_sensor_configs(self, *, attempts: int = 3) -> dict[str, dict]:
        """Pull SENSOR_CFG for all sensors.

        Merges successful GETs into the existing map so a single timeout / status
        under BLE load does not wipe a previously verified row (SET echo or prior GET).
        Retries missing keys with a short quiet gap.
        """
        merged = dict(self.state.sensor_cfg)
        pending = list(SENSOR_ID_TO_NUM.items())
        for attempt in range(max(1, attempts)):
            if not pending:
                break
            if attempt > 0:
                await asyncio.sleep(0.15 * attempt)
            still: list[tuple[str, int]] = []
            for key, sid in pending:
                try:
                    res = await self._send_req(
                        BS_CMD_SENSOR_CFG_GET,
                        bytes((sid,)),
                        timeout=8.0,
                    )
                    if res[2] != 0:
                        self._log(
                            "error",
                            f"SENSOR_CFG_GET {key} status={res[2]} (attempt {attempt + 1})",
                        )
                        still.append((key, sid))
                        continue
                    cfg = decode_sensor_cfg_body(res[3])
                    if cfg is None:
                        self._log(
                            "error",
                            f"SENSOR_CFG_GET {key} decode failed (attempt {attempt + 1})",
                        )
                        still.append((key, sid))
                        continue
                    merged[key] = cfg
                except Exception as exc:
                    self._log("error", f"SENSOR_CFG_GET {key}: {exc}")
                    still.append((key, sid))
            pending = still
        if pending:
            kept = [k for k, _ in pending if k in merged]
            dropped = [k for k, _ in pending if k not in merged]
            if kept:
                self._log(
                    "warn",
                    f"SENSOR_CFG_GET retry exhausted; kept prior cfg for: {', '.join(kept)}",
                )
            if dropped:
                self._log(
                    "error",
                    f"SENSOR_CFG_GET failed with no prior cfg: {', '.join(dropped)}",
                )
        self.state.sensor_cfg = merged
        self._emit_state()
        return merged

    async def set_sensor_cfg(self, cfg: dict, timeout: float = 8.0) -> dict:
        res = await self._send_req(
            BS_CMD_SENSOR_CFG_SET,
            encode_sensor_cfg_body(cfg),
            timeout=timeout,
        )
        if res[2] != 0:
            raise RuntimeError(f"SENSOR_CFG_SET status={res[2]}")
        echoed = decode_sensor_cfg_body(res[3])
        if echoed is None:
            raise RuntimeError("SENSOR_CFG_SET decode failed")
        key = NUM_TO_SENSOR_ID.get(echoed["sensor_id"])
        if key:
            self.state.sensor_cfg[key] = echoed
            self._emit_state()
        return echoed

    async def set_bmi270_mode(self, mode: int, timeout: float = 8.0) -> int:
        """BMI270 stream mode: 0=raw, 1=fusion, 2=hybrid."""
        res = await self._send_req(
            BS_CMD_BMI270_MODE_SET,
            bytes((mode & 0xFF,)),
            timeout=timeout,
        )
        if res[2] != 0:
            raise RuntimeError(f"BMI270_MODE_SET status={res[2]}")
        if not res[3]:
            raise RuntimeError("BMI270_MODE_SET empty body")
        return res[3][0]

    async def apply_1hz_lab(self) -> None:
        """Write 1 Hz sampling + publish for all sensors (RAM until reboot)."""
        was_streaming = self.state.streaming
        self._samples_muted = True
        # Quiet bootstrap already set boot policy; only re-assert if different.
        if self.state.policy_flags != BLE_POLICY_BOOT_DEFAULT:
            await self.set_ble_policy(BLE_POLICY_BOOT_DEFAULT)
            await asyncio.sleep(0.2)
        for cfg in LAB_1HZ_SENSOR_CFGS:
            key = NUM_TO_SENSOR_ID[cfg["sensor_id"]]
            try:
                await self.set_sensor_cfg(cfg)
                await asyncio.sleep(0.2)
                self._log("info", f"SENSOR_CFG_SET {key} -> 1 Hz")
            except Exception as exc:
                self._log("error", f"SENSOR_CFG_SET {key}: {exc}")
        await asyncio.sleep(0.25)
        await self.refresh_sensor_configs()
        missing = [k for k in SENSOR_IDS if k not in self.state.sensor_cfg]
        if missing:
            self._log("warn", f"Apply 1 Hz incomplete cfg: {', '.join(missing)}")
        if was_streaming:
            await self.enable_streaming(refresh_cfg=False)
        else:
            self._samples_muted = False

    async def read_link_snapshot(self) -> None:
        if self._client is None or not self._client.is_connected:
            return
        data = await self._client.read_gatt_char(BS2_BLE_CHAR_BS_LINK_UUID)
        if len(data) < 7:
            return
        self.state.link_state = data[0]
        self.state.link_mtu = data[1] | (data[2] << 8)
        self.state.link_tx_drops = struct.unpack_from("<I", data, 3)[0]
        self._emit_state()

    def get_measured_hz(self, sensor_key: str) -> float | None:
        sid = SENSOR_ID_TO_NUM.get(sensor_key)
        if sid is None:
            return None
        points = self._meas.get(sid)
        if not points or len(points) < 2:
            return None
        first = points[0]
        last = points[-1]
        span = (last.device_ms - first.device_ms) & 0xFFFFFFFF
        counter_span = last.counter - first.counter
        if span <= 0 or span >= 0x80000000 or counter_span <= 0:
            return None
        return (counter_span / span) * 1000.0

    def format_sample_meta(self, sample: dict) -> str:
        key = sample["sensor"]
        cfg = self.state.sensor_cfg.get(key)
        parts = [f"#{sample['counter']}", "ble"]
        if cfg:
            parts.append(f"cfg {format_configured_rate(cfg)}")
        hz = self.get_measured_hz(key)
        meas = format_measured_rate(hz)
        if meas:
            parts.append(f"meas {meas}")
        parts.append(f"device {sample['device_ms']} ms")
        return " · ".join(parts)

    async def _quiet_bootstrap(self) -> None:
        await self.set_ble_policy(BLE_POLICY_BOOT_DEFAULT)
        await asyncio.sleep(0.2)
        await self.ping(attempts=3)
        await self.refresh_sensor_configs()
        try:
            await self.read_link_snapshot()
        except Exception as exc:
            self._log("warn", f"BS_LINK read skipped: {exc}")
        self._log("info", "Quiet bootstrap: PING + SENSOR_CFG + BS_LINK")

    async def _send_req(self, cmd_id: int, body: bytes, timeout: float = 8.0) -> tuple[int, int, int, bytes]:
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("not connected")
        async with self._req_lock:
            req_id = self._next_req_id
            self._next_req_id = (self._next_req_id + 1) & 0xFFFF
            if self._next_req_id == 0:
                self._next_req_id = 1
            loop = asyncio.get_running_loop()
            fut: asyncio.Future = loop.create_future()
            self._pending[req_id] = _PendingReq(cmd_id=cmd_id, future=fut)
            wire = encode_bs_req(req_id, cmd_id, body)
            try:
                await self._client.write_gatt_char(BS2_BLE_CHAR_BS_RX_UUID, wire, response=False)
                # Small yield so WinRT notify callbacks can drain into the loop.
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
            frame = chunk if len(chunk) >= 3 and chunk[0:3] == BS_PREFIX else None
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

        sid = evt["sensor_id"]
        counter = evt["counter"]
        if self._on_raw_evt:
            self._on_raw_evt(evt)
        if self._last_counter.get(sid) == counter:
            return
        self._last_counter[sid] = counter
        self._note_meas(sid, evt["device_ms"], counter)

        if self._samples_muted:
            return

        sample = map_sensor_sample(evt)
        if sample is None:
            return

        key = sample["sensor"]
        cfg = self.state.sensor_cfg.get(key)
        if not cfg or not cfg.get("enabled") or cfg.get("mask", 0) == 0:
            return

        self.state.latest_sample[key] = sample
        self.state.measured_hz[key] = self.get_measured_hz(key) or 0.0
        if self._on_sample:
            self._on_sample(sample)

    def _note_meas(self, sensor_id: int, device_ms: int, counter: int) -> None:
        points = self._meas.setdefault(sensor_id, deque(maxlen=24))
        if points and points[-1].counter == counter:
            return
        points.append(_MeasPoint(device_ms=device_ms & 0xFFFFFFFF, counter=counter))
