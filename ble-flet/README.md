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

## Workflow (Auto UX)

**Auto is ON by default.** Launch → hunt `TESAIoT-*` → connect → apply **Motion** scene → Stream on → **Live** tab.

Same on every successful connect (Auto recover, Scan, or Connect button): **Motion + Stream on** without another click.

| Event | Behavior |
|-------|----------|
| Launch | Hunt with backoff `2s → 4s → 8s` |
| Connect (any path) | LINKED → Motion preset → Stream on → LIVE |
| Unintentional drop / board reboot | Recover grace → hunt → reconnect → Motion + stream |
| **Disconnect** button | **Park** — Auto off, no hunting until **Resume auto** / Auto toggle |
| Scene buttons | Motion / Realtime / Lab Quiet — optional override while already LIVE |

Tabs:

- **Live** — bar + big-number sensor widgets (BMI270 / BMM350 / SHT40 / DPS368)
- **Link** — debug text cards + same toolbar tools
- **Log** — timestamped diagnostics; **Copy log** (snapshot + lines) or **Copy snapshot** for paste into chat

Manual tools still work (Scan, Connect, Stream on, PING, BS_LINK, Reset counts) when Auto is off.

**Update on data** (toolbar switch, default off): when ON, Live/Link sensor widgets refresh on every accepted EVT; when OFF, paints are throttled (~4 Hz) so Realtime doesn’t thrash Flet.

## Sensor cards (Link + Live stats line)

`frames evt=N  raw=M  cfg ~20 Hz  meas ~20 Hz  [OK]`

- **`#NNN`** (card badge) — latest firmware `EVT_SENSOR` counter for that sensor (+1 per transmitted frame in the current epoch)
- **evt** — monotonic accepted EVT count (drops WinRT duplicates, stale reorder, and does not double-count when firmware resets `evt_seq` after SENSOR_CFG)
- **raw** — parseable notifies before counter-dedupe (WinRT may repeat ≈2×)
- **meas** — publish rate from **counter ÷ MCU `deviceMs`** (authoritative for periodic sensors); not `evt ÷ wall clock`
- **[OK]** — periodic: `meas` within ±25% of SENSOR_CFG; hybrid: `meas` at least the cfg floor (−25%)
- **`(evt counter resets=N)`** — firmware recycled `evt_seq` (SENSOR_CFG / stream-policy); normal after preset apply

Toolbar header: `evt total` sums accepted frames across all sensors in the count window.

## Layout

| Path | Role |
|------|------|
| `main.py` | Flet entry (starts Auto hunt) |
| `ui/app.py` | Tabs, Auto FSM, toolbar, Log copy |
| `ui/live_widgets.py` | Live sensor bar widgets |
| `ui/diag_log.py` | Timestamped log lines + pasteable session snapshot |
| `bs2/connection_fsm.py` | ConnPhase labels + backoff constants |
| `bs2/wire.py` | BS2 REQ encode + frame parse |
| `bs2/chunk.py` | ATT chunk reassembly |
| `bs2/decode.py` | EVT_SENSOR + SENSOR_CFG decode |
| `bs2/scene_presets.py` | Load Motion/Realtime/Lab Quiet from JSON |
| `bs2/sensor-scene-presets.v1.json` | Shared catalog (mirrors host TypeScript) |
| `bs2/session.py` | Async bleak session (scan ranked, link-lost callback) |

Wire logic mirrors `packages/bitstream-ble-client/examples/` and `extension/src/bitstream2/`.

## Related

- UART / provider web examples: [`../web-app/`](../web-app/) (ex01–ex08, no BLE)
- Bleak smoke scripts: [`../../packages/bitstream-ble-client/examples/`](../../packages/bitstream-ble-client/examples/)
