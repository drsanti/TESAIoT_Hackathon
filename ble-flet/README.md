# TESAIoT BLE Flet app

Desktop **BS2 over BLE** dashboard for the hackathon — replaces the experimental Web Bluetooth HTML pages.

Uses **bleak** (WinRT / BlueZ / CoreBluetooth) instead of browser Web Bluetooth, so EVT timing and UI updates are not affected by Chrome notify batching.

## Requirements

- Python **3.10+**
- TESAIoT firmware with **BLE module profile** enabled + reboot
- No other BLE central connected (nRF Connect, etc.)

## Setup (optional)

`run.bat` / `run.sh` create `.venv` and install deps on first run. Manual setup:

```bash
cd TESAIoT_Hackathon/ble-flet
python -m venv .venv
# Windows (cmd): .venv\Scripts\activate
# Git Bash / macOS / Linux: use run.sh (prefer) — do not rely on `python` after activate in Git Bash
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# .venv/bin/python -m pip install -r requirements.txt           # macOS / Linux
```

## Verify firmware EVT rate

Confirm SENSOR_CFG matches on-wire EVT cadence (no UI):

```bash
./.venv/Scripts/python.exe scripts/verify_firmware_evt_rate.py
./.venv/Scripts/python.exe scripts/verify_firmware_evt_rate.py --apply-1hz --duration 45
```

Exit **0** = pass; **3** = rate mismatch. Uses device `counter` + `deviceMs` on **parsed EVT_SENSOR** frames (not wall-clock notify bursts). Report columns: `unique` = deduped counters; `raw_notify` = parseable EVT before dedup; `decode_fail` = mask/payload decode errors.

## Run

**Windows (cmd / Explorer):**

```bat
run.bat
```

**Git Bash / macOS / Linux:**

```bash
./run.sh
```

Or call the venv interpreter directly (avoids Git Bash `python` aliases):

```bash
./.venv/Scripts/python.exe main.py
```

Hot reload during UI work (after venv is ready):

```bash
./.venv/Scripts/python.exe -m flet run main.py
```

## Workflow

1. **Scan** — finds peripherals named `TESAIoT-*`
2. **Connect** — quiet bootstrap: `BLE_POLICY` boot (`0x05`) → PING → `SENSOR_CFG_GET` ×4 → BS_LINK
3. **Stream on** — refresh cfg, set policy `0x07` (ADV + TX_EVT + RX_REQ), show live EVT_SENSOR cards
4. **PING** / **BS_LINK** — manual smoke / link snapshot

## Layout

| Path | Role |
|------|------|
| `main.py` | Flet entry |
| `ui/app.py` | Dashboard UI |
| `bs2/wire.py` | BS2 REQ encode + frame parse |
| `bs2/chunk.py` | ATT chunk reassembly |
| `bs2/decode.py` | EVT_SENSOR + SENSOR_CFG decode |
| `bs2/session.py` | Async bleak session |

Wire logic mirrors `packages/bitstream-ble-client/examples/` and `extension/src/bitstream2/`.

## Related

- UART / provider web examples: [`../web-app/`](../web-app/) (ex01–ex08, no BLE)
- Bleak smoke scripts: [`../../packages/bitstream-ble-client/examples/`](../../packages/bitstream-ble-client/examples/)
