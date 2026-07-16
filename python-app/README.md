# TESAIoT BLE Python teaching labs

Progressive **scripts + Markdown** labs: BLE GATT ATT ops → BS2 PING → all six wire sensors → a multi-sensor mini-app.

No Flet UI — only `bleak` and the teaching helpers under `shared/`.

## Prerequisites

- Flashed TESAIoT PSoC Edge DevKit with BLE advertising (TFT **soft-blue**)
- Python **3.10+**
- One BLE central at a time (Park `ble-flet` / close nRF Connect)

```bash
cd TESAIoT_Hackathon/python-app
python -m pip install -r requirements.txt
```

## Lab map

| Lab | Folder | Focus |
|----:|--------|-------|
| 01 | `labs/01_scan/` | Scan / advertise |
| 02 | `labs/02_connect/` | Connect, properties, **Read** `BS_LINK` |
| 03 | `labs/03_gatt_ops/` | **Write Request**, **Write Command**, **Notify** + CCCD |
| 04 | `labs/04_ping/` | BS2 PING / PONG |
| 05 | `labs/05_sensor_cfg/` | SENSOR_CFG for sensors **0–5** |
| 06 | `labs/06_stream_imu_env/` | Live BMI270 / BMM350 / SHT40 / DPS368 |
| 07 | `labs/07_adc_pot/` | Potentiometers (ADC_POT) |
| 08 | `labs/08_sw_btn/` | Buttons (SW_BTN) |
| 09 | `labs/09_multisensor_app/` | CLI dashboard — all six |
| 10 | `labs/10_your_app/` | Build-your-own template |

## How to run

```bash
# Unix
./run_lab.sh 01

# Windows
run_lab.cmd 01

# Or directly
python labs/01_scan/lab.py
```

Read each folder’s `LAB.md` before running.

## Docs

| File | Contents |
|------|----------|
| [`docs/BLE_CONCEPTS.md`](docs/BLE_CONCEPTS.md) | Central/peripheral, ATT ops, CCCD |
| [`docs/BS2_CHEATSHEET.md`](docs/BS2_CHEATSHEET.md) | Frame layout, commands |
| [`docs/SENSOR_CATALOG.md`](docs/SENSOR_CATALOG.md) | All six sensors, masks, labs |

## GATT ATT ops (Lab 03)

| Op | Bleak | Characteristic |
|----|-------|----------------|
| Write Request (ack) | `response=True` | `BS_RX` |
| Write Command (no ack) | `response=False` | `BS_RX` |
| Notify | `start_notify` | `BS_TX` |
| Read | `read_gatt_char` | `BS_LINK` (Lab 02) |

Firmware forwards only frames that start with the BS2 prefix (`BS `). Lab 03 uses **PING** so Write Request / Write Command still produce a visible **Notify** (PONG).

## BLE-safe rates (important)

Do **not** crank `SENSOR_CFG` to tens of Hz on many sensors over BLE — that can starve CM33 (TFT freezes / WDT). Teaching labs use ~**1 Hz** periodic rates from [`shared/rates.py`](shared/rates.py) (same idea as ble-flet `labQuiet`). Pots/buttons stay **on_change**.

## After labs (TFT / UART)

Labs **07** / **08** temporarily enable only pots or buttons. On disconnect, `SessionLite` restores teaching defaults for **all six** sensors ([`shared/sensor_cfg_defaults.py`](shared/sensor_cfg_defaults.py)) so the TFT and UART keep updating. If you interrupt a lab mid-run, re-run Lab **05** or call `session.restore_teaching_sensors()`.

Keep **Bitstream Studio** on COM3 while developing is fine — firmware only mirrors BS2 frames onto BLE when a BLE session is active (not every UART `HELLO`/`RES`).

## Related

- Desktop dashboard: [`../ble-flet/`](../ble-flet/)
- Host protocol: Bitstream Studio `extension/docs/BS2_PROTOCOL_INDEX.md`
