# TESAIoT BLE Python teaching labs

**Goal:** receive live **sensor / pot / button** data over BLE Notify.

All streaming labs use the same bring-up:

```
connect → start_notify(BS_TX) → print EVT_SENSOR
```

Firmware opens `TX_EVT` when CCCD notify turns on. **Do not gate labs on PING/PONG** — that path is fragile on Windows/WinRT.

## Prerequisites

- Flashed TESAIoT PSoC Edge DevKit (TFT **soft-blue** = advertising)
- Python **3.10+**
- One BLE central at a time

```bash
cd TESAIoT_Hackathon/python-app
python -m pip install -r requirements.txt
```

## Lab map

| Lab | Folder | Focus |
|----:|--------|-------|
| 01 | `labs/01_scan/` | Scan / advertise |
| 02 | `labs/02_connect/` | Connect + Read `BS_LINK` |
| 03 | `labs/03_gatt_ops/` | **Go live** — first EVT notifies |
| 04 | `labs/04_ping/` | **Continuous stream** (all sensors) |
| 05 | `labs/05_sensor_cfg/` | Focus one sensor (CFG fire-and-forget) |
| 06 | `labs/06_stream_imu_env/` | IMU + environment detail |
| 07 | `labs/07_adc_pot/` | Potentiometers |
| 08 | `labs/08_sw_btn/` | Buttons |
| 09 | `labs/09_multisensor_app/` | CLI dashboard — all six |
| 10 | `labs/10_your_app/` | Build-your-own template |

Folder names are historical (`03_gatt_ops`, `04_ping`); the scripts are EVT-first.

## How to run

```bash
./run_lab.sh 03          # Unix
run_lab.cmd 03           # Windows
python labs/03_gatt_ops/lab.py
python labs/07_adc_pot/lab.py --periodic   # smoke without turning pots
python labs/05_sensor_cfg/lab.py --focus 4
```

## Shared API

| Helper | Role |
|--------|------|
| `SessionLite.go_live()` | Enable BS_TX notify |
| `SessionLite.apply_cfgs_fire()` | SENSOR_CFG Write Command (no RES wait) |
| `shared/lab_helpers.connect_and_live()` | connect + go_live |

## BLE-safe rates

Keep ~**1 Hz** for IMU/env (`shared/rates.py`). Pots/buttons prefer **on_change** (use `--periodic` for unattended smoke).

## Related

- Protocol: Bitstream Studio `extension/docs/BS2_PROTOCOL_INDEX.md`
- Web UART demos: [`../web-app/`](../web-app/)
