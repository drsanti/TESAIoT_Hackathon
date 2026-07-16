# Lab 01 — Scan & advertise

## Learning goals

- Explain central vs peripheral roles
- Scan for `TESAIoT-*` advertisements and read RSSI
- Confirm the kit is advertising (TFT soft-blue)

## BLE concept

The DevKit is a **peripheral**: it advertises a local name. Your laptop is a **central**: it scans and chooses a device to connect later (Lab 02).

## Hardware check

1. Board powered and flashed
2. TFT shows **soft-blue** (advertising) — not gray Off
3. No other app holding a BLE connection (Park `ble-flet`, close nRF Connect)

## Run

```bash
# from python-app/
python labs/01_scan/lab.py
# or
./run_lab.sh 01
```

## Expected stdout

- A list of one or more `TESAIoT-…` devices with address and RSSI
- Hint to proceed to Lab 02

## Checkpoint questions

1. Who advertises — the kit or your PC?
2. What happens to advertising when a central connects? (preview Lab 02)

## Extend yourself

- Sort by strongest RSSI and print only the top device
- Filter by a specific board suffix if several kits are nearby

## Next lab

[`../02_connect/`](../02_connect/) — connect, list GATT properties, **read** `BS_LINK`
