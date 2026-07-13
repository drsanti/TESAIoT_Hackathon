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
from bleak.exc import BleakDeviceNotFoundError

from .chunk import BS2_BLE_CHUNK_VER, Bs2BleChunkReassembler
from .decode import (
    LAB_1HZ_SENSOR_CFGS,
    decode_sensor_cfg_body,
    encode_sensor_cfg_body,
    expected_cfg_hz,
    format_configured_rate,
    format_measured_rate,
    map_sensor_sample,
    rate_match_label,
)
from .gatt import (
    BS2_BLE_CHAR_BS_LINK_UUID,
    BS2_BLE_CHAR_BS_RX_UUID,
    BS2_BLE_CHAR_BS_TX_UUID,
    BS2_BLE_SERVICE_UUID,
    matches_bs2_ble_name,
)
from .scene_presets import (
    get_scene_preset,
    scene_preset_bmi270_mode,
    scene_preset_fusion_feed_ms,
    scene_preset_sensor_cfgs,
    scene_preset_status_line,
)
from .wire import (
    BLE_POLICY_BOOT_DEFAULT,
    BLE_POLICY_FACTORY_STREAMING,
    BS_CMD_BLE_POLICY_GET,
    BS_CMD_BLE_POLICY_SET,
    BS_CMD_BMI270_FUSION_FEED_SET,
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

# After MCU boot / BLE reconnect the REQ path is slow — use longer waits.
BOOT_REQ_TIMEOUT_S = 18.0
NORMAL_REQ_TIMEOUT_S = 8.0
POST_NOTIFY_SETTLE_S = 0.85

# deviceMs rollback larger than this while streaming ⇒ MCU reboot (not BLE-only drop).
_DEVICE_MS_REBOOT_GAP = 5000
# After reconnect, deviceMs below this while prior peak was high ⇒ reboot during outage.
_DEVICE_MS_POST_RECONNECT_LOW = 15000
_DEVICE_MS_POST_RECONNECT_PRIOR_MIN = 30000
# Firmware resets EVT counter on SENSOR_CFG / stream-policy change — detect rollback.
_COUNTER_RESET_PRIOR_MIN = 64


@dataclass
class _PendingReq:
    cmd_id: int
    future: asyncio.Future


@dataclass
class _MeasPoint:
    device_ms: int
    counter: int


@dataclass
class _RateSegment:
    """Monotonic counter span within one firmware evt_seq epoch."""

    start_counter: int
    start_device_ms: int
    last_counter: int
    last_device_ms: int


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
    # Unique EVT_SENSOR counters delivered after counter-dedupe.
    frame_unique: dict[str, int] = field(default_factory=dict)
    # Parseable EVT notifies before counter-dedupe (WinRT may repeat).
    frame_raw: dict[str, int] = field(default_factory=dict)
    # Wall-clock window for unique-frame rate check vs SENSOR_CFG.
    count_window_started_ms: float = 0.0
    # Monotonic MCU uptime ms from EVT_SENSOR (resets on chip reboot).
    peak_device_ms: int = 0
    # Last known BMI270 stream mode: 0=raw, 1=fusion, 2=hybrid (−1 = unknown).
    bmi270_stream_mode: int = -1


class Bs2BleSession:
    def __init__(
        self,
        *,
        on_log: LogFn | None = None,
        on_sample: SampleFn | None = None,
        on_raw_evt: RawEvtFn | None = None,
        on_state: Callable[[SessionState], None] | None = None,
        on_link_lost: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._on_log = on_log or (lambda _level, _text: None)
        self._on_sample = on_sample
        self._on_raw_evt = on_raw_evt
        self._on_state = on_state
        self._on_link_lost = on_link_lost
        self._client: BleakClient | None = None
        self._device: BLEDevice | None = None
        self._next_req_id = 1
        self._pending: dict[int, _PendingReq] = {}
        self._req_lock = asyncio.Lock()
        self._reassembler = Bs2BleChunkReassembler()
        self._last_counter: dict[int, int] = {}
        self._meas: dict[int, deque[_MeasPoint]] = {}
        self._rate_segment: dict[int, _RateSegment] = {}
        self._counter_resets: dict[int, int] = {}
        self._cfg_drop_logged: set[str] = set()
        self._samples_muted = True
        self._notify_loop: asyncio.AbstractEventLoop | None = None
        self._user_disconnect = False
        self._peak_device_ms = 0
        self._device_ms_at_link_lost: int | None = None
        self.state = SessionState()
        self._reset_frame_stats(emit=False)

    @property
    def peak_device_ms(self) -> int:
        return self._peak_device_ms

    def _note_device_ms(self, device_ms: int) -> None:
        """Track MCU uptime; detect chip reboot vs BLE-only disconnect."""
        ms = device_ms & 0xFFFFFFFF
        prior_peak = self._peak_device_ms

        if prior_peak > _DEVICE_MS_REBOOT_GAP and ms + _DEVICE_MS_REBOOT_GAP < prior_peak:
            self._log(
                "warn",
                f"MCU reboot detected · deviceMs rolled back {prior_peak} -> {ms}",
            )

        lost_peak = self._device_ms_at_link_lost
        if lost_peak is not None:
            if lost_peak >= _DEVICE_MS_POST_RECONNECT_PRIOR_MIN and ms < _DEVICE_MS_POST_RECONNECT_LOW:
                self._log(
                    "warn",
                    f"MCU reboot during outage · deviceMs {lost_peak} -> {ms} "
                    f"(chip reset — CM33 WDT / HardFault / SYSTEM_REBOOT)",
                )
            elif ms + 10_000 >= lost_peak:
                self._log(
                    "info",
                    f"BLE link restored · deviceMs still ~{ms} (peak before drop {lost_peak}) "
                    f"— MCU did not reboot",
                )
            self._device_ms_at_link_lost = None

        if ms >= prior_peak:
            self._peak_device_ms = ms
            self.state.peak_device_ms = ms

    def _reset_frame_stats(self, *, emit: bool = True) -> None:
        self.state.frame_unique = {k: 0 for k in SENSOR_IDS}
        self.state.frame_raw = {k: 0 for k in SENSOR_IDS}
        self.state.count_window_started_ms = time.monotonic() * 1000.0
        self._meas.clear()
        self._last_counter.clear()
        self._rate_segment.clear()
        self._counter_resets.clear()
        if emit:
            self._emit_state()

    def reset_frame_counts(self) -> None:
        """Clear unique/raw frame tallies and restart the rate window."""
        self._reset_frame_stats(emit=True)
        self._log("info", "Frame counters reset")

    def count_window_seconds(self) -> float:
        started = self.state.count_window_started_ms
        if started <= 0:
            return 0.0
        return max(0.0, (time.monotonic() * 1000.0 - started) / 1000.0)

    def unique_hz(self, sensor_key: str) -> float | None:
        """Wall-window rate of accepted monotonic EVT counters (after reset/stale filter)."""
        unique = self.state.frame_unique.get(sensor_key, 0)
        window_s = self.count_window_seconds()
        if window_s < 1.5 or unique < 2:
            return None
        return (unique - 1) / window_s

    def authoritative_meas_hz(self, sensor_key: str) -> float | None:
        """Publish rate for UI + cfg match — prefers MCU deviceMs span over wall window."""
        cfg = self.state.sensor_cfg.get(sensor_key)
        mode = int(cfg.get("publish_mode", 0)) if cfg else 0
        device_hz = self.get_measured_hz(sensor_key)
        wall_hz = self.unique_hz(sensor_key)
        if mode == 1:
            return device_hz or wall_hz
        if device_hz is not None and device_hz > 0:
            return device_hz
        return wall_hz

    def frame_stats_line(self, sensor_key: str) -> str:
        """Human line: evt frames, raw notifies, cfg vs deviceMs meas, match."""
        cfg = self.state.sensor_cfg.get(sensor_key)
        unique = self.state.frame_unique.get(sensor_key, 0)
        raw = self.state.frame_raw.get(sensor_key, 0)
        expected = expected_cfg_hz(cfg)
        mode = int(cfg.get("publish_mode", 0)) if cfg else 0
        meas_hz = self.authoritative_meas_hz(sensor_key)
        cfg_s = format_configured_rate(cfg)
        meas_s = format_measured_rate(meas_hz) or "…"
        match = rate_match_label(meas_hz, expected, publish_mode=mode)
        hint = ""
        sid = SENSOR_ID_TO_NUM.get(sensor_key)
        resets = self._counter_resets.get(sid, 0) if sid is not None else 0
        if resets > 0:
            hint = f"  (evt counter resets={resets})"
        return (
            f"frames evt={unique}  raw={raw}  "
            f"cfg {cfg_s}  meas {meas_s}  [{match}]{hint}"
        )

    def format_sample_meta(self, sample: dict) -> str:
        key = sample["sensor"]
        cfg = self.state.sensor_cfg.get(key)
        parts = [f"#{sample['counter']}", "ble"]
        if key == "bmi270":
            mode_names = {0: "raw", 1: "fusion", 2: "hybrid"}
            mode = mode_names.get(self.state.bmi270_stream_mode)
            if mode:
                parts.append(mode)
        if cfg:
            parts.append(f"cfg {format_configured_rate(cfg)}")
        meas = format_measured_rate(self.authoritative_meas_hz(key))
        if meas:
            parts.append(f"meas {meas}")
        parts.append(f"device {sample['device_ms']} ms")
        return " · ".join(parts)

    def _emit_state(self) -> None:
        if self._on_state:
            self._on_state(self.state)

    def _log(self, level: str, text: str) -> None:
        self._on_log(level, text)

    async def scan(self, timeout: float = 8.0) -> list[BLEDevice]:
        ranked = await self.scan_ranked(timeout=timeout)
        return [device for device, _rssi in ranked]

    def _tesaiot_adv_match(self, device: BLEDevice, adv: Any) -> bool:
        name = ""
        rssi = -999
        service_uuids: list[str] = []
        if adv is not None:
            name = adv.local_name or device.name or ""
            rssi = int(getattr(adv, "rssi", None) or -999)
            service_uuids = list(getattr(adv, "service_uuids", None) or [])
        else:
            name = device.name or ""
        if matches_bs2_ble_name(name):
            return True
        target = BS2_BLE_SERVICE_UUID.lower()
        return any(str(u).lower() == target for u in service_uuids)

    async def scan_ranked(self, timeout: float = 12.0) -> list[tuple[BLEDevice, int]]:
        """Return TESAIoT peripherals as (device, rssi) sorted best RSSI first."""
        found: dict[str, tuple[BLEDevice, int]] = {}
        raw_ble = 0

        def on_detect(device: BLEDevice, adv: Any) -> None:
            nonlocal raw_ble
            raw_ble += 1
            if not self._tesaiot_adv_match(device, adv):
                return
            rssi = -999
            if adv is not None:
                rssi = int(getattr(adv, "rssi", None) or -999)
            prev = found.get(device.address)
            if prev is None or rssi > prev[1]:
                found[device.address] = (device, rssi)

        scanner = BleakScanner(detection_callback=on_detect)
        await scanner.start()
        try:
            await asyncio.sleep(timeout)
        finally:
            await scanner.stop()

        ranked = sorted(found.values(), key=lambda item: item[1], reverse=True)
        if ranked:
            self._log("info", f"Scan: {len(ranked)} TESAIoT peripheral(s) ({raw_ble} BLE adverts)")
        else:
            self._log(
                "info",
                f"Scan: 0 TESAIoT peripheral(s) ({raw_ble} BLE adverts) — "
                "if board was up >60s, firmware may need ADV restart fix (reboot or reflash)",
            )
        return ranked

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def connect(self, device: BLEDevice, *, bootstrap: str = "full") -> None:
        await self.disconnect()
        self._device = device
        self._user_disconnect = False

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                self._client = BleakClient(
                    device,
                    disconnected_callback=self._on_ble_disconnected,
                    winrt={"use_cached_services": False},
                )
                await self._client.connect()
                last_exc = None
                break
            except (OSError, asyncio.TimeoutError, BleakDeviceNotFoundError) as exc:
                last_exc = exc
                self._log("warn", f"Connect attempt {attempt + 1}/3 failed: {exc!r}")
                if self._client is not None:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    self._client = None
                if attempt < 2:
                    await asyncio.sleep(1.0)
            except Exception as exc:
                last_exc = exc
                self._log("warn", f"Connect attempt {attempt + 1}/3 failed: {exc!r}")
                if self._client is not None:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    self._client = None
                if attempt < 2:
                    await asyncio.sleep(1.0)

        if last_exc is not None or self._client is None:
            raise last_exc or RuntimeError("connect failed")

        self._notify_loop = asyncio.get_running_loop()
        await self._client.start_notify(BS2_BLE_CHAR_BS_TX_UUID, self._on_notify)
        # WinRT notify path needs settle before first REQ/RES round-trip (longer after MCU boot).
        await asyncio.sleep(POST_NOTIFY_SETTLE_S)
        self.state.connected = True
        self.state.device_name = device.name or "TESAIoT"
        self.state.device_address = device.address
        self._peak_device_ms = 0
        self.state.peak_device_ms = 0
        self._emit_state()
        self._log("info", f"Connected: {self.state.device_name} ({device.address})")
        await self._quiet_bootstrap(mode=bootstrap)

    async def disconnect(self, *, user_initiated: bool = True) -> None:
        self._user_disconnect = user_initiated
        self._device_ms_at_link_lost = None
        client = self._client
        self._client = None
        self._reject_pending("disconnected")
        self._reassembler.reset()
        self._last_counter.clear()
        self._meas.clear()
        self._rate_segment.clear()
        self._counter_resets.clear()
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
        self._reset_frame_stats(emit=False)
        self._emit_state()
        self._log("info", "Disconnected" if user_initiated else "Link lost")

    def _on_ble_disconnected(self, _client: BleakClient) -> None:
        """Bleak stack dropped the link (range, reboot, central reset)."""
        if self._user_disconnect:
            return
        was_connected = self.state.connected
        prior_peak = self._peak_device_ms
        self._device_ms_at_link_lost = prior_peak if prior_peak > 0 else None
        self._client = None
        self._reject_pending("link lost")
        self._reassembler.reset()
        self._samples_muted = True
        self.state = SessionState()
        self._reset_frame_stats(emit=False)
        self._emit_state()
        if was_connected:
            if prior_peak > 0:
                self._log(
                    "warn",
                    f"BLE link lost · peak deviceMs={prior_peak} "
                    f"(compare after reconnect to see MCU reboot vs BLE-only)",
                )
            else:
                self._log("warn", "BLE link lost")
        if self._on_link_lost is None:
            return
        loop = self._notify_loop
        if loop is None or loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._on_link_lost(), loop)
        except RuntimeError:
            pass

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

    def _sync_streaming_from_policy(self) -> None:
        """Keep host delivery aligned with echoed BLE policy when SET retries fail."""
        tx_evt = (self.state.policy_flags & 0x02) != 0
        self._samples_muted = not tx_evt
        self.state.streaming = tx_evt
        self._emit_state()

    def unmute_receive(self) -> None:
        """Force host EVT delivery on (fallback when POLICY_SET is flaky)."""
        self._samples_muted = False
        self.state.streaming = True
        self._emit_state()

    async def enable_streaming(self, *, refresh_cfg: bool = False) -> None:
        """Enable BLE EVT egress (policy 0x07) and unmute host delivery.

        Unmutes as soon as TX_EVT is known — never waits on SENSOR_CFG GET.
        If POLICY_SET fails but EVTs are already flowing (or TX_EVT bit set),
        keep receiving so Auto is not stuck muted in LINKED.
        """
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("not connected")

        await self._ensure_tx_notify()

        flags = self.state.policy_flags
        try:
            flags = await self.set_ble_policy(
                BLE_POLICY_FACTORY_STREAMING,
                timeout=NORMAL_REQ_TIMEOUT_S,
                attempts=3,
            )
        except Exception as exc:
            evt_flowing = sum(self.state.frame_raw.values()) > 0
            if (self.state.policy_flags & 0x02) != 0 or evt_flowing:
                self._samples_muted = False
                self.state.streaming = True
                self._emit_state()
                self._log(
                    "warn",
                    f"BLE_POLICY_SET incomplete; streaming anyway "
                    f"(policy=0x{self.state.policy_flags:02x} evt_flowing={evt_flowing}): {exc!r}",
                )
            else:
                raise
        else:
            self._samples_muted = (flags & 0x02) == 0
            self.state.streaming = not self._samples_muted
            self._emit_state()

        if refresh_cfg or len(self.state.sensor_cfg) < 4:
            # Best-effort labels — do not block Stream on for long GET storms.
            try:
                await self.refresh_sensor_configs(attempts=1, timeout=4.0)
            except Exception as exc:
                self._log("warn", f"SENSOR_CFG refresh after stream on: {exc!r}")

        self._log(
            "info",
            f"Stream on — policy 0x{self.state.policy_flags:02x}, "
            f"SENSOR_CFG {len(self.state.sensor_cfg)}/4, muted={self._samples_muted}",
        )

    async def _ensure_tx_notify(self) -> None:
        """Re-arm BS_TX notify (WinRT can miss CCCD after reconnect)."""
        if self._client is None or not self._client.is_connected:
            return
        try:
            await self._client.start_notify(BS2_BLE_CHAR_BS_TX_UUID, self._on_notify)
            self._notify_loop = asyncio.get_running_loop()
            await asyncio.sleep(0.05)
        except Exception as exc:
            self._log("warn", f"BS_TX notify re-arm: {exc!r}")

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

    async def refresh_sensor_configs(
        self, *, attempts: int = 3, timeout: float = NORMAL_REQ_TIMEOUT_S
    ) -> dict[str, dict]:
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
                        timeout=timeout,
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
                    self._log("error", f"SENSOR_CFG_GET {key}: {exc!r}")
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
        applied = int(res[3][0])
        self.state.bmi270_stream_mode = applied
        self._emit_state()
        return applied

    async def set_bmi270_fusion_feed(self, interval_ms: int, timeout: float = 8.0) -> int:
        body = struct.pack("<H", int(interval_ms) & 0xFFFF)
        res = await self._send_req(BS_CMD_BMI270_FUSION_FEED_SET, body, timeout=timeout)
        if res[2] != 0:
            raise RuntimeError(f"BMI270_FUSION_FEED_SET status={res[2]}")
        if len(res[3]) < 2:
            raise RuntimeError("BMI270_FUSION_FEED_SET empty body")
        return struct.unpack_from("<H", res[3], 0)[0]

    async def apply_scene_preset(self, preset_id: str, *, go_live: bool = False) -> str:
        """Apply a sensor scene preset (RAM until reboot). Returns statusLine."""
        preset = get_scene_preset(preset_id)
        cfgs = scene_preset_sensor_cfgs(preset)
        was_streaming = self.state.streaming
        req_timeout = BOOT_REQ_TIMEOUT_S if go_live else NORMAL_REQ_TIMEOUT_S
        set_gap_s = 0.3 if go_live else 0.15

        if not go_live:
            self._samples_muted = True
            if self.state.policy_flags != BLE_POLICY_BOOT_DEFAULT:
                await self.set_ble_policy(BLE_POLICY_BOOT_DEFAULT, timeout=req_timeout)
                await asyncio.sleep(0.2)
        for cfg in cfgs:
            key = NUM_TO_SENSOR_ID[cfg["sensor_id"]]
            try:
                await self.set_sensor_cfg(cfg, timeout=req_timeout)
                await asyncio.sleep(set_gap_s)
                self._log("info", f"SENSOR_CFG_SET {key} ({preset_id})")
            except Exception as exc:
                self._log("error", f"SENSOR_CFG_SET {key}: {exc!r}")
        try:
            await self.set_bmi270_mode(scene_preset_bmi270_mode(preset), timeout=req_timeout)
            await asyncio.sleep(0.15)
            await self.set_bmi270_fusion_feed(
                scene_preset_fusion_feed_ms(preset), timeout=req_timeout
            )
        except Exception as exc:
            self._log("warn", f"BMI270 mode/feed for {preset_id}: {exc!r}")
        await asyncio.sleep(0.25)
        if go_live:
            try:
                await self.refresh_sensor_configs(attempts=1, timeout=4.0)
            except Exception as exc:
                self._log("warn", f"SENSOR_CFG refresh after preset: {exc!r}")
        else:
            await self.refresh_sensor_configs(timeout=req_timeout)
        missing = [k for k in SENSOR_IDS if k not in self.state.sensor_cfg]
        if missing:
            self._log("warn", f"Preset {preset_id} incomplete cfg: {', '.join(missing)}")
        if go_live:
            try:
                await self.enable_streaming(
                    refresh_cfg=len(self.state.sensor_cfg) < 4,
                )
            except Exception as exc:
                self._log("warn", f"Stream on after preset ({preset_id}): {exc!r}")
                self._sync_streaming_from_policy()
        elif was_streaming:
            try:
                await self.enable_streaming(refresh_cfg=False)
            except Exception as exc:
                self._log("warn", f"Stream restore after preset ({preset_id}): {exc!r}")
                self._sync_streaming_from_policy()
        else:
            self._samples_muted = False
        line = scene_preset_status_line(preset)
        self._log("info", line)
        return line

    async def apply_1hz_lab(self) -> None:
        """Back-compat: Lab Quiet scene (1 Hz)."""
        await self.apply_scene_preset("labQuiet")

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
        seg = self._rate_segment.get(sid)
        if seg is not None:
            span = (seg.last_device_ms - seg.start_device_ms) & 0xFFFFFFFF
            counter_span = seg.last_counter - seg.start_counter
            if span > 0 and span < 0x80000000 and counter_span > 0:
                return (counter_span / span) * 1000.0
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

    def _is_counter_reset(self, prior: int, counter: int) -> bool:
        if counter >= prior:
            return False
        if prior >= _COUNTER_RESET_PRIOR_MIN and counter <= prior // 2:
            return True
        # Early-session firmware reset (e.g. preset churn) — counter restarts near 1.
        return counter <= 2 and prior >= 8

    def _accept_evt_counter(self, sid: int, counter: int, device_ms: int) -> bool:
        """Drop WinRT duplicates, stale reorder, accept firmware evt_seq resets."""
        prior = self._last_counter.get(sid)
        if prior is not None:
            if counter == prior:
                return False
            if counter < prior:
                if self._is_counter_reset(prior, counter):
                    key = NUM_TO_SENSOR_ID.get(sid, str(sid))
                    self._counter_resets[sid] = self._counter_resets.get(sid, 0) + 1
                    self._log(
                        "info",
                        f"EVT counter reset {key}: {prior} -> {counter} "
                        f"(firmware SENSOR_CFG / stream-policy)",
                    )
                    self._meas.pop(sid, None)
                    ms = device_ms & 0xFFFFFFFF
                    self._rate_segment[sid] = _RateSegment(counter, ms, counter, ms)
                    self._last_counter[sid] = counter
                    return True
                return False
        self._last_counter[sid] = counter
        return True

    def _note_rate_segment(self, sid: int, device_ms: int, counter: int) -> None:
        ms = device_ms & 0xFFFFFFFF
        seg = self._rate_segment.get(sid)
        if seg is None:
            self._rate_segment[sid] = _RateSegment(counter, ms, counter, ms)
            return
        if counter >= seg.last_counter:
            seg.last_counter = counter
            seg.last_device_ms = ms

    async def _quiet_bootstrap(self, *, mode: str = "full") -> None:
        """Post-connect handshake. `fast` skips SENSOR_CFG GET storm (Auto go-live)."""
        req_timeout = BOOT_REQ_TIMEOUT_S if mode == "fast" else NORMAL_REQ_TIMEOUT_S
        try:
            await self.set_ble_policy(
                BLE_POLICY_BOOT_DEFAULT,
                timeout=NORMAL_REQ_TIMEOUT_S,
                attempts=2,
            )
            await asyncio.sleep(0.35)
        except Exception as exc:
            self._log("warn", f"Quiet policy bootstrap skipped: {exc!r}")
        await self.ping(timeout=req_timeout, attempts=4)
        if mode != "fast":
            await self.refresh_sensor_configs(attempts=2, timeout=req_timeout)
        try:
            await self.read_link_snapshot()
        except Exception as exc:
            self._log("warn", f"BS_LINK read skipped: {exc}")
        label = "Fast bootstrap: PING" if mode == "fast" else "Quiet bootstrap: PING + SENSOR_CFG + BS_LINK"
        self._log("info", label)

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
        key = NUM_TO_SENSOR_ID.get(sid)
        if key:
            self.state.frame_raw[key] = self.state.frame_raw.get(key, 0) + 1
        if self._on_raw_evt:
            self._on_raw_evt(evt)
        if not self._accept_evt_counter(sid, counter, evt["device_ms"]):
            return
        if key:
            self.state.frame_unique[key] = self.state.frame_unique.get(key, 0) + 1
        self._note_device_ms(evt["device_ms"])
        self._note_rate_segment(sid, evt["device_ms"], counter)
        self._note_meas(sid, evt["device_ms"], counter)

        if self._samples_muted:
            return

        sample = map_sensor_sample(evt)
        if sample is None:
            return

        sample_key = sample["sensor"]
        cfg = self.state.sensor_cfg.get(sample_key)
        if cfg is not None:
            if not cfg.get("enabled") or cfg.get("mask", 0) == 0:
                if sample_key not in self._cfg_drop_logged:
                    self._cfg_drop_logged.add(sample_key)
                    self._log(
                        "warn",
                        f"EVT dropped ({sample_key}): SENSOR_CFG disabled/mask=0 — "
                        f"tap Motion/Realtime or reconnect",
                    )
                return
        # When GET failed but SET succeeded, cfg may be missing — still deliver EVT.

        self.state.latest_sample[sample_key] = sample
        hz = self.authoritative_meas_hz(sample_key)
        self.state.measured_hz[sample_key] = hz or 0.0
        if self._on_sample:
            self._on_sample(sample)

    def _note_meas(self, sensor_id: int, device_ms: int, counter: int) -> None:
        points = self._meas.setdefault(sensor_id, deque(maxlen=24))
        if points and points[-1].counter == counter:
            return
        points.append(_MeasPoint(device_ms=device_ms & 0xFFFFFFFF, counter=counter))
