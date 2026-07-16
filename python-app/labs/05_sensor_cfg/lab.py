#!/usr/bin/env python3
"""Lab 05 — SENSOR_CFG GET/SET for sensors 0–5."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.rates import (
    TEACHING_ADC_DELTA_MV,
    TEACHING_ADC_MIN_PUB_MS,
    TEACHING_ADC_SAMPLE_MS,
    TEACHING_BTN_SAMPLE_MS,
    TEACHING_PERIODIC_MS,
)
from shared.sensor_ids import ALL_SENSOR_IDS, DEFAULT_MASKS, SENSOR_NAMES
from shared.session_lite import SessionLite

MODE_NAMES = {0: "periodic", 1: "on_change", 2: "hybrid"}


def _row(cfg: dict) -> str:
    sid = cfg["sensor_id"]
    name = SENSOR_NAMES.get(sid, "?")
    mode = MODE_NAMES.get(cfg.get("publish_mode", 0), str(cfg.get("publish_mode")))
    return (
        f"  {sid}  {name:<8}  en={int(cfg['enabled'])}  mode={mode:<10}  "
        f"mask=0x{cfg['mask']:02X}  samp={cfg['sampling_interval_ms']}ms  "
        f"pub={cfg['publish_interval_ms']}ms  delta={cfg.get('delta_x100', 0)}"
    )


def _teaching_cfg(sid: int) -> dict:
    if sid == 4:
        return {
            "sensor_id": sid,
            "enabled": True,
            "publish_mode": 1,
            "mask": DEFAULT_MASKS[sid],
            "sampling_interval_ms": TEACHING_ADC_SAMPLE_MS,
            "delta_x100": TEACHING_ADC_DELTA_MV,
            "min_publish_interval_ms": TEACHING_ADC_MIN_PUB_MS,
            "publish_interval_ms": 0,
        }
    if sid == 5:
        return {
            "sensor_id": sid,
            "enabled": True,
            "publish_mode": 1,
            "mask": DEFAULT_MASKS[sid],
            "sampling_interval_ms": TEACHING_BTN_SAMPLE_MS,
            "delta_x100": 0,
            "min_publish_interval_ms": 0,
            "publish_interval_ms": 0,
        }
    return {
        "sensor_id": sid,
        "enabled": True,
        "publish_mode": 0,
        "mask": DEFAULT_MASKS[sid],
        "sampling_interval_ms": TEACHING_PERIODIC_MS,
        "delta_x100": 0,
        "min_publish_interval_ms": 0,
        "publish_interval_ms": TEACHING_PERIODIC_MS,
    }


async def main() -> None:
    print("Lab 05 — SENSOR_CFG for all six sensors\n")
    print(f"Teaching rates: periodic ~{1000 // TEACHING_PERIODIC_MS} Hz (BLE-safe).\n")
    session = SessionLite()
    try:
        await session.connect()
        await session.enable_notify()
        await session.ping(attempts=3)
        session.mute_samples(True)
        await session.quiet_for_config()

        print("GET (current):\n")
        ok_get = 0
        ok_set = 0
        for sid in ALL_SENSOR_IDS:
            try:
                cfg = await session.sensor_cfg_get(sid)
                print(_row(cfg))
                ok_get += 1
            except Exception as exc:
                print(f"  {sid}  GET failed: {exc}")

        print("\nSET teaching defaults (BLE-safe)…\n")
        for sid in ALL_SENSOR_IDS:
            try:
                echoed = await session.sensor_cfg_set(_teaching_cfg(sid))
                print(_row(echoed))
                ok_set += 1
            except Exception as exc:
                print(f"  {sid}  SET failed: {exc}")

        print("\nFill the passport in docs/SENSOR_CATALOG.md.")
        print(f"GET ok {ok_get}/6 · SET ok {ok_set}/6")
        if ok_set < 6:
            print("FAIL: not all SENSOR_CFG_SET succeeded.")
            raise SystemExit(1)
        print("SUCCESS — configs for 0–5 exercised.")
        print("Next: Lab 06 (IMU + env stream) or 07/08 (pots / buttons)")
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
