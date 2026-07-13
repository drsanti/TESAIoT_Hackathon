# TESAIoT BLE Flet app

Desktop **BS2 over BLE** dashboard for the hackathon — replaces the experimental Web Bluetooth HTML pages.

Uses **bleak** (WinRT / BlueZ / CoreBluetooth) instead of browser Web Bluetooth, so EVT timing and UI updates are not affected by Chrome notify batching.

**Architecture** (FSM, scene presets, BLE data flow): [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

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

**Auto is ON by default.** Launch → hunt `TESAIoT-*` → connect → apply **Motion** scene → Stream on → **Live** page.

Same on every successful connect (Auto recover, Scan, or Connect button): **Motion + Stream on** without another click.

| Event | Behavior |
|-------|----------|
| Launch | Hunt with backoff `2s → 4s → 8s` |
| Connect (any path) | LINKED → Motion preset → Stream on → LIVE |
| Unintentional drop / board reboot | Recover grace → hunt → reconnect → Motion + stream |
| **Park** (Connect page) | Auto off, no hunting until **Resume auto** / Auto toggle |
| Board up **>60 s** undiscoverable | Firmware high-duty ADV timeout — reflash with ADV auto-restart fix or reboot board |
| Scene buttons | Motion / Realtime / Lab Quiet — optional override while already LIVE |

### Sidebar navigation

Collapsible left rail (Codex-style):

| Route | Content |
|-------|---------|
| **Live** | Status hero, layout presets (Grid / Stack / Focus), scene row, sensor cards |
| **Connect** | Scan, peripheral picker, Park, PING, BS_LINK, debug rows |
| **Log** | Timestamped log + copy/clear |
| **Settings** | Layout preset, focus sensor, Auto default, update-on-data, sidebar mode, per-sensor plot defaults |

- **Expanded** (~220 px): icon + label + device footer
- **Collapsed** (~56 px): icons only with tooltips

### Layout presets (app-level)

| Preset | Behavior |
|--------|----------|
| **Grid** | 2×2 sensor cards (default) |
| **Stack** | Single column, full-width cards |
| **Focus** | One enlarged card + three compact tiles |

### Plot mode (per-card)

Each sensor card header has **Bars | Lines**:

- **Bars** — progress bars + big numbers (original widgets)
- **Lines** — scrolling `LineChart` (~120 samples, throttled paint)

Modes persist in `~/.tesaiot/ble-flet-prefs.json` (Windows: `%USERPROFILE%\.tesaiot\ble-flet-prefs.json`).

**Update on data** (Settings or Live footer, default off): when ON, widgets refresh on every accepted EVT; when OFF, paints are throttled (~4 Hz).

**Connect** is disabled while Auto is hunting, connecting, or recovering (avoids WinRT races). Manual connect cancels the Auto loop first.

**Stream on** appears in the status hero when linked but policy is not yet `0x07`.

## Sensor cards (stats line)

`frames evt=N  raw=M  cfg ~20 Hz  meas ~20 Hz  [OK]`

- **`#NNN`** (card badge) — latest firmware `EVT_SENSOR` counter
- **evt** — monotonic accepted EVT count (deduped)
- **raw** — parseable notifies before dedupe
- **meas** — publish rate from counter ÷ MCU `deviceMs`
- **[OK]** — rate within SENSOR_CFG tolerance
- Live footer: `evt total` sums accepted frames in the count window

## Layout

| Path | Role |
|------|------|
| `main.py` | Flet entry (theme, min width) |
| `ui/app.py` | Session controller, routing, Auto FSM |
| `ui/app_shell.py` | Sidebar + main content shell |
| `ui/sidebar.py` | Collapsible nav rail |
| `ui/theme.py` | Dark palette + chip helpers |
| `ui/preferences.py` | JSON prefs load/save |
| `ui/status_hero.py` | Phase pill + Stream on CTA |
| `ui/live_grid.py` | Grid / stack / focus host |
| `ui/charts.py` | Ring buffers + line charts |
| `ui/live_widgets.py` | Sensor cards (bars + lines) |
| `ui/pages/` | Live, Connect, Log, Settings pages |
| `ui/diag_log.py` | Timestamped log + session snapshot |
| `bs2/session.py` | Async bleak session (connect retry, WinRT cache off) |
| `bs2/connection_fsm.py` | ConnPhase labels + backoff |

Wire logic mirrors `packages/bitstream-ble-client/examples/` and `extension/src/bitstream2/`.

## Related

- UART / provider web examples: [`../web-app/`](../web-app/) (ex01–ex08, no BLE)
- Bleak smoke scripts: [`../../packages/bitstream-ble-client/examples/`](../../packages/bitstream-ble-client/examples/)
