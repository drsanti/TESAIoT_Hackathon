#!/usr/bin/env python3
"""Verify firmware EVT_SENSOR rate matches SENSOR_CFG over BLE.

Reads SENSOR_CFG per sensor, enables BLE streaming, soaks EVTs, and compares
measured Hz (device counter + deviceMs) to the expected periodic cadence.

Usage (from ble-flet/ with venv active):
  python scripts/verify_firmware_evt_rate.py
  python scripts/verify_firmware_evt_rate.py --duration 45 --apply-1hz
  python scripts/verify_firmware_evt_rate.py --tolerance 0.2 --sensor bmi270

Exit 0 = all enabled periodic sensors within tolerance; non-zero = failure.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Allow `python scripts/verify_firmware_evt_rate.py` from ble-flet/
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bleak import BleakScanner

from bs2.decode import (
    SENSOR_LABELS,
    evt_cadence_interval_ms,
    format_configured_rate,
    format_measured_rate,
    map_sensor_sample,
)
from bs2.gatt import matches_bs2_ble_name
from bs2.session import NUM_TO_SENSOR_ID, SENSOR_ID_TO_NUM, Bs2BleSession
from bs2.wire import BLE_POLICY_BOOT_DEFAULT, BLE_POLICY_FACTORY_STREAMING

SENSOR_ORDER = ("bmi270", "bmm350", "sht40", "dps368")

BMI270_MODE_NAMES = {0: "raw", 1: "fusion", 2: "hybrid"}


def _sensor_off_cfg(sensor_id: int) -> dict:
    return {
        "sensor_id": sensor_id,
        "enabled": False,
        "publish_mode": 0,
        "mask": 0,
        "sampling_interval_ms": 1000,
        "publish_interval_ms": 0,
        "delta_x100": 0,
        "min_publish_interval_ms": 0,
    }


async def isolate_bmi270(session: Bs2BleSession) -> None:
    """Disable env/mag sensors so BMI270 has the I2C bus."""
    was_streaming = session.state.streaming
    session._samples_muted = True
    await session.set_ble_policy(BLE_POLICY_BOOT_DEFAULT)
    for sid in (1, 2, 3):
        key = NUM_TO_SENSOR_ID[sid]
        try:
            await session.set_sensor_cfg(_sensor_off_cfg(sid))
            await asyncio.sleep(0.25)
            print(f"  disabled {key}")
        except Exception as exc:
            print(f"  WARN: disable {key}: {exc!r}")
    await session.refresh_sensor_configs()
    if was_streaming:
        await session.enable_streaming()
    else:
        session._samples_muted = False


@dataclass
class SensorProbe:
    sensor_id: int
    key: str
    deliveries: int = 0
    raw_frames: int = 0
    decode_fail: int = 0
    _seen_counters: set[int] = field(default_factory=set)
    first_counter: int | None = None
    last_counter: int | None = None
    first_device_ms: int | None = None
    last_device_ms: int | None = None
    last_mask: int = 0

    def note_raw(self) -> None:
        self.raw_frames += 1

    def note_decode_fail(self) -> None:
        self.decode_fail += 1

    def note_unique(self, counter: int, device_ms: int, mask: int) -> None:
        if counter in self._seen_counters:
            return
        self._seen_counters.add(counter)
        self.deliveries += 1
        self.last_mask = mask
        if self.first_counter is None:
            self.first_counter = counter
            self.first_device_ms = device_ms
        self.last_counter = counter
        self.last_device_ms = device_ms

    def note(self, counter: int, device_ms: int, mask: int) -> None:
        """Decoded sample delivered to app (post cfg filter)."""
        self.note_unique(counter, device_ms, mask)

    def measured_hz(self) -> float | None:
        if (
            self.first_counter is None
            or self.last_counter is None
            or self.first_device_ms is None
            or self.last_device_ms is None
        ):
            return None
        span = (self.last_device_ms - self.first_device_ms) & 0xFFFFFFFF
        counter_span = self.last_counter - self.first_counter
        if span <= 0 or span >= 0x80000000 or counter_span <= 0:
            return None
        return (counter_span / span) * 1000.0

    def measured_hz_by_events(self, wall_s: float) -> float | None:
        if wall_s <= 0 or self.deliveries < 2:
            return None
        return (self.deliveries - 1) / wall_s


@dataclass
class VerifyReport:
    key: str
    label: str
    cfg_summary: str
    expected_hz: float | None
    measured_hz: float | None
    events: int
    raw_frames: int
    decode_fail: int
    counter_span: int
    device_span_ms: int
    publish_mode: int
    passed: bool
    note: str = ""


def expected_periodic_hz(cfg: dict) -> float | None:
    if not cfg.get("enabled") or cfg.get("mask", 0) == 0:
        return None
    mode = int(cfg.get("publish_mode", 0))
    if mode == 1:
        return None
    ms = evt_cadence_interval_ms(cfg)
    if ms <= 0:
        return None
    return 1000.0 / ms


def cfg_one_line(cfg: dict | None) -> str:
    if not cfg:
        return "no cfg"
    return (
        f"mode={cfg.get('publish_mode', 0)} "
        f"samp={cfg.get('sampling_interval_ms', 0)}ms "
        f"pub={cfg.get('publish_interval_ms', 0)}ms "
        f"mask=0x{cfg.get('mask', 0):02x} "
        f"-> {format_configured_rate(cfg)}"
    )


def within_tolerance(measured: float, expected: float, tolerance: float) -> bool:
    if expected <= 0:
        return False
    lo = expected * (1.0 - tolerance)
    hi = expected * (1.0 + tolerance)
    return lo <= measured <= hi


def evaluate_sensor(
    key: str,
    cfg: dict | None,
    probe: SensorProbe,
    wall_s: float,
    tolerance: float,
    min_events: int,
) -> VerifyReport:
    label = SENSOR_LABELS.get(key, key)
    if cfg is None:
        return VerifyReport(
            key=key,
            label=label,
            cfg_summary="missing",
            expected_hz=None,
            measured_hz=None,
            events=probe.deliveries,
            raw_frames=probe.raw_frames,
            decode_fail=probe.decode_fail,
            counter_span=0,
            device_span_ms=0,
            publish_mode=-1,
            passed=False,
            note="SENSOR_CFG_GET failed",
        )

    mode = int(cfg.get("publish_mode", 0))
    expected = expected_periodic_hz(cfg)
    measured = probe.measured_hz()
    if measured is None:
        measured = probe.measured_hz_by_events(wall_s)

    counter_span = 0
    device_span_ms = 0
    if probe.first_counter is not None and probe.last_counter is not None:
        counter_span = probe.last_counter - probe.first_counter
    if probe.first_device_ms is not None and probe.last_device_ms is not None:
        device_span_ms = (probe.last_device_ms - probe.first_device_ms) & 0xFFFFFFFF

    note = ""
    if not cfg.get("enabled") or cfg.get("mask", 0) == 0:
        passed = probe.deliveries == 0 and probe.raw_frames == 0
        note = "disabled - expect 0 EVT" if passed else (
            f"unexpected raw={probe.raw_frames} delivered={probe.deliveries}"
        )
    elif mode == 1:
        passed = probe.deliveries >= 1 or probe.raw_frames >= 1
        note = "on_change - rate not checked" if passed else "no EVT in soak"
    elif expected is None:
        passed = False
        note = "cannot derive expected Hz"
    elif probe.deliveries < min_events and probe.raw_frames < min_events:
        passed = False
        if probe.raw_frames > 0 and probe.deliveries == 0:
            note = (
                f"raw={probe.raw_frames} but 0 decoded deliveries "
                f"(decode_fail={probe.decode_fail})"
            )
        else:
            note = f"need >={min_events} EVT, got raw={probe.raw_frames} delivered={probe.deliveries}"
    elif measured is None:
        passed = False
        note = "could not compute measured Hz"
    else:
        passed = within_tolerance(measured, expected, tolerance)
        note = (
            f"ok within +/-{tolerance * 100:.0f}% of {expected:.2f} Hz"
            if passed
            else f"outside +/-{tolerance * 100:.0f}% of {expected:.2f} Hz"
        )

    return VerifyReport(
        key=key,
        label=label,
        cfg_summary=cfg_one_line(cfg),
        expected_hz=expected,
        measured_hz=measured,
        events=probe.deliveries,
        raw_frames=probe.raw_frames,
        decode_fail=probe.decode_fail,
        counter_span=counter_span,
        device_span_ms=device_span_ms,
        publish_mode=mode,
        passed=passed,
        note=note,
    )


def print_report(reports: list[VerifyReport], wall_s: float) -> None:
    print()
    print(f"Soak wall time: {wall_s:.1f}s")
    print("-" * 88)
    for r in reports:
        exp = f"{r.expected_hz:.2f} Hz" if r.expected_hz is not None else "n/a"
        meas = format_measured_rate(r.measured_hz) or "n/a"
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.label} ({r.key})")
        print(f"       cfg: {r.cfg_summary}")
        print(
            f"       unique={r.events}  raw_notify={r.raw_frames}  decode_fail={r.decode_fail}  "
            f"counter+{r.counter_span}  deviceMs+{r.device_span_ms}  "
            f"expected={exp}  meas={meas}"
        )
        if r.note:
            print(f"       -> {r.note}")
    print("-" * 88)
    failed = [r for r in reports if not r.passed]
    if failed:
        print(f"FAILED: {len(failed)} sensor(s)")
    else:
        print("PASS: all sensors match expected firmware stream rate")


async def run(args: argparse.Namespace) -> int:
    try:
        from bleak import BleakClient  # noqa: F401 — import check
    except ImportError:
        print("Install bleak: pip install bleak", file=sys.stderr)
        return 1

    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: matches_bs2_ble_name(ad.local_name or d.name or ""),
        timeout=args.scan_timeout,
    )
    if device is None:
        print("No TESAIoT-* peripheral found", file=sys.stderr)
        return 2

    probes = {sid: SensorProbe(sensor_id=sid, key=NUM_TO_SENSOR_ID[sid]) for sid in NUM_TO_SENSOR_ID}

    def on_raw_evt(evt: dict) -> None:
        sid = evt["sensor_id"]
        if sid not in probes:
            return
        probe = probes[sid]
        probe.note_raw()
        probe.note_unique(evt["counter"], evt["device_ms"], evt.get("mask", 0))
        if map_sensor_sample(evt) is None:
            probe.note_decode_fail()

    def on_sample(_sample: dict) -> None:
        pass

    session = Bs2BleSession(on_sample=on_sample, on_raw_evt=on_raw_evt)
    exit_code = 1

    try:
        print(f"Connecting: {device.name} ({device.address})")
        await session.connect(device)

        if args.apply_1hz:
            print("Applying 1 Hz lab SENSOR_CFG (RAM until reboot)...")
            await session.apply_1hz_lab()
        else:
            await session.refresh_sensor_configs()

        if args.isolate_bmi270:
            print("Isolating BMI270 (disable BMM350/SHT40/DPS368)...")
            await isolate_bmi270(session)

        if args.bmi270_mode is not None:
            mode_code = {"raw": 0, "fusion": 1, "hybrid": 2}[args.bmi270_mode]
            echoed = await session.set_bmi270_mode(mode_code)
            print(f"BMI270_MODE_SET -> {BMI270_MODE_NAMES.get(echoed, echoed)}")

        # Snapshot expected cfg *before* streaming. Under EVT flood a GET can
        # time out; session.refresh now merges, but evaluate must not depend on
        # a partial post-stream map wiping SET echoes.
        cfgs = dict(session.state.sensor_cfg)

        print("\nSENSOR_CFG (pre-stream):")
        for key in SENSOR_ORDER:
            if args.sensor and key != args.sensor:
                continue
            print(f"  {SENSOR_LABELS[key]:8} {cfg_one_line(cfgs.get(key))}")

        missing_pre = [k for k in SENSOR_ORDER if (not args.sensor or k == args.sensor) and k not in cfgs]
        if missing_pre:
            print(f"Warning: missing SENSOR_CFG before stream: {', '.join(missing_pre)}")

        print("\nEnabling BLE stream (policy 0x07)...")
        await session.enable_streaming(refresh_cfg=len(cfgs) < 4)
        # Keep any newly fetched rows; never drop pre-stream baselines.
        for key, cfg in session.state.sensor_cfg.items():
            cfgs[key] = cfg
        if len(cfgs) < 4:
            print(f"Warning: SENSOR_CFG known {len(cfgs)}/4 after stream on")

        if args.warmup > 0:
            print(f"Warmup {args.warmup:.0f}s...")
            await asyncio.sleep(args.warmup)

        print(f"Soaking {args.duration:.0f}s - counting EVT_SENSOR per sensor...")
        t0 = asyncio.get_event_loop().time()
        link_start = session.state.link_tx_drops
        elapsed = 0.0
        poll_s = max(5.0, args.link_poll)
        while elapsed < args.duration:
            step = min(poll_s, args.duration - elapsed)
            await asyncio.sleep(step)
            elapsed += step
            await session.read_link_snapshot()
            link = session.state
            if link.link_state != 0 or link.link_mtu != 0:
                print(
                    f"  BS_LINK @ {elapsed:.0f}s: state={link.link_state} "
                    f"mtu={link.link_mtu} tx_drops={link.link_tx_drops}"
                )
        wall_s = asyncio.get_event_loop().time() - t0

        session._samples_muted = True
        try:
            await session.set_ble_policy(BLE_POLICY_BOOT_DEFAULT)
            await asyncio.sleep(0.35)
            await session.refresh_sensor_configs()
            for key, cfg in session.state.sensor_cfg.items():
                cfgs[key] = cfg
        except Exception as exc:
            print(f"Warning: post-soak quiet refresh skipped ({exc!r})")

        try:
            await session.read_link_snapshot()
        except Exception as exc:
            print(f"Warning: BS_LINK read failed ({exc!r})")
        link = session.state
        drop_delta = link.link_tx_drops - link_start
        print(
            f"BS_LINK final: state={link.link_state} mtu={link.link_mtu} "
            f"tx_drops={link.link_tx_drops} (+{drop_delta} during soak)"
        )

        print("\nSENSOR_CFG (used for rate check):")
        for key in SENSOR_ORDER:
            if args.sensor and key != args.sensor:
                continue
            print(f"  {SENSOR_LABELS[key]:8} {cfg_one_line(cfgs.get(key))}")

        reports: list[VerifyReport] = []
        for key in SENSOR_ORDER:
            if args.sensor and key != args.sensor:
                continue
            sid = SENSOR_ID_TO_NUM[key]
            reports.append(
                evaluate_sensor(
                    key,
                    cfgs.get(key),
                    probes[sid],
                    wall_s,
                    args.tolerance,
                    args.min_events,
                )
            )

        print_report(reports, wall_s)
        exit_code = 0 if all(r.passed for r in reports) else 3
    finally:
        await session.disconnect()

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify TESAIoT firmware EVT rate vs SENSOR_CFG over BLE",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Soak seconds after warmup (default 30)",
    )
    parser.add_argument(
        "--warmup",
        type=float,
        default=3.0,
        help="Seconds after stream on before measuring (default 3)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.25,
        help="Allowed fractional error vs expected Hz (default 0.25 = ±25%%)",
    )
    parser.add_argument(
        "--min-events",
        type=int,
        default=3,
        help="Minimum EVT count per sensor to judge periodic rate (default 3)",
    )
    parser.add_argument(
        "--apply-1hz",
        action="store_true",
        help="SENSOR_CFG_SET 1 Hz all sensors before soak",
    )
    parser.add_argument(
        "--sensor",
        choices=SENSOR_ORDER,
        default=None,
        help="Verify one sensor only",
    )
    parser.add_argument(
        "--scan-timeout",
        type=float,
        default=20.0,
        help="BLE scan timeout seconds (default 20)",
    )
    parser.add_argument(
        "--isolate-bmi270",
        action="store_true",
        help="SENSOR_CFG_SET disable BMM350/SHT40/DPS368 before soak",
    )
    parser.add_argument(
        "--bmi270-mode",
        choices=("raw", "fusion", "hybrid"),
        default=None,
        help="BMI270_MODE_SET before soak (default: firmware hybrid)",
    )
    parser.add_argument(
        "--link-poll",
        type=float,
        default=10.0,
        help="Read BS_LINK every N seconds during soak (default 10)",
    )
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
