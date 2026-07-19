# TESAIoT BLE Flet app

Desktop **BS2 over BLE** viewer dashboard for the hackathon — replaces the experimental Web Bluetooth HTML pages.

Uses **bleak** (WinRT / BlueZ / CoreBluetooth) instead of browser Web Bluetooth, so EVT timing and UI updates are not affected by Chrome notify batching.

**Architecture** (FSM, BLE data flow): [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Sensor-node contract (central + device)

The MCU is a **sensor node**. **Flet is a receive-only central** (viewer). Bitstream Studio and `python-app` labs remain optional **configurators**.

| Role | Owner | Responsibility |
|------|-------|----------------|
| Sensor node | Firmware (CM55 + CM33 BLE) | Boot `SENSOR_CFG` defaults; sample/publish; ADV when idle; gate BLE EVT with session + CCCD + `TX_EVT` |
| Viewer central | **ble-flet** (this app) | Scan → connect → CCCD → open EVT pipe → decode → tables |
| Configurator | Studio / `python-app` labs | Optional `SENSOR_CFG_SET`, BMI270 mode, scene presets |

### Flet viewer wire sequence (Auto / Connect)

```text
Scan TESAIoT-*
→ GATT connect
→ start_notify(BS_TX)          # CCCD — firmware auto-arms TX_EVT on rising edge
→ PING (fast bootstrap liveness)
→ BLE_POLICY_SET 0x07          # backup / heal when policy not yet TX_EVT
→ decode EVT_SENSOR → Live tables
```

On reconnect: CCCD again + `go_live_on_existing_link()` (policy heal only).

**Never on Auto path:** `SENSOR_CFG_SET`, scene presets, BMI270 mode/feed SET.

Manual **Motion / Realtime / Lab Quiet** buttons on the Live page still call `apply_scene_preset` for operator experiments — same as `scripts/verify_firmware_evt_rate.py --apply-1hz`.

API: `Bs2BleSession.connect_as_viewer(device)` or `connect(bootstrap="fast")` + `go_live_on_existing_link()`.

### Configurator workflow (Studio / labs) — unchanged

```text
Connect → (optional quiet policy) → SENSOR_CFG_GET/SET as needed → POLICY 0x07 → stream
```

### Firmware notes

- Boot BLE policy **`0x05`** = ADV + RX_REQ only (no `TX_EVT`).
- Stream policy **`0x07`** = ADV + `TX_EVT` + RX_REQ.
- **`SENSOR_CFG` is not required** for the Flet viewer — boot defaults from `bitstream_bs_cfg_init_defaults` already enable the sensors shown in Live.
- CCCD rising edge auto-sets `TX_EVT` in `bitstream_bs_ble_policy.c` (see `extension/src/bitstream2/docs/BLE_BS2.md` §4.1).

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

## Verify (sensor-node matrix)

With board advertising `TESAIoT-*` (press **RESET** if WinRT connect left ADV quiet):

| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| Flet viewer, no CFG | `python scripts/verify_viewer_go_live.py` | Exit **0**; log has **no** `SENSOR_CFG_SET`; EVT count > 0 |
| Flet UI | `run.bat` / `run.sh` → Auto connect | Live tables fill; log shows `cfg=device` |
| python-app viewer | `python labs/03_gatt_ops/lab.py 8` | SUCCESS with EVT samples; no CFG writes |
| python-app configurator | `python labs/05_sensor_cfg/lab.py 12` | Focus sensor EVTs after fire-and-forget SET |
| Studio CFG | Bitstream UART → Sensor settings Apply | Device rates change; Flet reconnect shows new `meas` without Flet SET |
| Reconnect | Disconnect BLE → Auto recover | Stream resumes after CCCD + policy heal |

Configurator-only rate script (writes CFG): `scripts/verify_firmware_evt_rate.py --apply-1hz`.

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

**Auto is ON by default.** Launch → hunt `TESAIoT-*` → connect → stream from **firmware SENSOR_CFG defaults** → **Live** page.

Same on every successful connect (Auto recover, Scan, or Connect button): **viewer go-live** without `SENSOR_CFG_SET`.

| Event | Behavior |
|-------|----------|
| Launch | Hunt with backoff `2s → 4s → 8s` |
| Connect (any path) | LINKED → CCCD + stream heal → LIVE (device cfg) |
| Unintentional drop / board reboot | Recover grace → hunt → reconnect → viewer stream |
| **Park** (Connect page) | Auto off, no hunting until **Resume auto** / Auto toggle |
| Board up **>60 s** undiscoverable | Firmware high-duty ADV timeout — reflash with ADV auto-restart fix or reboot board |
| Scene buttons | Motion / Realtime / Lab Quiet — **optional** manual override (configurator path) |

### Sidebar navigation

Collapsible left rail (Codex-style):

| Route | Content |
|-------|---------|
| **Live** | Status hero, layout presets (Grid / Stack / Focus), optional scene row, sensor cards |
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
- **[OK]** — rate within SENSOR_CFG tolerance (when cfg was read or set)
- Live footer: `evt total` sums accepted frames in the count window

Without a prior `SENSOR_CFG_GET`, **cfg** may show `…` while **meas** still reflects live EVT rate from device defaults.

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
| `bs2/session.py` | Async bleak session (`connect_as_viewer`, stream heal) |
| `bs2/connection_fsm.py` | ConnPhase labels + backoff |

Wire logic mirrors `packages/bitstream-ble-client/examples/` and `extension/src/bitstream2/`.

## Related

- Teaching labs (configurator examples): [`../python-app/`](../python-app/)
- UART / provider web examples: [`../web-app/`](../web-app/) (ex01–ex08 + ex16–ex17 pots/switches, no BLE)
- Bleak smoke scripts: [`../../packages/bitstream-ble-client/examples/`](../../packages/bitstream-ble-client/examples/)
- Host BLE spec: [`../../extension/src/bitstream2/docs/BLE_BS2.md`](../../extension/src/bitstream2/docs/BLE_BS2.md)
